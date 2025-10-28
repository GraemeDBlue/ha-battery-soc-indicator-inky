import time
import requests
import sys
import os
import datetime
import random
from dotenv import load_dotenv
from PIL import Image, ImageFont, ImageDraw
# The following import can be a common point of failure.
# This check helps debug if the inky library is missing.
try:
    from inky.auto import auto
except ImportError:
    print("Error: The 'inky' library was not found.")
    print("Please install it by running 'pip install inky[phat]' or 'pip3 install inky[phat]'.")
    sys.exit(1)

# --- Configuration ---
# Load environment variables from a .env file
load_dotenv()

# Home Assistant details
HA_URL = os.getenv("HA_URL", "http://your_home_assistant_ip:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "your_long_lived_access_token")
SENSOR_ENTITY_ID = os.getenv("SENSOR_ENTITY_ID", "sensor.growatt_battery_level")

# Inky pHAT details
# The color depends on your specific Inky pHAT model (e.g., "red", "yellow", "black").
INKY_COLOUR = "black"

# Update interval in seconds (e.g., 300 for 5 minutes)
UPDATE_INTERVAL = 300

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 5  # Initial delay in seconds
MAX_RETRY_DELAY = 60     # Maximum delay in seconds
RETRY_BACKOFF_MULTIPLIER = 2  # Exponential backoff multiplier

# Connection timeout in seconds
CONNECTION_TIMEOUT = 15

# --- Function Definitions ---

def get_battery_status_with_retry():
    """
    Fetches the battery status from Home Assistant's REST API with retry logic.
    Returns the battery level as a float, or None if all retries failed.
    """
    for attempt in range(MAX_RETRIES):
        print(f"Attempting to fetch battery status from Home Assistant (attempt {attempt + 1}/{MAX_RETRIES})...")
        
        battery_level = get_battery_status()
        if battery_level is not None:
            return battery_level
        
        # If this wasn't the last attempt, wait before retrying
        if attempt < MAX_RETRIES - 1:
            # Calculate delay with exponential backoff and jitter
            delay = min(INITIAL_RETRY_DELAY * (RETRY_BACKOFF_MULTIPLIER ** attempt), MAX_RETRY_DELAY)
            # Add jitter to avoid thundering herd
            jitter = random.uniform(0.1, 0.5) * delay
            total_delay = delay + jitter
            
            print(f"Retry attempt {attempt + 1} failed. Waiting {total_delay:.1f} seconds before next attempt...")
            time.sleep(total_delay)
    
    print(f"All {MAX_RETRIES} attempts failed. Will try again in {UPDATE_INTERVAL} seconds.")
    return None

def get_battery_status():
    """
    Fetches the battery status from Home Assistant's REST API.
    """
    url = f"{HA_URL}/api/states/{SENSOR_ENTITY_ID}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "content-type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=CONNECTION_TIMEOUT)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        
        # The 'state' is a string, so we convert it to a float.
        battery_level = float(data.get("state", 0))
        print(f"Successfully fetched battery level: {battery_level}%")
        return battery_level
    except requests.exceptions.Timeout:
        print(f"Timeout error: Home Assistant did not respond within {CONNECTION_TIMEOUT} seconds")
        return None
    except requests.exceptions.ConnectionError:
        print("Connection error: Unable to connect to Home Assistant")
        return None
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error from Home Assistant: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error when contacting Home Assistant: {e}")
        return None
    except ValueError:
        print("Error: Could not convert battery level to a number. Is the sensor data correct?")
        return None
    except Exception as e:
        print(f"Unexpected error while fetching battery status: {e}")
        return None

def update_inky_display_safe(battery_level, last_updated_time, connection_status="OK"):
    """
    Safely updates the Inky pHAT display with error handling.
    Returns True if successful, False otherwise.
    """
    try:
        update_inky_display(battery_level, last_updated_time, connection_status)
        return True
    except Exception as e:
        print(f"Error updating display: {e}")
        print("Display update failed, but continuing with main loop...")
        return False

def update_inky_display(battery_level, last_updated_time, connection_status="OK"):
    """
    Updates the Inky pHAT display with a clean, readable layout.
    """
    print("Attempting to update the Inky pHAT display...")
    try:
        # Check if we are running with elevated privileges
        if 'SUDO_UID' not in os.environ:
            print("Warning: This script may need to be run with 'sudo' for hardware access.")
            print("Please try running 'sudo python3 growatt_display.py'")

        inky_display = auto()
        inky_display.set_border(inky_display.WHITE)

        img = Image.new("P", (inky_display.WIDTH, inky_display.HEIGHT))
        draw = ImageDraw.Draw(img)

        # Clear background
        draw.rectangle((0, 0, inky_display.WIDTH, inky_display.HEIGHT), fill=inky_display.WHITE)

        # Font setup
        try:
            large_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
            medium_font = ImageFont.truetype("DejaVuSans.ttf", 14)
            small_font = ImageFont.truetype("DejaVuSans.ttf", 10)
        except IOError:
            # Fallback to default fonts with different sizes
            try:
                large_font = ImageFont.truetype("DejaVuSans.ttf", 28)
                medium_font = ImageFont.truetype("DejaVuSans.ttf", 14)
                small_font = ImageFont.truetype("DejaVuSans.ttf", 10)
            except IOError:
                large_font = ImageFont.load_default()
                medium_font = ImageFont.load_default()
                small_font = ImageFont.load_default()

        # Color mapping
        color_map = {
            "black": inky_display.BLACK,
            "white": inky_display.WHITE,
            "red": inky_display.RED,
            "yellow": inky_display.YELLOW,
        }
        default_color = color_map.get(INKY_COLOUR.lower(), inky_display.BLACK)

        # Layout dimensions
        margin = 8
        current_time = datetime.datetime.now()
        
        # Determine colors and status
        if battery_level is not None:
            if battery_level < 20:
                battery_color = inky_display.RED
                status_symbol = "!"
            elif battery_level < 50:
                battery_color = color_map.get("yellow", default_color)
                status_symbol = "~"
            else:
                battery_color = default_color
                status_symbol = "+"
            
            main_text = f"{int(battery_level)}%"
            is_error = False
        else:
            battery_color = inky_display.RED
            status_symbol = "X"
            main_text = "ERROR"
            is_error = True

        # 1. TOP SECTION: Main percentage/status (y: 0-40)
        if not is_error:
            # Center the large percentage
            bbox = draw.textbbox((0, 0), main_text, font=large_font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (inky_display.WIDTH - text_width) // 2
            y = 5
            draw.text((x, y), main_text, battery_color, font=large_font)
        else:
            # Center the ERROR text
            bbox = draw.textbbox((0, 0), main_text, font=medium_font)
            text_width = bbox[2] - bbox[0]
            x = (inky_display.WIDTH - text_width) // 2
            y = 15
            draw.text((x, y), main_text, battery_color, font=medium_font)

        # 2. MIDDLE SECTION: Battery bar (y: 45-65)
        bar_y = 45
        bar_height = 16
        bar_margin = margin
        bar_width = inky_display.WIDTH - (2 * bar_margin)
        
        # Draw battery bar outline
        draw.rectangle(
            (bar_margin, bar_y, bar_margin + bar_width, bar_y + bar_height),
            outline=default_color,
            width=2
        )

        if battery_level is not None and not is_error:
            # Fill the battery bar
            fill_width = int((battery_level / 100) * (bar_width - 4))
            if fill_width > 0:
                draw.rectangle(
                    (bar_margin + 2, bar_y + 2, bar_margin + 2 + fill_width, bar_y + bar_height - 2),
                    fill=battery_color
                )
        else:
            # Show dotted pattern for error state
            for i in range(bar_margin + 4, bar_margin + bar_width - 4, 6):
                draw.rectangle((i, bar_y + 4, i + 2, bar_y + bar_height - 4), fill=default_color)

        # 3. BOTTOM SECTION: Status and time info (y: 70-104)
        bottom_y = 72
        
        # Current time (top right)
        time_text = current_time.strftime("%H:%M")
        time_bbox = draw.textbbox((0, 0), time_text, font=small_font)
        time_x = inky_display.WIDTH - (time_bbox[2] - time_bbox[0]) - margin
        draw.text((time_x, bottom_y), time_text, default_color, font=small_font)
        
        # Status symbol next to time
        symbol_x = time_x - 15
        status_color = inky_display.RED if (is_error or connection_status != "OK") else default_color
        draw.text((symbol_x, bottom_y), status_symbol, status_color, font=small_font)

        # Status text (bottom left)
        if is_error:
            status_text = "Connection Failed"
            draw.text((margin, bottom_y), status_text, inky_display.RED, font=small_font)
            
            # Show last known value if available - we need to access global variables
            try:
                # These variables should be available from the main loop
                if 'last_successful_battery_level' in globals() and last_successful_battery_level is not None and 'last_successful_update_time' in globals() and last_successful_update_time is not None:
                    last_text = f"Last: {int(last_successful_battery_level)}% at {last_successful_update_time.strftime('%H:%M')}"
                    draw.text((margin, bottom_y + 12), last_text, default_color, font=small_font)
            except:
                pass
        else:
            status_text = f"Battery Level"
            draw.text((margin, bottom_y), status_text, default_color, font=small_font)
            
            # Show last update time
            if last_updated_time:
                age = current_time - last_updated_time
                if age.total_seconds() < 60:
                    age_text = "Just now"
                elif age.total_seconds() < 3600:
                    age_text = f"{int(age.total_seconds() / 60)}m ago"
                else:
                    age_text = f"{int(age.total_seconds() / 3600)}h ago"
                
                update_text = f"Updated: {age_text}"
                draw.text((margin, bottom_y + 12), update_text, default_color, font=small_font)

        # Add connection quality indicator if needed
        try:
            if 'consecutive_failures' in globals() and consecutive_failures > 0 and not is_error:
                quality_text = f"Retries: {consecutive_failures}"
                draw.text((margin, bottom_y + 24), quality_text, inky_display.RED, font=small_font)
        except:
            pass

        inky_display.set_image(img)
        inky_display.show()
        print(f"Display updated with battery level: {battery_level}%")
        
    except Exception as e:
        print(f"A critical error occurred while updating the Inky pHAT display: {e}")
        # Don't re-raise the exception to prevent crashing the main loop
        raise

# --- Main loop ---
if __name__ == "__main__":
    print("Starting Growatt battery monitor script...")
    print(f"Update interval: {UPDATE_INTERVAL} seconds")
    print(f"Max retries: {MAX_RETRIES}")
    print(f"Connection timeout: {CONNECTION_TIMEOUT} seconds")
    
    last_successful_battery_level = None
    last_successful_update_time = None
    consecutive_failures = 0
    
    while True:
        try:
            print(f"\n--- Update cycle started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            battery_status = get_battery_status_with_retry()
            
            if battery_status is not None:
                # Successfully got battery status
                last_successful_battery_level = battery_status
                last_successful_update_time = datetime.datetime.now()
                consecutive_failures = 0
                
                # Try to update the display
                display_success = update_inky_display_safe(battery_status, last_successful_update_time, "OK")
                if display_success:
                    print("✓ Battery status fetched and display updated successfully")
                else:
                    print("✓ Battery status fetched, but display update failed")
            else:
                # Failed to get battery status
                consecutive_failures += 1
                connection_status = "FAILED"
                print(f"✗ Failed to fetch battery status (consecutive failures: {consecutive_failures})")
                
                # If we have a previous successful reading, show it with an error indicator
                if last_successful_battery_level is not None:
                    print(f"Using last known battery level: {last_successful_battery_level}%")
                    # Update display with last known value but show it's stale
                    update_inky_display_safe(last_successful_battery_level, last_successful_update_time, connection_status)
                else:
                    # No previous data, show error on display
                    print("No previous battery data available, showing error on display")
                    update_inky_display_safe(None, None, connection_status)
                
                # If we've had many consecutive failures, consider longer wait
                if consecutive_failures >= 5:
                    extended_wait = min(UPDATE_INTERVAL * 2, 1800)  # Max 30 minutes
                    print(f"Many consecutive failures detected. Extending wait to {extended_wait} seconds.")
                    time.sleep(extended_wait - UPDATE_INTERVAL)  # Subtract normal interval since we sleep below
                    
        except KeyboardInterrupt:
            print("\nReceived interrupt signal. Shutting down gracefully...")
            break
        except Exception as main_e:
            consecutive_failures += 1
            print(f"An unexpected error occurred in the main loop: {main_e}")
            print(f"Consecutive failures: {consecutive_failures}")
            print("The script will continue to run after the update interval.")
            
            # Log the full traceback for debugging
            import traceback
            print("Full traceback:")
            traceback.print_exc()

        print(f"Waiting for {UPDATE_INTERVAL} seconds...")
        time.sleep(UPDATE_INTERVAL)


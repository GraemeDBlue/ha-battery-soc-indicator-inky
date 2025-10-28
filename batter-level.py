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

def update_inky_display_safe(battery_level, last_updated_time):
    """
    Safely updates the Inky pHAT display with error handling.
    Returns True if successful, False otherwise.
    """
    try:
        update_inky_display(battery_level, last_updated_time)
        return True
    except Exception as e:
        print(f"Error updating display: {e}")
        print("Display update failed, but continuing with main loop...")
        return False

def update_inky_display(battery_level, last_updated_time):
    """
    Updates the Inky pHAT display with the current battery level, scaling
    the text to fill the screen and centering it.
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

        # A common font file on many Linux systems. You might need to install it.
        # For example, on Raspberry Pi OS: sudo apt-get install fonts-dejavu-core
        font_file = "DejaVuSans.ttf"
        
        can_size_text = False
        try:
            # First, try to load the desired font for dynamic sizing.
            font = ImageFont.truetype(font_file, 1)
            can_size_text = True
        except IOError:
            print(f"Font '{font_file}' not found. Falling back to default font.")
            font = ImageFont.load_default()
            can_size_text = False
        
        # Load a small font for the timestamp
        try:
            small_font = ImageFont.truetype(font_file, 10)
        except IOError:
            small_font = ImageFont.load_default()

        # Map the string INKY_COLOUR to the actual Inky color constant
        color_map = {
            "black": inky_display.BLACK,
            "white": inky_display.WHITE,
            "red": inky_display.RED,
            "yellow": inky_display.YELLOW,
        }
        
        # Default color is based on the INKY_COLOUR variable
        default_color = color_map.get(INKY_COLOUR.lower(), inky_display.BLACK)
        
        if battery_level is not None:
            message = f"{int(battery_level)}%"
            if battery_level < 20:
                text_color = inky_display.RED
            else:
                text_color = default_color
        else:
            message = "Error"
            text_color = inky_display.RED
            can_size_text = False

        draw.rectangle((0, 0, inky_display.WIDTH, inky_display.HEIGHT), fill=inky_display.WHITE)

        # Define dimensions based on percentages of screen height
        bar_section_height = int(inky_display.HEIGHT * 0.40)
        text_section_height = int(inky_display.HEIGHT * 0.40)
        top_margin = int(inky_display.HEIGHT * 0.05)
        middle_margin = int(inky_display.HEIGHT * 0.10)

        # Define y-coordinates for layout
        bar_y_start = top_margin
        bar_y_end = bar_y_start + bar_section_height
        text_y_start = bar_y_end + middle_margin

        # Draw the horizontal battery bar first
        if battery_level is not None:
            bar_height = bar_section_height - 10 # small buffer
            bar_margin = 10
            bar_width = inky_display.WIDTH - (2 * bar_margin)
            
            # Bar graph background
            draw.rectangle(
                (bar_margin, bar_y_start + 5, bar_margin + bar_width, bar_y_start + 5 + bar_height),
                outline=default_color,
                fill=None
            )

            # Filled bar
            fill_width = (battery_level / 100) * bar_width
            draw.rectangle(
                (bar_margin, bar_y_start + 5, bar_margin + fill_width, bar_y_start + 5 + bar_height),
                fill=text_color,
                outline=None
            )

        if can_size_text:
            # Calculate a font size that fits the text section.
            max_width = inky_display.WIDTH - 10
            max_height = text_section_height
            font_size = 1
            
            while font_size < 1000:
                font = ImageFont.truetype(font_file, font_size)
                bbox = draw.textbbox((0, 0), message, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                if text_width < max_width and text_height < max_height:
                    font_size += 1
                else:
                    font_size -= 1
                    font = ImageFont.truetype(font_file, font_size)
                    break
            
            bbox = draw.textbbox((0, 0), message, font=font)
            
            # Calculate text position to center it within its section
            x = (inky_display.WIDTH - (bbox[2] - bbox[0])) / 2
            y = text_y_start + (text_section_height - (bbox[3] - bbox[1])) / 2
            
            draw.text((x, y), message, text_color, font)

        else:
            # Fallback for when the font file is missing.
            draw.text((5, text_y_start), message, inky_display.BLACK, font)
            draw.text((5, text_y_start + 20), "Font missing.", inky_display.BLACK, font)

        # Draw the last updated timestamp at the bottom
        if last_updated_time:
            timestamp_text = f"Updated: {last_updated_time.strftime('%H:%M')}"
            ts_bbox = draw.textbbox((0,0), timestamp_text, font=small_font)
            ts_x = inky_display.WIDTH - (ts_bbox[2] - ts_bbox[0]) - 5
            ts_y = inky_display.HEIGHT - (ts_bbox[3] - ts_bbox[1]) - 15  # Adjusted for more padding
            draw.text((ts_x, ts_y), timestamp_text, inky_display.BLACK, font=small_font)


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
                display_success = update_inky_display_safe(battery_status, last_successful_update_time)
                if display_success:
                    print("✓ Battery status fetched and display updated successfully")
                else:
                    print("✓ Battery status fetched, but display update failed")
            else:
                # Failed to get battery status
                consecutive_failures += 1
                print(f"✗ Failed to fetch battery status (consecutive failures: {consecutive_failures})")
                
                # If we have a previous successful reading, show it with an error indicator
                if last_successful_battery_level is not None:
                    print(f"Using last known battery level: {last_successful_battery_level}%")
                    # Update display with last known value but show it's stale
                    update_inky_display_safe(last_successful_battery_level, last_successful_update_time)
                else:
                    # No previous data, show error on display
                    print("No previous battery data available, showing error on display")
                    update_inky_display_safe(None, None)
                
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


import time
import requests
import sys
import os
import datetime
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

# --- Function Definitions ---

def get_battery_status():
    """
    Fetches the battery status from Home Assistant's REST API.
    """
    print("Attempting to fetch battery status from Home Assistant...")
    url = f"{HA_URL}/api/states/{SENSOR_ENTITY_ID}"
    headers = {
        "Authorization": f"Bearer {HA_TOKEN}",
        "content-type": "application/json",
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        data = response.json()
        
        # The 'state' is a string, so we convert it to a float.
        battery_level = float(data.get("state", 0))
        print(f"Successfully fetched battery level: {battery_level}%")
        return battery_level
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Home Assistant: {e}")
        return None
    except ValueError:
        print("Error: Could not convert battery level to a number. Is the sensor data correct?")
        return None

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
            
            # Find the largest font size that fits
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
            
            # Get the bbox for the original, large font size
            original_bbox = draw.textbbox((0, 0), message, font=font)

            # Reduce the font size by 5%
            font_size = int(font_size * 0.95)
            font = ImageFont.truetype(font_file, font_size)
            
            # Get the new bbox for the smaller font size
            new_bbox = draw.textbbox((0, 0), message, font=font)

            # Calculate text position to align the top of the text with the original position
            x = (inky_display.WIDTH - (new_bbox[2] - new_bbox[0])) / 2
            # The y coordinate is calculated to center the original larger text
            original_y = text_y_start + (text_section_height - (original_bbox[3] - original_bbox[1])) / 2
            
            draw.text((x, original_y), message, text_color, font)

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
        # Re-raise the exception to provide a full traceback for debugging.
        raise

# --- Main loop ---
if __name__ == "__main__":
    print("Starting Growatt battery monitor script...")
    
    while True:
        try:
            battery_status = get_battery_status()
            if battery_status is not None:
                last_updated_time = datetime.datetime.now()
                update_inky_display(battery_status, last_updated_time)
        except Exception as main_e:
            print(f"An unexpected error occurred in the main loop: {main_e}")
            print("The script will continue to run after the update interval.")

        print(f"Waiting for {UPDATE_INTERVAL} seconds...")
        time.sleep(UPDATE_INTERVAL)

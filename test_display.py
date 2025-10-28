#!/usr/bin/env python3
"""
Test script for the Inky display layout
This script creates PNG images showing how the display will look in different scenarios
without requiring the actual Inky hardware.
"""

import datetime
from PIL import Image, ImageFont, ImageDraw
import os

# Mock Inky display class for testing
class MockInkyDisplay:
    def __init__(self):
        self.WIDTH = 212
        self.HEIGHT = 104
        self.BLACK = 0
        self.WHITE = 1
        self.RED = 2
        self.YELLOW = 3
    
    def set_border(self, color):
        pass
    
    def set_image(self, img):
        pass
    
    def show(self):
        pass

def create_test_display(battery_level, last_updated_time, connection_status="OK", consecutive_failures=0, filename="test_display.png"):
    """
    Creates a test image showing how the display will look
    """
    # Mock display
    inky_display = MockInkyDisplay()
    
    img = Image.new("RGB", (inky_display.WIDTH, inky_display.HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Font setup - use RGB colors for testing
    try:
        large_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
        medium_font = ImageFont.truetype("DejaVuSans.ttf", 16)
        small_font = ImageFont.truetype("DejaVuSans.ttf", 12)
    except IOError:
        # Fallback to default fonts
        try:
            large_font = ImageFont.truetype("DejaVuSans.ttf", 28)
            medium_font = ImageFont.truetype("DejaVuSans.ttf", 16)
            small_font = ImageFont.truetype("DejaVuSans.ttf", 12)
        except IOError:
            large_font = ImageFont.load_default()
            medium_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

    # Color mapping (RGB for testing)
    BLACK = (0, 0, 0)
    WHITE = (255, 255, 255)
    RED = (255, 0, 0)
    YELLOW = (255, 255, 0)
    
    default_color = BLACK

    # Layout dimensions
    margin = 8
    current_time = datetime.datetime.now()
    
    # Determine colors and status
    if battery_level is not None:
        if battery_level < 20:
            battery_color = RED
            status_symbol = "!"
        elif battery_level < 50:
            battery_color = YELLOW
            status_symbol = "~"
        else:
            battery_color = default_color
            status_symbol = "+"
        
        main_text = f"{int(battery_level)}%"
        is_error = False
    else:
        battery_color = RED
        status_symbol = "X"
        main_text = "ERROR"
        is_error = True

    # Clear background
    draw.rectangle((0, 0, inky_display.WIDTH, inky_display.HEIGHT), fill=WHITE)
    
    # Add border for visualization
    draw.rectangle((0, 0, inky_display.WIDTH-1, inky_display.HEIGHT-1), outline=BLACK, width=1)

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
    status_color = RED if (is_error or connection_status != "OK") else default_color
    draw.text((symbol_x, bottom_y), status_symbol, status_color, font=small_font)

    # Status text (bottom left)
    if is_error:
        status_text = "Connection Failed"
        draw.text((margin, bottom_y), status_text, RED, font=small_font)
        
        # Show last known value if available
        if last_updated_time:
            last_text = f"Last: 85% at {last_updated_time.strftime('%H:%M')}"
            draw.text((margin, bottom_y + 14), last_text, default_color, font=small_font)
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
            draw.text((margin, bottom_y + 14), update_text, default_color, font=small_font)

    # Add connection quality indicator if needed
    if consecutive_failures > 0 and not is_error:
        quality_text = f"Retries: {consecutive_failures}"
        draw.text((margin, bottom_y + 28), quality_text, RED, font=small_font)

    # Save the test image
    img.save(filename)
    print(f"Test display saved as: {filename}")
    return img

def main():
    """
    Create test images for different scenarios
    """
    print("Creating test display images...")
    
    # Test scenario 1: Normal high battery
    create_test_display(
        battery_level=85,
        last_updated_time=datetime.datetime.now(),
        connection_status="OK",
        filename="test_high_battery.png"
    )
    
    # Test scenario 2: Low battery
    create_test_display(
        battery_level=18,
        last_updated_time=datetime.datetime.now() - datetime.timedelta(minutes=2),
        connection_status="OK",
        filename="test_low_battery.png"
    )
    
    # Test scenario 3: Medium battery with retries
    create_test_display(
        battery_level=72,
        last_updated_time=datetime.datetime.now() - datetime.timedelta(minutes=5),
        connection_status="OK",
        consecutive_failures=2,
        filename="test_medium_battery_retries.png"
    )
    
    # Test scenario 4: Connection error
    create_test_display(
        battery_level=None,
        last_updated_time=datetime.datetime.now() - datetime.timedelta(minutes=10),
        connection_status="FAILED",
        filename="test_connection_error.png"
    )
    
    # Test scenario 5: Very old update
    create_test_display(
        battery_level=95,
        last_updated_time=datetime.datetime.now() - datetime.timedelta(hours=2),
        connection_status="OK",
        filename="test_old_update.png"
    )
    
    print("\nTest images created:")
    print("- test_high_battery.png: Normal operation (85%)")
    print("- test_low_battery.png: Low battery warning (18%)")
    print("- test_medium_battery_retries.png: Medium battery with connection retries (72%)")
    print("- test_connection_error.png: Connection failed state")
    print("- test_old_update.png: Very old update (2h ago)")
    print("\nOpen these PNG files to see how the display will look!")

if __name__ == "__main__":
    main()
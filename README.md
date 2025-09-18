# ha-battery-soc-indicator-inky

# Prerequisites
Before you run the script, you'll need to do the following:

## Install the necessary Python libraries: Open a terminal on your Raspberry Pi and run:

```
pip install requests
pip install inky[phat]
```

## Generate a Home Assistant Long-Lived Access Token:

In Home Assistant, go to your Profile.

Scroll to the bottom and click "Create Token" under Long-Lived Access Tokens.

Give it a name (e.g., "Inky pHAT Script") and copy the token. You will only see this once.

Find your sensor entity ID:

Go to Developer Tools > States in Home Assistant.

Find the entity for your Growatt battery level (e.g., sensor.growatt_battery_level). Note down the exact entity ID.

This script will run in a continuous loop, fetching the battery status every 5 minutes and updating the display.


## Cron

```
crontab -e
```

```
@reboot /usr/bin/python3 /path/to/your/script/battery-level.py >> /path/to/your/script/battery-level.log 2>&1
```

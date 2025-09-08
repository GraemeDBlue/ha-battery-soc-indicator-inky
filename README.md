# ha-battery-soc-indicator-inky


## Cron

```
crontab -e
```

```
@reboot /usr/bin/python3 /path/to/your/script/battery-level.py >> /path/to/your/script/battery-level.log 2>&1
```

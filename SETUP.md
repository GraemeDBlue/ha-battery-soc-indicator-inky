# Installation and Setup Instructions

## Improved Battery Monitor

The battery monitor script has been enhanced with the following resilience features:

### Improvements Made:

1. **Retry Logic with Exponential Backoff**
   - Up to 3 retry attempts for Home Assistant connections
   - Exponential backoff with jitter to avoid thundering herd
   - Configurable timeout and retry parameters

2. **Better Error Handling**
   - Specific error handling for different connection issues
   - Display updates are isolated from main loop failures
   - Graceful degradation when HA is unreachable

3. **State Preservation**
   - Maintains last known battery level when HA is unreachable
   - Shows stale data with timestamp rather than complete failure
   - Tracks consecutive failures for adaptive behavior

4. **Extended Wait on Multiple Failures**
   - Increases wait time when many consecutive failures occur
   - Prevents excessive retry attempts during extended outages

## Quick Setup (Recommended)

For automatic setup with correct paths and configuration:

```bash
# Make the setup script executable and run it
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Configure service files with correct paths and user
- Install the systemd service
- Make scripts executable
- Optionally set up cron jobs for monitoring
- Provide next steps for configuration

## Manual Setup Instructions

### 1. Make Scripts Executable
```bash
chmod +x watchdog.sh
chmod +x scheduled-reboot.sh
```

### 2. Install as System Service (Recommended)

```bash
# First, update the service file with your specific paths and user
# Replace YOUR_USER with your actual username (e.g., pi, ubuntu, etc.)
# Replace PROJECT_PATH with the full path to this project directory
sed -i 's/YOUR_USER/your_actual_username/g' battery-monitor.service
sed -i 's|PROJECT_PATH|/full/path/to/project|g' battery-monitor.service

# Copy service file to systemd directory
sudo cp battery-monitor.service /etc/systemd/system/

# Alternatively, manually edit the service file
sudo nano /etc/systemd/system/battery-monitor.service

# Reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable battery-monitor.service
sudo systemctl start battery-monitor.service

# Check service status
sudo systemctl status battery-monitor.service

# View logs
sudo journalctl -u battery-monitor.service -f
```

### 3. Setup Watchdog (Optional but Recommended)

The watchdog script monitors the service and restarts it if it appears stuck:

```bash
# Get the full path to the project directory
PROJECT_PATH=$(pwd)

# Add to crontab to run every 15 minutes
crontab -e

# Add this line (replace /path/to/project with your actual project path):
*/15 * * * * /path/to/project/watchdog.sh

# Or use the current directory if you're in the project folder:
# */15 * * * * $PROJECT_PATH/watchdog.sh
```

### 4. Setup Scheduled Reboot (Optional)

For extreme resilience, you can set up a weekly reboot:

```bash
# Add to crontab for weekly reboot (Sundays at 3 AM)
crontab -e

# Add this line (replace /path/to/project with your actual project path):
0 3 * * 0 /path/to/project/scheduled-reboot.sh
```

### 5. Configuration

Edit your `.env` file or the systemd service to configure:

- `HA_URL`: Your Home Assistant URL
- `HA_TOKEN`: Your Home Assistant long-lived access token
- `SENSOR_ENTITY_ID`: Your battery sensor entity ID
- `UPDATE_INTERVAL`: How often to check (in seconds)
- `MAX_RETRIES`: Number of retry attempts
- `CONNECTION_TIMEOUT`: Timeout for HA connections

### Monitoring and Troubleshooting

```bash
# View real-time logs
sudo journalctl -u battery-monitor.service -f

# Check watchdog logs
sudo tail -f /var/log/battery-monitor-watchdog.log

# Check reboot logs
sudo tail -f /var/log/scheduled-reboot.log

# Restart service manually
sudo systemctl restart battery-monitor.service

# Stop service
sudo systemctl stop battery-monitor.service
```

### Configuration Parameters

The following parameters can be adjusted in the script:

- `MAX_RETRIES = 3` - Number of retry attempts
- `INITIAL_RETRY_DELAY = 5` - Initial retry delay in seconds
- `MAX_RETRY_DELAY = 60` - Maximum retry delay in seconds
- `RETRY_BACKOFF_MULTIPLIER = 2` - Exponential backoff multiplier
- `CONNECTION_TIMEOUT = 15` - HTTP timeout in seconds
- `UPDATE_INTERVAL = 300` - Update frequency in seconds

These improvements should make your battery monitor much more resilient to network issues and Home Assistant connectivity problems.
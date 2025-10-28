#!/bin/bash

# Battery Monitor Watchdog Script
# This script checks if the battery monitor is stuck and restarts it if needed

# Configuration - Update these paths for your system
PROJECT_PATH="${PROJECT_PATH:-$(dirname "$(readlink -f "$0")")}"
LOG_FILE="/var/log/battery-monitor-watchdog.log"
PID_FILE="/tmp/battery-monitor.pid"
SCRIPT_PATH="$PROJECT_PATH/batter-level.py"
MAX_LOG_AGE_MINUTES=30  # Consider the process stuck if no log updates for this many minutes

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | sudo tee -a "$LOG_FILE"
}

# Check if the battery monitor process is running
is_process_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Process is running
        else
            # PID file exists but process is not running
            sudo rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1  # No PID file
}

# Check if the process seems to be stuck (no recent activity)
is_process_stuck() {
    # Check systemd journal for recent activity
    local recent_logs=$(sudo journalctl -u battery-monitor.service --since="$MAX_LOG_AGE_MINUTES minutes ago" --no-pager -q)
    
    if [ -z "$recent_logs" ]; then
        return 0  # No recent logs, might be stuck
    fi
    return 1  # Has recent activity
}

# Main watchdog logic
main() {
    log_message "Watchdog check started"
    
    if systemctl is-active --quiet battery-monitor.service; then
        log_message "Battery monitor service is active"
        
        if is_process_stuck; then
            log_message "Process appears stuck (no activity for $MAX_LOG_AGE_MINUTES minutes). Restarting service..."
            sudo systemctl restart battery-monitor.service
            log_message "Service restart commanded"
        else
            log_message "Process appears healthy"
        fi
    else
        log_message "Battery monitor service is not active. Starting service..."
        sudo systemctl start battery-monitor.service
        log_message "Service start commanded"
    fi
    
    log_message "Watchdog check completed"
}

# Create log directory if it doesn't exist
sudo mkdir -p "$(dirname "$LOG_FILE")"

# Run the main function
main
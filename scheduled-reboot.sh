#!/bin/bash

# Simple device reboot script for when all else fails
# This script can be run via cron to periodically reboot the device

LOG_FILE="/var/log/scheduled-reboot.log"
UPTIME_DAYS_THRESHOLD=7  # Reboot if uptime exceeds this many days

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Get system uptime in days
get_uptime_days() {
    local uptime_seconds=$(cat /proc/uptime | cut -d' ' -f1 | cut -d'.' -f1)
    local uptime_days=$((uptime_seconds / 86400))
    echo $uptime_days
}

main() {
    local uptime_days=$(get_uptime_days)
    
    log_message "Scheduled reboot check - System uptime: $uptime_days days"
    
    if [ "$uptime_days" -ge "$UPTIME_DAYS_THRESHOLD" ]; then
        log_message "System uptime ($uptime_days days) exceeds threshold ($UPTIME_DAYS_THRESHOLD days). Initiating reboot..."
        
        # Give some time for the log to be written
        sleep 2
        
        # Reboot the system
        sudo /sbin/reboot
    else
        log_message "System uptime is within acceptable range. No reboot needed."
    fi
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Run the main function
main
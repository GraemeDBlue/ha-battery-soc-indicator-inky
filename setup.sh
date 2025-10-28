#!/bin/bash

# Setup script for Home Assistant Battery Monitor
# This script configures the service files with the correct paths and user

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="$(whoami)"
SERVICE_NAME="battery-monitor.service"
SERVICE_FILE="$PROJECT_DIR/$SERVICE_NAME"
SYSTEMD_DIR="/etc/systemd/system"

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    print_info "Checking requirements..."
    
    # Check if running on systemd system
    if ! command -v systemctl &> /dev/null; then
        print_error "systemctl not found. This script requires a systemd-based system."
        exit 1
    fi
    
    # Check if main script exists
    if [ ! -f "$PROJECT_DIR/batter-level.py" ]; then
        print_error "Main script 'batter-level.py' not found in $PROJECT_DIR"
        exit 1
    fi
    
    print_info "Requirements check passed"
}

setup_service_file() {
    print_info "Setting up systemd service file..."
    
    # Create a copy of the service file with correct paths
    TEMP_SERVICE="/tmp/$SERVICE_NAME"
    cp "$SERVICE_FILE" "$TEMP_SERVICE"
    
    # Replace placeholders with actual values
    sed -i "s/YOUR_USER/$CURRENT_USER/g" "$TEMP_SERVICE"
    sed -i "s|PROJECT_PATH|$PROJECT_DIR|g" "$TEMP_SERVICE"
    
    print_info "Service file configured for user: $CURRENT_USER"
    print_info "Service file configured for path: $PROJECT_DIR"
    
    # Copy to systemd directory (requires sudo)
    print_info "Installing service file (requires sudo)..."
    sudo cp "$TEMP_SERVICE" "$SYSTEMD_DIR/$SERVICE_NAME"
    
    # Clean up temp file
    rm "$TEMP_SERVICE"
    
    print_info "Service file installed successfully"
}

setup_scripts() {
    print_info "Making scripts executable..."
    
    chmod +x "$PROJECT_DIR/watchdog.sh"
    chmod +x "$PROJECT_DIR/scheduled-reboot.sh"
    chmod +x "$PROJECT_DIR/setup.sh"
    
    print_info "Scripts are now executable"
}

enable_service() {
    print_info "Enabling and starting the battery monitor service..."
    
    sudo systemctl daemon-reload
    sudo systemctl enable battery-monitor.service
    
    # Ask user if they want to start the service now
    echo
    read -p "Do you want to start the service now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo systemctl start battery-monitor.service
        print_info "Service started"
        
        # Show service status
        echo
        print_info "Service status:"
        sudo systemctl status battery-monitor.service --no-pager
    else
        print_warning "Service not started. You can start it later with: sudo systemctl start battery-monitor.service"
    fi
}

setup_cron() {
    echo
    print_info "Cron job setup (optional)"
    echo "You can set up cron jobs for additional monitoring:"
    echo
    echo "1. Watchdog (monitors and restarts the service if stuck):"
    echo "   */15 * * * * $PROJECT_DIR/watchdog.sh"
    echo
    echo "2. Weekly reboot (extreme resilience measure):"
    echo "   0 3 * * 0 $PROJECT_DIR/scheduled-reboot.sh"
    echo
    
    read -p "Do you want to add the watchdog cron job? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        (crontab -l 2>/dev/null; echo "*/15 * * * * $PROJECT_DIR/watchdog.sh") | crontab -
        print_info "Watchdog cron job added"
    fi
    
    read -p "Do you want to add the weekly reboot cron job? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        (crontab -l 2>/dev/null; echo "0 3 * * 0 $PROJECT_DIR/scheduled-reboot.sh") | crontab -
        print_info "Weekly reboot cron job added"
    fi
}

show_next_steps() {
    echo
    print_info "Setup completed successfully!"
    echo
    echo "Next steps:"
    echo "1. Configure your .env file with Home Assistant details:"
    echo "   - HA_URL=http://your_home_assistant_ip:8123"
    echo "   - HA_TOKEN=your_long_lived_access_token"
    echo "   - SENSOR_ENTITY_ID=sensor.your_battery_sensor"
    echo
    echo "2. Monitor the service:"
    echo "   sudo journalctl -u battery-monitor.service -f"
    echo
    echo "3. Control the service:"
    echo "   sudo systemctl start battery-monitor.service"
    echo "   sudo systemctl stop battery-monitor.service"
    echo "   sudo systemctl restart battery-monitor.service"
    echo "   sudo systemctl status battery-monitor.service"
    echo
    echo "4. Check logs:"
    echo "   sudo tail -f /var/log/battery-monitor-watchdog.log"
    echo "   sudo tail -f /var/log/scheduled-reboot.log"
}

main() {
    echo "Home Assistant Battery Monitor Setup Script"
    echo "=========================================="
    echo
    
    check_requirements
    setup_scripts
    setup_service_file
    enable_service
    setup_cron
    show_next_steps
}

# Run main function
main
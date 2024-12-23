#!/bin/bash

# Configuration
PI_USER="vo603-rpi-1"  # Replace with your Pi username
PI_HOST="vo603-rpi-1.local"  # Replace with your Pi's hostname or IP
LOCAL_DIR="/Users/safierinx/playground/smarthome/GitLit/backend"  # Replace with your local directory
REMOTE_DIR="/home/vo603-rpi-1/v2"  # Replace with your Pi directory
LOG_FILE="$HOME/rsync_backup.log"

# Ensure log directory exists
touch "$LOG_FILE"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to check if Pi is reachable
check_connection() {
    if ping -c 1 "$PI_HOST" &> /dev/null; then
        return 0
    else
        log_message "ERROR: Cannot reach Raspberry Pi at $PI_HOST"
        echo "Error: Cannot reach Raspberry Pi. Check connection and hostname/IP."
        exit 1
    fi
}

# Function to perform rsync
do_rsync() {
    local direction=$1  # "to_pi" or "from_pi"

    if [ "$direction" = "to_pi" ]; then
        src="$LOCAL_DIR/"
        dst="$PI_USER@$PI_HOST:$REMOTE_DIR"
        log_message "Starting sync TO Raspberry Pi"
    else
        src="$PI_USER@$PI_HOST:$REMOTE_DIR/"
        dst="$LOCAL_DIR"
        log_message "Starting sync FROM Raspberry Pi"
    fi

    rsync -avz -W --compress-level=3 --progress --stats \
        --exclude='.DS_Store' \
        --exclude='*.tmp' \
        --exclude='.venv/' \
        --exclude='__pycache__/' \
        --exclude='*.pyc' \
        --exclude='.git/' \
        --exclude='.idea/' \
        --exclude='*.log' \
        --exclude='node_modules/' \
        "$src" "$dst" 2>&1 | tee -a "$LOG_FILE"

    if [ ${PIPESTATUS[0]} -eq 0 ]; then
        log_message "Sync completed successfully"
    else
        log_message "ERROR: Sync failed"
        echo "Error: Sync failed. Check log file at $LOG_FILE"
        exit 1
    fi
}

# Main execution
check_connection

# Check command line arguments
case "$1" in
    "to_pi")
        do_rsync "to_pi"
        ;;
    "from_pi")
        do_rsync "from_pi"
        ;;
    *)
        echo "Usage: $0 [to_pi|from_pi]"
        echo "  to_pi   - Sync local files TO Raspberry Pi"
        echo "  from_pi - Sync files FROM Raspberry Pi to local"
        exit 1
        ;;
esac
#!/bin/bash

set -u

##############################################
# Multi-Channel RPi Eco Monitoring
# Startup script with mode detection
# (Offline recording vs Online upload)
##############################################

LOGFILE_ACTIVE=""

log_msg() {
    local msg="$1"
    local stamp="[$(date '+%Y-%m-%d %H:%M:%S')]"
    if [ -n "$LOGFILE_ACTIVE" ]; then
        echo "$stamp $msg" | tee -a "$LOGFILE_ACTIVE"
    else
        echo "$stamp $msg"
    fi
}

log_msg "##############################################"
log_msg "Start of ecosystem monitoring startup script"
log_msg "##############################################"

# Get script directory for sourcing helpers
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Optional: auto-update repository on startup before running the rest of the script.
# Set AUTO_UPDATE_ON_STARTUP=0 to disable.
# Behavior is force-sync to remote branch: fetch + reset --hard + clean -fd.
# Preserves local config.json and logs/ by excluding them from git clean.
if [ "${AUTO_UPDATE_ON_STARTUP:-1}" = "1" ]; then
    if command -v git >/dev/null 2>&1 && [ -d "$SCRIPT_DIR/.git" ]; then
        log_msg "Checking for repository updates from GitHub..."

        current_branch=$(git -C "$SCRIPT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || true)
        if [ -n "$current_branch" ]; then
            if timeout 30 git -C "$SCRIPT_DIR" fetch origin "$current_branch" >/dev/null 2>&1; then
                local_hash=$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || true)
                remote_hash=$(git -C "$SCRIPT_DIR" rev-parse "origin/$current_branch" 2>/dev/null || true)

                if [ -n "$remote_hash" ]; then
                          log_msg "Force-syncing local repository to origin/$current_branch (discarding local changes, keeping config.json and logs/)..."
                    if timeout 45 git -C "$SCRIPT_DIR" reset --hard "origin/$current_branch" >/dev/null 2>&1 \
                              && timeout 30 git -C "$SCRIPT_DIR" clean -fd -e config.json -e logs/ >/dev/null 2>&1; then
                        new_hash=$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || true)
                        if [ -n "$local_hash" ] && [ -n "$new_hash" ] && [ "$local_hash" != "$new_hash" ]; then
                            log_msg "Repository updated successfully. Restarting startup script to use latest code."
                            exec bash "$0" "$@"
                        else
                            log_msg "Repository already up to date."
                        fi
                    else
                        log_msg "WARNING: Force-sync failed, continuing with current local version."
                    fi
                else
                    log_msg "WARNING: Could not resolve origin/$current_branch, skipping auto-update."
                fi
            else
                log_msg "WARNING: Could not reach GitHub for fetch (offline/timeout). Continuing without auto-update."
            fi
        else
            log_msg "WARNING: Could not determine current git branch, skipping auto-update."
        fi
    else
        log_msg "Git or repository metadata not found, skipping auto-update."
    fi
fi

log_msg "Note: /home/pi/.config/rclone is outside this git repo and is not affected by git clean."

# Source helper functions for upload mode
if [ -f "$SCRIPT_DIR/upload_mode_helper.sh" ]; then
    source "$SCRIPT_DIR/upload_mode_helper.sh"
else
    log_msg "ERROR: upload_mode_helper.sh not found!"
    exit 1
fi

# Source rclone config sync helper
if [ -f "$SCRIPT_DIR/sync_rclone_config.sh" ]; then
    source "$SCRIPT_DIR/sync_rclone_config.sh"
else
    log_msg "WARNING: sync_rclone_config.sh not found, rclone config sync will be skipped."
fi

# Disable activity LED to save power (path differs across Raspberry Pi models/images)
if [ -d /sys/class/leds/ACT ]; then
    if sudo sh -c 'echo none > /sys/class/leds/ACT/trigger' && sudo sh -c 'echo 0 > /sys/class/leds/ACT/brightness'; then
        log_msg "Activity LED disabled via /sys/class/leds/ACT"
    else
        log_msg "Failed to disable activity LED via /sys/class/leds/ACT"
    fi
elif [ -d /sys/class/leds/led0 ]; then
    if sudo sh -c 'echo none > /sys/class/leds/led0/trigger' && sudo sh -c 'echo 0 > /sys/class/leds/led0/brightness'; then
        log_msg "Activity LED disabled via /sys/class/leds/led0"
    else
        log_msg "Failed to disable activity LED via /sys/class/leds/led0"
    fi
else
    log_msg "Activity LED sysfs path not found, skipping LED disable."
fi

# One off expanding of filesystem to fill SD card
if [ ! -f fs_expanded ]; then
  # Check if root filesystem is already using most of the disk space
  ROOT_SIZE=$(df / | tail -1 | awk '{print $2}')
  DISK_SIZE=$(lsblk -b -o SIZE /dev/mmcblk0 2>/dev/null | head -2 | tail -1)
  # Convert to same units (KB)
  ROOT_SIZE_KB=$ROOT_SIZE
  DISK_SIZE_KB=$((DISK_SIZE / 1024))
  if [ -n "$DISK_SIZE" ] && [ $ROOT_SIZE_KB -gt $((DISK_SIZE_KB * 90 / 100)) ]; then
        log_msg "Filesystem already expanded, skipping..."
    touch fs_expanded
  else
        log_msg "Expanding filesystem..."
    sudo touch fs_expanded
    sudo raspi-config --expand-rootfs
    sudo reboot
  fi
fi

# Change to correct folder
cd /home/pi/multi-channel-rpi-eco-monitoring

config_file="./config.json"
sensor_type=""
if [ -f "$config_file" ]; then
    sensor_type=$(python3 -c "import json; config=json.load(open('$config_file')); print(config.get('sensor', {}).get('sensor_type', ''))" 2>/dev/null)
fi

if [ "$sensor_type" = "Sipeed7Mic" ]; then
    log_msg "Turning all 12 LEDs off on the mic array (Sipeed7Mic)"
    chmod +x ./led_off.sh
    chmod +x ./led_on.sh
    sudo bash ./led_off.sh
elif [[ "$sensor_type" == Respeaker* ]]; then
    log_msg "Sensor is $sensor_type, skipping Sipeed LED control"
else
    log_msg "Sensor type unknown or not Sipeed, skipping Sipeed LED control"
fi

# Update time from internet
log_msg "Update time from internet"
sudo bash ./update_time.sh

# Start ssh-agent so password not required
eval $(ssh-agent -s)

# Add in current date and time to log files
currentDate=$(date +"%Y-%m-%d_%H.%M")

# Check if required Python modules are available
log_msg "Checking Python dependencies..."
python3 -c "import pyaudio, numpy, RPi.GPIO, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    log_msg "WARNING: Some Python dependencies may be missing."
    log_msg "Run: sudo apt-get install python3-rpi.gpio python3-numpy python3-pyaudio"
    log_msg "Then: python3 -m pip install -r requirements.txt"
    log_msg "Continuing anyway..."
fi

# Ensure logs directory exists
logdir='logs'
if [ ! -d "$logdir" ]; then
    log_msg "Creating logs directory..."
    mkdir -p "$logdir"
fi

# Check if required files exist
log_msg "Checking required files..."
required_files="python_record.py discover_serial.py upload_mode_helper.sh"
for file in $required_files; do
    if [ ! -f "$file" ]; then
        log_msg "ERROR: Required file '$file' not found!"
        exit 1
    fi
done
log_msg "All required files found."
if [ ! -f $config_file ]; then
        log_msg "Config file '$config_file' not found!"
        log_msg "Would you like to run setup_config.py to create it? (1 for yes, 0 for no) [1]:"
        read -r response
        response=${response:-1}
        if [ "$response" = "1" ]; then
            python3 setup_config.py
        else
            log_msg "Exiting without creating config."
            exit 1
        fi
fi

# export the raspberry pi serial number to an environment variable
log_msg "Getting Raspberry Pi serial number..."
if ! PI_ID=$(python3 discover_serial.py 2>&1); then
    log_msg "ERROR: Failed to get Raspberry Pi serial number!"
    log_msg "Command output: $PI_ID"
    log_msg "Please check if discover_serial.py exists and is executable."
    exit 1
fi
export PI_ID

##############################################
# MODE DETECTION - Online vs Offline
##############################################

log_msg "Detecting operating mode based on internet connectivity..."
log_msg "Checking for internet access (this may take a minute)..."

# Check internet availability (waits up to 1 minute on each check)
if check_internet; then
    OPERATING_MODE="ONLINE"
    log_msg "Internet is AVAILABLE - Switching to UPLOAD mode"
else
    OPERATING_MODE="OFFLINE"
    log_msg "Internet NOT available - Switching to RECORDING mode"
fi

log_msg "##############################################"
log_msg "Operating Mode: $OPERATING_MODE"
log_msg "##############################################"

##############################################
# RECORDING MODE - Offline Recording
##############################################
if [ "$OPERATING_MODE" = "OFFLINE" ]; then
    
    # the file in which to store the logging from this run
    logfile_name="multi_rpi_eco_"$PI_ID"_"$currentDate".log"
    LOGFILE_ACTIVE="$logdir/$logfile_name"
    
    # Start recording script with auto-restart on failure
    log_msg "Starting RECORDING mode (offline)"
    log_msg "Command: sudo -E python3 -u python_record.py $config_file $logfile_name $logdir"
    
    restart_count=0
    while true; do
        log_msg "Attempting to start recording script (attempt $((restart_count + 1)))..."
        if sudo -E env FORCE_OFFLINE_MODE=1 python3 -u python_record.py $config_file $logfile_name $logdir; then
            log_msg "Recording script exited successfully."
            break
        else
            log_msg "ERROR: Recording script failed (attempt $((restart_count + 1)))!"
            log_msg "Will retry in 10 seconds..."
            log_msg "Check logs at $logdir/$logfile_name for details."
            sleep 10
            restart_count=$((restart_count + 1))
        fi
    done

##############################################
# UPLOAD MODE - Online Data Upload
##############################################
else
    
    logfile_name="multi_rpi_eco_upload_"$PI_ID"_"$currentDate".log"
    upload_logfile="$logdir/$logfile_name"
    LOGFILE_ACTIVE="$upload_logfile"
    
    # Ensure logs directory exists
    if [ ! -d "$logdir" ]; then
        mkdir -p "$logdir"
    fi
    
    log_msg "Starting UPLOAD mode (online)"
    
    # Get upload configuration from config.json
    log_msg "Initializing upload mode..."

    # Sync rclone.conf with Gist at startup — pull if Gist is newer, push if local is newer
    if declare -f sync_rclone_config > /dev/null 2>&1; then
        log_msg "Syncing rclone.conf with Gist (startup)..."
        sync_rclone_config "$config_file" "$upload_logfile"
    else
        log_msg "WARNING: sync_rclone_config not available, skipping."
    fi

    # Extract optional rclone settings from config.json
    rclone_remote_name=$(python3 -c "import json; config=json.load(open('$config_file')); print((config.get('rclone', {}) or {}).get('remote_name', ''))" 2>/dev/null)
    rclone_config_path=$(python3 -c "import json; config=json.load(open('$config_file')); print((config.get('rclone', {}) or {}).get('config_path', ''))" 2>/dev/null)
    rclone_target_path=$(python3 -c "import json; config=json.load(open('$config_file')); print((config.get('rclone', {}) or {}).get('target_path', ''))" 2>/dev/null)

    if [ -z "$rclone_remote_name" ]; then
        rclone_remote_name="mybox"
        log_msg "No rclone remote_name in config; using default: $rclone_remote_name"
    else
        log_msg "Using rclone remote_name from config: $rclone_remote_name"
    fi

    if [ -n "$rclone_config_path" ]; then
        log_msg "Using explicit rclone config path: $rclone_config_path"
    else
        log_msg "Using default rclone config lookup"
    fi

    if [ -z "$rclone_target_path" ]; then
        rclone_target_path="monitoring_data"
        log_msg "No rclone target_path in config; using default shared folder: $rclone_target_path"
    else
        log_msg "Using rclone target_path from config: $rclone_target_path"
    fi
    
    # Data directory to upload
    live_data_dir="/home/pi/monitoring_data/live_data"
    state_file="$live_data_dir/.rclone_state.json"
    
    # Ensure live_data directory exists
    if [ ! -d "$live_data_dir" ]; then
        log_msg "ERROR: live_data directory not found: $live_data_dir"
        exit 1
    fi
    
    log_msg "Live data directory: $live_data_dir"

    # Fallback state file path if live_data is not writable by current user
    if [ ! -w "$live_data_dir" ] || { [ -e "$state_file" ] && [ ! -w "$state_file" ]; }; then
        fallback_state_dir="/tmp/monitoring_upload_state"
        mkdir -p "$fallback_state_dir"
        state_file="$fallback_state_dir/.rclone_state_${PI_ID}.json"
        log_msg "WARNING: Cannot write state file in $live_data_dir, using fallback: $state_file"
    fi
    
    # Initialize rclone state
    init_rclone_state "$state_file" "$live_data_dir"
    
    # Scan and update state with files on disk
    update_rclone_state_from_disk "$state_file" "$live_data_dir"
    
    log_msg "Starting upload process..."
    log_msg "For graceful shutdown, press Ctrl+C or press physical shutdown button"
    
    # Main upload loop - keep retrying upload with internet monitoring
    upload_complete=0
    retry_count=0
    max_retries=999  # Essentially unlimited until user intervenes
    
    while [ $upload_complete -eq 0 ] && [ $retry_count -lt $max_retries ]; do
        
        # Check internet before attempting upload
        log_msg "Checking internet connectivity before upload..."
        
        if ! check_internet_quick; then
            log_msg "No internet available, waiting to reconnect..."
            sleep 30
            continue
        fi
        
        log_msg "Internet available, proceeding with upload..."
        
        # Run upload script with sudo so verified files can be deleted even if
        # they are owned by root (recording flow often runs with elevated perms).
        if sudo -E bash ./rclone_upload.sh "$live_data_dir" "$rclone_remote_name" "$state_file" "$upload_logfile" "$rclone_config_path" "$rclone_target_path"; then
            log_msg "Upload cycle completed successfully"
            upload_complete=1
        else
            retry_count=$((retry_count + 1))
            log_msg "Upload cycle failed, will retry... (attempt $retry_count)"
            sleep 30
        fi
    done
    
    log_msg "Upload mode finished"
    
fi

log_msg "End of startup script"

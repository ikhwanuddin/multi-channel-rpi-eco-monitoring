#!/bin/bash

set -u

##############################################
# Multi-Channel RPi Eco Monitoring
# Startup script with mode detection
# (Offline recording vs Online upload)
##############################################

printf '##############################################\n Start of ecosystem monitoring startup script\n##############################################\n'

# Get script directory for sourcing helpers
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source helper functions for upload mode
if [ -f "$SCRIPT_DIR/upload_mode_helper.sh" ]; then
    source "$SCRIPT_DIR/upload_mode_helper.sh"
else
    echo "ERROR: upload_mode_helper.sh not found!"
    exit 1
fi

# Disable activity LED to save power (path differs across Raspberry Pi models/images)
if [ -d /sys/class/leds/ACT ]; then
    if sudo sh -c 'echo none > /sys/class/leds/ACT/trigger' && sudo sh -c 'echo 0 > /sys/class/leds/ACT/brightness'; then
        echo "Activity LED disabled via /sys/class/leds/ACT"
    else
        echo "Failed to disable activity LED via /sys/class/leds/ACT"
    fi
elif [ -d /sys/class/leds/led0 ]; then
    if sudo sh -c 'echo none > /sys/class/leds/led0/trigger' && sudo sh -c 'echo 0 > /sys/class/leds/led0/brightness'; then
        echo "Activity LED disabled via /sys/class/leds/led0"
    else
        echo "Failed to disable activity LED via /sys/class/leds/led0"
    fi
else
    echo "Activity LED sysfs path not found, skipping LED disable."
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
    echo "Filesystem already expanded, skipping..."
    touch fs_expanded
  else
    echo "Expanding filesystem..."
    sudo touch fs_expanded
    sudo raspi-config --expand-rootfs
    sudo reboot
  fi
fi

# Restart udev to simulate hotplugging of 3G dongle
sudo service udev stop
sudo service udev start

# Change to correct folder
cd /home/pi/multi-channel-rpi-eco-monitoring

config_file="./config.json"
sensor_type=""
if [ -f "$config_file" ]; then
    sensor_type=$(python3 -c "import json; config=json.load(open('$config_file')); print(config.get('sensor', {}).get('sensor_type', ''))" 2>/dev/null)
fi

if [ "$sensor_type" = "Sipeed7Mic" ]; then
    printf 'Turning all 12 LEDs off on the mic array (Sipeed7Mic)\n'
    chmod +x ./led_off.sh
    chmod +x ./led_on.sh
    sudo bash ./led_off.sh
elif [[ "$sensor_type" == Respeaker* ]]; then
    printf 'Sensor is %s, skipping Sipeed LED control\n' "$sensor_type"
else
    printf 'Sensor type unknown or not Sipeed, skipping Sipeed LED control\n'
fi

# Update time from internet
printf 'Update time from internet\n'
sudo bash ./update_time.sh

# Start ssh-agent so password not required
eval $(ssh-agent -s)

# Add in current date and time to log files
currentDate=$(date +"%Y-%m-%d_%H.%M")

# Check if required Python modules are available
echo "Checking Python dependencies..."
python3 -c "import pyaudio, numpy, RPi.GPIO, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: Some Python dependencies may be missing."
    echo "Run: sudo apt-get install python3-rpi.gpio python3-numpy python3-pyaudio"
    echo "Then: python3 -m pip install -r requirements.txt"
    echo "Continuing anyway..."
fi

# Ensure logs directory exists
logdir='logs'
if [ ! -d "$logdir" ]; then
    echo "Creating logs directory..."
    mkdir -p "$logdir"
fi

# Check if required files exist
echo "Checking required files..."
required_files="python_record.py discover_serial.py upload_mode_helper.sh"
for file in $required_files; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Required file '$file' not found!"
        exit 1
    fi
done
echo "All required files found."
if [ ! -f $config_file ]; then
        echo "Config file '$config_file' not found!"
        echo "Would you like to run setup_config.py to create it? (1 for yes, 0 for no) [1]: "
        read -r response
        response=${response:-1}
        if [ "$response" = "1" ]; then
            python3 setup_config.py
        else
            echo "Exiting without creating config."
            exit 1
        fi
fi

# export the raspberry pi serial number to an environment variable
echo "Getting Raspberry Pi serial number..."
if ! PI_ID=$(python3 discover_serial.py 2>&1); then
    echo "ERROR: Failed to get Raspberry Pi serial number!"
    echo "Command output: $PI_ID"
    echo "Please check if discover_serial.py exists and is executable."
    exit 1
fi
export PI_ID

##############################################
# MODE DETECTION - Online vs Offline
##############################################

echo "Detecting operating mode based on internet connectivity..."
echo "Checking for internet access (this may take a minute)..."

# Check internet availability (waits up to 1 minute on each check)
if check_internet; then
    OPERATING_MODE="ONLINE"
    echo "Internet is AVAILABLE - Switching to UPLOAD mode"
else
    OPERATING_MODE="OFFLINE"
    echo "Internet NOT available - Switching to RECORDING mode"
fi

printf '\n##############################################\n'
printf ' Operating Mode: %s\n' "$OPERATING_MODE"
printf '##############################################\n\n'

##############################################
# RECORDING MODE - Offline Recording
##############################################
if [ "$OPERATING_MODE" = "OFFLINE" ]; then
    
    # the file in which to store the logging from this run
    logfile_name="multi_rpi_eco_"$PI_ID"_"$currentDate".log"
    
    # Start recording script with auto-restart on failure
    printf 'Starting RECORDING mode (offline)\n'
    echo "Command: sudo -E python3 -u python_record.py $config_file $logfile_name $logdir"
    echo ""
    
    restart_count=0
    while true; do
        echo "Attempting to start recording script (attempt $((restart_count + 1)))..."
        if sudo -E env FORCE_OFFLINE_MODE=1 python3 -u python_record.py $config_file $logfile_name $logdir; then
            echo "Recording script exited successfully."
            break
        else
            echo ""
            echo "ERROR: Recording script failed (attempt $((restart_count + 1)))!"
            echo "Will retry in 10 seconds..."
            echo "Check logs at $logdir/$logfile_name for details."
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
    
    # Ensure logs directory exists
    if [ ! -d "$logdir" ]; then
        mkdir -p "$logdir"
    fi
    
    printf 'Starting UPLOAD mode (online)\n' | tee -a "$upload_logfile"
    
    # Get upload configuration from config.json
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Initializing upload mode..." | tee -a "$upload_logfile"
    
    # Extract optional rclone settings from config.json
    rclone_remote_name=$(python3 -c "import json; config=json.load(open('$config_file')); print((config.get('rclone', {}) or {}).get('remote_name', ''))" 2>/dev/null)
    rclone_config_path=$(python3 -c "import json; config=json.load(open('$config_file')); print((config.get('rclone', {}) or {}).get('config_path', ''))" 2>/dev/null)

    if [ -z "$rclone_remote_name" ]; then
        rclone_remote_name="mybox"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] No rclone remote_name in config; using default: $rclone_remote_name" | tee -a "$upload_logfile"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Using rclone remote_name from config: $rclone_remote_name" | tee -a "$upload_logfile"
    fi

    if [ -n "$rclone_config_path" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Using explicit rclone config path: $rclone_config_path" | tee -a "$upload_logfile"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Using default rclone config lookup" | tee -a "$upload_logfile"
    fi
    
    # Data directory to upload
    live_data_dir="/home/pi/monitoring_data/live_data"
    state_file="$live_data_dir/.rclone_state.json"
    
    # Ensure live_data directory exists
    if [ ! -d "$live_data_dir" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: live_data directory not found: $live_data_dir" | tee -a "$upload_logfile"
        exit 1
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Live data directory: $live_data_dir" | tee -a "$upload_logfile"
    
    # Initialize rclone state
    init_rclone_state "$state_file" "$live_data_dir"
    
    # Scan and update state with files on disk
    update_rclone_state_from_disk "$state_file" "$live_data_dir"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting upload process..." | tee -a "$upload_logfile"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] For graceful shutdown, press Ctrl+C or press physical shutdown button" | tee -a "$upload_logfile"
    
    # Main upload loop - keep retrying upload with internet monitoring
    upload_complete=0
    retry_count=0
    max_retries=999  # Essentially unlimited until user intervenes
    
    while [ $upload_complete -eq 0 ] && [ $retry_count -lt $max_retries ]; do
        
        # Check internet before attempting upload
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Checking internet connectivity before upload..." | tee -a "$upload_logfile"
        
        if ! check_internet_quick; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] No internet available, waiting to reconnect..." | tee -a "$upload_logfile"
            sleep 30
            continue
        fi
        
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Internet available, proceeding with upload..." | tee -a "$upload_logfile"
        
        # Run upload script
        # Note: This will be replaced with the refactored rclone_upload.sh
        if bash ./rclone_upload.sh "$live_data_dir" "$rclone_remote_name" "$state_file" "$upload_logfile" "$rclone_config_path"; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload cycle completed successfully" | tee -a "$upload_logfile"
            upload_complete=1
        else
            retry_count=$((retry_count + 1))
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload cycle failed, will retry... (attempt $retry_count)" | tee -a "$upload_logfile"
            sleep 30
        fi
    done
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload mode finished" | tee -a "$upload_logfile"
    
fi

printf 'End of startup script\n'

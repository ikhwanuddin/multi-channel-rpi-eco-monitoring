#!/bin/bash

printf '##############################################\n Start of ecosystem monitoring startup script\n##############################################\n'

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

# On boot up, remove all the prev data (that should have been retrieved)
# so we don't run out of SD card storage space.
# NOTE: This is now controlled by config.json 'wipe_data_on_boot' setting

tries=0
max_tries=10
while true; do
	timeout 2s wget -q --spider http://google.com
	if [ $? -eq 0 ]; then
		printf "Online\n"
    break
	else
	    printf "Offline\n"
	fi
	printf 'Waiting for internet connection before continuing ('$max_tries' tries max)\n'
	sleep 2
	let tries=tries+1
	if [[ $tries -eq $max_tries ]] ;then
		break
	fi
done	

# Change to correct folder
cd /home/pi/multi-channel-rpi-eco-monitoring

printf 'Turning all 12 LEDs off on the mic array\n'
chmod +x ./led_off.sh
chmod +x ./led_on.sh
sudo bash ./led_off.sh

# Update time from internet
printf 'Update time from internet\n'
sudo bash ./update_time.sh

# Check if data wipe is enabled in config
config_file="./config.json"
if [ -f "$config_file" ]; then
    wipe_enabled=$(python3 -c "import json; config=json.load(open('$config_file')); print(config.get('sys', {}).get('wipe_data_on_boot', 0))")
    if [ "$wipe_enabled" = "1" ]; then
        printf 'Wiping old data on boot as configured\n'
        sudo rm -rf /home/pi/multi_channel_monitoring_data/live_data
        printf 'Old data wiped\n'
    else
        printf 'Data wipe disabled in config, keeping existing data\n'
    fi
else
    printf 'Config file not found, skipping data wipe\n'
fi

# Start ssh-agent so password not required
eval $(ssh-agent -s)

# Add in current date and time to log files
currentDate=$(date +"%Y-%m-%d_%H.%M")

# Check if required Python modules are available
echo "Checking Python dependencies..."
python3 -c "import pyaudio, numpy, RPi.GPIO, psutil" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "WARNING: Some Python dependencies may be missing."
    echo "Run: pip3 install pyaudio numpy RPi.GPIO psutil"
    echo "Continuing anyway..."
fi

# Ensure logs directory exists
if [ ! -d "$logdir" ]; then
    echo "Creating logs directory..."
    mkdir -p "$logdir"
fi

# Check if required files exist
echo "Checking required files..."
required_files="python_record.py discover_serial.py"
for file in $required_files; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Required file '$file' not found!"
        exit 1
    fi
done
echo "All required files found."
config_file="./config.json"
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

# the file in which to store to store the logging from this run
logdir='logs'
logfile_name="multi_rpi_eco_"$PI_ID"_"$currentDate".log"

# Start recording script with auto-restart on failure
printf 'End of startup script\n'
echo "Starting recording with auto-restart on failure"
echo "Command: sudo -E python3 -u python_record.py $config_file $logfile_name $logdir"
echo ""

restart_count=0
while true; do
    echo "Attempting to start recording script (attempt $((restart_count + 1)))..."
    if sudo -E python3 -u python_record.py $config_file $logfile_name $logdir; then
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

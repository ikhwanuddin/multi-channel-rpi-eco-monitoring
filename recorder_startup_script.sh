#!/bin/bash

set -u

##############################################
# Multi-Channel RPi Eco Monitoring
# Startup script with mode detection
# (Offline recording vs Online upload)
##############################################

LOGFILE_ACTIVE=""
LOG_MODE="boot"
LOG_PHASE="init"

log_msg() {
    local msg="$1"
    local stamp="[$(date '+%Y-%m-%d %H:%M:%S')]"
    if [ -n "$LOGFILE_ACTIVE" ]; then
        echo "$stamp [startup][mode=$LOG_MODE][phase=$LOG_PHASE] $msg" | tee -a "$LOGFILE_ACTIVE"
    else
        echo "$stamp [startup][mode=$LOG_MODE][phase=$LOG_PHASE] $msg"
    fi
}

set_log_mode() {
    LOG_MODE="${1:-unknown}"
}

set_log_phase() {
    LOG_PHASE="${1:-unknown}"
}

resolve_log_owner() {
    local owner_user="${SUDO_USER:-${USER:-$(whoami)}}"
    local owner_group
    owner_group=$(id -gn "$owner_user" 2>/dev/null || echo "$owner_user")
    echo "$owner_user:$owner_group"
}

ensure_logfile_writable() {
    local logfile_path="$1"
    local owner_spec

    [ -n "$logfile_path" ] || return 1
    owner_spec=$(resolve_log_owner)

    mkdir -p "$(dirname "$logfile_path")"

    if [ ! -e "$logfile_path" ]; then
        : > "$logfile_path" 2>/dev/null || {
            if command -v sudo >/dev/null 2>&1; then
                sudo touch "$logfile_path" 2>/dev/null || return 1
            else
                return 1
            fi
        }
    fi

    if ! chown "$owner_spec" "$logfile_path" 2>/dev/null; then
        if command -v sudo >/dev/null 2>&1; then
            sudo chown "$owner_spec" "$logfile_path" 2>/dev/null || true
        fi
    fi

    if ! chmod 664 "$logfile_path" 2>/dev/null; then
        if command -v sudo >/dev/null 2>&1; then
            sudo chmod 664 "$logfile_path" 2>/dev/null || true
        fi
    fi
}

log_ffmpeg_timeout_event() {
    local wav_file="$1"
    local timeout_secs="$2"
    local context_label="$3"
    local size_bytes="?"
    local event_id
    local feedback_log

    size_bytes=$(stat -f%z "$wav_file" 2>/dev/null || echo "?")
    event_id=$(date +"%Y%m%dT%H%M%S")

    log_msg "FFMPEG_TIMEOUT_DETECTED event_id=$event_id context=$context_label timeout_secs=$timeout_secs file=$wav_file size_bytes=$size_bytes action=kept_for_retry"
    log_msg "FEEDBACK_HINT event_id=$event_id share='Kirimkan baris FFMPEG_TIMEOUT_DETECTED + 30 baris sebelum/sesudahnya dari log upload.'"

    if [ -n "${logdir:-}" ]; then
        feedback_log="$logdir/ffmpeg_timeout_feedback.log"
        ensure_logfile_writable "$feedback_log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] event_id=$event_id context=$context_label timeout_secs=$timeout_secs file=$wav_file size_bytes=$size_bytes action=kept_for_retry" >> "$feedback_log"
    fi
}

normalize_path_for_conversion() {
    local raw_path="$1"
    # Strip accidental CR/LF so ffmpeg receives a clean single path argument.
    raw_path="${raw_path//$'\r'/}"
    raw_path="${raw_path//$'\n'/}"
    printf '%s' "$raw_path"
}

log_ffmpeg_failure_event() {
    local wav_file="$1"
    local context_label="$2"
    local exit_code="$3"
    local stderr_preview="$4"
    local size_bytes="?"
    local event_id
    local feedback_log

    size_bytes=$(stat -f%z "$wav_file" 2>/dev/null || echo "?")
    event_id=$(date +"%Y%m%dT%H%M%S")

    if [ -z "$stderr_preview" ]; then
        stderr_preview="no-stderr-captured"
    fi

    log_msg "FFMPEG_CONVERSION_FAILED event_id=$event_id context=$context_label exit_code=$exit_code file=$wav_file size_bytes=$size_bytes stderr='$stderr_preview' action=kept_for_retry"
    log_msg "FEEDBACK_HINT event_id=$event_id share='Kirimkan baris FFMPEG_CONVERSION_FAILED + 30 baris sebelum/sesudahnya dari log upload.'"

    if [ -n "${logdir:-}" ]; then
        feedback_log="$logdir/ffmpeg_timeout_feedback.log"
        ensure_logfile_writable "$feedback_log"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] event_id=$event_id context=$context_label exit_code=$exit_code file=$wav_file size_bytes=$size_bytes stderr='$stderr_preview' action=kept_for_retry" >> "$feedback_log"
    fi
}

# Execute a command and replay its stdout/stderr via log_msg to keep timestamps consistent.
run_and_log() {
    local line_prefix=""
    if [ "${1:-}" = "--prefix" ]; then
        line_prefix="${2:-}"
        shift 2
    fi

    local cmd_output
    cmd_output=$("$@" 2>&1)
    local cmd_status=$?

    if [ -n "$cmd_output" ]; then
        while IFS= read -r line; do
            if [[ "$line" =~ ^\[[0-9]{4}-[0-9]{2}-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}\][[:space:]]+(.*)$ ]]; then
                line="${BASH_REMATCH[1]}"
            fi
            [ -n "$line" ] && log_msg "$line_prefix$line"
        done <<< "$cmd_output"
    fi

    return $cmd_status
}

log_msg "##############################################"
log_msg "Start of ecosystem monitoring startup script"
log_msg "##############################################"
set_log_phase "bootstrap"

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
if ! run_and_log --prefix "[time-sync] " sudo bash ./update_time.sh; then
    log_msg "WARNING: Time update command returned non-zero status."
fi

# Start ssh-agent so password not required
if ssh_agent_env=$(ssh-agent -s 2>/dev/null); then
    eval "$ssh_agent_env" >/dev/null
    log_msg "ssh-agent started successfully"
else
    log_msg "WARNING: Failed to start ssh-agent"
fi

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

set_log_phase "detect-mode"
log_msg "Detecting operating mode based on internet connectivity..."
log_msg "Checking for internet access (this may take a minute)..."

# Check internet availability (waits up to 1 minute on each check)
if check_internet; then
    OPERATING_MODE="ONLINE"
    set_log_mode "online"
    log_msg "Internet is AVAILABLE - Switching to UPLOAD mode"
else
    OPERATING_MODE="OFFLINE"
    set_log_mode "offline"
    log_msg "Internet NOT available - Switching to RECORDING mode"
fi

log_msg "##############################################"
log_msg "Operating Mode: $OPERATING_MODE"
log_msg "##############################################"

##############################################
# RECORDING MODE - Offline Recording
##############################################
if [ "$OPERATING_MODE" = "OFFLINE" ]; then
    set_log_phase "recording"
    
    # the file in which to store the logging from this run
    logfile_name="multi_rpi_eco_"$PI_ID"_"$currentDate".log"
    LOGFILE_ACTIVE="$logdir/$logfile_name"
    ensure_logfile_writable "$LOGFILE_ACTIVE"
    
    # Start recording script with auto-restart on failure
    log_msg "Starting RECORDING mode (offline)"
    log_msg "Command: sudo -E python3 -u python_record.py $config_file $logfile_name $logdir"
    
    restart_count=0
    set_log_phase "recording-loop"
    while true; do
        log_msg "Attempting to start recording script (attempt $((restart_count + 1)))..."
        if sudo -E env FORCE_OFFLINE_MODE=1 python3 -u python_record.py $config_file $logfile_name $logdir; then
            ensure_logfile_writable "$LOGFILE_ACTIVE"
            log_msg "Recording script exited successfully."
            break
        else
            ensure_logfile_writable "$LOGFILE_ACTIVE"
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
    set_log_phase "upload-init"
    
    logfile_name="multi_rpi_eco_upload_"$PI_ID"_"$currentDate".log"
    upload_logfile="$logdir/$logfile_name"
    LOGFILE_ACTIVE="$upload_logfile"
    
    # Ensure logs directory exists
    if [ ! -d "$logdir" ]; then
        mkdir -p "$logdir"
    fi
    ensure_logfile_writable "$upload_logfile"
    
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

    # Convert pending WAV files from pre_upload_dir to FLAC before upload.
    # Only FLAC files are staged into live_data_dir.
    set_log_phase "pre-convert-flac"
    pre_upload_dir_wav="/home/pi/pre_upload_dir"

    if [ -d "$pre_upload_dir_wav" ]; then
        # Remove known bad leftovers before staging.
        while IFS= read -r -d '' error_file; do
            sudo rm -f "$error_file" 2>/dev/null || true
            log_msg "Removed error marker: $(basename "$error_file")"
        done < <(find "$pre_upload_dir_wav" -iname "*ERROR*" -print0 2>/dev/null)

          wav_count=$(find "$pre_upload_dir_wav" -name "*.wav" 2>/dev/null | wc -l)
          if [ "$wav_count" -gt 0 ]; then
              if ! command -v ffmpeg >/dev/null 2>&1; then
                  log_msg "ERROR: ffmpeg not found. Cannot convert WAV to FLAC, skipping upload staging for WAV files."
              else
                  log_msg "Found $wav_count pending WAV file(s) in $pre_upload_dir_wav, converting to FLAC..."
                  # Keep conversion timeout bounded to avoid long hangs per file.
                  ffmpeg_timeout_secs=600
                  log_msg "Using ffmpeg timeout per file: ${ffmpeg_timeout_secs}s"
                  converted_count=0
                  failed_count=0
                  while IFS= read -r -d '' wav_file; do
                      wav_file=$(normalize_path_for_conversion "$wav_file")
                      if [ ! -f "$wav_file" ]; then
                          log_msg "WARNING: Source WAV missing before conversion (pre_upload_dir): $(printf '%q' "$wav_file")"
                          failed_count=$((failed_count+1))
                          continue
                      fi
                      ffmpeg_err_file=$(mktemp "${TMPDIR:-/tmp}/ffmpeg_pre_upload_err.XXXXXX")
                      date_subdir=$(basename "$(dirname "$wav_file")")
                      dest_dir="$live_data_dir/$PI_ID/${date_subdir}"
                      sudo mkdir -p "$dest_dir"

                      base_name=$(basename "$wav_file" .wav)
                      flac_file="$dest_dir/${base_name}.flac"
                      input_size=$(stat -f%z "$wav_file" 2>/dev/null || echo "?")
                      log_msg "Converting ($((converted_count+failed_count+1))/$wav_count): $(basename "$wav_file") [$input_size bytes] -> $(basename "$flac_file")"

                      ffmpeg_input="file:$wav_file"
                      ffmpeg_output="file:$flac_file"
                      if sudo timeout "$ffmpeg_timeout_secs" ffmpeg -y -loglevel error -i "$ffmpeg_input" -c:a flac -compression_level 2 "$ffmpeg_output" 2>"$ffmpeg_err_file"; then
                          if sudo rm -f "$wav_file"; then
                              output_size=$(stat -f%z "$flac_file" 2>/dev/null || echo "?")
                              log_msg "Converted successfully: $(basename "$wav_file") -> $(basename "$flac_file") [$output_size bytes]"
                              converted_count=$((converted_count+1))
                          else
                              log_msg "WARNING: FLAC created but failed to remove source WAV: $(basename "$wav_file")"
                              converted_count=$((converted_count+1))
                          fi
                      else
                          ffmpeg_exit_code=$?
                          ffmpeg_error_preview=$(head -n 2 "$ffmpeg_err_file" 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g')
                          sudo rm -f "$flac_file" 2>/dev/null || true
                          if [ "$ffmpeg_exit_code" -eq 124 ]; then
                              log_ffmpeg_timeout_event "$wav_file" "$ffmpeg_timeout_secs" "pre_upload_dir"
                          else
                              log_ffmpeg_failure_event "$wav_file" "pre_upload_dir" "$ffmpeg_exit_code" "$ffmpeg_error_preview"
                          fi
                          failed_count=$((failed_count+1))
                      fi
                      rm -f "$ffmpeg_err_file" 2>/dev/null || true
                  done < <(find "$pre_upload_dir_wav" -name "*.wav" -print0 2>/dev/null)
                  log_msg "WAV->FLAC conversion complete: success=$converted_count, failed=$failed_count, total=$wav_count"
              fi
          else
              log_msg "No pending WAV files found in $pre_upload_dir_wav."
          fi

          # Stage any pre-existing FLAC files from pre_upload_dir into live_data_dir.
          flac_count=$(find "$pre_upload_dir_wav" -name "*.flac" 2>/dev/null | wc -l)
          if [ "$flac_count" -gt 0 ]; then
              staged_flac_count=0
              while IFS= read -r -d '' flac_src; do
                  date_subdir=$(basename "$(dirname "$flac_src")")
                  dest_dir="$live_data_dir/$PI_ID/${date_subdir}"
                  sudo mkdir -p "$dest_dir"
                  if sudo mv "$flac_src" "$dest_dir/"; then
                      staged_flac_count=$((staged_flac_count+1))
                  else
                      log_msg "WARNING: Failed to stage FLAC $(basename "$flac_src"), keeping in pre_upload_dir"
                  fi
              done < <(find "$pre_upload_dir_wav" -name "*.flac" -print0 2>/dev/null)
              log_msg "FLAC staging complete: $staged_flac_count/$flac_count file(s) moved to live_data_dir."
          fi
        fi

        # Safety pass: convert any WAV that already exists in live_data for this device.
        # This covers reruns where WAV files were staged previously.
        set_log_phase "pre-convert-live-data-wav"
        pi_live_data_dir="$live_data_dir/$PI_ID"
        if [ -d "$pi_live_data_dir" ]; then
            live_wav_count=$(find "$pi_live_data_dir" -name "*.wav" 2>/dev/null | wc -l)
            if [ "$live_wav_count" -gt 0 ]; then
                if ! command -v ffmpeg >/dev/null 2>&1; then
                    log_msg "ERROR: ffmpeg not found. Cannot convert existing WAV files in live_data."
                else
                    ffmpeg_timeout_secs=600
                    log_msg "Found $live_wav_count WAV file(s) already in live_data, converting in-place to FLAC (timeout=${ffmpeg_timeout_secs}s)..."
                    converted_live_count=0
                    failed_live_count=0
                    while IFS= read -r -d '' live_wav_file; do
                        live_wav_file=$(normalize_path_for_conversion "$live_wav_file")
                        if [ ! -f "$live_wav_file" ]; then
                            log_msg "WARNING: Source WAV missing before conversion (live_data): $(printf '%q' "$live_wav_file")"
                            failed_live_count=$((failed_live_count+1))
                            continue
                        fi
                        ffmpeg_err_file=$(mktemp "${TMPDIR:-/tmp}/ffmpeg_live_data_err.XXXXXX")
                        live_flac_file="${live_wav_file%.wav}.flac"
                        ffmpeg_input="file:$live_wav_file"
                        ffmpeg_output="file:$live_flac_file"
                        if sudo timeout "$ffmpeg_timeout_secs" ffmpeg -y -loglevel error -i "$ffmpeg_input" -c:a flac -compression_level 2 "$ffmpeg_output" 2>"$ffmpeg_err_file"; then
                            if sudo rm -f "$live_wav_file"; then
                                converted_live_count=$((converted_live_count+1))
                            else
                                log_msg "WARNING: FLAC created but failed to remove source WAV: $(basename "$live_wav_file")"
                                converted_live_count=$((converted_live_count+1))
                            fi
                        else
                            ffmpeg_exit_code=$?
                            ffmpeg_error_preview=$(head -n 2 "$ffmpeg_err_file" 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g')
                            sudo rm -f "$live_flac_file" 2>/dev/null || true
                            if [ "$ffmpeg_exit_code" -eq 124 ]; then
                                log_ffmpeg_timeout_event "$live_wav_file" "$ffmpeg_timeout_secs" "live_data"
                            else
                                log_ffmpeg_failure_event "$live_wav_file" "live_data" "$ffmpeg_exit_code" "$ffmpeg_error_preview"
                            fi
                            failed_live_count=$((failed_live_count+1))
                        fi
                        rm -f "$ffmpeg_err_file" 2>/dev/null || true
                    done < <(find "$pi_live_data_dir" -name "*.wav" -print0 2>/dev/null)
                    log_msg "Live-data WAV->FLAC conversion complete: success=$converted_live_count, failed=$failed_live_count, total=$live_wav_count"
                fi
            fi
        fi

        set_log_phase "upload-init"

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
    if ! run_and_log --prefix "[component=upload-helper] " update_rclone_state_from_disk "$state_file" "$live_data_dir"; then
        log_msg "WARNING: Failed to refresh rclone state from disk."
    fi
    
    log_msg "Starting upload process..."
    log_msg "For graceful shutdown, press Ctrl+C or press physical shutdown button"
    
    # Main upload loop - keep retrying upload with internet monitoring
    upload_complete=0
    retry_count=0
    max_retries=999  # Essentially unlimited until user intervenes
    set_log_phase "upload-loop"
    
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
            ensure_logfile_writable "$upload_logfile"
            log_msg "Upload cycle completed successfully"
            upload_complete=1
        else
            ensure_logfile_writable "$upload_logfile"
            retry_count=$((retry_count + 1))
            log_msg "Upload cycle failed, will retry... (attempt $retry_count)"
            sleep 30
        fi
    done
    
    log_msg "Upload mode finished"
    
fi

set_log_phase "shutdown"
log_msg "End of startup script"

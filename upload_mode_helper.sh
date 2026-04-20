#!/bin/bash

##############################################
# Upload Mode Helper Functions
# Handles internet detection, state tracking,
# and upload mode coordination
##############################################

# Helper function to check internet connectivity
# Pings Google and Cloudflare, retries every 60 seconds indefinitely
check_internet() {
    local max_attempts=10
    local attempt=0
    
    while true; do
        # Try Google
        if timeout 2 ping -c 1 8.8.8.8 >/dev/null 2>&1; then
            return 0
        fi
        
        # Try Cloudflare
        if timeout 2 ping -c 1 1.1.1.1 >/dev/null 2>&1; then
            return 0
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -ge $max_attempts ]; then
            # Just log, don't return failure - will retry indefinitely
            return 1
        fi
        
        sleep 1
    done
}

# Check internet quickly (for background monitoring)
# Returns 0 if online, 1 if offline, doesn't retry
check_internet_quick() {
    if timeout 2 ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        return 0
    fi
    if timeout 2 ping -c 1 1.1.1.1 >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Initialize or load rclone state JSON
# Creates new state if doesn't exist
init_rclone_state() {
    local state_file="$1"
    local live_data_dir="$2"
    
    if [ ! -f "$state_file" ]; then
        # Create new state file
        local session_start=$(date +"%Y-%m-%d_%H.%M.%S")
        cat > "$state_file" <<EOF
{
  "session_start": "$session_start",
  "last_sync": "$session_start",
  "files": {},
  "upload_stats": {
    "total_files": 0,
    "completed": 0,
    "pending": 0,
    "uploading": 0,
    "total_size_gb": 0.0
  }
}
EOF
    fi
}

# Scan live_data directory and add new files to state as "pending"
# Updates existing files if they've grown larger
update_rclone_state_from_disk() {
    local state_file="$1"
    local live_data_dir="$2"
    
    if [ ! -f "$state_file" ] || [ ! -d "$live_data_dir" ]; then
        return 1
    fi
    
    # Temporary file for updated state
    local temp_state=$(mktemp)
    
    python3 - "$state_file" "$live_data_dir" << 'PYTHON_EOF'
import json
import os
import sys
from datetime import datetime

state_file = sys.argv[1]
live_data_dir = sys.argv[2]

try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {
        "session_start": datetime.now().strftime("%Y-%m-%d_%H.%M.%S"),
        "last_sync": datetime.now().strftime("%Y-%m-%d_%H.%M.%S"),
        "files": {},
        "upload_stats": {"total_files": 0, "completed": 0, "pending": 0, "uploading": 0, "total_size_gb": 0.0}
    }

# Scan for .flac files in live_data and subdirectories
found_files = {}
total_size = 0

for root, dirs, files in os.walk(live_data_dir):
    for file in files:
        if file.endswith('.flac'):
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            total_size += file_size
            
            # Use relative path as key for consistency
            rel_path = os.path.relpath(file_path, live_data_dir)
            
            if rel_path not in state['files']:
                # New file - add as pending
                found_files[rel_path] = 'pending'
            else:
                # Keep existing status
                found_files[rel_path] = state['files'][rel_path]

# Remove files from state if they no longer exist on disk
# (but only if status is 'completed' to avoid removing still-uploading files)
for filename in list(state['files'].keys()):
    if filename not in found_files and state['files'][filename] == 'completed':
        del state['files'][filename]
    elif filename not in found_files:
        # File disappeared but wasn't completed - restore to pending if we want to track it
        # For now, just remove it
        pass

state['files'] = found_files
state['last_sync'] = datetime.now().strftime("%Y-%m-%d_%H.%M.%S")

# Update stats
state['upload_stats']['total_files'] = len(found_files)
state['upload_stats']['completed'] = sum(1 for s in found_files.values() if s == 'completed')
state['upload_stats']['pending'] = sum(1 for s in found_files.values() if s == 'pending')
state['upload_stats']['uploading'] = sum(1 for s in found_files.values() if s == 'uploading')
state['upload_stats']['total_size_gb'] = round(total_size / (1024**3), 2)

with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)

print(f"State updated: {len(found_files)} files, {state['upload_stats']['total_size_gb']}GB total")

PYTHON_EOF
}

# Update file status in rclone state
update_file_status() {
    local state_file="$1"
    local filename="$2"
    local new_status="$3"
    
    python3 - "$state_file" "$filename" "$new_status" << 'PYTHON_EOF'
import json
import sys

state_file = sys.argv[1]
filename = sys.argv[2]
new_status = sys.argv[3]

try:
    with open(state_file, 'r') as f:
        state = json.load(f)
    
    if filename in state['files']:
        state['files'][filename] = new_status
        
        # Recalculate stats
        state['upload_stats']['completed'] = sum(1 for s in state['files'].values() if s == 'completed')
        state['upload_stats']['pending'] = sum(1 for s in state['files'].values() if s == 'pending')
        state['upload_stats']['uploading'] = sum(1 for s in state['files'].values() if s == 'uploading')
        
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
except Exception as e:
    print(f"Error updating status: {e}", file=sys.stderr)

PYTHON_EOF
}

# Get all files that need uploading (pending or uploading status)
get_pending_files() {
    local state_file="$1"
    local live_data_dir="$2"
    
    python3 - "$state_file" "$live_data_dir" << 'PYTHON_EOF'
import json
import sys
import os

state_file = sys.argv[1]
live_data_dir = sys.argv[2]

try:
    with open(state_file, 'r') as f:
        state = json.load(f)
    
    for filename, status in state['files'].items():
        if status in ['pending', 'uploading']:
            file_path = os.path.join(live_data_dir, filename)
            if os.path.exists(file_path):
                print(filename)
except Exception as e:
    print(f"Error getting pending files: {e}", file=sys.stderr)

PYTHON_EOF
}

# Monitor internet connectivity during upload
# Runs in background, checks internet every 30 seconds (2x per minute)
# If internet is lost, sends SIGTERM to rclone process
monitor_internet_during_upload() {
    local rclone_pid="$1"
    local logfile="$2"
    local check_interval=30  # 2x per minute
    
    local last_online=1
    local last_offline_log=""
    
    while kill -0 "$rclone_pid" 2>/dev/null; do
        sleep $check_interval
        
        if check_internet_quick; then
            if [ $last_online -eq 0 ]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Internet connection restored" >> "$logfile"
                last_online=1
            fi
        else
            if [ $last_online -eq 1 ]; then
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] Internet connection lost! Sending SIGTERM to rclone (PID: $rclone_pid)" >> "$logfile"
                kill -TERM "$rclone_pid" 2>/dev/null || true
                last_online=0
            fi
        fi
    done
}

# Safe shutdown during upload
# Handles GPIO button for different sensor types
setup_upload_shutdown_handler() {
    local sensor_type="$1"
    local upload_pid="$2"
    local logfile="$3"
    local button_pin=26  # Default for Respeaker
    
    # For Sipeed7Mic, button is via GPIO but we assume it's already handled at OS level
    # So we just trap SIGTERM here
    trap "handle_upload_shutdown $upload_pid '$logfile'" SIGTERM SIGINT
}

handle_upload_shutdown() {
    local upload_pid="$1"
    local logfile="$2"
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Shutdown signal received during upload mode" >> "$logfile"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Terminating upload gracefully..." >> "$logfile"
    
    # Send SIGTERM to upload process to let it cleanup
    if kill -0 "$upload_pid" 2>/dev/null; then
        kill -TERM "$upload_pid"
        # Wait max 30 seconds for process to terminate
        local wait_count=0
        while kill -0 "$upload_pid" 2>/dev/null && [ $wait_count -lt 30 ]; do
            sleep 1
            wait_count=$((wait_count + 1))
        done
        
        # Force kill if still running
        if kill -0 "$upload_pid" 2>/dev/null; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] Force killing upload process" >> "$logfile"
            kill -9 "$upload_pid" 2>/dev/null || true
        fi
    fi
    
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Upload mode ended, system can now shutdown or switch mode" >> "$logfile"
}

export -f check_internet
export -f check_internet_quick
export -f init_rclone_state
export -f update_rclone_state_from_disk
export -f update_file_status
export -f get_pending_files
export -f monitor_internet_during_upload
export -f setup_upload_shutdown_handler
export -f handle_upload_shutdown

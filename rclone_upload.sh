#!/bin/bash

##############################################
# Rclone Upload Script with State Tracking
# Uses rclone copy (not move) to safely track uploads
# Deletes files only after verification
##############################################

# Usage:
#   ./rclone_upload.sh <data_dir> [remote_name] [state_file] [logfile]

set -u

data_dir="$1"
remote_name="${2:-mybox}"
state_file="${3:-.rclone_state.json}"
logfile="${4:-/dev/stdout}"

# Function to log messages
log_msg() {
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $msg" | tee -a "$logfile"
}

log_msg "=== Starting rclone upload ==="
log_msg "Data directory: $data_dir"
log_msg "Remote: $remote_name"
log_msg "State file: $state_file"

if ! command -v rclone >/dev/null 2>&1; then
    log_msg "ERROR: rclone binary not found in PATH"
    exit 127
fi

if [ ! -d "$data_dir" ]; then
    log_msg "ERROR: Source directory does not exist: $data_dir"
    exit 1
fi

# Get data folder name for remote path
data_top_folder_name=$(basename "$data_dir")

# Determine remote target
remote_target="${remote_name}:${data_top_folder_name}"
log_msg "Remote target: $remote_target"

# Initialize state file if it doesn't exist
if [ ! -f "$state_file" ]; then
    python3 << 'PYTHON_INIT'
import json
import os
state_file = os.environ.get('STATE_FILE', '.rclone_state.json')
state = {
    "session_start": "",
    "last_sync": "",
    "files": {},
    "upload_stats": {"total_files": 0, "completed": 0, "pending": 0, "uploading": 0, "total_size_gb": 0.0}
}
with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)
PYTHON_INIT
fi

# Scan local files and mark as uploading before starting rclone
python3 << 'PYTHON_SCAN'
import json
import os
import sys
from datetime import datetime

data_dir = sys.argv[1]
state_file = sys.argv[2]

try:
    with open(state_file, 'r') as f:
        state = json.load(f)
except:
    state = {"session_start": "", "last_sync": "", "files": {}, "upload_stats": {"total_files": 0, "completed": 0, "pending": 0, "uploading": 0, "total_size_gb": 0.0}}

found_files = {}
total_size = 0

# Scan for .flac files
for root, dirs, files in os.walk(data_dir):
    for file in files:
        if file.endswith('.flac'):
            file_path = os.path.join(root, file)
            file_size = os.path.getsize(file_path)
            total_size += file_size
            rel_path = os.path.relpath(file_path, data_dir)
            
            if rel_path in state['files']:
                found_files[rel_path] = state['files'][rel_path]
            else:
                found_files[rel_path] = 'pending'

state['files'] = found_files
state['last_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
state['upload_stats']['total_files'] = len(found_files)
state['upload_stats']['completed'] = sum(1 for s in found_files.values() if s == 'completed')
state['upload_stats']['pending'] = sum(1 for s in found_files.values() if s == 'pending')
state['upload_stats']['uploading'] = sum(1 for s in found_files.values() if s == 'uploading')
state['upload_stats']['total_size_gb'] = round(total_size / (1024**3), 2)

with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)

print(json.dumps(state['upload_stats']))
PYTHON_SCAN \
    "$data_dir" "$state_file" > /tmp/upload_stats.json 2>/dev/null || true

# Read and log the stats
if [ -f /tmp/upload_stats.json ]; then
    stats=$(cat /tmp/upload_stats.json)
    log_msg "Upload stats: $stats"
fi

# Mark all pending/uploading files as 'uploading'
python3 << 'PYTHON_MARK'
import json
import sys

state_file = sys.argv[1]

with open(state_file, 'r') as f:
    state = json.load(f)

for filename in state['files']:
    if state['files'][filename] in ['pending', 'uploading']:
        state['files'][filename] = 'uploading'

state['upload_stats']['uploading'] = len([s for s in state['files'].values() if s == 'uploading'])
state['upload_stats']['pending'] = 0

with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)
PYTHON_MARK \
    "$state_file"

log_msg "Marked files as 'uploading' in state"

# Run rclone copy (not move!) with error handling
log_msg "Starting rclone copy process..."
rclone_logfile="/tmp/rclone_$(date +%s).log"

# Use copy instead of move for safety
if rclone copy "$data_dir" "$remote_target" \
    --delete-empty-src-dirs \
    --log-level INFO \
    --log-file "$rclone_logfile" \
    2>&1 | tee -a "$logfile"; then
    
    rclone_exit_code=0
    log_msg "Rclone copy completed with exit code 0"
else
    rclone_exit_code=$?
    log_msg "Rclone copy failed with exit code $rclone_exit_code"
fi

# Append rclone logs to main logfile
if [ -f "$rclone_logfile" ]; then
    log_msg "--- Rclone detailed logs ---"
    cat "$rclone_logfile" >> "$logfile"
    log_msg "--- End rclone logs ---"
    rm -f "$rclone_logfile"
fi

# If rclone succeeded, verify files on remote and mark as completed
if [ $rclone_exit_code -eq 0 ]; then
    log_msg "Verifying uploaded files on remote..."
    
    python3 << 'PYTHON_VERIFY'
import json
import os
import subprocess
import sys
from datetime import datetime

data_dir = sys.argv[1]
remote_target = sys.argv[2]
state_file = sys.argv[3]
logfile = sys.argv[4]

def log_msg(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")
    with open(logfile, 'a') as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

try:
    with open(state_file, 'r') as f:
        state = json.load(f)
    
    # List files on remote
    remote_list = subprocess.check_output(
        ['rclone', 'lsf', remote_target, '--recursive'],
        universal_newlines=True,
        stderr=subprocess.DEVNULL
    ).strip().split('\n')
    
    remote_set = set(remote_list) if remote_list else set()
    log_msg(f"Found {len(remote_set)} files on remote")
    
    # Mark local files as completed if they exist on remote
    deleted_count = 0
    for filename in list(state['files'].keys()):
        if state['files'][filename] == 'uploading':
            # Check if file exists on remote (exact match)
            if filename in remote_set:
                state['files'][filename] = 'completed'
                
                # Delete local file after verification
                local_path = os.path.join(data_dir, filename)
                if os.path.exists(local_path):
                    try:
                        os.remove(local_path)
                        deleted_count += 1
                        log_msg(f"Deleted verified uploaded file: {filename}")
                    except Exception as e:
                        log_msg(f"ERROR deleting {filename}: {e}")
            else:
                log_msg(f"File not found on remote (yet): {filename} - keeping local copy")
    
    # Update stats
    state['upload_stats']['completed'] = sum(1 for s in state['files'].values() if s == 'completed')
    state['upload_stats']['uploading'] = sum(1 for s in state['files'].values() if s == 'uploading')
    state['upload_stats']['pending'] = sum(1 for s in state['files'].values() if s == 'pending')
    state['last_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    
    log_msg(f"Upload verification complete: {deleted_count} files deleted after verification")
    log_msg(f"Upload stats after verify: completed={state['upload_stats']['completed']}, pending={state['upload_stats']['pending']}, uploading={state['upload_stats']['uploading']}")
    
except Exception as e:
    log_msg(f"ERROR during verification: {e}")
    sys.exit(1)

PYTHON_VERIFY \
        "$data_dir" "$remote_target" "$state_file" "$logfile"
    
    if [ $? -eq 0 ]; then
        log_msg "Rclone upload cycle completed successfully"
        exit 0
    else
        log_msg "Verification failed, files kept for retry"
        exit 1
    fi
else
    log_msg "Rclone copy failed, files kept for retry"
    exit $rclone_exit_code
fi

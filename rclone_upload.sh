#!/bin/bash

##############################################
# Rclone Upload Script with State Tracking
# Uses rclone copy (not move) to safely track uploads
# Deletes files only after verification
##############################################

# Usage:
#   ./rclone_upload.sh <data_dir> [remote_name] [state_file] [logfile] [config_path] [target_path]

set -u
set -o pipefail

data_dir="$1"
remote_name="${2:-mybox}"
state_file="${3:-.rclone_state.json}"
logfile="${4:-/dev/stdout}"
config_path="${5:-}"
target_path="${6:-}"
UPLOAD_PHASE="init"
UPLOAD_LOG_LAST_MINUTE=""
UPLOAD_LOG_TS_PREFIX=""
upload_stats_tmp=$(mktemp "${TMPDIR:-/tmp}/upload_stats.XXXXXX") || upload_stats_tmp=""
rclone_logfile=""

cleanup_temp_files() {
    [ -n "$upload_stats_tmp" ] && [ -e "$upload_stats_tmp" ] && rm -f "$upload_stats_tmp"
    [ -n "$rclone_logfile" ] && [ -e "$rclone_logfile" ] && rm -f "$rclone_logfile"
}

trap cleanup_temp_files EXIT

# Source rclone config sync helper (path relative to this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
if [ -f "$SCRIPT_DIR/sync_rclone_config.sh" ]; then
    source "$SCRIPT_DIR/sync_rclone_config.sh"
fi

# Function to log messages
update_upload_log_minute_prefix() {
    local current_minute
    current_minute="$(date '+%Y-%m-%d %H:%M')"
    if [ "$current_minute" != "$UPLOAD_LOG_LAST_MINUTE" ]; then
        UPLOAD_LOG_LAST_MINUTE="$current_minute"
        UPLOAD_LOG_TS_PREFIX="[$current_minute] "
    else
        UPLOAD_LOG_TS_PREFIX=""
    fi
}

log_msg() {
    local msg="$1"
    update_upload_log_minute_prefix
    echo "${UPLOAD_LOG_TS_PREFIX}[upload][phase=$UPLOAD_PHASE] $msg" | tee -a "$logfile"
}

set_upload_phase() {
    UPLOAD_PHASE="${1:-unknown}"
}

# Stream stdin to log_msg with an optional message prefix.
log_stream() {
    local prefix="${1:-}"
    while IFS= read -r line; do
        if [ -n "$prefix" ]; then
            log_msg "$prefix$line"
        else
            log_msg "$line"
        fi
    done
}

log_msg "=== Starting rclone upload ==="
log_msg "Data directory: $data_dir"
log_msg "Remote: $remote_name"
log_msg "State file: $state_file"
if [ -n "$config_path" ]; then
    log_msg "Rclone config path: $config_path"
else
    log_msg "Rclone config path: default lookup"
fi

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
if [ -n "$target_path" ]; then
    remote_target="${remote_name}:${target_path}"
    log_msg "Using explicit remote target path: $target_path"
else
    remote_target="${remote_name}:${data_top_folder_name}"
    log_msg "Using default remote target path from data dir name: $data_top_folder_name"
fi
log_msg "Remote target: $remote_target"

# Initialize state and scan files
set_upload_phase "scan-mark"
log_msg "Scanning and marking files..."

# Use the new state manager to replace the three separate Python calls
manager_output=$(python3 "$SCRIPT_DIR/state_manager.py" init-scan-mark "$data_dir" "$state_file")
stats=$(echo "$manager_output" | jq -c '.stats')
files_to_upload=$(echo "$manager_output" | jq -r '.files_to_upload[]')

log_msg "Upload stats: $stats"
log_msg "Marked $(echo "$files_to_upload" | wc -l) files as 'uploading'"

# Run rclone copy (not move!) with error handling
set_upload_phase "rclone-copy"
log_msg "Starting rclone copy process..."
rclone_logfile=$(mktemp "${TMPDIR:-/tmp}/rclone.XXXXXX.log") || rclone_logfile="${TMPDIR:-/tmp}/rclone_$(date +%s).log"

# Define rclone args
rclone_args=(
    copy "$data_dir" "$remote_target"
    --log-level INFO
    --stats 10s
    --stats-one-line
    --files-from -  # Read from stdin
)
if [ -n "$config_path" ]; then
    rclone_args+=(--config "$config_path")
fi

log_msg "Starting live rclone stream..."
# Feed the file list to rclone
if printf '%s\n' "$files_to_upload" | rclone "${rclone_args[@]}" 2>&1 | tee -a "$rclone_logfile" | log_stream "[component=rclone] "; then
    rclone_exit_code=0
    log_msg "Rclone copy completed with exit code 0"
else
    rclone_exit_code=$?
    log_msg "Rclone copy failed with exit code $rclone_exit_code"
fi

# If rclone succeeded, verify files on remote and mark as completed
if [ $rclone_exit_code -eq 0 ]; then
    set_upload_phase "verify"
    log_msg "Verifying uploaded files on remote..."

    python3 - "$data_dir" "$remote_target" "$state_file" "$logfile" "$config_path" << 'PYTHON_VERIFY'
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime

data_dir = sys.argv[1]
remote_target = sys.argv[2]
state_file = sys.argv[3]
logfile = sys.argv[4]
config_path = sys.argv[5]
last_minute = None

def log_msg(msg):
    global last_minute
    now = datetime.now()
    minute_stamp = now.strftime('%Y-%m-%d %H:%M')
    if minute_stamp != last_minute:
        prefix = f"[{minute_stamp}] "
        last_minute = minute_stamp
    else:
        prefix = ""
    line = f"{prefix}[upload][phase=verify][component=verify] {msg}"
    print(line, flush=True)
    with open(logfile, 'a') as f:
        f.write(f"{line}\n")

try:
    with open(state_file, 'r') as f:
        state = json.load(f)

    uploading_files = {k for k, v in state['files'].items() if v == 'uploading'}
    if not uploading_files:
        log_msg("No files to verify.")
        sys.exit(0)

    # Use rclone check --one-way --missing-on-dst to find files not yet on remote.
    # rclone streams live progress stats every 10s natively — no silent waiting.
    missing_tmp = tempfile.mktemp(suffix='_missing.txt')
    check_cmd = [
        'rclone', 'check', data_dir, remote_target,
        '--one-way',
        '--missing-on-dst', missing_tmp,
        '--log-level', 'INFO',
        '--stats', '10s',
        # Avoid one-line carriage-return stats so piped logging does not look frozen.
        '--filter', '+ **.flac',
        '--filter', '+ **.log',
        '--filter', '- **',
    ]
    if config_path:
        check_cmd.extend(['--config', config_path])

    log_msg(f"Running rclone check for {len(uploading_files)} files (live stats every 10s)...")
    # Merge stderr into stdout so stats lines are captured and forwarded to log
    proc = subprocess.Popen(
        check_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            log_msg(f"  [rclone check] {line}")
    proc.wait()
    check_exit = proc.returncode
    # Exit code 1 = some files missing/different (normal if any failed); >1 = rclone error
    if check_exit > 1:
        log_msg(f"WARNING: rclone check exited with code {check_exit}, results may be incomplete")

    # Read list of files confirmed missing on remote
    missing_on_remote = set()
    if os.path.exists(missing_tmp):
        with open(missing_tmp) as f:
            for line in f:
                line = line.strip()
                if line:
                    missing_on_remote.add(line)
        os.remove(missing_tmp)

    log_msg(f"rclone check done: {len(missing_on_remote)} files still missing on remote")

    # Files not in missing_on_remote are confirmed present on remote — safe to delete locally
    deleted_count = 0
    for filename in list(state['files'].keys()):
        if state['files'][filename] == 'uploading':
            if filename not in missing_on_remote:
                state['files'][filename] = 'completed'
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

PYTHON_VERIFY

    if [ $? -eq 0 ]; then
        set_upload_phase "finalize"
        log_msg "Rclone upload cycle completed successfully"
        # Push rclone.conf to Gist — token was likely refreshed during this run
        _push_rclone_config_to_gist
        exit 0
    else
        set_upload_phase "error"
        log_msg "Verification failed, files kept for retry"
        # Still push conf — token refresh happens before transfer, not only on success
        _push_rclone_config_to_gist
        exit 1
    fi
else
    set_upload_phase "error"
    log_msg "Rclone copy failed, files kept for retry"
    # Still push conf — rclone may have refreshed the token before the transfer failed
    _push_rclone_config_to_gist
    exit $rclone_exit_code
fi

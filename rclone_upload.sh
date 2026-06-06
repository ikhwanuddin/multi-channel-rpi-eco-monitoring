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

# Helper for rclone copy with retry logic
rclone_copy_with_retry() {
    local max_attempts=3
    local attempt=1
    local delay=10

    while [ $attempt -le $max_attempts ]; do
        if printf '%s\n' "$files_to_upload" | rclone "${rclone_args[@]}" 2>&1 | tee -a "$rclone_logfile" | log_stream "[component=rclone] "; then
            return 0
        fi

        local exit_code=$?
        # Retry on transient network/rclone errors (codes 3-9)
        if [[ "$exit_code" =~ ^[3-9]$ ]] && [ $attempt -lt $max_attempts ]; then
            log_msg "Rclone copy failed (exit $exit_code), retrying in ${delay}s (attempt $attempt/$max_attempts)..."
            sleep $delay
            ((attempt++))
            delay=$((delay * 2)) # Exponential backoff
        else
            return $exit_code
        fi
    done
    return 1
}

log_msg "Starting live rclone stream..."
if rclone_copy_with_retry; then
    rclone_exit_code=0
    log_msg "Rclone copy completed with exit code 0"
else
    rclone_exit_code=$?
    log_msg "Rclone copy failed after retries with exit code $rclone_exit_code"
fi

# If rclone succeeded, verify files on remote and mark as completed
if [ $rclone_exit_code -eq 0 ]; then
    set_upload_phase "verify"
    log_msg "Verifying uploaded files on remote..."

    verify_output=$(python3 "$SCRIPT_DIR/state_manager.py" verify-finalize "$data_dir" "$state_file" --remote-target "$remote_target" --config-path "$config_path")
    deleted_count=$(echo "$verify_output" | jq -r '.deleted // 0')
    stats=$(echo "$verify_output" | jq -c '.stats')

    log_msg "Upload verification complete: $deleted_count files deleted after verification"
    log_msg "Upload stats after verify: $stats"

    set_upload_phase "finalize"
    log_msg "Rclone upload cycle completed successfully"
    # Push rclone.conf to Gist — token was likely refreshed during this run
    _push_rclone_config_to_gist
    exit 0
else
    set_upload_phase "error"
    log_msg "Rclone copy failed, files kept for retry"
    # Still push conf — rclone may have refreshed the token before the transfer failed
    _push_rclone_config_to_gist
    exit $rclone_exit_code
fi

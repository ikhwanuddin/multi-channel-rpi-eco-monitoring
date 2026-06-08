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
UPLOAD_LOG_TS_NEWLINE=""
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
        UPLOAD_LOG_TS_NEWLINE="[$current_minute]"
    else
        UPLOAD_LOG_TS_NEWLINE=""
    fi
}

short_path() {
    local p="$1"
    local max_len="${2:-72}"
    local base
    base="$(basename "$p")"

    if [ ${#p} -le "$max_len" ]; then
        printf '%s' "$p"
    else
        printf '.../%s' "$base"
    fi
}

format_rclone_line() {
    local line="$1"

    # Drop rclone timestamp/level prefix to keep terminal concise.
    line="$(echo "$line" | sed -E 's/^[0-9]{4}\/[0-9]{2}\/[0-9]{2}[[:space:]]+[0-9]{2}:[0-9]{2}:[0-9]{2}[[:space:]]+[A-Z]+[[:space:]]+:[[:space:]]*//')"

    # Compact one-line stats output.
    if [[ "$line" == *"xfr#"* ]]; then
        line="$(echo "$line" | sed -E 's/^[[:space:]]+//')"
        printf 'stats %s' "$line"
        return
    fi

    # Shorten long file paths in transfer lines.
    if [[ "$line" =~ ^(.+):[[:space:]]+(.+)$ ]]; then
        local lhs="${BASH_REMATCH[1]}"
        local rhs="${BASH_REMATCH[2]}"
        if [[ "$lhs" == *"/"* ]]; then
            printf '%s: %s' "$(basename "$lhs")" "$rhs"
            return
        fi
    fi

    printf '%s' "$line"
}

log_msg() {
    local msg="$1"
    local prefix="[upload:$UPLOAD_PHASE]"
    local suppress_ts_newline="${2:-0}"
    update_upload_log_minute_prefix

    if [ "$suppress_ts_newline" = "0" ] && [ -n "$UPLOAD_LOG_TS_NEWLINE" ]; then
        printf '\n%s\n' "$UPLOAD_LOG_TS_NEWLINE" | tee -a "$logfile"
    fi
    echo "$prefix $msg" | tee -a "$logfile"
}

log_stats_block() {
    local label="$1"
    local stats_json="$2"

    local total completed pending uploading size_gb
    total="$(echo "$stats_json" | jq -r '.total_files // 0' 2>/dev/null || echo 0)"
    completed="$(echo "$stats_json" | jq -r '.completed // 0' 2>/dev/null || echo 0)"
    pending="$(echo "$stats_json" | jq -r '.pending // 0' 2>/dev/null || echo 0)"
    uploading="$(echo "$stats_json" | jq -r '.uploading // 0' 2>/dev/null || echo 0)"
    size_gb="$(echo "$stats_json" | jq -r '.total_size_gb // 0' 2>/dev/null || echo 0)"

    log_msg "$label"
    log_msg "  total files : $total"
    log_msg "  uploading   : $uploading"
    log_msg "  pending     : $pending"
    log_msg "  completed   : $completed"
    log_msg "  total size  : ${size_gb} GB"
}

set_upload_phase() {
    UPLOAD_PHASE="${1:-unknown}"
}

# Stream stdin to log_msg with an optional message prefix.
# Pass mode="rclone" to apply compact rclone formatting without adding extra prefix text.
log_stream() {
    local prefix="${1:-}"
    local mode="${2:-}"
    local line
    while IFS= read -r line; do
        if [ "$mode" = "rclone" ]; then
            line="$(format_rclone_line "$line")"
        fi
        [ -z "$line" ] && continue

        if [ "$mode" = "rclone" ] && [[ "$line" == stats\ * ]]; then
            log_msg "$line" 1
        elif [ -n "$prefix" ]; then
            log_msg "$prefix$line"
        else
            log_msg "$line"
        fi
    done
}

log_msg "=== Starting rclone upload ==="
log_msg "Data dir: $(short_path "$data_dir")"
log_msg "Remote: $remote_name"
log_msg "State file: $(short_path "$state_file")"
if [ -n "$config_path" ]; then
    log_msg "Rclone config: $(short_path "$config_path")"
else
    log_msg "Rclone config: default lookup"
fi

if ! command -v jq >/dev/null 2>&1; then
    log_msg "ERROR: jq binary not found. Please install with 'sudo apt install jq'"
    exit 127
fi

if ! command -v rclone >/dev/null 2>&1; then
    log_msg "ERROR: rclone binary not found in PATH"
    exit 127
fi

if [ ! -d "$data_dir" ]; then
    log_msg "ERROR: Source directory does not exist"
    log_msg "  path: $(short_path "$data_dir")"
    exit 1
fi

    # Get data folder name for remote path
    # Custom structure: Files/monitoring_data/<RPiID>/<date>
    # data_dir is expected to be: .../live_data/<RPiID>

    rpi_id=$(basename "$data_dir")
    current_date=$(date '+%Y-%m-%d')
    remote_target_path="monitoring_data/${rpi_id}/${current_date}"

    remote_target="${remote_name}:${remote_target_path}"
    log_msg "Remote target path: $remote_target_path"
    log_msg "Remote target: $remote_target"

# Initialize state and scan files
set_upload_phase "scan-mark"
log_msg "Pre-verifying existing files on remote..."
python3 "$SCRIPT_DIR/state_manager.py" pre-verify "$data_dir" "$state_file" --remote-target "$remote_target" --config-path "$config_path"

log_msg "Scanning and marking new files..."

# Use the new state manager to replace the three separate Python calls
manager_output=$(python3 "$SCRIPT_DIR/state_manager.py" init-scan-mark "$data_dir" "$state_file")
stats=$(echo "$manager_output" | jq -c '.stats')
files_to_upload=$(echo "$manager_output" | jq -r '.files_to_upload[]')

log_stats_block "Upload stats:" "$stats"
log_msg "Marked $(echo "$files_to_upload" | wc -l) files as 'uploading'"

# Run rclone copy (not move!) with error handling
set_upload_phase "rclone-copy"
log_msg "Starting rclone copy process..."
rclone_logfile=$(mktemp "${TMPDIR:-/tmp}/rclone.XXXXXX.log") || rclone_logfile="${TMPDIR:-/tmp}/rclone_$(date +%s).log"

# Define rclone args
rclone_args=(
    copy "$data_dir" "$remote_target"
    --log-level INFO
    --stats 30s
    --stats-one-line
    --files-from -  # Read from stdin
    --transfers 4
    --checkers 8
    --buffer-size 16M
)
if [ -n "$config_path" ]; then
    rclone_args+=(--config "$config_path")
fi

# Push rclone.conf to Gist — token may have been refreshed
# Called regardless of upload success/failure.
_push_rclone_config_to_gist() {
    if declare -f _read_gist_config > /dev/null 2>&1; then
        local cf="$SCRIPT_DIR/config.json"
        [ -f "$cf" ] || cf="./config.json"
        if [ -f "$cf" ]; then
            log_msg "Pushing updated rclone.conf to Gist (token may have refreshed)..."
            if _read_gist_config "$cf"; then
                if [ -n "$config_path" ]; then
                    RCLONE_CONF_PATH="$config_path" _push_to_gist "$logfile"
                else
                    _push_to_gist "$logfile"
                fi
            fi
        fi
    else
        log_msg "WARNING: sync_rclone_config not sourced, skipping Gist push."
    fi
}

# Helper for rclone copy with retry logic
rclone_copy_with_retry() {
    local max_attempts=3
    local attempt=1
    local delay=10

    while [ $attempt -le $max_attempts ]; do
        if printf '%s\n' "$files_to_upload" | rclone "${rclone_args[@]}" 2>&1 | tee -a "$rclone_logfile" | log_stream "" "rclone"; then
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
    log_stats_block "Upload stats after verify:" "$stats"

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

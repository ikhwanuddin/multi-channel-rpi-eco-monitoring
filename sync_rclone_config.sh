#!/bin/bash

##############################################
# sync_rclone_config.sh
# Syncs rclone.conf with a private GitHub Gist.
#
# Logic:
#   - Compares last-modified timestamp of local rclone.conf
#     vs the Gist's updated_at timestamp.
#   - If local is NEWER  → push local config to Gist.
#   - If Gist is NEWER   → pull Gist config to local.
#   - If identical time  → no action needed.
#
# Requires config.json to contain:
#   {
#     "gist": {
#       "github_token": "ghp_...",
#       "gist_id":      "abc123...",
#       "filename":     "rclone.conf"   <-- optional, default: rclone.conf
#     }
#   }
#
# Usage:
#   source sync_rclone_config.sh          (to use functions)
#   bash sync_rclone_config.sh [logfile]  (to run directly)
##############################################

RCLONE_CONF_PATH="${RCLONE_CONF_PATH:-$HOME/.config/rclone/rclone.conf}"
CURL_CONNECT_TIMEOUT="${CURL_CONNECT_TIMEOUT:-10}"
CURL_MAX_TIME="${CURL_MAX_TIME:-30}"

_curl_common_args() {
    echo "-sS --connect-timeout $CURL_CONNECT_TIMEOUT --max-time $CURL_MAX_TIME"
}

# ── Internal: log helper ──────────────────────────────────────────────────────
_gist_log() {
    local msg="$1"
    local logfile="${2:-/dev/stdout}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [gist-sync] $msg" | tee -a "$logfile"
}

# ── Read gist credentials from config.json ────────────────────────────────────
_read_gist_config() {
    local config_file="${1:-./config.json}"

    if [ ! -f "$config_file" ]; then
        echo "ERROR: config file not found: $config_file" >&2
        return 1
    fi

    GIST_TOKEN=$(python3 -c "
import json, sys
try:
    c = json.load(open('$config_file'))
    print(c['gist']['github_token'])
except (KeyError, FileNotFoundError):
    sys.exit(1)
" 2>/dev/null)

    GIST_ID=$(python3 -c "
import json, sys
try:
    c = json.load(open('$config_file'))
    print(c['gist']['gist_id'])
except (KeyError, FileNotFoundError):
    sys.exit(1)
" 2>/dev/null)

    GIST_FILENAME=$(python3 -c "
import json
try:
    c = json.load(open('$config_file'))
    print(c.get('gist', {}).get('filename', 'rclone.conf'))
except:
    print('rclone.conf')
" 2>/dev/null)
    GIST_FILENAME="${GIST_FILENAME:-rclone.conf}"

    if [ -z "$GIST_TOKEN" ] || [ -z "$GIST_ID" ]; then
        echo "ERROR: gist.github_token or gist.gist_id missing in config.json" >&2
        return 1
    fi

    return 0
}

# ── Push local rclone.conf to Gist ───────────────────────────────────────────
_push_to_gist() {
    local logfile="${1:-/dev/stdout}"

    _gist_log "Pushing local rclone.conf to Gist..." "$logfile"

    # Read file content and escape for JSON
    local content
    content=$(python3 -c "
import json, sys
with open('$RCLONE_CONF_PATH', 'r') as f:
    content = f.read()
print(json.dumps(content))
" 2>/dev/null)

    if [ -z "$content" ]; then
        _gist_log "ERROR: Failed to read rclone.conf for upload" "$logfile"
        return 1
    fi

    local payload
    payload=$(python3 -c "
import json
content = $content
payload = {'files': {'$GIST_FILENAME': {'content': content}}}
print(json.dumps(payload))
")

    local http_code
    http_code=$(curl $(_curl_common_args) -o /tmp/_gist_push_response.json -w "%{http_code}" \
        -X PATCH \
        -H "Authorization: token $GIST_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "https://api.github.com/gists/$GIST_ID" 2>/tmp/_gist_push_curl.err)

    if [ "$http_code" = "200" ]; then
        _gist_log "Push successful (HTTP $http_code)" "$logfile"
        return 0
    else
        local err
        if [ "$http_code" = "000" ]; then
            err=$(head -n 1 /tmp/_gist_push_curl.err 2>/dev/null)
            err=${err:-"network error (timeout/DNS/TLS/connectivity)"}
        else
            err=$(python3 -c "import json; d=json.load(open('/tmp/_gist_push_response.json')); print(d.get('message','unknown error'))" 2>/dev/null)
        fi
        _gist_log "ERROR: Push failed (HTTP $http_code): $err" "$logfile"
        return 1
    fi
}

# ── Pull rclone.conf from Gist ────────────────────────────────────────────────
_pull_from_gist() {
    local logfile="${1:-/dev/stdout}"

    _gist_log "Pulling rclone.conf from Gist..." "$logfile"

    local http_code
    http_code=$(curl $(_curl_common_args) -o /tmp/_gist_pull_response.json -w "%{http_code}" \
        -H "Authorization: token $GIST_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/gists/$GIST_ID" 2>/tmp/_gist_pull_curl.err)

    if [ "$http_code" != "200" ]; then
        local err
        if [ "$http_code" = "000" ]; then
            err=$(head -n 1 /tmp/_gist_pull_curl.err 2>/dev/null)
            err=${err:-"network error (timeout/DNS/TLS/connectivity)"}
        else
            err=$(python3 -c "import json; d=json.load(open('/tmp/_gist_pull_response.json')); print(d.get('message','unknown error'))" 2>/dev/null)
        fi
        _gist_log "ERROR: Pull failed (HTTP $http_code): $err" "$logfile"
        return 1
    fi

    # Extract file content from response
    local raw_url
    raw_url=$(python3 -c "
import json, sys
try:
    d = json.load(open('/tmp/_gist_pull_response.json'))
    print(d['files']['$GIST_FILENAME']['raw_url'])
except (KeyError, TypeError):
    sys.exit(1)
" 2>/dev/null)

    if [ -z "$raw_url" ]; then
        _gist_log "ERROR: Could not find '$GIST_FILENAME' in Gist response" "$logfile"
        return 1
    fi

    # Ensure directory exists
    mkdir -p "$(dirname "$RCLONE_CONF_PATH")"

    # Download raw content
    local dl_code
    dl_code=$(curl $(_curl_common_args) -o "$RCLONE_CONF_PATH" -w "%{http_code}" \
        -H "Authorization: token $GIST_TOKEN" \
        "$raw_url" 2>/tmp/_gist_raw_curl.err)

    if [ "$dl_code" = "200" ]; then
        # Fix ownership to current user and set proper permissions
        sudo chown $(whoami):$(whoami) "$RCLONE_CONF_PATH" 2>/dev/null || true
        sudo chmod 600 "$RCLONE_CONF_PATH" 2>/dev/null || true
        _gist_log "Pull successful - rclone.conf updated (HTTP $dl_code)" "$logfile"
        return 0
    else
        local err
        if [ "$dl_code" = "000" ]; then
            err=$(head -n 1 /tmp/_gist_raw_curl.err 2>/dev/null)
            err=${err:-"network error (timeout/DNS/TLS/connectivity)"}
            _gist_log "ERROR: Failed to download raw Gist content (HTTP $dl_code): $err" "$logfile"
        else
            _gist_log "ERROR: Failed to download raw Gist content (HTTP $dl_code)" "$logfile"
        fi
        return 1
    fi
}

# ── Main sync function (compare timestamps & decide direction) ─────────────────
sync_rclone_config() {
    local config_file="${1:-./config.json}"
    local logfile="${2:-/dev/stdout}"

    _gist_log "Starting rclone.conf sync..." "$logfile"

    # Load credentials
    if ! _read_gist_config "$config_file"; then
        _gist_log "Skipping sync: gist credentials not configured" "$logfile"
        return 1
    fi

    # ── Get Gist updated_at timestamp ──────────────────────────────────────────
    local http_code
    http_code=$(curl $(_curl_common_args) -o /tmp/_gist_meta.json -w "%{http_code}" \
        -H "Authorization: token $GIST_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        "https://api.github.com/gists/$GIST_ID" 2>/tmp/_gist_meta_curl.err)

    if [ "$http_code" != "200" ]; then
        local err
        if [ "$http_code" = "000" ]; then
            err=$(head -n 1 /tmp/_gist_meta_curl.err 2>/dev/null)
            err=${err:-"network error (timeout/DNS/TLS/connectivity)"}
        else
            err=$(python3 -c "import json; d=json.load(open('/tmp/_gist_meta.json')); print(d.get('message','unknown error'))" 2>/dev/null)
        fi
        _gist_log "ERROR: Cannot fetch Gist metadata (HTTP $http_code): $err" "$logfile"
        return 1
    fi

    local gist_updated_epoch
    gist_updated_epoch=$(python3 -c "
import json, datetime, calendar
d = json.load(open('/tmp/_gist_meta.json'))
updated_at = d['updated_at']  # ISO 8601 e.g. '2026-04-20T10:00:00Z'
dt = datetime.datetime.strptime(updated_at, '%Y-%m-%dT%H:%M:%SZ')
print(calendar.timegm(dt.timetuple()))
" 2>/dev/null)

    if [ -z "$gist_updated_epoch" ]; then
        _gist_log "ERROR: Could not parse Gist updated_at timestamp" "$logfile"
        return 1
    fi

    # ── Get local rclone.conf modification time ────────────────────────────────
    if [ ! -f "$RCLONE_CONF_PATH" ]; then
        _gist_log "Local rclone.conf not found — pulling from Gist..." "$logfile"
        _pull_from_gist "$logfile"
        return $?
    fi

    local local_mtime_epoch
    local_mtime_epoch=$(stat -c %Y "$RCLONE_CONF_PATH" 2>/dev/null || stat -f %m "$RCLONE_CONF_PATH" 2>/dev/null)

    if [ -z "$local_mtime_epoch" ]; then
        _gist_log "ERROR: Cannot read local rclone.conf modification time" "$logfile"
        return 1
    fi

    _gist_log "Local  mtime : $(date -d @$local_mtime_epoch '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r $local_mtime_epoch '+%Y-%m-%d %H:%M:%S')" "$logfile"
    _gist_log "Gist updated : $(date -d @$gist_updated_epoch '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -r $gist_updated_epoch '+%Y-%m-%d %H:%M:%S')" "$logfile"

    # ── Compare and decide ─────────────────────────────────────────────────────
    # Allow a small tolerance (30 seconds) to avoid unnecessary pushes
    # when the timestamps are nearly identical.
    local diff=$(( local_mtime_epoch - gist_updated_epoch ))

    if [ "$diff" -gt 30 ]; then
        _gist_log "Local is newer by ${diff}s → pushing to Gist" "$logfile"
        _push_to_gist "$logfile"
        return $?
    elif [ "$diff" -lt -30 ]; then
        _gist_log "Gist is newer by $(( -diff ))s → pulling from Gist" "$logfile"
        _pull_from_gist "$logfile"
        return $?
    else
        _gist_log "Timestamps are in sync (diff=${diff}s), no action needed" "$logfile"
        return 0
    fi
}

# ── Run directly if not being sourced ─────────────────────────────────────────
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    logfile="${1:-/dev/stdout}"
    config_file="${2:-./config.json}"
    sync_rclone_config "$config_file" "$logfile"
    exit $?
fi

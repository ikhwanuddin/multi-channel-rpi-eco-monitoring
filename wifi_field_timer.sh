#!/bin/bash
# =============================================================================
# wifi_field_timer.sh — Field WiFi duty cycle for MAARU (power saving)
#
# Policy (until next reboot):
#   1. On boot / service start: WiFi is turned ON so the unit can join a LAN
#      (upload, SSH, time sync).
#   2. WiFi may stay ON only during the first MAX_ON_SECONDS (default: 1200 = 20 min).
#   3. If no network association appears within NO_LINK_GRACE_SECONDS
#      (default: 900 = 15 min), WiFi sleeps early (typical forest deploy).
#   4. After MAX_ON_SECONDS, WiFi is forced asleep regardless of link state.
#   5. The only supported way to turn WiFi on again is rebooting the Pi
#      (this service runs once per boot and does not re-enable WiFi).
#
# Environment overrides (optional, via systemd unit Environment=):
#   MAX_ON_SECONDS=1200
#   NO_LINK_GRACE_SECONDS=900
#   CHECK_INTERVAL=30
#   LOG_FILE=/var/log/wifi-field-timer.log
# =============================================================================

set -u

MAX_ON_SECONDS="${MAX_ON_SECONDS:-1200}"
NO_LINK_GRACE_SECONDS="${NO_LINK_GRACE_SECONDS:-900}"
CHECK_INTERVAL="${CHECK_INTERVAL:-30}"
LOG_FILE="${LOG_FILE:-/var/log/wifi-field-timer.log}"
LOG_TAG="wifi-field-timer"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [$LOG_TAG] $*"
    echo "$msg"
    # Best-effort file log (may fail if /var/log not writable; journal still has stdout).
    echo "$msg" >>"$LOG_FILE" 2>/dev/null || true
    logger -t "$LOG_TAG" "$*" 2>/dev/null || true
}

list_wlan_ifaces() {
    local iface
    for iface in /sys/class/net/wlan*; do
        [ -e "$iface" ] || continue
        basename "$iface"
    done
}

wifi_on() {
    log "Enabling WiFi (field window start)"
    # Unblock all soft-blocked wifi radios (onboard if any + USB).
    if command -v rfkill >/dev/null 2>&1; then
        rfkill unblock wifi 2>/dev/null || true
        # Some USB dongles appear as "wlan" type rather than "wifi".
        rfkill list 2>/dev/null | awk -F: '/^[[:space:]]*[0-9]+:/{id=$1} /Wireless|wlan|Wi-Fi|Wireless LAN/{print id}' \
            | while read -r id; do
                [ -n "${id:-}" ] && rfkill unblock "$id" 2>/dev/null || true
            done
    fi

    local name
    for name in $(list_wlan_ifaces); do
        ip link set "$name" up 2>/dev/null || true
    done

    # Give USB dongles / wpa_supplicant a moment after unblock.
    sleep 2
}

wifi_off() {
    local reason="${1:-timer expired}"
    log "Sleeping WiFi until next reboot ($reason)"

    local name
    for name in $(list_wlan_ifaces); do
        ip link set "$name" down 2>/dev/null || true
    done

    if command -v rfkill >/dev/null 2>&1; then
        rfkill block wifi 2>/dev/null || true
        rfkill list 2>/dev/null | awk -F: '/^[[:space:]]*[0-9]+:/{id=$1} /Wireless|wlan|Wi-Fi|Wireless LAN/{print id}' \
            | while read -r id; do
                [ -n "${id:-}" ] && rfkill block "$id" 2>/dev/null || true
            done
    fi

    # NetworkManager (if present): keep radio off after we leave.
    if command -v nmcli >/dev/null 2>&1; then
        nmcli radio wifi off 2>/dev/null || true
    fi

    log "WiFi is asleep. Reboot the Raspberry Pi to enable WiFi for another window."
}

# True when any wlan* has a global IPv4 (associated + configured) or is the
# default-route device. Carrier alone is not enough (can be "up" while scanning).
is_connected() {
    local name
    for name in $(list_wlan_ifaces); do
        if ip -4 -o addr show dev "$name" scope global 2>/dev/null | grep -q .; then
            return 0
        fi
    done
    if ip route show default 2>/dev/null | grep -qE '[[:space:]]dev[[:space:]]+wlan[0-9]+'; then
        return 0
    fi
    return 1
}

main() {
    log "Starting field WiFi timer: max_on=${MAX_ON_SECONDS}s, no_link_grace=${NO_LINK_GRACE_SECONDS}s, check_every=${CHECK_INTERVAL}s"

    wifi_on

    local start_ts now elapsed ever_connected=0
    start_ts=$(date +%s)

    while true; do
        now=$(date +%s)
        elapsed=$((now - start_ts))

        if [ "$elapsed" -ge "$MAX_ON_SECONDS" ]; then
            wifi_off "reached MAX_ON_SECONDS=${MAX_ON_SECONDS}"
            break
        fi

        if is_connected; then
            if [ "$ever_connected" -eq 0 ]; then
                log "Network link detected on wlan (elapsed ${elapsed}s); WiFi stays on until max window"
            fi
            ever_connected=1
        else
            # Forest / no AP: do not keep the radio scanning for the full hour.
            if [ "$ever_connected" -eq 0 ] && [ "$elapsed" -ge "$NO_LINK_GRACE_SECONDS" ]; then
                wifi_off "no network link within NO_LINK_GRACE_SECONDS=${NO_LINK_GRACE_SECONDS}"
                break
            fi
        fi

        local remaining=$((MAX_ON_SECONDS - elapsed))
        if [ "$remaining" -lt "$CHECK_INTERVAL" ]; then
            sleep "$remaining"
        else
            sleep "$CHECK_INTERVAL"
        fi
    done

    log "Timer finished; process exiting (WiFi remains asleep until reboot)"
    exit 0
}

main "$@"

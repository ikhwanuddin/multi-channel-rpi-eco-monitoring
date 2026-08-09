#!/bin/bash
# =============================================================================
# wifi_field_timer.sh — Field WiFi keep-alive + no-link sleep for MAARU
#
# Policy (until next reboot):
#   1. On boot / service start: WiFi ON (upload, SSH, time sync, phone hotspot).
#   2. While wlan has an active link: WiFi stays ON with no time limit
#      (home / base / remote Tailscale over WiFi must not be cut).
#   3. When wlan link is missing — from boot, or after a link drops — start a
#      no-link timer. If the link returns before the timer ends, cancel it.
#   4. After NO_LINK_GRACE_SECONDS (default: 1200 = 20 min) with no wlan link:
#      soft-sleep WiFi for the rest of this boot (forest / left behind).
#   5. Soft sleep does not persist across reboot. Reboot starts the policy again.
#
# Sleep method (soft sleep — intentional):
#   - Disconnect NM wifi devices (if nmcli present) and bring wlan* down.
#   - Do NOT `rfkill block wifi` and do NOT `nmcli radio wifi off`.
#     Those write persistent state and can leave units radio-dead after uninstall.
#
# Environment overrides (optional, via systemd unit Environment=):
#   NO_LINK_GRACE_SECONDS=1200
#   CHECK_INTERVAL=30
#   LOG_FILE=/var/log/wifi-field-timer.log
# =============================================================================

set -u

NO_LINK_GRACE_SECONDS="${NO_LINK_GRACE_SECONDS:-1200}"
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

# Clear leftover hard-off state from older timer versions / manual ops, then
# bring radios up so NM (or dhcpcd/wpa) can associate.
wifi_on() {
    log "Enabling WiFi (keep-alive while linked; sleep only after no-link grace)"

    if command -v rfkill >/dev/null 2>&1; then
        rfkill unblock wifi 2>/dev/null || true
        # Some USB dongles appear as "wlan" type rather than "wifi".
        rfkill list 2>/dev/null | awk -F: '/^[[:space:]]*[0-9]+:/{id=$1} /Wireless|wlan|Wi-Fi|Wireless LAN/{print id}' \
            | while read -r id; do
                [ -n "${id:-}" ] && rfkill unblock "$id" 2>/dev/null || true
            done
    fi

    # NetworkManager persists "radio wifi off" in NetworkManager.state — always
    # re-enable so a previous hard-sleep cannot stick across boots.
    if command -v nmcli >/dev/null 2>&1; then
        nmcli radio wifi on 2>/dev/null || true
    fi

    local name
    for name in $(list_wlan_ifaces); do
        ip link set "$name" up 2>/dev/null || true
    done

    # Give USB dongles / NetworkManager a moment after unblock.
    sleep 2
}

# Soft sleep: stop scanning/association for this boot without persistent kill.
wifi_off() {
    local reason="${1:-no-link grace expired}"
    log "Sleeping WiFi until next reboot ($reason)"

    if command -v nmcli >/dev/null 2>&1; then
        # Disconnect only wifi devices; leave ethernet/USB-tether alone.
        nmcli -t -f DEVICE,TYPE device status 2>/dev/null \
            | awk -F: '$2 == "wifi" && $1 != "" { print $1 }' \
            | while read -r dev; do
                [ -n "${dev:-}" ] || continue
                nmcli device disconnect "$dev" 2>/dev/null || true
            done
    fi

    local name
    for name in $(list_wlan_ifaces); do
        ip link set "$name" down 2>/dev/null || true
    done

    # Intentionally NOT:
    #   rfkill block wifi
    #   nmcli radio wifi off
    # Those persist across reboot and can brick field WiFi after uninstall.

    log "WiFi is asleep (soft). Reboot for another session, or: ip link set wlan0 up"
}

# True when any wlan* has a global IPv4 (associated + configured) or is the
# default-route device. Carrier alone is not enough (can be "up" while scanning).
# USB tether / Tailscale alone do not count — only real wlan link.
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
    log "Starting field WiFi timer: no_link_grace=${NO_LINK_GRACE_SECONDS}s, check_every=${CHECK_INTERVAL}s"

    wifi_on

    # 0 = not in a no-link countdown; otherwise unix time when no-link started.
    local no_link_since=0
    local was_linked=0
    local now no_link_for

    while true; do
        now=$(date +%s)

        if is_connected; then
            if [ "$was_linked" -eq 0 ]; then
                log "wlan link up; WiFi stays on for as long as the link holds"
            elif [ "$no_link_since" -ne 0 ]; then
                log "wlan link restored; no-link sleep timer cancelled"
            fi
            was_linked=1
            no_link_since=0
        else
            if [ "$no_link_since" -eq 0 ]; then
                no_link_since=$now
                if [ "$was_linked" -eq 1 ]; then
                    log "wlan link lost; starting no-link sleep timer (${NO_LINK_GRACE_SECONDS}s)"
                else
                    log "no wlan link yet; starting no-link sleep timer (${NO_LINK_GRACE_SECONDS}s)"
                fi
            fi

            no_link_for=$((now - no_link_since))
            if [ "$no_link_for" -ge "$NO_LINK_GRACE_SECONDS" ]; then
                if [ "$was_linked" -eq 1 ]; then
                    wifi_off "no wlan link for NO_LINK_GRACE_SECONDS=${NO_LINK_GRACE_SECONDS} after link was lost"
                else
                    wifi_off "no wlan link within NO_LINK_GRACE_SECONDS=${NO_LINK_GRACE_SECONDS}"
                fi
                break
            fi
        fi

        sleep "$CHECK_INTERVAL"
    done

    log "Timer finished; process exiting (WiFi remains soft-asleep until reboot or manual up)"
    exit 0
}

main "$@"

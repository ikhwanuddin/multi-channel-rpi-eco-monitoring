#!/bin/bash

# Time sync strategy:
# 1) Prefer internet (timedatectl + optional chrony)
# 2) Fallback for offline deployment: accept epoch from SSH client
#    Usage from client device:
#    ssh pi@raspberrypi.local "cd ~/multi-channel-rpi-eco-monitoring && sudo bash ./update_time.sh --epoch $(date +%s)"

SSH_EPOCH=""
TIME_SYNC_MODE="auto"
TIME_SYNC_PHASE="init"

log_msg() {
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [time-sync][mode=$TIME_SYNC_MODE][phase=$TIME_SYNC_PHASE] $msg"
}

if [ "${1:-}" = "--epoch" ] && [ -n "${2:-}" ]; then
    SSH_EPOCH="$2"
elif [ -n "${SSH_TIME_EPOCH:-}" ]; then
    SSH_EPOCH="$SSH_TIME_EPOCH"
fi

# Jika --epoch diberikan, langsung pakai epoch (mode offline) tanpa cek internet
if [ -n "$SSH_EPOCH" ]; then
    TIME_SYNC_MODE="ssh-epoch"
    TIME_SYNC_PHASE="validate-epoch"
    if [[ "$SSH_EPOCH" =~ ^[0-9]+$ ]]; then
        TIME_SYNC_PHASE="apply-epoch"
        log_msg "Offline mode: syncing time from SSH-provided epoch $SSH_EPOCH"
        if sudo date -s "@$SSH_EPOCH" >/dev/null; then
            sudo hwclock -w >/dev/null 2>&1 || true
            TIME_SYNC_PHASE="completed"
            log_msg "SSH-based time sync successful"
        else
            TIME_SYNC_PHASE="error"
            log_msg "Failed to set system time from SSH epoch"
            exit 1
        fi
    else
        TIME_SYNC_PHASE="error"
        log_msg "Invalid epoch value: $SSH_EPOCH"
        exit 1
    fi
else
    TIME_SYNC_MODE="ntp"
    TIME_SYNC_PHASE="probe-internet"
    # Tidak ada epoch, cek internet lalu sync NTP
    ONLINE=0
    if timeout 3s wget -q --spider http://google.com; then
        ONLINE=1
    fi

    if [ "$ONLINE" -eq 1 ]; then
        TIME_SYNC_PHASE="sync-ntp"
        log_msg "Internet detected, syncing time via NTP"
        sudo timedatectl set-ntp true
        sleep 10
    else
        TIME_SYNC_PHASE="offline-no-source"
        log_msg "No internet and no SSH epoch provided. Time not updated."
        log_msg "Tip: run from client device with:"
        log_msg "ssh pi@raspberrypi.local \"cd ~/multi-channel-rpi-eco-monitoring && sudo bash ./update_time.sh --epoch \$(date +%s)\""
        exit 1
    fi
fi

TIME_SYNC_PHASE="completed"
log_msg "Current time after sync: $(date)"

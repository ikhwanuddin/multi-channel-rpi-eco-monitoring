#!/bin/bash

# Time sync strategy:
# 1) Prefer internet (timedatectl + optional chrony)
# 2) Fallback for offline deployment: accept epoch from SSH client
#    Usage from client device:
#    ssh pi@raspberrypi.local "cd ~/multi-channel-rpi-eco-monitoring && sudo bash ./update_time.sh --epoch $(date +%s)"

SSH_EPOCH=""

if [ "${1:-}" = "--epoch" ] && [ -n "${2:-}" ]; then
    SSH_EPOCH="$2"
elif [ -n "${SSH_TIME_EPOCH:-}" ]; then
    SSH_EPOCH="$SSH_TIME_EPOCH"
fi

# Jika --epoch diberikan, langsung pakai epoch (mode offline) tanpa cek internet
if [ -n "$SSH_EPOCH" ]; then
    if [[ "$SSH_EPOCH" =~ ^[0-9]+$ ]]; then
        printf "Offline mode: syncing time from SSH-provided epoch %s\n" "$SSH_EPOCH"
        if sudo date -s "@$SSH_EPOCH" >/dev/null; then
            sudo hwclock -w >/dev/null 2>&1 || true
            printf "SSH-based time sync successful\n"
        else
            printf "Failed to set system time from SSH epoch\n"
            exit 1
        fi
    else
        printf "Invalid epoch value: %s\n" "$SSH_EPOCH"
        exit 1
    fi
else
    # Tidak ada epoch, cek internet lalu sync NTP
    ONLINE=0
    if timeout 3s wget -q --spider http://google.com; then
        ONLINE=1
    fi

    if [ "$ONLINE" -eq 1 ]; then
        printf "Internet detected, syncing time via NTP\n"
        sudo timedatectl set-ntp true
        sleep 10
    else
        printf "No internet and no SSH epoch provided. Time not updated.\n"
        printf "Tip: run from client device with:\n"
        printf "ssh pi@raspberrypi.local \"cd ~/multi-channel-rpi-eco-monitoring && sudo bash ./update_time.sh --epoch \$(date +%%s)\"\n"
        exit 1
    fi
fi

printf "Current time after sync: %s\n" "$(date)"

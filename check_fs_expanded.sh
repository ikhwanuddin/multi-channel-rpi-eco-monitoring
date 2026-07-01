#!/usr/bin/env bash
# check_fs_expanded.sh
#
# One-time filesystem expansion helper for eco-monitor.service.
#
# Logic:
#   - If /home/pi/.fs_expanded marker exists, do nothing.
#   - Otherwise, compare the root partition size to the underlying
#     /dev/mmcblk0 device size. If root uses less than 90% of the disk,
#     call `raspi-config --expand-rootfs` (the actual resize happens on
#     the next reboot via the init script).
#   - Always create the marker so this is a one-shot operation.
#
# Called by ExecStartPre in eco-monitor.service.

set -u

MARKER="/home/pi/.fs_expanded"

if [ -f "$MARKER" ]; then
    # Already expanded (or already attempted). No-op.
    exit 0
fi

ROOT_SIZE=""
DISK_SIZE_KB=""

# Root partition size in 1K blocks (last column of `df /` output).
ROOT_SIZE="$(df / 2>/dev/null | awk 'NR==2 {print $2}')"

# Underlying block device size in bytes, then convert to 1K blocks.
RAW_BYTES="$(lsblk -b -o SIZE /dev/mmcblk0 2>/dev/null | awk 'NR==2 {print $1}')"
if [ -n "$RAW_BYTES" ]; then
    DISK_SIZE_KB=$((RAW_BYTES / 1024))
fi

if [ -n "$ROOT_SIZE" ] && [ -n "${DISK_SIZE_KB:-}" ]; then
    THRESHOLD=$((DISK_SIZE_KB * 90 / 100))
    if [ "$ROOT_SIZE" -lt "$THRESHOLD" ]; then
        sudo raspi-config --expand-rootfs 2>/dev/null || true
        echo "FS expansion triggered (resize on next reboot)"
    else
        echo "FS already expanded"
    fi
else
    echo "Cannot determine disk size; skipping expansion"
fi

# Always create the marker so we don't retry every boot.
mkdir -p "$(dirname "$MARKER")" 2>/dev/null || true
touch "$MARKER" 2>/dev/null || true

exit 0

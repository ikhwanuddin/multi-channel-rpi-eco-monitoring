#!/bin/bash

# Clean all data under multi_channel_monitoring_data/live_data safely.
# Default target is the path used by this project on Raspberry Pi.

set -u

DEFAULT_TARGET="/home/pi/multi_channel_monitoring_data/live_data"
TARGET_DIR="${1:-$DEFAULT_TARGET}"

printf '##############################################\n'
printf ' Clean live_data utility\n'
printf '##############################################\n'
printf 'Target directory: %s\n' "$TARGET_DIR"

if [ ! -d "$TARGET_DIR" ]; then
    echo "ERROR: Target directory does not exist: $TARGET_DIR"
    exit 1
fi

# Refuse to run on clearly unsafe paths.
case "$TARGET_DIR" in
    "/"|"/home"|"/home/pi"|"/home/pi/multi_channel_monitoring_data")
        echo "ERROR: Refusing to clean unsafe target path: $TARGET_DIR"
        exit 1
        ;;
esac

# Ensure script is only used for live_data directories.
if [[ "$TARGET_DIR" != */live_data ]]; then
    echo "ERROR: Target path must end with /live_data"
    echo "Tip: pass explicit path, for example:"
    echo "  ./clean_live_data.sh /home/pi/multi_channel_monitoring_data/live_data"
    exit 1
fi

echo ""
echo "This action will permanently delete all contents inside:"
echo "  $TARGET_DIR"
echo "Type 'yes' to continue, or anything else to cancel."
read -r confirm

if [ "$confirm" != "yes" ]; then
    echo "Canceled. No data was deleted."
    exit 0
fi

# Remove everything inside live_data, including hidden files/folders.
# Keep the live_data directory itself.
if find "$TARGET_DIR" -mindepth 1 -print -quit | grep -q .; then
    echo "Cleaning all contents inside: $TARGET_DIR"
    rm -rf -- "$TARGET_DIR"/* "$TARGET_DIR"/.[!.]* "$TARGET_DIR"/..?* 2>/dev/null || true
    echo "Clean completed successfully."
else
    echo "Nothing to clean. Directory is already empty."
fi

#!/bin/bash

# Clean all data under multi_channel_monitoring_data/live_data safely.
# Default target is the path used by this project on Raspberry Pi.

set -u

DEFAULT_TARGET="/home/pi/multi_channel_monitoring_data/live_data"
TARGET_DIR="${1:-$DEFAULT_TARGET}"

printf '##############################################\n'
printf '           Clean live_data utility\n'
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
echo "This action will permanently delete recording data inside:"
echo "  $TARGET_DIR"
echo "All folder structure will be preserved exactly as-is."
echo "Type 'y' to continue delete, or 'n' to cancel."
read -r confirm

case "$confirm" in
    y)
        ;;
    n)
        echo "Canceled. No data was deleted."
        exit 0
        ;;
    *)
        echo "Invalid input. Canceled for safety."
        exit 0
        ;;
esac

# Remove only files (including hidden files) under live_data.
# Keep all directories so folder structure remains unchanged.
# Use sudo because files may be owned by root (python_record.py runs as sudo).
if sudo find "$TARGET_DIR" -mindepth 1 -print -quit | grep -q .; then
    echo "Cleaning recording files while preserving all folder structure in: $TARGET_DIR"
    if sudo find "$TARGET_DIR" -type f -delete; then
        echo "Clean completed successfully."
    else
        echo "ERROR: Some files could not be deleted. Check permissions."
        exit 1
    fi
else
    echo "Nothing to clean. Directory is already empty."
fi

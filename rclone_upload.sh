#!/bin/bash

# Usage:
#   ./rclone_upload.sh <data_dir> [remote_name] [config_path] [remote_base_path]

data_dir="$1"
remote_name="${2:-mybox}"
config_path="${3:-}"
remote_base_path="${4:-}"

if ! command -v rclone >/dev/null 2>&1; then
    echo "rclone binary not found in PATH"
    exit 127
fi

if [ ! -d "$data_dir" ]; then
	echo "Source directory does not exist: $data_dir"
	exit 1
fi

data_top_folder_name=$(basename "$data_dir")
remote_target="${remote_name}:${remote_base_path}/${data_top_folder_name}"

echo "Starting rclone upload from $data_dir to $remote_target"

if [ -n "$config_path" ]; then
    rclone move "$data_dir" "$remote_target" --config "$config_path" --delete-empty-src-dirs --log-level INFO
else
    rclone move "$data_dir" "$remote_target" --delete-empty-src-dirs --log-level INFO
fi

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "Rclone upload completed successfully"
else
    echo "Rclone upload failed with exit code $exit_code"
fi
exit $exit_code

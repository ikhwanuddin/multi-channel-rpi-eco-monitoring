#!/bin/bash

# ftp_string is now ignored, using rclone with 'box' remote
# data_dir=$1 (but in original it's $2, wait: original ftp_string=$1, data_dir=$2)
# Since changing to rclone, we only need data_dir as $1, but to keep compatibility, use $2 as data_dir

data_dir=$2

if [ ! -d "$data_dir" ]; then
	exit 1
fi

data_top_folder_name=$(basename "$data_dir")

# Use rclone to move files to Box (upload and remove from local)
rclone move "$data_dir" "mybox:$data_top_folder_name" --delete-empty-src-dirs --progress --log-level INFO

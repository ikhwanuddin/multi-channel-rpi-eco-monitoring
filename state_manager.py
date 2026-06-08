import argparse
import json
import os
import subprocess
import sys
from datetime import datetime


def load_state(state_file):
    if not os.path.exists(state_file):
        return {
            "session_start": "",
            "last_sync": "",
            "files": {},
            "upload_stats": {
                "total_files": 0,
                "completed": 0,
                "pending": 0,
                "uploading": 0,
                "total_size_gb": 0.0,
            },
        }
    with open(state_file, "r") as f:
        return json.load(f)


def save_state(state_file, state):
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)


def init_scan_mark(data_dir, state_file):
    state = load_state(state_file)
    found_files = {}
    total_size = 0

    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".flac"):
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                total_size += file_size
                rel_path = os.path.relpath(file_path, data_dir)

                # Logic: if completed locally, re-verify. Otherwise keep state
                status = state["files"].get(rel_path, "pending")
                if status == "completed":
                    status = "pending"
                found_files[rel_path] = status

    # Mark pending as uploading
    file_list = []
    for rel_path, status in found_files.items():
        if status in ["pending", "uploading"]:
            found_files[rel_path] = "uploading"
            file_list.append(rel_path)

    state["files"] = found_files
    state["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state["upload_stats"].update(
        {
            "total_files": len(found_files),
            "completed": sum(1 for s in found_files.values() if s == "completed"),
            "pending": 0,
            "uploading": len(file_list),
            "total_size_gb": round(total_size / (1024**3), 2),
        }
    )

    save_state(state_file, state)
    print(json.dumps({"stats": state["upload_stats"], "files_to_upload": file_list}))


def pre_verify(data_dir, state_file, remote_target, config_path):
    state = load_state(state_file)

    # 1. Get remote list
    lsf_cmd = ["rclone", "lsf", "-R", "--files-only", "--format", "p", remote_target]
    if config_path:
        lsf_cmd.extend(["--config", config_path])

    try:
        remote_list = subprocess.check_output(
            lsf_cmd, universal_newlines=True
        ).splitlines()
        remote_set = set(remote_list)
    except subprocess.CalledProcessError:
        print("Error: Failed to list remote files for pre-verify")
        return

    # 2. Update state to completed if found on remote
    updated = False
    for rel_path in list(state["files"].keys()):
        if rel_path in remote_set and state["files"][rel_path] != "completed":
            state["files"][rel_path] = "completed"
            updated = True

    if updated:
        # Update stats
        state["upload_stats"].update(
            {
                "completed": sum(
                    1 for s in state["files"].values() if s == "completed"
                ),
                "uploading": sum(
                    1 for s in state["files"].values() if s == "uploading"
                ),
                "pending": sum(1 for s in state["files"].values() if s == "pending"),
            }
        )
        save_state(state_file, state)
        print(json.dumps({"status": "updated", "stats": state["upload_stats"]}))
    else:
        print(json.dumps({"status": "no_change"}))


def verify_finalize(data_dir, state_file, remote_target, config_path, dry_run=False):
    state = load_state(state_file)
    uploading_files = [k for k, v in state["files"].items() if v == "uploading"]
    if not uploading_files:
        return

    # 1. Get remote list using lsf (much faster than check)
    lsf_cmd = ["rclone", "lsf", "-R", "--files-only", "--format", "p", remote_target]
    if config_path:
        lsf_cmd.extend(["--config", config_path])

    try:
        remote_list = subprocess.check_output(
            lsf_cmd, universal_newlines=True
        ).splitlines()
        remote_set = set(remote_list)
    except subprocess.CalledProcessError:
        print("Error: Failed to list remote files")
        return

    # 2. Compare and cleanup
    deleted_count = 0
    for rel_path in uploading_files:
        if rel_path in remote_set:
            state["files"][rel_path] = "completed"
            local_path = os.path.join(data_dir, rel_path)
            if os.path.exists(local_path):
                if not dry_run:
                    os.remove(local_path)
                deleted_count += 1

    # 3. Update stats
    state["upload_stats"].update(
        {
            "completed": sum(1 for s in state["files"].values() if s == "completed"),
            "uploading": sum(1 for s in state["files"].values() if s == "uploading"),
            "pending": sum(1 for s in state["files"].values() if s == "pending"),
        }
    )

    save_state(state_file, state)
    print(json.dumps({"deleted": deleted_count, "stats": state["upload_stats"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "op", choices=["init-scan-mark", "verify-finalize", "pre-verify"]
    )
    parser.add_argument("data_dir")
    parser.add_argument("state_file")
    parser.add_argument("--remote-target", required=False)
    parser.add_argument("--config-path", required=False)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.op == "init-scan-mark":
        init_scan_mark(args.data_dir, args.state_file)
    elif args.op == "verify-finalize":
        verify_finalize(
            args.data_dir,
            args.state_file,
            args.remote_target,
            args.config_path,
            dry_run=args.dry_run,
        )
    elif args.op == "pre-verify":
        pre_verify(args.data_dir, args.state_file, args.remote_target, args.config_path)

import json
import os
import sys
import argparse
from datetime import datetime

def load_state(state_file):
    if not os.path.exists(state_file):
        return {
            "session_start": "",
            "last_sync": "",
            "files": {},
            "upload_stats": {"total_files": 0, "completed": 0, "pending": 0, "uploading": 0, "total_size_gb": 0.0}
        }
    with open(state_file, 'r') as f:
        return json.load(f)

def save_state(state_file, state):
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)

def init_scan_mark(data_dir, state_file):
    state = load_state(state_file)
    found_files = {}
    total_size = 0

    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.flac'):
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                total_size += file_size
                rel_path = os.path.relpath(file_path, data_dir)

                # Logic: if completed locally, re-verify. Otherwise keep state
                status = state['files'].get(rel_path, 'pending')
                if status == 'completed':
                    status = 'pending'
                found_files[rel_path] = status

    # Mark pending as uploading
    file_list = []
    for rel_path, status in found_files.items():
        if status in ['pending', 'uploading']:
            found_files[rel_path] = 'uploading'
            file_list.append(rel_path)

    state['files'] = found_files
    state['last_sync'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state['upload_stats'].update({
        'total_files': len(found_files),
        'completed': sum(1 for s in found_files.values() if s == 'completed'),
        'pending': 0,
        'uploading': len(file_list),
        'total_size_gb': round(total_size / (1024**3), 2)
    })

    save_state(state_file, state)
    print(json.dumps({"stats": state['upload_stats'], "files_to_upload": file_list}))

def verify_finalize(data_dir, state_file, remote_target, config_path):
    # This part would be implemented in Phase 2
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("op", choices=["init-scan-mark", "verify-finalize"])
    parser.add_argument("data_dir")
    parser.add_argument("state_file")
    args = parser.parse_args()

    if args.op == "init-scan-mark":
        init_scan_mark(args.data_dir, args.state_file)

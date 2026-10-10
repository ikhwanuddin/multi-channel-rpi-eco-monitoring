# Cloud Upload Setup Guide

Configure your Raspberry Pi to automatically upload recordings to cloud storage using rclone.

## Overview

The system supports uploading to **any rclone-compatible service**:
- Box (recommended for research)
- Google Drive
- Dropbox
- AWS S3
- Azure Blob Storage
- OneDrive
- FTP / SFTP
- And [many more](https://rclone.org/overview/)

## Step 1: Install and Configure Rclone

### Install rclone on Raspberry Pi

```bash
sudo apt-get install -y rclone jq
```

(`jq` is required by `rclone_upload.sh`. You can also use the official installer, `curl https://rclone.org/install.sh | sudo bash`, for a newer rclone.)

Verify installation:
```bash
rclone version
```

### Configure Your Cloud Service

Run the interactive configuration as the `pi` user (not root), so the config lands in `/home/pi/.config/rclone/rclone.conf`:

```bash
rclone config
```

**Example: Box.com Setup**

```
No remotes found - make a new one
n) New remote
s) Set configuration password
q) Quit config
n/s/q> n

name> mybox                    # Name your remote (e.g., "mybox")
Type of storage> box           # Type box for Box
...follow prompts...
```

For detailed guides per service, see [rclone documentation](https://rclone.org/docs/).

### Test Your Remote

```bash
rclone listremotes          # Should show "mybox:"
rclone ls mybox:            # List contents
rclone mkdir mybox:test     # Create test folder
```

### Optional: share rclone.conf between Pis via a private Gist

OAuth remotes such as Box refresh their token inside `rclone.conf`. To keep several Pis in sync, put the file in a private GitHub Gist and fill the `gist` section of `config.json` (`github_token`, `gist_id`, `filename`). `sync_rclone_config.sh` then runs at every service start and pulls or pushes whichever copy is newer; after each upload cycle `rclone_upload.sh` pushes the local file back (at most once per hour).

---

## Step 2: Target Folder on Cloud

You do not need to create the folder by hand; `rclone copy` creates it. The remote path is fixed in `rclone_upload.sh`:

```
<remote_name>:monitoring_data/RPiID-<cpu serial>/<YYYY-MM-DD>/HH-MM-SS_dur=1200secs.flac
```

`RPiID-<cpu serial>` comes from `discover_serial.py`, so every Pi uploads into its own folder.

---

## Step 3: Enable Uploads in config.json

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py   # menu option 1 (or 5)
```

When prompted:
- **test_mode**: `0` (test mode skips all uploads)
- **remote_name**: enter `mybox` (or your remote name)
- **config_path**: path to your `rclone.conf` (default `/home/pi/.config/rclone/rclone.conf`)
- **target_path**: accepted but currently ignored (see [config.md](config.md#target_path--remote_base_path))

The installer always writes `"upload_enabled": true`. Or manually edit `config.json`:

```json
{
  "upload_enabled": true,
  "test_mode": 0,
  "rclone": {
    "remote_name": "mybox",
    "config_path": "/home/pi/.config/rclone/rclone.conf",
    "target_path": "monitoring_data"
  }
}
```

---

## Step 4: Test Upload

Uploads are started by `record.py` itself, not by cron. With `upload_enabled: true` and `test_mode: 0`, connect the Pi to a network with internet and restart the service:

```bash
sudo systemctl restart eco-monitor.service
sudo journalctl -u eco-monitor.service -f | grep -i upload
```

You can also run one upload cycle by hand (stop the service first so the two do not run at the same time):

```bash
sudo systemctl stop eco-monitor.service
cd ~/multi-channel-rpi-eco-monitoring
bash rclone_upload.sh /home/pi/monitoring_data/live_data/RPiID-<serial> mybox \
    /home/pi/monitoring_data/live_data/rclone_state.json /dev/stdout \
    /home/pi/.config/rclone/rclone.conf
```

Check your cloud folder: the file should appear, and the local copy is deleted once it is verified on the remote.

---

## How Uploads Work

### Recording → Upload Workflow

1. **Record**: `arecord` writes a WAV in `/home/pi/tmp_dir/<date>/`, which is moved to `/home/pi/pre_upload_dir/<date>/`
2. **Compress**: `ffmpeg` converts it to FLAC in `/home/pi/monitoring_data/live_data/RPiID-<serial>/<date>/` (if `compress_data` is true)
3. **Detect internet**: the upload thread wakes every `record_length + capture_delay` seconds, or immediately when the recording loop sees internet. While internet is reachable, recording is paused
4. **Time sync**: `update_time.sh` runs before each upload cycle
5. **Upload**: `rclone_upload.sh` runs `rclone copy` (2 transfers, 4 checkers, 4 MB buffer, up to 3 attempts with backoff on exit codes 3–9)
6. **Verify and delete local**: files listed on the remote (`rclone lsf`) are marked `completed` and the local copy is deleted. Files that fail stay local and are retried next cycle

### State Tracking

The system uses `rclone_state.json` (in `/home/pi/monitoring_data/live_data/`) to track uploads:
- Each `.flac` / `.wav` file is `pending`, `uploading` or `completed`
- Survives Pi reboots (atomic writes)
- Before each copy, files already on the remote are marked `completed`, so they are not uploaded again

---

## Common Rclone Commands

These are manual commands for checking a Pi's data; `LIVE` is `/home/pi/monitoring_data/live_data/RPiID-<serial>`.

### Upload a folder
```bash
rclone copy "$LIVE" mybox:monitoring_data/RPiID-<serial>/
```

### Check what will be uploaded (dry-run)
```bash
rclone --dry-run copy "$LIVE" mybox:monitoring_data/RPiID-<serial>/
```

### Show upload progress verbosely
```bash
rclone -v copy "$LIVE" mybox:monitoring_data/RPiID-<serial>/
```

### Verify files on cloud match local
```bash
rclone check "$LIVE" mybox:monitoring_data/RPiID-<serial>/
```

Note: files are deleted locally after a verified upload, so `rclone check` will report remote-only files as expected.

---

## Bandwidth Limiting (Optional)

There is no config option for this. To limit upload bandwidth, add a flag such as `--bwlimit 1M` to the `rclone_args` array in `rclone_upload.sh`. Keep in mind that the auto-update on service start resets local edits to `origin/master`, so such a change has to be committed upstream.

---

## Troubleshooting

### "Remote not found" error

Check rclone config:
```bash
rclone listremotes --config /home/pi/.config/rclone/rclone.conf
```

If empty, rerun `rclone config` to set up your service.

### Upload fails with authentication error

Your cloud service credentials may have expired:
```bash
rclone config reconnect mybox:
```

Then follow the prompts to re-authenticate. If you use Gist sync, the refreshed `rclone.conf` is pushed to the Gist at the next upload cycle or service start.

### Slow uploads

Check your network:
```bash
# Test connection to Pi
ping <pi-ip>

# Check Pi internet speed
curl -o /dev/null -s -w '%{speed_download}\n' https://www.google.com
```

Consider:
- Using bandwidth limits (see above)
- Moving the Pi closer to the access point
- Using a faster cloud service

Remember that recording is paused while internet is reachable, so a slow upload also means a longer gap in recording.

### Files not appearing on cloud

1. Check logs:
   ```bash
   grep -i upload ~/multi-channel-rpi-eco-monitoring/logs/logfile.log | tail -n 100
   tail -n 100 /home/pi/monitoring_data/live_data/rclone.log
   ```

2. Check the remote path:
   ```bash
   rclone lsf -R mybox:monitoring_data/RPiID-<serial>/ | tail
   ```

3. Check local recordings exist and uploads are enabled:
   ```bash
   ls -laR /home/pi/monitoring_data/live_data/ | tail
   grep -E '"upload_enabled"|"test_mode"' ~/multi-channel-rpi-eco-monitoring/config.json
   ```

---

## Advanced: Scheduled Uploads

There is no time-based upload schedule. Uploads happen whenever the Pi has internet (checked every `record_length + capture_delay` seconds, and before every recording). In the field this is usually controlled by when a WiFi network or hotspot is in range; see the field WiFi timer in [advanced_configuration.md](advanced_configuration.md).

---

## Multiple Deployment Sites

Several Pis can share one remote (and one `rclone.conf` via the Gist sync). Each Pi uploads to its own folder named after its CPU serial:

```
mybox:monitoring_data/RPiID-<serial-of-pi-1>/
mybox:monitoring_data/RPiID-<serial-of-pi-2>/
```

`target_path` cannot be used to choose a different folder per site (it is ignored by the current code), so keep a note of which serial is deployed where (`python3 discover_serial.py` prints it).

---

## Data Safety

### What happens if upload fails?

- Local file is **kept** (not deleted)
- Retry happens on next cycle
- State file prevents duplicate uploads

### What if Pi loses power during upload?

- The file being copied stays local and is copied again on the next cycle
- Files already on the remote are detected by the pre-verify step and are not re-uploaded
- Local files are only deleted after they are listed on the remote

### Can I access files during upload?

Yes, rclone uploads don't lock files. Note that a file disappears locally once its upload is verified.

---

## Performance Tips

| Scenario | Recommendation |
|----------|-----------------|
| Slow internet (< 1 Mbps) | Add `--bwlimit` or keep upload sessions short; recording is paused while online |
| Fast internet | No changes needed |
| Large backlog | Keep `compress_data: true` (FLAC) |
| Multiple Pis | Folders are per-Pi automatically (`RPiID-<serial>`) |
| Unreliable connection | Check `rclone.log` and the `[upload]` lines in the log |
| More RAM (Pi 3/4) | You can raise `--transfers` / `--buffer-size` in `rclone_upload.sh` |

---

## Next Steps

- **Review logs?** See [log_guide.md](log_guide.md)
- **Advanced settings?** See [advanced_configuration.md](advanced_configuration.md)
- **Troubleshooting?** See [troubleshooting.md](troubleshooting.md)

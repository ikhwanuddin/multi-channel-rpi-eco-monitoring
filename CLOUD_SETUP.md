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
curl https://rclone.org/install.sh | sudo bash
```

Verify installation:
```bash
rclone version
```

### Configure Your Cloud Service

Run the interactive configuration:

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

---

## Step 2: Create Target Folder on Cloud

```bash
# Create a folder on your cloud service for recordings
rclone mkdir mybox:ecosound_monitoring/deployment_01
```

---

## Step 3: Enable Online Mode in config.json

```bash
cd ~/multi-channel-rpi-eco-monitoring
python setup_config.py
```

When prompted:
- **Monitoring mode**: Choose `online`
- **Remote name**: Enter `mybox` (or your remote name)
- **Target path**: Enter `ecosound_monitoring/deployment_01/`

Or manually edit `config.json`:

```json
{
  "record": {
    "monitoring_mode": "online",
    ...
  },
  "upload": {
    "remote_name": "mybox",
    "target_path": "ecosound_monitoring/deployment_01/",
    "rclone_config_path": "~/.config/rclone/rclone.conf"
  }
}
```

---

## Step 4: Test Upload

```bash
# Create a test recording (30 seconds)
python python_record.py --duration 30

# Manually trigger upload
./rclone_upload.sh ~/multichannel_audio mybox .rclone_state.json
```

Check your cloud folder—the file should appear!

---

## How Uploads Work

### Recording → Upload Workflow

1. **Record**: Audio captured in `~/multichannel_audio/`
2. **Verify**: File integrity checked
3. **Upload**: Rclone copies to cloud (with bandwidth throttling if configured)
4. **Delete Local**: Original file deleted (if `keep_recorded_data: false`)
5. **Resume on Failure**: State file tracks what's been uploaded

### State Tracking

The system uses `.rclone_state.json` to track uploads:
- Prevents re-uploading files
- Survives Pi reboots
- Cleaned periodically

---

## Common Rclone Commands

### Upload a folder
```bash
rclone copy ~/multichannel_audio mybox:target/path/
```

### Check what will be uploaded (dry-run)
```bash
rclone --dry-run copy ~/multichannel_audio mybox:target/path/
```

### Show upload progress verbosely
```bash
rclone -v copy ~/multichannel_audio mybox:target/path/
```

### Verify files on cloud match local
```bash
rclone check ~/multichannel_audio mybox:target/path/
```

---

## Bandwidth Limiting (Optional)

To avoid saturating your network, edit `recorder_startup_script.sh`:

```bash
# Add this before calling rclone:
rclone --bwlimit 1M copy ~/multichannel_audio mybox:target/path/
```

This limits uploads to 1 MB/s.

---

## Troubleshooting

### "Remote not found" error

Check rclone config:
```bash
rclone listremotes
```

If empty, rerun `rclone config` to set up your service.

### Upload fails with authentication error

Your cloud service credentials may have expired:
```bash
rclone config reconnect mybox
```

Then follow the prompts to re-authenticate.

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
- Recording during off-peak hours
- Using a faster cloud service

### Files not appearing on cloud

1. Check logs:
   ```bash
   tail -n 100 ~/logs/*.log | grep upload
   ```

2. Verify target path exists:
   ```bash
   rclone ls mybox:ecosound_monitoring/deployment_01/
   ```

3. Check local recordings exist:
   ```bash
   ls -la ~/multichannel_audio/
   ```

---

## Advanced: Scheduled Uploads

If you want uploads to happen at specific times (e.g., daily at 2 AM):

Add to `crontab`:
```bash
crontab -e
```

Add this line:
```
0 2 * * * ~/multi-channel-rpi-eco-monitoring/rclone_upload.sh ~/multichannel_audio mybox
```

---

## Multiple Deployment Sites

Run multiple Pis uploading to different cloud folders:

**Pi #1** (`config.json`):
```json
"target_path": "ecosound_monitoring/site_01/"
```

**Pi #2** (`config.json`):
```json
"target_path": "ecosound_monitoring/site_02/"
```

All upload to the same remote, different folders = easy to organize.

---

## Data Safety

### What happens if upload fails?

- Local file is **kept** (not deleted)
- Retry happens on next cycle
- State file prevents duplicate uploads

### What if Pi loses power during upload?

- Rclone resumes partial transfers
- State file ensures files aren't re-uploaded
- No data loss

### Can I access files during upload?

Yes, rclone uploads don't lock files. You can download or analyze while upload is in progress.

---

## Performance Tips

| Scenario | Recommendation |
|----------|-----------------|
| Slow internet (< 1 Mbps) | Increase `record_duration_s` to batch uploads |
| Fast internet | No changes needed |
| Large files (high bit depth) | Use FLAC codec + bandwidth limit |
| Multiple Pis | Use different cloud folders |
| Unreliable connection | Enable verbose logging for debugging |

---

## Next Steps

- **Review logs?** See [LOG_GUIDE.md](LOG_GUIDE.md)
- **Advanced settings?** See [advanced_configuration.md](advanced_configuration.md)
- **Troubleshooting?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

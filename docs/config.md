# Configuration Guide

Complete reference for all `config.json` options.

## Quick Overview

The `config.json` file controls how your monitoring system behaves. Generate it interactively with:

```bash
python installer.py
```

Or manually edit the file following this guide.

## Configuration Structure

```json
{
  "rclone": { /* Cloud upload settings */ },
  "gist": { /* GitHub Gist sync settings */ },
  "upload_enabled": true,
  "test_mode": 0,
  "sensor": { /* Sensor-specific options */ },
  "sys": { /* System-level settings */ }
}
```

---

## `upload_enabled`

**Type**: Boolean (`true` / `false`)  
**Default**: `true`

Controls whether the upload sync thread is started at runtime:

- `true` — Upload sync thread runs in background. Recording pauses when internet is detected so upload can use bandwidth. Recording resumes when upload completes or internet is unavailable.
- `false` — Murni recording lokal. Upload sync thread tidak dibuat.

Penentuan upload vs. recording dilakukan secara **runtime** oleh `is_internet_available()` — config ini hanya menentukan apakah thread upload diaktifkan.

```json
"upload_enabled": true
```

---

## `test_mode`

**Type**: Integer (0 or 1)  
**Default**: `0`

- `1` — Forces recording, skips all uploads (useful for testing).
- `0` — Standard behavior (upload if enabled and internet available).

```json
"test_mode": 0
```

---

## `sensor`

Root-level object containing sensor type and its specific options.

### `sensor_type`

**Type**: String  
**Options**: `"Sipeed7Mic"`, `"Respeaker6Mic"`, `"Respeaker4Mic"`, `"Respeaker_Custom"`  

Which microphone array to use.

```json
"sensor": {
  "sensor_type": "Sipeed7Mic"
}
```

### `device_index`

**Type**: Integer  
**Default**: `0`

Audio device index. Use `discover_serial.py` to find the right number:

```bash
python discover_serial.py
```

### `record_duration_s`

**Type**: Integer  
**Default**: `1200` (20 minutes)  
**Unit**: Seconds

How long to record in each interval.

```json
"record_duration_s": 1200
```

### `channels`

**Type**: Integer  
**Options**: `6` (Respeaker), `7` (Sipeed)  
**Default**: `7`

Number of microphone channels to record.

### `bit_depth`

**Type**: Integer  
**Options**: `16`, `24`, `32`  
**Default**: `16`

Bits per sample. Higher = better quality but larger files.

### `sample_rate`

**Type**: Integer  
**Options**: `16000`, `44100`, `48000`  
**Default**: `16000`

Samples per second (Hz). Standard for acoustic ecology: 16 kHz.

### `codec`

**Type**: String  
**Options**: `"flac"`, `"wav"`  
**Default**: `"flac"`

Audio format. FLAC is recommended (lossless + compressed).

### `server_sync_interval`

**Type**: Integer  
**Default**: `900` (15 minutes)  
**Unit**: Seconds

How often the upload sync thread checks for new files to upload.

---

## Rclone Settings (`rclone` section)

### `remote_name`

**Type**: String  
**Default**: `"mybox"`

Rclone remote name configured in `~/.config/rclone/rclone.conf`.

```json
"rclone": {
  "remote_name": "mybox",
  "config_path": "/home/pi/.config/rclone/rclone.conf",
  "remote_base_path": "monitoring_data",
  "target_path": "monitoring_data"
}
```

### `config_path`

**Type**: String  
**Default**: `"/home/pi/.config/rclone/rclone.conf"`

Full path to rclone configuration file.

### `remote_base_path`

**Type**: String  
**Default**: `"monitoring_data"`

Base path on remote storage where files are uploaded. The device serial is appended: `{remote_base_path}/{cpu_serial}`.

### `target_path`

(Deprecated alias for `remote_base_path`, kept for backwards compatibility.)

---

## Gist Settings (`gist` section)

Optional. Syncs `rclone.conf` across multiple Raspberry Pis via a private GitHub Gist.

### `enabled`

**Type**: Integer (0 or 1)  
**Default**: `1`

### `github_token`

**Type**: String  
**Default**: `""`

GitHub personal access token with Gist scope.

### `gist_id`

**Type**: String  
**Default**: `""`

The Gist ID (from URL) that stores the shared `rclone.conf`.

### `filename`

**Type**: String  
**Default**: `"rclone.conf"`

Filename inside the Gist.

---

## System Settings (`sys` section)

### `working_dir`

**Type**: String  
**Default**: `"/home/pi/tmp_dir"`

Temporary directory for active recordings.

### `upload_dir`

**Type**: String  
**Default**: `"/home/pi/monitoring_data"`

Root directory for processed FLAC files ready for upload.

### `reboot_time`

**Type**: String  
**Default**: `"02:00"`

Primary daily reboot time in 24-hour HH:MM format.

### `reboot_time_2`

**Type**: String  
**Default**: `""`

Optional second daily reboot time. Leave blank to disable.

### `use_system_shutdown_button`

**Type**: Integer (0 or 1)  
**Default**: `1`

- `1`: Use system-wide GPIO shutdown overlay (dtoverlay gpio-shutdown)
- `0`: Use Python GPIO listener

### `min_free_storage_gb`

**Type**: Float  
**Default**: `1.0`

Minimum free storage in GB. System shuts down below this threshold.

### `warn_free_storage_gb`

**Type**: Float  
**Default**: `4.0`

Warn when free storage falls below this threshold.

---

## Complete Example

```json
{
  "rclone": {
    "remote_name": "mybox",
    "config_path": "/home/pi/.config/rclone/rclone.conf",
    "remote_base_path": "monitoring_data",
    "target_path": "monitoring_data"
  },
  "gist": {
    "enabled": 1,
    "github_token": "",
    "gist_id": "",
    "filename": "rclone.conf"
  },
  "upload_enabled": true,
  "test_mode": 0,
  "sensor": {
    "sensor_type": "Sipeed7Mic",
    "device_index": 0,
    "record_duration_s": 360,
    "channels": 7,
    "bit_depth": 32,
    "sample_rate": 16000,
    "codec": "flac",
    "server_sync_interval": 900,
    "sleep_duration_s": 300
  },
  "sys": {
    "working_dir": "/home/pi/tmp_dir",
    "upload_dir": "/home/pi/monitoring_data",
    "reboot_time": "02:00",
    "reboot_time_2": "",
    "use_system_shutdown_button": 1,
    "min_free_storage_gb": 1.0,
    "warn_free_storage_gb": 4.0
  }
}
```

---

## Recording Parameters Explained

### Sample Rate & Bit Depth

Standard ecoacoustic monitoring uses **16 kHz / 16-bit**:
- Captures frequencies up to 8 kHz (Nyquist theorem)
- Sufficient for most animal calls and biophony
- Conservative file sizes
- Compatible with analysis tools

Higher settings (44.1 kHz / 24-bit) for:
- Ultra-high frequency recordings (bats, insects)
- Post-processing flexibility
- Expect 2-3× larger files

### Recording Duration

- **Short (5-15 min)**: Rapid site survey, testing setup
- **Medium (20-60 min)**: Typical field deployment
- **Long (2-4 hours)**: Continuous monitoring, higher battery drain

For autonomous recording: balance file size, storage, and ecological sampling intensity.

### Codec: FLAC vs WAV

| Codec | Size | Quality | Speed | Recommended |
|-------|------|---------|-------|-------------|
| FLAC | ~50% of WAV | Lossless | Slower | ✓ Yes (default) |
| WAV | 100% | Lossless | Faster | Legacy use |

FLAC is recommended: similar quality, half the storage, slightly more CPU used (acceptable on Pi).

---

## Troubleshooting Config Issues

### "Config not found" error

Create it:
```bash
python installer.py
```

### "Invalid sensor specified"

Check spelling. Valid values:
- `Sipeed7Mic`
- `Respeaker6Mic`
- `Respeaker4Mic`
- `Respeaker_Custom`

### Upload fails but no error message

Enable verbose logging in `config.json`:
```json
"upload_enabled": true
```

Then inspect logs:
```bash
grep -i error logs/*.log
```

---

## Next Steps

- **Recording test?** See [quickstart.md](quickstart.md)
- **Setting up cloud upload?** See [cloud_setup.md](cloud_setup.md)
- **Advanced settings?** See [advanced_configuration.md](advanced_configuration.md)
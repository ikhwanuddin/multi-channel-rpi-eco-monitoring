# Configuration Guide

Complete reference for all `config.json` options.

## Quick Overview

The `config.json` file controls how your monitoring system behaves. Generate it interactively with:

```bash
sudo python3 installer.py   # menu option 1, or 5 for full setup
```

Or manually edit the file following this guide. `config.json` is git-ignored and is kept by the auto-update.

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
**Default**: `true` (the installer always writes `true`; edit the file to change it)

Controls whether the upload sync thread is started at runtime:

- `true` — Upload sync thread runs in background. Recording pauses when internet is detected so upload can use bandwidth. Recording resumes once internet is no longer reachable and the sync trigger is cleared.
- `false` — Local recording only. The upload sync thread is not created.

Whether to upload or record is decided **at runtime** by `is_internet_available()` (a TCP connection to `8.8.8.8:53`); this setting only decides whether the upload thread exists.

Setting the environment variable `FORCE_OFFLINE_MODE=1` (or `true`/`yes`/`on`) for the service has the same effect as `upload_enabled: false` for that run.

Older configs that use `offline_mode` can be converted with installer menu option 7.

```json
"upload_enabled": true
```

---

## `test_mode`

**Type**: Integer (0 or 1)  
**Default**: `0`

- `1` — Forces recording even when internet is available, and skips all uploads (no upload thread).
- `0` — Standard behavior (upload if enabled and internet available).

```json
"test_mode": 0
```

---

## `sensor`

Root-level object containing sensor type and its specific options. Options not present in the file (or with the wrong type) fall back to the sensor's defaults.

### `sensor_type`

**Type**: String  
**Options**: `"Sipeed7Mic"`, `"Respeaker6Mic"`, `"Respeaker4Mic"`, `"Respeaker_Custom"`, `"UnixDevice"` (test sensor that reads `/dev/urandom`)  

Which sensor class to use. The installer also writes `sensor_index` (the number picked in its menu); it is not used at runtime.

```json
"sensor": {
  "sensor_type": "Sipeed7Mic"
}
```

### `record_length`

**Type**: Integer  
**Default**: `1200` (20 minutes)  
**Unit**: Seconds

Length of each recording.

```json
"record_length": 1200
```

### `capture_delay`

**Type**: Integer  
**Default**: `300` (5 minutes)  
**Unit**: Seconds

Pause between the end of one recording (and its compression) and the start of the next. The upload sync interval is derived from it: `server_sync_interval = record_length + capture_delay` (1500 s by default).

### `compress_data`

**Type**: Boolean  
**Default**: `true` for `Sipeed7Mic` and `Respeaker6Mic`, `false` for `Respeaker4Mic` and `Respeaker_Custom`

If `true`, each WAV is compressed to FLAC with `ffmpeg` (`-compression_level 2`) and the WAV is deleted. If `false`, the WAV is moved to the upload directory as-is.

### `microphone_number` (`Respeaker_Custom` only)

**Type**: Integer  
**Default**: `1`

Number of channels passed to `arecord -c`.

### Fixed audio format

Channels, sample rate and bit depth are **not** configurable in `config.json`; they are fixed in each sensor class:

| Sensor | ALSA device | Channels | Rate | Format |
|--------|-------------|----------|------|--------|
| `Sipeed7Mic` | `plughw:<card>,0` (card auto-detected from `arecord -l`, fallback `1`) | 8 | 16 kHz | `S16_LE` |
| `Respeaker6Mic` | `ac108` | 6 | 16 kHz | `S32_LE` |
| `Respeaker4Mic` | `ac108` | 4 | 16 kHz | `S32_LE` |
| `Respeaker_Custom` | `ac108` | `microphone_number` | 16 kHz | `S32_LE` |

The Sipeed MA-USB8 board streams 8 channels at 48 kHz natively; because the code opens it through `plughw`, ALSA resamples to 16 kHz. Per the [Sipeed MA-USB8 wiki](https://wiki.sipeed.com/hardware/en/modules/micarray_usbboard_bl616.html), CH0–CH5 are the ring microphones, CH6 is the board's beamformed output (time-aligned average of CH0–CH5, not a physical microphone) and CH7 is the centre microphone. The code does not remap channels.

---

## Rclone Settings (`rclone` section)

### `remote_name`

**Type**: String  
**Default**: `"mybox"`

Rclone remote name configured in your `rclone.conf`.

```json
"rclone": {
  "remote_name": "mybox",
  "config_path": "/home/pi/.config/rclone/rclone.conf",
  "target_path": "monitoring_data"
}
```

### `config_path`

**Type**: String  
**Default**: `"/home/pi/.config/rclone/rclone.conf"` (installer default; if empty, rclone's default lookup is used)

Full path to rclone configuration file.

### `target_path` / `remote_base_path`

**Type**: String  
**Default**: `"monitoring_data"`

Currently **has no effect**. The installer writes `target_path`; `record.py` reads `remote_base_path` and passes it to `rclone_upload.sh`, but the script ignores it. The remote path is hard-coded in `rclone_upload.sh` as:

```
<remote_name>:monitoring_data/RPiID-<cpu serial>/<YYYY-MM-DD>/<file>
```

---

## Gist Settings (`gist` section)

Optional. Syncs `rclone.conf` across multiple Raspberry Pis via a private GitHub Gist (`sync_rclone_config.sh`).

### `enabled`

**Type**: Integer (0 or 1)  
**Default**: `1` (installer prompt default)

Used by the installer to decide whether to ask for the token and Gist ID. The sync scripts do not read it: sync runs whenever `github_token` and `gist_id` are both non-empty.

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

Directory for the recording in progress (`<working_dir>/<YYYY-MM-DD>/`). Note: the post-processing step always scans `/home/pi/tmp_dir`, so keep the default.

### `upload_dir`

**Type**: String  
**Default**: `"/home/pi/monitoring_data"`

Root for finished files. Recordings go to `<upload_dir>/live_data/RPiID-<cpu serial>/<YYYY-MM-DD>/`; the upload state file `rclone_state.json` and `rclone.log` are written to `<upload_dir>/live_data/`. The staging directory `/home/pi/pre_upload_dir` is hard-coded.

### `reboot_time`

**Type**: String  
**Default**: `"02:00"`

Primary daily reboot time in 24-hour HH:MM format (local time). A reboot that falls during a recording is deferred until that recording finishes.

### `reboot_time_2`

**Type**: String  
**Default**: `""`

Optional second daily reboot time. Leave blank to disable.

`reboot_times` (list, or comma-separated string) is also accepted when editing by hand.

### `use_system_shutdown_button`

**Type**: Integer (0 or 1)  
**Default**: `1`

- `1`: Use system-wide GPIO shutdown overlay (dtoverlay gpio-shutdown)
- `0`: For ReSpeaker sensors, `record.py` listens on GPIO 26 itself. `Sipeed7Mic` never uses the Python listener.

### `min_free_storage_gb`

**Type**: Float  
**Default**: `1.0` (not written by the installer; add it by hand to change)

Minimum free storage in GB, checked on the upload directory before each recording. The Pi shuts down below this threshold. Data is never deleted automatically.

### `warn_free_storage_gb`

**Type**: Float  
**Default**: `4.0` (not written by the installer)

Warn when free storage falls below this threshold.

---

## Complete Example

As written by `installer.py` for a Sipeed unit (plus the two optional storage keys):

```json
{
  "rclone": {
    "remote_name": "mybox",
    "config_path": "/home/pi/.config/rclone/rclone.conf",
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
    "sensor_index": 4,
    "sensor_type": "Sipeed7Mic",
    "record_length": 1200,
    "compress_data": true,
    "capture_delay": 300
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

The Sipeed sensor records **16 kHz / 16-bit**:
- Captures frequencies up to 8 kHz (Nyquist theorem)
- Sufficient for most animal calls and biophony
- Conservative file sizes (one 20-minute, 8-channel WAV is about 307 MB before FLAC)

To change this you have to edit the `arecord` command in `sensors/Sipeed7Mic.py`; it is not a config option.

### Recording Duration

- **Short (5-15 min)**: Rapid site survey, testing setup
- **Medium (20-60 min)**: Typical field deployment
- **Long (2-4 hours)**: Continuous monitoring, higher battery drain

For autonomous recording: balance file size, storage, and ecological sampling intensity. Each recording is compressed before the next one starts, so long recordings also mean a longer compression step.

### FLAC vs WAV (`compress_data`)

| Output | Size | Quality | CPU | Recommended |
|-------|------|---------|-------|-------------|
| FLAC (`true`) | smaller than WAV | Lossless | ffmpeg run after each recording | ✓ Yes (default) |
| WAV (`false`) | 100% | Lossless | none | Legacy use |

Both `.flac` and `.wav` files are uploaded.

---

## Troubleshooting Config Issues

### "Config file not found" error

Create it:
```bash
sudo python3 installer.py   # menu option 1
```

### "Sensor type ... not found."

Check spelling. Valid values:
- `Sipeed7Mic`
- `Respeaker6Mic`
- `Respeaker4Mic`
- `Respeaker_Custom`
- `UnixDevice`

### Upload fails but no error message

Check that uploads are actually enabled (`"upload_enabled": true` and `"test_mode": 0`), then inspect logs:
```bash
grep -i "upload" ~/multi-channel-rpi-eco-monitoring/logs/logfile.log | tail -50
tail -n 100 /home/pi/monitoring_data/live_data/rclone.log
```

---

## Next Steps

- **Recording test?** See [quickstart.md](quickstart.md)
- **Setting up cloud upload?** See [cloud_setup.md](cloud_setup.md)
- **Advanced settings?** See [advanced_configuration.md](advanced_configuration.md)

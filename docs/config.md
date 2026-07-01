# Configuration Guide

Complete reference for all `config.json` options.

## Quick Overview

The `config.json` file controls how your monitoring system behaves. Generate it interactively with:

```bash
python setup_config.py
```

Or manually edit the file following this guide.

## Configuration Structure

```json
{
  "record": { /* Recording settings */ },
  "upload": { /* Cloud upload settings */ },
  "sys": { /* System-level settings */ }
}
```

---

## Recording Settings (`record` section)

### `sensor`
**Type**: String  
**Options**: `"sipeed7mic"`, `"respeaker4mic"`, `"respeaker6mic"`  
**Default**: `"sipeed7mic"`

Which microphone array to use.

```json
"sensor": "sipeed7mic"
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

```json
"channels": 7
```

### `bit_depth`
**Type**: Integer  
**Options**: `16`, `24`, `32`  
**Default**: `16`

Bits per sample. Higher = better quality but larger files.

```json
"bit_depth": 16
```

### `sample_rate`
**Type**: Integer  
**Options**: `16000`, `44100`, `48000`  
**Default**: `16000`

Samples per second (Hz). Standard for acoustic ecology: 16 kHz.

```json
"sample_rate": 16000
```

### `codec`
**Type**: String  
**Options**: `"flac"`, `"wav"`  
**Default**: `"flac"`

Audio format. FLAC is recommended (lossless + compressed).

```json
"codec": "flac"
```

### `monitoring_mode`
**Type**: String  
**Options**: `"offline"`, `"online"`  
**Default**: `"offline"`

- **offline**: Records locally, no uploads
- **online**: Records and uploads after each session

```json
"monitoring_mode": "offline"
```

### `keep_recorded_data`
**Type**: Boolean  
**Default**: `false`

- `true`: Keep local files after upload
- `false`: Delete after successful upload

```json
"keep_recorded_data": false
```

### `log_output_dir`
**Type**: String  
**Default**: `"logs"`

Directory for log files (created if doesn't exist).

```json
"log_output_dir": "logs"
```

---

## Upload Settings (`upload` section)

**Note**: Only required if `monitoring_mode` is `"online"`

### `remote_name`
**Type**: String  
**Default**: `"mybox"`

Rclone remote name configured in `~/.config/rclone/rclone.conf`.

```json
"remote_name": "mybox"
```

### `target_path`
**Type**: String  
**Default**: `""`

Path on cloud storage where files are uploaded.

```json
"target_path": "ecosystem_monitoring/site_01/"
```

### `rclone_config_path`
**Type**: String  
**Default**: `"~/.config/rclone/rclone.conf"`

Path to rclone configuration file.

```json
"rclone_config_path": "~/.config/rclone/rclone.conf"
```

---

## System Settings (`sys` section)

### `use_system_shutdown_button`
**Type**: Integer (0 or 1)  
**Default**: `0`

- `1`: Use GPIO shutdown button (Respeaker 6-Mic with device tree overlay)
- `0`: Use Python GPIO listener

Only relevant for Respeaker deployments. See [advanced_configuration.md](advanced_configuration.md).

```json
"use_system_shutdown_button": 1
```

### `timezone`
**Type**: String  
**Default**: `"UTC"`

IANA timezone identifier. Examples: `"Europe/London"`, `"America/New_York"`, `"Asia/Shanghai"`

```json
"timezone": "Europe/London"
```

---

## Complete Example: Offline Recording

```json
{
  "record": {
    "sensor": "sipeed7mic",
    "device_index": 0,
    "record_duration_s": 1200,
    "channels": 7,
    "bit_depth": 16,
    "sample_rate": 16000,
    "codec": "flac",
    "monitoring_mode": "offline",
    "keep_recorded_data": true,
    "log_output_dir": "logs"
  },
  "upload": {
    "remote_name": "",
    "target_path": "",
    "rclone_config_path": ""
  },
  "sys": {
    "use_system_shutdown_button": 0,
    "timezone": "UTC"
  }
}
```

## Complete Example: Online Upload

```json
{
  "record": {
    "sensor": "sipeed7mic",
    "device_index": 0,
    "record_duration_s": 900,
    "channels": 7,
    "bit_depth": 16,
    "sample_rate": 16000,
    "codec": "flac",
    "monitoring_mode": "online",
    "keep_recorded_data": false,
    "log_output_dir": "logs"
  },
  "upload": {
    "remote_name": "mybox",
    "target_path": "ecosound_data/deployment_01/",
    "rclone_config_path": "~/.config/rclone/rclone.conf"
  },
  "sys": {
    "use_system_shutdown_button": 0,
    "timezone": "Europe/London"
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
python setup_config.py
```

### "Invalid sensor specified"

Check spelling. Valid values:
- `sipeed7mic`
- `respeaker6mic`
- `respeaker4mic`

### Upload fails but no error message

Enable verbose logging in `config.json`:
```json
"log_output_dir": "logs"
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

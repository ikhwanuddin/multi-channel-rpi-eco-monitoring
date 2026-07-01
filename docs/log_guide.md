# Log Guide

Understanding logs and structured logging format.

## Quick Start

### View recent logs

```bash
# Last 50 lines
tail -n 50 ~/logs/*.log

# Follow logs in real-time
tail -f ~/logs/*.log

# Filter for errors
grep -i error ~/logs/*.log
```

---

## Log File Locations

```
~/logs/
├── startup.log          # Boot sequence, recorder startup
├── monitor.log          # Recording session details
└── upload.log           # Cloud upload events
```

---

## Structured Log Format

All logs use a **prefix contract** to make filtering easier:

```
[TIMESTAMP] [COMPONENT][mode=MODE][phase=PHASE] message
```

### Example Log Lines

```
[2024-07-01 14:23] [startup][mode=offline][phase=init] System boot detected
[2024-07-01 14:23] [startup][mode=offline][phase=config-load] Loaded config from ./config.json
[2024-07-01 14:24] [record][component=recording][phase=start] Recording to ./multichannel_audio/20240701_142400.flac
[2024-07-01 14:44] [record][component=recording][phase=finalize] Stopped recording - duration: 20 minutes
[2024-07-01 14:44] [upload][phase=verify][component=verify] File integrity OK: 287 MB
[2024-07-01 14:45] [upload][phase=finalize] Upload complete: 287 MB to mybox:site_01/
```

---

## Log Components

### Startup Phase

**Prefix**: `[startup]`

| Mode | Meaning |
|------|---------|
| `mode=offline` | Recording locally, no uploads |
| `mode=online` | Recording and uploading to cloud |

| Phase | Meaning |
|-------|---------|
| `phase=init` | System initializing |
| `phase=config-load` | Reading config.json |
| `phase=sensor-init` | Initializing audio sensor |
| `phase=ready` | System ready to record |

**Example**:
```bash
grep "\[startup\]" ~/logs/*.log
```

---

### Recording Phase

**Prefix**: `[record]`

| Component | Meaning |
|-----------|---------|
| `component=recording` | Main recording process |
| `component=audio-buffer` | Audio queue status |
| `component=gpio` | Shutdown button events |

| Phase | Meaning |
|-------|---------|
| `phase=start` | Recording session began |
| `phase=progress` | Recording in progress (per minute) |
| `phase=finalize` | Recording session ended |
| `phase=error` | Recording error occurred |

**Example**:
```bash
# All recording events
grep "\[record\]" ~/logs/*.log

# Only recording start/end
grep "\[record\]\[phase=\(start\|finalize\)\]" ~/logs/*.log

# Audio buffer warnings
grep "component=audio-buffer" ~/logs/*.log
```

---

### Upload Phase

**Prefix**: `[upload]`

| Component | Meaning |
|-----------|---------|
| `component=verify` | File verification before upload |
| `component=rclone` | Rclone copy operation |
| `component=state` | Upload state tracking |
| `component=upload-helper` | Upload helper script |

| Phase | Meaning |
|-------|---------|
| `phase=init` | Upload process starting |
| `phase=verify` | Checking file integrity |
| `phase=compress` | Compressing (if needed) |
| `phase=upload` | Transferring to cloud |
| `phase=finalize` | Upload completed successfully |
| `phase=error` | Upload failed |

**Example**:
```bash
# All upload events
grep "\[upload\]" ~/logs/*.log

# Only upload errors
grep "\[upload\]\[phase=error\]" ~/logs/*.log

# Upload success only
grep "\[upload\]\[phase=finalize\]" ~/logs/*.log

# Rclone diagnostics
grep "component=rclone" ~/logs/*.log
```

---

### Time Sync Phase

**Prefix**: `[time-sync]`

System synchronizes time with NTP servers.

| Mode | Meaning |
|------|---------|
| `mode=ntp` | Using Network Time Protocol |
| `mode=offline` | Using system clock (no internet) |

**Example**:
```bash
grep "\[time-sync\]" ~/logs/*.log
```

---

## Common Log Patterns

### Healthy recording session

```
[14:23] [startup][mode=offline][phase=init] System boot
[14:23] [startup][mode=offline][phase=config-load] Loaded config
[14:23] [startup][mode=offline][phase=sensor-init] Sipeed7Mic initialized
[14:23] [startup][mode=offline][phase=ready] Ready to record
[14:23] [record][component=recording][phase=start] Recording to file_202407011423.flac
[14:43] [record][component=recording][phase=progress] Recorded: 20 minutes, 287 MB
[14:43] [record][component=recording][phase=finalize] Stopped recording - OK
```

### Successful upload

```
[14:44] [upload][phase=init] Starting upload cycle
[14:44] [upload][phase=verify][component=verify] Checking file integrity
[14:44] [upload][phase=verify][component=verify] File OK: 287 MB
[14:45] [upload][component=rclone][phase=upload] Copying to cloud...
[15:02] [upload][component=rclone][phase=finalize] Copy complete
[15:02] [upload][phase=finalize] All files uploaded, deleting local copies
```

### Recording error (typical)

```
[14:23] [record][component=recording][phase=start] Starting...
[14:35] [record][component=audio-buffer][phase=error] OVERRUN ERROR
[14:35] [record][component=recording][phase=error] Recording aborted - audio buffer overrun
```

**Fix**: SD card too slow (see [troubleshooting.md](troubleshooting.md))

### Upload failure

```
[14:44] [upload][phase=init] Starting upload
[14:44] [upload][component=verify][phase=verify] File OK
[14:44] [upload][component=rclone][phase=upload] Attempting upload...
[14:55] [upload][component=rclone][phase=error] Connection timeout
[14:55] [upload][phase=error] Upload failed - will retry next cycle
[14:55] [record][component=recording][phase=start] Starting next recording...
```

**Note**: Local file is kept, upload retried on next cycle.

---

## Filtering Logs

### Find all errors in the last 24 hours

```bash
grep -h "\[phase=error\]" ~/logs/*.log
```

### Monitor specific component live

```bash
# Watch rclone operations
tail -f ~/logs/*.log | grep --line-buffered "component=rclone"

# Watch only upload phase
tail -f ~/logs/*.log | grep --line-buffered "\[upload\]"

# Watch only recording issues
tail -f ~/logs/*.log | grep --line-buffered "\[record\].*\[phase=\(progress\|error\)\]"
```

### Count events by type

```bash
# How many recording sessions?
grep -c "\[record\]\[phase=start\]" ~/logs/*.log

# How many uploads?
grep -c "\[upload\]\[phase=finalize\]" ~/logs/*.log

# How many errors total?
grep -c "\[phase=error\]" ~/logs/*.log
```

### Upload errors per day

```bash
grep "\[upload\]\[phase=error\]" ~/logs/*.log | \
  cut -d']' -f1 | tr -d '[' | cut -d' ' -f1 | sort | uniq -c
```

**Output**:
```
     3 2024-07-01
     1 2024-07-02
     0 2024-07-03
```

### Last 200 lines health snapshot

```bash
tail -n 200 ~/logs/*.log | grep -E "\[phase=(error|finalize|shutdown)\]"
```

This shows only key events (errors, completion, shutdown).

---

## Log Messages Explained

### Startup

| Message | Meaning | Action |
|---------|---------|--------|
| `Loaded config from ./config.json` | Config found and loaded | Normal |
| `config.json not found` | Config missing | Run `python setup_config.py` |
| `Sensor initialization failed` | Audio device not found | Check USB cable, run `discover_serial.py` |
| `Cannot write to logs directory` | Permission denied | `chmod 755 ~/logs` |

### Recording

| Message | Meaning | Action |
|---------|---------|--------|
| `Recording to file_...flac` | Session started | Normal |
| `OVERRUN ERROR` | Audio buffer dropped samples | SD card too slow, see troubleshooting |
| `Recorded: X minutes` | Progress update | Normal |
| `Stopping - keyboard interrupt` | Ctrl+C pressed | Normal if manual test |

### Upload

| Message | Meaning | Action |
|---------|---------|--------|
| `File integrity OK` | Verification passed | Normal |
| `Checking remote...` | Contacting cloud | Normal, may take time on slow network |
| `Upload complete` | File transferred | Normal |
| `Connection timeout` | No internet or slow network | Check network, retry later |
| `Authentication failed` | Cloud credentials expired | Re-auth: `rclone config reconnect mybox` |

---

## Log Rotation

Logs accumulate over time. To prevent disk fill:

### Manual cleanup

```bash
# Delete logs older than 30 days
find ~/logs -name "*.log" -mtime +30 -delete

# Or compress old logs
gzip ~/logs/*.log.old
```

### Automatic cleanup (Optional)

Add to `crontab`:

```bash
crontab -e
```

```
# Delete logs older than 30 days, daily at 3 AM
0 3 * * * find ~/logs -name "*.log" -mtime +30 -delete
```

---

## Advanced: Parsing Logs Programmatically

### Extract upload statistics

```bash
#!/bin/bash
# Parse upload logs to get summary

for log in ~/logs/upload*.log; do
  echo "=== $(basename $log) ==="
  grep "\[phase=finalize\]" "$log" | wc -l
  echo "Successful uploads"
  grep "\[phase=error\]" "$log" | wc -l
  echo "Failed uploads"
done
```

### Monitor disk usage during recording

```bash
#!/bin/bash
# Track how much data each recording session uses

grep "Recording to" ~/logs/*.log | while read line; do
  file=$(echo "$line" | grep -oP "(?<=to ).*(?=\s)")
  if [ -f "$file" ]; then
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    echo "$file: $(numfmt --to=iec-i --suffix=B $size 2>/dev/null || echo $size bytes)"
  fi
done
```

---

## Troubleshooting Based on Logs

**No logs appearing**:
```bash
# Check directory exists
ls -la ~/logs/

# Check permissions
touch ~/logs/test.log

# If touch fails, fix:
chmod 755 ~/logs
```

**Logs full of errors**:
```bash
# Get error summary
grep "\[phase=error\]" ~/logs/*.log | head -5

# Most common error?
grep "\[phase=error\]" ~/logs/*.log | sort | uniq -c | sort -rn
```

**Can't find specific event**:
```bash
# Unsure of exact format? Search for keywords:
grep -i "upload" ~/logs/*.log
grep -i "recording" ~/logs/*.log
grep -i "error" ~/logs/*.log
```

---

## See Also

- [troubleshooting.md](troubleshooting.md) - Interpreting error messages
- [advanced_configuration.md](advanced_configuration.md) - Log configuration options
- [config.md](config.md) - `log_output_dir` setting

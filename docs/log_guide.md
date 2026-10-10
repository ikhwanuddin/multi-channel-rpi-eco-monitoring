# Log Guide

Understanding where logs go and what the lines mean.

## Quick Start

### View recent logs

```bash
cd ~/multi-channel-rpi-eco-monitoring

# Last 50 lines
tail -n 50 logs/logfile.log

# Follow logs in real-time
tail -f logs/logfile.log

# Filter for errors
grep -iE "error|critical|failed" logs/logfile.log

# Full service output (includes the ExecStartPre steps)
sudo journalctl -u eco-monitor.service -f
```

If you installed the shell shortcuts (installer menu 4), `monitor` shows a health snapshot followed by the live journal of `eco-monitor` and `wifi-field-timer`, and `healtheco` shows only the snapshot.

---

## Log File Locations

```
~/multi-channel-rpi-eco-monitoring/logs/logfile.log   # record.py log (appended across restarts, not rotated)
journalctl -u eco-monitor.service                      # same lines + ExecStartPre output + update_time.sh output
/home/pi/monitoring_data/live_data/rclone.log          # rclone_upload.sh messages (appended each upload cycle)
/home/pi/monitoring_data/live_data/rclone_state.json   # upload state (JSON, not a log)
journalctl -u wifi-field-timer.service                 # field WiFi timer
/var/log/wifi-field-timer.log                          # same, best-effort file copy
```

At startup, any other `*.log` file found in `logs/` (anything except `logfile.log`) is moved to `live_data/RPiID-<serial>/logs/`. Log files are not uploaded (the uploader only tracks `.flac` and `.wav`).

---

## Log Format

`record.py` uses a `MinuteBoundaryFormatter`: a line is prefixed with `[YYYY-MM-DD HH:MM]` only when the minute changes; the following lines in the same minute have no timestamp. There are no level names in the file.

```
[2026-07-01 14:23] Start of continuous sampling: 20260701_1423
Starting repository auto-update...
Auto-update complete.
Config file found
Config loaded
Sensor type Sipeed7Mic being configured.
Detected USB audio card: 2
Sipeed7Mic Sensor config succeeded.
Sensor setup succeeded
Draining pending queue before first recording...
[2026-07-01 14:24] Capture started.
Recording started: 14-24-03_dur=1200secs
[2026-07-01 14:44] arecord exit code=0, size=307200044 bytes.
Recorded: 293.0 MB -> 14-24-03_dur=1200secs.wav
Recording done.
Capture completed in 1201.3s.
```

(Values above are illustrative.) A banner with the shell shortcut list is printed at each start.

Scripts launched by `record.py` add their own prefixes:

| Source | Prefix | Where |
|---|---|---|
| `rclone_upload.sh` | `[upload] [upload:<phase>] ...` (record.py adds `[upload] `) | `logfile.log`, journal, `rclone.log` |
| `sync_rclone_config.sh` | `[gist-sync] ...` | journal, `rclone.log` (when pushed after an upload) |
| `offline_time_sync.py` | `[*] ...` | journal |
| `wifi_field_timer.sh` | `[YYYY-MM-DD HH:MM:SS] [wifi-field-timer] ...` | journal, `/var/log/wifi-field-timer.log` |

---

## Log Components

### Startup

Lines written once per service start, in this order:

| Message | Meaning |
|---------|---------|
| `Start of continuous sampling: <YYYYMMDD_HHMM>` | `record.py` started |
| `Starting repository auto-update...` / `Auto-update complete.` | `git reset --hard origin/master` done |
| `Current git commit hash: ...` | Code version in use |
| `Config file found` / `Config loaded` | `config.json` parsed |
| `Configured daily reboot times: 02:00` | Scheduled reboot active |
| `Storage safety policy: no auto-delete, warn below 4.00 GB, shutdown below 1.00 GB` | Storage thresholds |
| `Sensor setup succeeded` | Sensor ready |
| `Running with upload enabled - upload sync thread active` | Upload thread started |

The `ExecStartPre` steps (fake-hwclock restore, time sync, filesystem check, LED off, Gist sync) appear only in the journal:

```bash
sudo journalctl -u eco-monitor.service -b | grep -E "fake-hwclock|gist-sync|FS |LEDs"
```

---

### Recording

| Message | Meaning |
|---------|---------|
| `Capture started.` / `Recording started: <file>` | New recording |
| `arecord exit code=<n>, size=<bytes> bytes.` | Logged after every recording |
| `arecord stderr: ...` | Any `arecord` warning (e.g. `overrun!!!`) |
| `Recorded: <MB> MB -> <file>.wav` | WAV moved to `pre_upload_dir` |
| `Recording failed: ...` | Failure; a `*_ERROR_audio-record-failed` marker is written |
| `Tiny file: n/3 consecutive.` | Small/failed recording; at 3 the Pi reboots |
| `Compressing <file> -> FLAC` / `Compression done: <file>.flac` | ffmpeg step |
| `CPU governor set to powersave` / `ondemand` | Power saving switch |
| `RAM[gc]: ...` / `RAM[skip-gc]: ...` | Memory snapshot after each cycle |
| `Upload in progress (internet=True, syncing=False); pausing record.` | Recording paused because internet is reachable |

**Example**:
```bash
grep -E "Recording started|Recorded:|Recording failed" logs/logfile.log | tail
```

---

### Upload

`rclone_upload.sh` tags each line with its phase: `init`, `scan-mark`, `rclone-copy`, `verify`, `finalize`, `error`.

| Phase | Meaning |
|-------|---------|
| `init` | Paths, remote and config file printed |
| `scan-mark` | Pre-verify against remote, then mark local files as `uploading` |
| `rclone-copy` | `rclone copy` running; one-line `stats` every 30 s |
| `verify` | Remote listing compared; verified local files deleted |
| `finalize` | Cycle completed; Gist push (or "Skipping Gist push (throttled ...)") |
| `error` | `rclone copy` failed after retries; files kept for next cycle |

`record.py` also logs `Internet detected. Starting immediate upload sync.`, `Upload sync completed successfully.` or `Upload sync failed with exit code <n>`.

**Example**:
```bash
# All upload events
grep "\[upload" logs/logfile.log

# Only upload errors
grep "\[upload:error\]" logs/logfile.log

# Upload success only
grep "Upload sync completed successfully" logs/logfile.log

# Rclone copy-phase lines
grep "\[upload:rclone-copy\]" logs/logfile.log
```

---

### Time Sync

`update_time.sh` prints plain messages (no prefix) to the journal, both at service start and before every upload cycle:

| Message | Meaning |
|------|---------|
| `Internet detected and clock already synced. Time not updated.` | NTP already in sync |
| `Internet detected, syncing time via NTP` | `timedatectl set-ntp true` |
| `Attempting silent automatic offline time sync via Wi-Fi gateway...` | No internet; trying the gateway |
| `Offline mode: syncing time from SSH-provided epoch <n>` | `--epoch` used |

**Example**:
```bash
sudo journalctl -u eco-monitor.service | grep -iE "time sync|NTP|already synced|\[\*\]"
```

---

## Common Log Patterns

### Healthy recording session

```
[2026-07-01 14:24] Capture started.
Recording started: 14-24-03_dur=1200secs
[2026-07-01 14:44] arecord exit code=0, size=307200044 bytes.
Recorded: 293.0 MB -> 14-24-03_dur=1200secs.wav
Recording done.
Capture completed in 1201.3s.
Last recording file ... size is ... bytes, OK.
RAM[skip-gc]: 41 MB proc, 230/416 MB free/total, 0 objects freed (continuous_recording).
CPU governor set to powersave
```

### Successful upload

```
Internet detected. Starting immediate upload sync.
[upload] Launching rclone_upload.sh...
[upload] [upload:init] === Starting rclone upload ===
[upload] [upload:scan-mark] Pre-verifying existing files on remote...
[upload] [upload:rclone-copy] Starting rclone copy process...
[upload] [upload:verify] Upload verification complete: 3 files deleted after verification
[upload] [upload:finalize] Rclone upload cycle completed successfully
Upload sync completed successfully.
```

### Recording error (typical)

```
arecord exit code=1, size=0 bytes.
arecord stderr: arecord: main:...: audio open error: No such file or directory
Recording failed: arecord exited with code 1 | ...
Tiny file: 1/3 consecutive.
```

**Fix**: check the USB connection and `arecord -l` (see [troubleshooting.md](troubleshooting.md))

### Upload failure

```
[upload] [upload:rclone-copy] Rclone copy failed (exit 5), retrying in 10s (attempt 1/3)...
[upload] [upload:rclone-copy] Rclone copy failed after retries with exit code 5
[upload] [upload:error] Rclone copy failed, files kept for retry
Upload sync failed with exit code 5
```

**Note**: Local file is kept, upload retried on next cycle.

---

## Filtering Logs

### Find all errors

```bash
grep -iE "error|failed|critical" logs/logfile.log | tail -n 50
```

### Monitor specific component live

```bash
# Watch rclone operations
tail -f logs/logfile.log | grep --line-buffered "\[upload:rclone-copy\]"

# Watch only upload lines
tail -f logs/logfile.log | grep --line-buffered "\[upload"

# Watch only recording issues
tail -f logs/logfile.log | grep --line-buffered -E "arecord stderr|Recording failed|Tiny file"
```

### Count events by type

```bash
# How many recordings?
grep -c "Recording started" logs/logfile.log

# How many successful upload cycles?
grep -c "Upload sync completed successfully" logs/logfile.log

# How many failed recordings?
grep -c "Recording failed" logs/logfile.log
```

### Upload errors per day

Lines in the same minute have no timestamp, so per-day counts are easiest from the journal:

```bash
sudo journalctl -u eco-monitor.service -o short-iso | grep "Upload sync failed" | cut -c1-10 | sort | uniq -c
```

### Last 200 lines health snapshot

```bash
tail -n 200 logs/logfile.log | grep -iE "error|failed|WATCHDOG|Storage low|Scheduled reboot"
```

---

## Log Messages Explained

### Startup

| Message | Meaning | Action |
|---------|---------|--------|
| `Config file found` | Config found and loaded | Normal |
| `Config file not found` | Config missing | Run `sudo python3 installer.py` (menu 1) |
| `Failed to load config` | A required key (`sys`, `rclone`, `sensor`, `working_dir`, `upload_dir`) is missing | Regenerate or fix `config.json` |
| `Sensor setup failed.` | Sensor `setup()` returned false | Check sensor and `arecord -l` |
| `No environment variable set for cpu_serial` | `PI_ID` missing (run outside the service) | Normal when run by hand; files go under `CPU_SERIAL_ERROR` |

### Recording

| Message | Meaning | Action |
|---------|---------|--------|
| `Recording started: <file>` | Session started | Normal |
| `arecord stderr: overrun!!!` | Audio buffer dropped samples | SD card / power, see troubleshooting |
| `File too small: ... discarding.` | Recording under 1 MB was deleted | Check sensor |
| `Storage low on ...` | Free space under `warn_free_storage_gb` | Offload data |
| `Storage below safe threshold ... Safely shutting down.` | Under `min_free_storage_gb` | Offload data |

### Upload

| Message | Meaning | Action |
|---------|---------|--------|
| `Internet not available. Skipping sync.` | Periodic check, offline | Normal |
| `ERROR: jq binary not found` | `jq` missing | `sudo apt-get install jq` |
| `ERROR: rclone binary not found in PATH` | rclone missing | Install rclone |
| `Upload verification complete: N files deleted after verification` | Files on remote, deleted locally | Normal |
| `WATCHDOG: upload sync thread has not reported a heartbeat ...` | Upload thread stalled | Restart the service |

---

## Log Rotation

`logs/logfile.log` is appended forever and is not rotated; `rclone.log` likewise. To prevent disk fill:

### Manual cleanup

```bash
# Truncate the recorder log (stop the service first)
sudo systemctl stop eco-monitor.service
: > ~/multi-channel-rpi-eco-monitoring/logs/logfile.log
sudo systemctl start eco-monitor.service
```

### Automatic cleanup (Optional)

Not provided by this repository. The journal is managed by `journald` (see `journalctl --disk-usage`).

---

## Advanced: Parsing Logs Programmatically

### Upload state summary

```bash
jq '.upload_stats' /home/pi/monitoring_data/live_data/rclone_state.json
```

### Recording sizes

```bash
grep -E "^Recorded:|Recorded:" ~/multi-channel-rpi-eco-monitoring/logs/logfile.log | tail -n 20
```

---

## Troubleshooting Based on Logs

**No logs appearing**:
```bash
# Is the service running?
sudo systemctl status eco-monitor.service

# Check directory exists
ls -la ~/multi-channel-rpi-eco-monitoring/logs/
```

**Logs full of errors**:
```bash
# Most common error lines
grep -iE "error|failed" logs/logfile.log | sed 's/^\[[^]]*\] //' | sort | uniq -c | sort -rn | head
```

**Can't find specific event**:
```bash
# Unsure of exact format? Search for keywords:
grep -i "upload" logs/logfile.log
grep -i "recording" logs/logfile.log
grep -i "error" logs/logfile.log
```

---

## See Also

- [troubleshooting.md](troubleshooting.md) - Interpreting error messages
- [advanced_configuration.md](advanced_configuration.md) - Runtime optimizations and their log lines
- [config.md](config.md) - Configuration reference

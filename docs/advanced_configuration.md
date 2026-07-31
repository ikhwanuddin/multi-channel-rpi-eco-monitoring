# Advanced Configuration Guide

This document contains additional setup instructions for specialized configurations and optimizations for the multi-channel Raspberry Pi ecosystem monitoring system.

> **Note**: For fundamental configuration of operational modes (Forest/Home/Test) and how to safely edit `config.json`, please refer to the [Configuration & Operational Scenarios](../README.md#configuration--operational-scenarios) section in the `README.md`.

## GPIO Shutdown Button via the Installer (Recommended)

The integrated installer (`installer.py`, menu option 3) is the recommended way to configure the GPIO shutdown button. It combines both the boot-config overlay and the `config.json` flag in a single step:

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py
# Select menu option 3 (Configure GPIO shutdown button)
sudo reboot
```

The installer detects the sensor type from `config.json` and suggests the appropriate default pin (GPIO 21 for Sipeed, GPIO 26 for Respeaker). It applies the `dtoverlay=gpio-shutdown` overlay and sets `sys.use_system_shutdown_button=1` automatically.

The manual and helper-script methods below are still available as alternatives.

## Shutdown Button Setup for Sipeed 7-Mic Array

![GPIO Pin on Raspberry Pi Zero 2 W](https://i.sstatic.net/yHddo.png)

*GPIO Pin on Raspberry Pi Zero 2 W.*

If using Sipeed 7-Mic Array sensor, you can set up a hardware shutdown button using device tree overlay:

* Edit `/boot/config.txt` (or `/boot/firmware/config.txt` on newer OS versions):
  ```
  sudo nano /boot/config.txt
  ```

* Add this line at the end of the file:
  ```
  dtoverlay=gpio-shutdown,gpio_pin=21,active_low=1,gpio_pull=up
  ```

* Save and exit (Ctrl+X, Y, Enter)

* Reboot the Raspberry Pi:
  ```
  sudo reboot
  ```

This configures GPIO pin 21 as a shutdown button. Connect a momentary push button between GPIO 21 and GND. Pressing the button will trigger a safe system shutdown.

**Note**: This is a system-level configuration that works independently of the Python monitoring script.

## Shutdown Button Setup for Respeaker 6-Mic (System-Wide)

For Respeaker 6-Mic deployments, you can also use a system-level shutdown button so it still works even if the Python recorder is not running.

* Edit `/boot/config.txt` (or `/boot/firmware/config.txt` on newer OS versions):
  ```
  sudo nano /boot/config.txt
  ```

* Add this line at the end of the file:
  ```
  dtoverlay=gpio-shutdown,gpio_pin=26,active_low=1,gpio_pull=up
  ```

* Save and exit (Ctrl+X, Y, Enter)

* Reboot the Raspberry Pi:
  ```
  sudo reboot
  ```

This configures GPIO pin 26 as a shutdown button. Connect a momentary push button between GPIO 26 and GND.

To avoid duplicate handling with the Python GPIO listener, set this in your `config.json`:

```json
{
  "sys": {
    "use_system_shutdown_button": 1
  }
}
```

With `use_system_shutdown_button` enabled, `record.py` will skip registering the Python-side button callback for Respeaker sensors.

### One-command helper (alternative to the installer)

This repository provides `enable_system_shutdown_button.sh` to apply both changes automatically:

```bash
cd ~/multi-channel-rpi-eco-monitoring
chmod +x enable_system_shutdown_button.sh
sudo ./enable_system_shutdown_button.sh 26 ./config.json
sudo reboot
```

What it does:
* Adds (or replaces) `dtoverlay=gpio-shutdown,gpio_pin=26,active_low=1,gpio_pull=up` in boot config.
* Sets `sys.use_system_shutdown_button=1` in `config.json`.

## Power Saving Configuration

For long-term battery-powered monitoring deployments, you can reduce power consumption with these configurations:

### Disable HDMI Output
* **Option 1: Permanent configuration** (add to `/boot/config.txt`, recommended):
  ```
  hdmi_blanking=1
  hdmi_force_hotplug=0
  ```

* **Option 2: Run on startup** (legacy `recorder_startup_script.sh` — only if still using the /etc/profile method):
  ```
  # Disable HDMI to save power
  tvservice -o
  ```

### Disable Bluetooth
* Add to `/boot/config.txt`:
  ```
  dtoverlay=disable-bt
  ```

### Disable Activity LED
* **Option 1: Add to `/boot/config.txt`**:
  ```
  dtparam=act_led_trigger=none
  dtparam=act_led_activelow=on
  ```

* **Option 2: Run on startup** (legacy `recorder_startup_script.sh` — only if still using the /etc/profile method):
  ```
  # Disable activity LED to save power
  echo 0 > /sys/class/leds/led0/brightness
  ```

### Additional Power Saving Tips
* Use a quality power supply with appropriate voltage/current
* Disable unnecessary services: `sudo systemctl disable bluetooth.service`
* Consider using Raspberry Pi Zero 2 W for lower power consumption
* Monitor battery voltage if using battery power
* For field deployments with a USB WiFi dongle, enable the **field WiFi timer** below so the radio is not scanning all day

## Field WiFi Timer (20 min after boot, then sleep until reboot)

USB WiFi dongles draw significant current even with **no internet** (scan/reconnect). On power-limited units (e.g. Pi 2B + powerbank) this can contribute to under-voltage and short recordings.

`wifi_field_timer.sh` + `wifi-field-timer.service` implement a simple duty cycle:

| Phase | Behaviour |
|-------|-----------|
| Boot | WiFi **ON** (rfkill unblock + `wlan*` up) |
| First **20 min** max (`MAX_ON_SECONDS=1200`) | Stays on if a **network link** appears (wlan has IPv4 / default route via wlan) |
| No link within 15 min | WiFi **sleeps early** (typical forest: no SSID) |
| After 20 min | WiFi **forced sleep** even if still linked |
| Rest of uptime | WiFi stays off |
| Turn WiFi on again | **Reboot** the Pi (only supported method) |

### Install on the Pi (recommended)

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py
# Select: Enable / manage field WiFi timer
```

Manual install (same effect as the installer menu):

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo chmod +x wifi_field_timer.sh
sudo cp wifi-field-timer.service /etc/systemd/system/
sudo sed -i "s|__REPO_DIR__|$(pwd)|g" /etc/systemd/system/wifi-field-timer.service
sudo systemctl daemon-reload
sudo systemctl enable --now wifi-field-timer.service
```

### Verify

```bash
systemctl status wifi-field-timer
journalctl -u wifi-field-timer -f
# or
tail -f /var/log/wifi-field-timer.log

# After sleep:
rfkill list
ip -br link | grep wlan
```

### Tuning

Defaults are baked into the unit and script (`MAX_ON_SECONDS=1200`). Override via the systemd unit:

```ini
# /etc/systemd/system/wifi-field-timer.service  (under [Service])
Environment=MAX_ON_SECONDS=1200
Environment=NO_LINK_GRACE_SECONDS=900
Environment=CHECK_INTERVAL=30
```

Examples:

* Longer base upload window: `MAX_ON_SECONDS=1800` (30 min)
* Forest: fail faster if no AP: `NO_LINK_GRACE_SECONDS=300`
* Keep radio on the full window even without link (not recommended): set grace ≥ max

Then: `sudo systemctl daemon-reload && sudo systemctl restart wifi-field-timer`

### Notes

* Independent of `eco-monitor.service` — does **not** delay recording.
* Does not change `config.json` / `upload_enabled`; it only controls the radio.
* After WiFi sleeps, uploads wait until the next reboot window (or you upload at base after reboot).
* To disable: installer menu **Disable field WiFi timer**, or `sudo systemctl disable --now wifi-field-timer.service` and optionally `sudo rfkill unblock wifi`.

## Runtime Optimizations (Automatic)

The following optimizations are applied automatically by the recorder at runtime — no manual configuration is required. They are tuned for the Raspberry Pi Zero 2 W running on a limited powerbank and are documented here so behavior is predictable during field debugging.

### CPU Scaling Governor

`record.py` switches the CPU scaling governor between two modes to balance capture reliability and idle power draw:

| Phase | Governor | Reason |
|---|---|---|
| Boot and idle (between captures) | `powersave` | Lowest clock during long `capture_delay` gaps — biggest powerbank savings |
| `arecord` + `ffmpeg` (capture/postprocess) | `ondemand` | Allows short frequency bursts to keep up with audio and avoid xruns |

The switch is performed via `set_cpu_governor()` writing to
`/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` using `sudo`. If the
sysfs interface is unavailable (e.g. on a non-Pi host or in a container), the
call silently no-ops at `DEBUG` log level — it never blocks recording.

**Requirement:** the service user must be allowed to run
`echo <mode> > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor` via
`sudo` without a password, or the service must run as root. If sudo requires a
password, governor switching is skipped (logged at `DEBUG`) and the kernel's
default governor is used.

**Verification:**
```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```
Expect `powersave` while idle and `ondemand` during a recording cycle.

### Adaptive Garbage Collection

Previously `gc.collect()` ran on every recording cycle, causing a predictable
Python pause that could trigger `arecord` underruns on the Pi Zero 2 W. The
new `gc_and_log_memory()` is adaptive:

* Runs `gc.collect()` only when process RSS exceeds **120 MB**, **or**
* Once every **12 calls** as a leak safety net.

Log lines now tag the action so you can confirm it is working:
```
RAM[gc]:      134 MB proc, 312/484 MB free/total, 5321 objects freed (continuous_recording).
RAM[skip-gc]:  88 MB proc, 318/484 MB free/total, 0 objects freed (upload_server_sync).
```

No configuration is exposed — the thresholds are tuned for the Pi Zero 2 W
(512 MB RAM). If you deploy on a higher-RAM Pi (3/4/5) and want more eager
collection, edit `GC_THRESHOLD_MB` and `GC_FORCE_EVERY_N_CALLS` in
`record.py`.

### Upload Sync Thread Watchdog

The `upload_server_sync` thread is now wrapped in a `try/except` per loop
iteration so a transient exception no longer silently kills all future uploads
until the next full process restart. Each iteration updates a heartbeat in
`sync_watchdog["last_beat"]`.

The main idle loop monitors this heartbeat and logs a `WATCHDOG` error if the
sync thread has not reported in for longer than `3 * server_sync_interval + 300`
seconds. This catches silent stalls that `systemd`'s `Restart=always` cannot
detect (the process is still alive, just not syncing).

**Filter watchdog events:**
```bash
grep -hE "WATCHDOG" logs/*.log
```

The watchdog only logs — it does not auto-restart the process. If you want a
stall to trigger `safe_shutdown()` (and thus a `systemd` restart), wire that
into the watchdog block in `record.py`.

### Rclone Tuning for Pi Zero 2 W

`rclone_upload.sh` now uses conservative concurrency tuned for 512 MB RAM:

| Flag | Old | New | Reason |
|---|---|---|---|
| `--transfers` | 4 | 2 | Concurrent uploads × buffer = peak RAM |
| `--checkers` | 8 | 4 | Fewer concurrent file stat calls |
| `--buffer-size` | 16M | 4M | 2 × 4 MB = 8 MB peak vs 4 × 16 MB = 64 MB |

This eliminates out-of-memory kills observed during large backlog uploads on
the Pi Zero 2 W. On higher-RAM Pi models you can safely raise these values
again in `rclone_upload.sh`.

### Gist Config Push Throttle

`_push_rclone_config_to_gist` in `rclone_upload.sh` is now throttled to **at
most once per hour** to avoid hammering the GitHub Gist API on every sync
cycle and to reduce network/power usage during frequent sync attempts.

* Throttle state is stored in `${TMPDIR:-/tmp}/eco_monitor_gist_push_last`
  (a Unix timestamp of the last successful push).
* A failed push does **not** update the stamp, so the next cycle retries.
* The stamp lives in `/tmp` and is cleared on reboot — meaning the first push
  after each boot still runs, which is the desired behavior.
* Throttled calls log:
  ```
  [upload:finalize] Skipping Gist push (throttled: last push 2400s ago, min interval 3600s)
  ```

To force an immediate push (e.g. after rotating the GitHub token), delete the
stamp file:
```bash
rm -f /tmp/eco_monitor_gist_push_last
```

### Time Sync Short-Circuit

`update_time.sh` now checks `timedatectl` before forcing an NTP re-sync. If
the system clock is already synchronised (`System clock synchronized: yes`),
it logs `already-synced` and returns immediately — skipping the previous
fixed 10-second `sleep`. This keeps the upload loop fast and avoids
unnecessary wake-ups on battery power.

New phase values in the time-sync log contract:
* `check-ntp` — about to inspect `timedatectl`
* `already-synced` — clock already synchronized, no action taken
* `sync-ntp` — NTP re-sync forced (previous behavior)

**Filter:**
```bash
grep -hE "already-synced|sync-ntp" logs/*.log
```

### Automated Offline Time Synchronization (Zero-Touch)

For forest/field deployments where no public internet is available, the system incorporates a 100% automated, zero-touch background time synchronization mechanism. This is fully integrated into the systemd boot flow via `eco-monitor.service` (using `ExecStartPre`).

When the Raspberry Pi boots up in the forest, if it is configured to connect to a local Wi-Fi router (such as a battery-powered travel router or field access point) or a mobile hotspot, it immediately detects the gateway IP and executes a silent, multi-layered synchronization query in the background before starting the main recording loop.

#### How it Works (Background Flow)

The automated system executes two sequential background probes against the local network gateway (the router or host device):

1. **Local NTP Query (Port 123)**:
   The RPi attempts a lightweight, standard NTP protocol request directly to the gateway's IP address. If the router or local AP runs an NTP server daemon (which is extremely common in OpenWRT or travel routers), the RPi parses the timestamp, sets the system clock, and writes the time to the Hardware Clock (RTC).
   
2. **Gateway HTTP Date Header Harvesting (Ports 80, 443, 8080, 8081)**:
   If the gateway does not respond to NTP, the RPi sends a rapid HTTP `HEAD` request to common web-admin ports of the gateway IP. Almost all local routers run a web configuration panel on port 80 or 443. The RPi captures the HTTP response's standard `Date` header, extracts the accurate calendar time, synchronizes the system clock, and writes it to the RTC.

If either of the probes succeeds, the clock is instantly updated within 2 seconds. If both probes fail (e.g., if there is no local Wi-Fi gateway or the router is offline), the system bypasses time sync gracefully without blocking or crashing, and starts recording using the current system time.

#### Operator Workflow (Zero-Touch)

The field operator does not need to perform any manual intervention:

1. Turn on the local field Wi-Fi router (which has its own clock set or was synchronized).
2. Power on the Raspberry Pi (MAARU).
3. The RPi connects to the Wi-Fi network, silently synchronizes its system time from the router in less than 2 seconds, and automatically launches `record.py` with the correct system time.

*No mobile web browser, terminal typing, SSH connection, or manual operator instructions are required.*

### State Manager: WAV + FLAC Tracking

`state_manager.py` previously only tracked `.flac` files, which meant
deployments with `compress_data=false` silently never uploaded anything.
It now tracks both `.flac` and `.wav` (case-insensitive) via
`TRACKED_EXTENSIONS`. Failure marker files (`*_ERROR_audio-record-failed`)
are still excluded automatically because they do not match either extension.

No action is needed for existing deployments — the fix is transparent. To
verify which files are queued for upload on a given Pi:
```bash
python3 state_manager.py init-scan-mark <data_dir> <state_file> | jq '.files_to_upload'
```

## Troubleshooting PyAudio Installation

If PyAudio installation fails on Raspberry Pi, try these alternatives:

### Option 1: Use system package (recommended for Raspberry Pi)
```bash
sudo apt-get install python3-pyaudio python3-psutil
```

### (DEPRECATED) Option 2: Manual installation with pip
```bash
# This method is deprecated as the project now relies on system packages
# Ensure dependencies are installed
sudo apt-get install portaudio19-dev python3-dev

# Install PyAudio
pip install --no-cache-dir pyaudio
```

### (DEPRECATED) Option 3: Force binary installation
```bash
pip install --only-binary=all pyaudio
```

### Test installation:
```bash
python3 -c "import pyaudio; print('PyAudio installed successfully')"
```
    
## Useful Shell Shortcuts

To speed up *debugging* and monitoring when connected via SSH, install shell shortcuts via the installer (re-run menu **4** after updating the repo so `monitor` picks up new checks):

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py
# Select menu option 4 (Install shell shortcuts)
source ~/.bashrc
```

| Shortcut | What it does |
|----------|----------------|
| **`monitor`** | **Health dashboard** then live logs (`eco-monitor` + `wifi-field-timer`). Ctrl+C quits the log follow. |
| **`healtheco`** | Health dashboard only (no log follow) — quick SSH check. |
| `statuseco` | `systemctl status` for eco-monitor + wifi-field-timer |
| `sizeeco` | Disk usage of monitoring folders |
| `restarteco` / `starteco` / `stopeco` | Restart / start / stop eco-monitor |

**`monitor` / `healtheco` dashboard includes:**

* Host model, uptime, load
* Service state: `eco-monitor.service`, `wifi-field-timer.service`
* WiFi: `rfkill`, each `wlan*` operstate + IPv4, default route, probe to 8.8.8.8
* Power: `vcgencmd get_throttled` **decoded** (under-voltage / throttle NOW vs since boot), volts, temp
* Disk free + `live_data` / `tmp_dir` / `pre_upload_dir` sizes
* Recent `dmesg` under-voltage / USB / I/O lines
* Recent journal warnings from both services

After install, type **`monitor`** or **`healtheco`** in the shell.

## Log Filter Examples (Prefix Contract)

The runtime logs use structured prefixes such as:

* `[startup][mode=online][phase=upload-loop] ...`
* `[upload][phase=verify][component=verify] ...`
* `[time-sync][mode=ntp][phase=sync-ntp] ...`

This makes targeted filtering easier during debugging.

### Find all startup logs in offline mode

```bash
grep -h "\[startup\]\[mode=offline\]" logs/*.log
```

### Follow only upload verify events live

```bash
tail -F logs/*.log | grep --line-buffered "\[upload\]\[phase=verify\]"
```

### Show only terminal upload outcomes (success or error)

```bash
grep -hE "\[upload\]\[phase=(finalize|error)\]" logs/*.log
```

### Show only time synchronization flow

```bash
grep -h "\[time-sync\]" logs/*.log
```

### Show rclone copy-phase lines only

```bash
grep -h "\[upload\]\[phase=rclone-copy\]" logs/*.log
```

`rclone` one-line stats are emitted every `30s` during this phase (`--stats 30s --stats-one-line`).

### Show helper state-scan lines only

```bash
grep -h "\[component=upload-helper\]" logs/*.log
```

### Count upload errors per day

```bash
grep -h "\[upload\]\[phase=error\]" logs/*.log | cut -d']' -f1 | tr -d '[' | cut -d' ' -f1 | sort | uniq -c
```

### Quick health snapshot (last 200 lines)

```bash
tail -n 200 logs/*.log | grep -E "\[phase=(error|finalize|shutdown)\]"
```

## Side Notes

* Be careful not to pull the power cable from the Pi (or pull the plug from the socket) - this has been known to corrupt the SD card, and requires a fresh install.
* Using a battery bank is a safe option - if it runs out of power, the Pi tends to shutdown safely.
* To safely power off, use the appropriate method for your sensor (e.g. button on Respeaker 6-Mic array or software shutdown), and wait for the green light (on the Pi) to stop flashing.

## Make a new disk image

* Take the microSD card from the Pi, and make a copy of it onto your computer [(How?)](https://howchoo.com/pi/create-a-backup-image-of-your-raspberry-pi-sd-card-in-mac-osx).
  * Note: May need to run ``sudo -i`` (before sudo dd...) - this puts the terminal into root mode
  * Note: After running sudo dd... it may take a while - You get no indication of how far through you are - as long as the no error appears in the terminal, or no new line for code entry, just wait (up to 1 hour for 32 GB SD card)
* Now you can clone as many of these SD cards as you need for your monitoring devices with no extra setup required - install on new SD card with Balena Etcher
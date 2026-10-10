# Quick Start Guide

Get your multi-channel ecosystem monitoring system up and running.

## Prerequisites

- Raspberry Pi (Zero 2 W, 3B+, or 4B)
- Sipeed 6+1 Mic Array with the Sipeed MA-USB8 USB board (recommended) or ReSpeaker 4/6-Mic Array (legacy)
- microSD card (Class 10, minimum 150 MB/s)
- Power supply (5V for Pi)
- Optional: Network connection (for cloud uploads, time sync and auto-update)

## Setup

### Prebuilt image

There is no prebuilt image for the Sipeed version. The image linked from Becky Heath's original repository ([Drive link](https://drive.google.com/file/d/1sTKPgUOcT4SQeJqtF6wdd6rjtqFLZzfR/view?usp=sharing)) is the **legacy Raspbian Buster image for ReSpeaker hardware** and does not contain this fork. Use the manual setup below.

### Manual Setup (Sipeed, current Raspberry Pi OS)

```bash
# 1. Flash current Raspberry Pi OS to the SD card (Raspberry Pi Imager or Balena Etcher).
#    Create the user "pi": recorder paths are hard-coded to /home/pi.
# 2. Insert card, power on, and SSH or connect directly

# 3. Install the system packages the code uses
sudo apt-get update
sudo apt-get install -y git python3-psutil python3-rpi.gpio alsa-utils ffmpeg rclone jq curl wget

# 4. Clone this repository into /home/pi
cd ~
git clone https://github.com/ikhwanuddin/multi-channel-rpi-eco-monitoring.git
cd multi-channel-rpi-eco-monitoring

# 5. Continue to Configuration below
```

There is no `requirements.txt` and no `pip install` step. The installer does not install packages.

For the legacy ReSpeaker path (Raspbian Buster, Seeed voicecard driver, frozen kernel), follow the original repository: [BeckyHeath/multi-channel-rpi-eco-monitoring](https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring).

## Configuration

Run the interactive installer as root:

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py
```

Menu:

```
  1) Configure sensor & generate config.json
  2) Install systemd service (eco-monitor.service)
  3) Configure GPIO shutdown button
  4) Install shell shortcuts (monitor, restarteco, ...)
  5) Full setup (1 -> 2 -> 3 -> 4, recommended)
  6) Migrate from legacy /etc/profile startup
  7) Migrate config.json to latest schema (remove has_internet, rename offline_mode)
  8) Show current status
  9) Enable / manage field WiFi timer (sleep 1200s after wlan lost)
  10) Exit
```

Choose **5 (Full setup)**. It runs, in order: generate `config.json`, install and enable `eco-monitor.service`, (optional) GPIO shutdown button, (optional) shell shortcuts, (optional) field WiFi timer.

`config.json` contains:
- Sensor type (pick `Sipeed7Mic`, option 4 in the sensor list) and its options: `record_length` (default 1200 s), `compress_data` (default true), `capture_delay` (default 300 s)
- `test_mode`
- rclone and GitHub Gist settings (optional)
- Working/upload directories, daily reboot time(s), shutdown button mode

The installer does not set the time zone. Recording file and folder names use local time, so set it with `sudo raspi-config` (Localisation Options) or `sudo timedatectl set-timezone <Area/City>`.

### Without Interactive Setup

If you prefer manual configuration, edit `config.json` directly (strict JSON, no comments, no trailing commas). See [config.md](config.md) for all options.

## Run It

### Start the service

The installer enables `eco-monitor.service`, so recording starts on every boot. To start it now:

```bash
sudo systemctl start eco-monitor.service
sudo systemctl status eco-monitor.service
```

There is no one-shot test command; the service records continuously in cycles of `record_length` seconds followed by a `capture_delay` pause. For a short test, set a small `record_length` in `config.json` and restart the service.

> **Recording pauses while internet is reachable** if `upload_enabled` is `true` and `test_mode` is `0`, so the upload can use the bandwidth. To record while connected to WiFi (e.g. bench testing at home), set `"test_mode": 1` (this also disables uploads).

> **Auto-update**: each time the service starts, `record.py` resets the repository to `origin/master` (local changes are discarded, `config.json` and `logs/` are kept).

### Reboot

```bash
sudo reboot
```

If you configured the GPIO shutdown button, a reboot is required for the overlay to take effect.

## What's Being Recorded?

- **Location**: `/home/pi/monitoring_data/live_data/RPiID-<cpu serial>/<YYYY-MM-DD>/`
- **File name**: `HH-MM-SS_dur=<record_length>secs.flac`
- **Format**: FLAC (lossless) when `compress_data` is true, otherwise WAV
- **Channels / rate**: Sipeed 8 channels, 16 kHz, 16-bit. ReSpeaker 6-Mic 6 channels, 16 kHz, 32-bit
- **Duration**: Configurable (default: 1200 s = 20 minutes, then a 300 s pause)

While a recording is in progress the WAV is in `/home/pi/tmp_dir/<date>/`, then it is moved to `/home/pi/pre_upload_dir/<date>/` and compressed into `live_data`.

## Next Steps

- **Upload to cloud?** See [cloud_setup.md](cloud_setup.md)
- **Troubleshooting?** See [troubleshooting.md](troubleshooting.md)
- **Advanced settings?** See [advanced_configuration.md](advanced_configuration.md)
- **Understanding logs?** See [log_guide.md](log_guide.md)

## Check It's Working

```bash
# SSH into your Pi and check latest recordings
ls -lhR /home/pi/monitoring_data/live_data/ | tail -5

# View recent logs
tail -n 50 ~/multi-channel-rpi-eco-monitoring/logs/logfile.log
sudo journalctl -u eco-monitor.service -n 50

# Or, if you installed the shell shortcuts (menu 4)
healtheco
monitor
```

## Safety Tips

⚠️ **Critical**: Do NOT pull the power cable suddenly. This can corrupt the SD card.

- Use a hardware **shutdown button** (see [advanced_configuration.md](advanced_configuration.md))
- Or use software shutdown: `sudo shutdown -h now`
- Wait for the Pi to finish shutting down before removing power (the service switches the green ACT LED off at start, so it may not flash as on a stock Pi)

---

**Need help?** Check the [README](../README.md) or [troubleshooting.md](troubleshooting.md) for common issues.

# multi-channel-rpi-eco-monitoring

Autonomous multichannel acoustic recording system for ecosystem monitoring using a Raspberry Pi and the Sipeed 6+1 Mic Array on the Sipeed MA-USB8 USB audio board (legacy ReSpeaker 4-Mic / 6-Mic hardware is still supported).

Part of the **MAARU** (Multichannel Acoustic Autonomous Recording Unit) project. Full project details: [beckyheath.github.io/MAARU](https://beckyheath.github.io/MAARU/)

This repository is a fork of [BeckyHeath/multi-channel-rpi-eco-monitoring](https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring), adapted by Rifqi Ikhwanuddin to run the Sipeed array on current Raspberry Pi OS (tested on Raspberry Pi Zero 2 W, 3B+ and 4B).

---

## 🚀 Quick Start

### New to this project?

1. **Read first**: [`docs/quickstart.md`](docs/quickstart.md) - Install and start recording
2. **Configure**: [`docs/config.md`](docs/config.md) - All options explained
3. **Deploy**: [`docs/cloud_setup.md`](docs/cloud_setup.md) - Enable cloud uploads (optional)
4. **Monitor**: [`docs/log_guide.md`](docs/log_guide.md) - Understand logs
5. **Help**: [`docs/troubleshooting.md`](docs/troubleshooting.md) - Common issues

### Experienced users?

- **System design**: [`docs/architecture.md`](docs/architecture.md)
- **Advanced config**: [`docs/advanced_configuration.md`](docs/advanced_configuration.md)
- **Documentation hub**: [`docs/index.md`](docs/index.md)

---

## 📋 What This Does

Records multichannel audio at ecosystem monitoring sites:

- **8-channel recording** from the Sipeed MA-USB8 board (6 ring mics, 1 beamformed channel, 1 centre mic), via `arecord`
- **16 kHz, 16-bit** (`S16_LE`) WAV; ALSA `plughw` resamples from the board's native 48 kHz
- **FLAC compression** (lossless, via `ffmpeg`) after each recording, optional
- **Local recording** and optional **cloud upload** through rclone (Box, Google Drive, Dropbox, etc.)
- **Auto-start on boot** via a systemd service (`eco-monitor.service`)
- **Logging** to `logs/logfile.log` and the systemd journal

---

## 💾 Hardware Options

### Recommended: Sipeed 6+1 Mic Array + MA-USB8 board (sensor `Sipeed7Mic`)
- USB Audio Class device, no extra kernel driver
- No kernel freezing required
- Works with current Raspberry Pi OS
- Recommended for new deployments

### Legacy: ReSpeaker 4-Mic / 6-Mic (sensors `Respeaker4Mic`, `Respeaker6Mic`, `Respeaker_Custom`)
- Older hardware, still in the code
- Needs the Seeed voicecard driver, so in practice an older Raspbian Buster image with the kernel frozen
- For this path, use the original repository ([BeckyHeath/multi-channel-rpi-eco-monitoring](https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring)) as the reference

---

## 🔧 Installation

There is **no prebuilt image** for the Sipeed version. (The disk image linked from Becky Heath's original repository is a legacy Raspbian Buster image for the ReSpeaker setup and does not contain this fork.)

### Manual Setup (current Raspberry Pi OS)

Several paths are hard-coded to `/home/pi` (for example `/home/pi/pre_upload_dir`), so create the user **`pi`** when flashing the OS and clone the repository into `/home/pi`.

```bash
sudo apt-get update
sudo apt-get install -y git python3-psutil python3-rpi.gpio alsa-utils ffmpeg rclone jq curl wget

cd ~
git clone https://github.com/ikhwanuddin/multi-channel-rpi-eco-monitoring.git
cd multi-channel-rpi-eco-monitoring
sudo python3 installer.py      # choose 5 = Full setup
```

There is no `requirements.txt` and no `pip install` step; the code runs from source using the system packages above. The installer does not install packages itself.

See [`docs/quickstart.md`](docs/quickstart.md) for detailed steps.

---

## 📚 Documentation

| Document | Purpose |
|----------|----------|
| [`quickstart.md`](docs/quickstart.md) | Install and first recording |
| [`config.md`](docs/config.md) | Configuration reference |
| [`cloud_setup.md`](docs/cloud_setup.md) | Cloud upload setup |
| [`troubleshooting.md`](docs/troubleshooting.md) | Common issues & solutions |
| [`log_guide.md`](docs/log_guide.md) | Log format & analysis |
| [`architecture.md`](docs/architecture.md) | System design |
| [`advanced_configuration.md`](docs/advanced_configuration.md) | Power saving, shutdown buttons, WiFi timer, etc. |
| [`physical-setup.md`](docs/physical-setup.md) | Enclosure and hardware notes |
| [`index.md`](docs/index.md) | Documentation hub |

---

## 📁 Project Structure

```
multi-channel-rpi-eco-monitoring/
├── README.md                     (this file)
├── docs/                         (all documentation)
│
├── installer.py                  (interactive installer: config.json, service, GPIO, shortcuts, WiFi timer)
├── record.py                     (main recorder, run by eco-monitor.service)
├── eco-monitor.service           (systemd unit template)
├── wifi_field_timer.sh           (field WiFi power saving)
├── wifi-field-timer.service      (systemd unit template for the WiFi timer)
├── rclone_upload.sh              (cloud upload, called by record.py)
├── state_manager.py              (upload state tracking, used by rclone_upload.sh)
├── sync_rclone_config.sh         (sync rclone.conf with a private GitHub Gist)
├── update_time.sh                (time sync: NTP, gateway, or SSH epoch)
├── offline_time_sync.py          (time sync from the Wi-Fi gateway)
├── discover_serial.py            (prints the Pi ID, RPiID-<cpu serial>)
├── check_fs_expanded.sh          (one-time root filesystem expansion)
├── enable_system_shutdown_button.sh (helper for the gpio-shutdown overlay)
├── led_on.sh / led_off.sh        (Sipeed board LEDs on/off)
├── clean_live_data.sh            (manual deletion of local live_data files)
├── sensors/                      (sensor classes)
├── audio_sensor_scripts/         (asound.state mixer levels)
├── pyproject.toml                (repository metadata only)
├── logs/                         (runtime log, created at first run)
└── config.json                   (your configuration, created by installer.py, git-ignored)
```

Recordings are written outside the repository, by default under `/home/pi/monitoring_data/live_data/RPiID-<serial>/<YYYY-MM-DD>/`.

---

## 🎯 Common Tasks

**I want to record locally:**
→ [`docs/quickstart.md`](docs/quickstart.md)

**I want to upload to the cloud:**
→ [`docs/cloud_setup.md`](docs/cloud_setup.md)

**Something broke:**
→ [`docs/troubleshooting.md`](docs/troubleshooting.md)

**I need to find something:**
→ [`docs/index.md`](docs/index.md)

---

## 💡 Key Features

- ✅ **8-channel recording** (Sipeed) with logging to file and journal
- ✅ **Multiple cloud services** via rclone (Box, Drive, Dropbox, S3, etc.)
- ✅ **Auto-start on boot** via systemd, with automatic restart on crash
- ✅ **Graceful shutdown** with an optional GPIO button (`dtoverlay=gpio-shutdown`)
- ✅ **State tracking** - uploads are verified on the remote before local files are deleted
- ✅ **Power saving** - Sipeed and ACT LEDs off, CPU governor switching, field WiFi timer
- ✅ **Configurable parameters** - recording length, pause between recordings, FLAC on/off, daily reboot times

> **Note**: on every service start, `record.py` force-updates the repository to `origin/master` (`git reset --hard`, then `git clean` keeping `config.json` and `logs/`). Local edits on the Pi are discarded. See [`docs/architecture.md`](docs/architecture.md).

---

## ⚙️ System Requirements

- **Raspberry Pi**: Zero 2 W, 3B+, 4B (tested; minimum 512 MB RAM)
- **OS**: current Raspberry Pi OS, user `pi`
- **Storage**: Class 10 SD card, **minimum 150 MB/s** read/write
- **Power**: 5V 2A+ supply
- **Sensor**: Sipeed 6+1 Mic Array + MA-USB8 board (recommended) or ReSpeaker 4/6-Mic (legacy)

---

## 📖 Full Setup Guide

Complete technical documentation available in `docs/` folder:

1. Start with [`docs/quickstart.md`](docs/quickstart.md)
2. Reference [`docs/config.md`](docs/config.md) for customization
3. Consult [`docs/troubleshooting.md`](docs/troubleshooting.md) for issues
4. See [`docs/architecture.md`](docs/architecture.md) for system design

For a comprehensive index, see [`docs/index.md`](docs/index.md).

---

## 👥 Credits

**Original project**: Becky Heath and contributors ([BeckyHeath/multi-channel-rpi-eco-monitoring](https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring)), building on Sarab Sethi's [rpi-eco-monitoring](https://github.com/sarabsethi/rpi-eco-monitoring)

**Contributors**: Rifqi Ikhwanuddin, Neel Le Penru, James Skinner, Sarab Sethi, and others

**Citation**: 
- Heath et al. (2024): *Spatial ecosystem monitoring with a Multichannel Acoustic Autonomous Recording Unit (MAARU)*
- Le Penru et al. (2024): *Towards using virtual acoustics for evaluating spatial ecoacoustic monitoring technologies*

---

## 📄 License

See LICENSE file for details.

---

## ❓ Need Help?

- **Quick answers**: See [`docs/index.md`](docs/index.md)
- **Setup issues**: See [`docs/troubleshooting.md`](docs/troubleshooting.md)
- **Configuration questions**: See [`docs/config.md`](docs/config.md)
- **Understand logs**: See [`docs/log_guide.md`](docs/log_guide.md)

---

**Ready to get started?** → Go to [`docs/quickstart.md`](docs/quickstart.md)

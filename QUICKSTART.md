# Quick Start Guide

Get your multi-channel ecosystem monitoring system up and running in 5 minutes.

## Prerequisites

- Raspberry Pi (Zero 2 W, 3B+, or 4B+)
- Sipeed 7-Mic Array (recommended) or Respeaker 4/6-Mic Array (legacy)
- microSD card (Class 10, minimum 150 MB/s)
- Power supply (5V for Pi)
- Optional: Network connection (for cloud uploads)

## 30-Second Setup

### Option 1: Use Prebuilt Image (Easiest)

1. Download the prebuilt image: [Drive link](https://drive.google.com/file/d/1sTKPgUOcT4SQeJqtF6wdd6rjtqFLZzfR/view?usp=sharing)
2. Flash to SD card using [Balena Etcher](https://www.balena.io/etcher/)
3. Insert SD card, power on, and go to **Configuration** below

### Option 2: Manual Setup (15 minutes)

```bash
# 1. Flash current Raspberry Pi OS to SD card (use Balena Etcher)
# 2. Insert card, power on, and SSH or connect directly

# 3. Clone this repository
git clone https://github.com/your-username/multi-channel-rpi-eco-monitoring.git
cd multi-channel-rpi-eco-monitoring

# 4. Install dependencies
pip install -r requirements.txt
sudo apt-get install portaudio19-dev

# 5. Continue to Configuration below
```

## Configuration

Run the interactive setup:

```bash
cd ~/multi-channel-rpi-eco-monitoring
python setup_config.py
```

This creates a `config.json` file with:
- Sensor type (Sipeed 7-Mic or Respeaker)
- Recording interval
- Cloud upload settings (optional)
- Time zone

### Without Interactive Setup

If you prefer manual configuration, edit `config.json` directly. See [CONFIG.md](CONFIG.md) for all options.

## Run It

### One-Time Test

```bash
python python_record.py
```

Records one audio file and saves it locally.

### Auto-Start on Boot

```bash
sudo nano /etc/profile
# Add these lines at the end:
chmod +x ~/multi-channel-rpi-eco-monitoring/*;
sudo -u pi ~/multi-channel-rpi-eco-monitoring/recorder_startup_script.sh;
```

Then reboot:
```bash
sudo reboot
```

## What's Being Recorded?

- **Location**: `~/multichannel_audio/`
- **Format**: FLAC (compressed, lossless audio)
- **Channels**: 7 (Sipeed array) or 6 (Respeaker)
- **Duration**: Configurable (default: 20 minutes)

## Next Steps

- **Upload to cloud?** See [CLOUD_SETUP.md](CLOUD_SETUP.md)
- **Troubleshooting?** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Advanced settings?** See [advanced_configuration.md](advanced_configuration.md)
- **Understanding logs?** See [LOG_GUIDE.md](LOG_GUIDE.md)

## Check It's Working

```bash
# SSH into your Pi and check latest recordings
ls -lh ~/multichannel_audio/ | tail -5

# View recent logs
tail -n 50 ~/logs/*.log
```

## Safety Tips

⚠️ **Critical**: Do NOT pull the power cable suddenly. This can corrupt the SD card.

- Use a hardware **shutdown button** (see [advanced_configuration.md](advanced_configuration.md))
- Or use software shutdown: `sudo halt`
- Wait for the green LED to stop flashing before removing power

---

**Need help?** Check [README.md](README.md) for full documentation or [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.

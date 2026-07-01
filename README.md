# multi-channel-rpi-eco-monitoring

Autonomous multichannel acoustic recording system for ecosystem monitoring using Raspberry Pi and the Sipeed 7-Mic Array (or legacy Respeaker hardware).

Part of the **MAARU** (Multichannel Autonomous Acoustic Recording Unit) project. Full project details: [beckyheath.github.io/MAARU](https://beckyheath.github.io/MAARU/)

---

## 🚀 Quick Start

### New to this project?

1. **Read first**: [`docs/quickstart.md`](docs/quickstart.md) - Get running in 5 minutes
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

Records high-quality multichannel audio from ecosystem monitoring sites:

- **7-channel recording** using Sipeed 7-Mic Array (recommended)
- **16-bit, 16 kHz** or customizable quality
- **FLAC compression** for efficient storage
- **Local recording** or **cloud upload** (Box, Google Drive, Dropbox, etc.)
- **Auto-start on boot** for unattended deployments
- **Structured logging** for debugging and analysis

---

## 💾 Hardware Options

### Recommended: Sipeed 7-Mic Array
- Modern, reliable
- No kernel freezing required
- Works with current Raspberry Pi OS
- Recommended for new deployments

### Legacy: Respeaker 4-Mic / 6-Mic
- Older hardware, still supported
- Requires Raspbian Buster + kernel freeze
- See [`docs/quickstart.md`](docs/quickstart.md) for legacy path

---

## 🔧 Installation

### Easiest: Prebuilt Image
Download prebuilt image → Flash with Balena Etcher → Configure → Done

### Manual Setup (15 min)
```bash
git clone https://github.com/your-org/multi-channel-rpi-eco-monitoring.git
cd multi-channel-rpi-eco-monitoring
pip install -r requirements.txt
sudo apt-get install portaudio19-dev
python setup_config.py
```

See [`docs/quickstart.md`](docs/quickstart.md) for detailed steps.

---

## 📚 Documentation

| Document | Purpose |
|----------|----------|
| [`quickstart.md`](docs/quickstart.md) | Get started in 5 minutes |
| [`config.md`](docs/config.md) | Configuration reference |
| [`cloud_setup.md`](docs/cloud_setup.md) | Cloud upload setup |
| [`troubleshooting.md`](docs/troubleshooting.md) | Common issues & solutions |
| [`log_guide.md`](docs/log_guide.md) | Log format & analysis |
| [`architecture.md`](docs/architecture.md) | System design |
| [`advanced_configuration.md`](docs/advanced_configuration.md) | Power saving, shutdown buttons, etc. |
| [`index.md`](docs/index.md) | Documentation hub |

---

## 📁 Project Structure

```
multi-channel-rpi-eco-monitoring/
├── README.md                    (this file)
├── docs/                        (all documentation)
│   ├── quickstart.md
│   ├── config.md
│   ├── cloud_setup.md
│   ├── troubleshooting.md
│   ├── log_guide.md
│   ├── architecture.md
│   ├── advanced_configuration.md
│   └── index.md
│
├── python_record.py             (main recorder)
├── setup_config.py              (configuration wizard)
├── recorder_startup_script.sh   (auto-start on boot)
├── rclone_upload.sh             (cloud upload)
├── sensors/                     (sensor implementations)
├── audio_sensor_scripts/        (helper scripts)
├── logs/                        (runtime logs)
├── multichannel_audio/          (recorded audio files)
└── config.json                  (your configuration)
```

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

- ✅ **7-channel recording** with structured logging
- ✅ **Multiple cloud services** via rclone (Box, Drive, Dropbox, S3, etc.)
- ✅ **Auto-start on boot** - no manual intervention needed
- ✅ **Graceful shutdown** - with optional GPIO button
- ✅ **State tracking** - resume uploads after reboot
- ✅ **Power saving** - HDMI, Bluetooth, LED disable options
- ✅ **Configurable parameters** - sample rate, bit depth, duration, codec

---

## ⚙️ System Requirements

- **Raspberry Pi**: Zero 2 W, 3B+, 4B+ (minimum 512 MB RAM)
- **Storage**: Class 10 SD card, **minimum 150 MB/s** read/write
- **Power**: 5V 2A+ supply
- **Sensor**: Sipeed 7-Mic Array (recommended) or Respeaker 6-Mic

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

**Original project**: Becky Heath and contributors ([BeckyHeath/multi-channel-rpi-eco-monitoring](https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring))

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

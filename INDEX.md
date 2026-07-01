# Documentation Index

Quick reference for all documentation in this project.

## 🚀 Getting Started (Pick One)

### If you're in a hurry (5 minutes)
→ **[QUICKSTART.md](QUICKSTART.md)**
- Prebuilt image setup
- Manual setup
- Basic configuration
- Verification steps

### If you want full details
→ **[README.md](README.md)**
- Complete setup instructions
- Hardware options (Sipeed vs Respeaker)
- OS configuration
- Boot automation

---

## ⚙️ Configuration & Customization

### Understanding all config options
→ **[CONFIG.md](CONFIG.md)**
- Complete reference for config.json
- Recording parameters explained
- Upload settings
- System settings
- Best practices

### Setting up cloud uploads
→ **[CLOUD_SETUP.md](CLOUD_SETUP.md)**
- Rclone configuration (Box, Google Drive, etc.)
- Creating cloud storage paths
- Testing uploads
- Bandwidth limiting
- Multiple deployment sites

### Advanced configurations
→ **[advanced_configuration.md](advanced_configuration.md)**
- Shutdown buttons
- Power saving options
- PyAudio troubleshooting
- Log filtering examples
- Making disk images

---

## 🏗️ Understanding the System

### How does it work?
→ **[ARCHITECTURE.md](ARCHITECTURE.md)**
- System components diagram
- Boot sequence
- Recording workflow
- Core scripts overview
- Data flow
- Performance characteristics
- Deployment models

### Understanding log files
→ **[LOG_GUIDE.md](LOG_GUIDE.md)**
- Log file locations
- Structured log format
- Component reference
- Common patterns
- Filtering techniques
- Parsing examples
- Troubleshooting based on logs

---

## ❓ Troubleshooting & Support

### Something not working?
→ **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**
- Recording issues (silence, overrun errors, no files)
- Upload problems (slow, failing, authentication)
- Startup/shutdown issues
- Performance problems
- Configuration errors
- Sensor-specific issues
- Recovery procedures
- Diagnostic information collection

---

## 📊 Documentation by Topic

| Topic | Document | Key Sections |
|-------|----------|--------------|
| **First-time setup** | QUICKSTART.md | Prerequisites, 30-second setup, configuration |
| **Configuration** | CONFIG.md | All options, examples, best practices |
| **Cloud uploads** | CLOUD_SETUP.md | Rclone setup, testing, troubleshooting |
| **System overview** | ARCHITECTURE.md | Components, workflows, performance |
| **Log analysis** | LOG_GUIDE.md | Format, filtering, patterns, parsing |
| **Debugging** | TROUBLESHOOTING.md | Common issues, diagnostics, recovery |
| **Advanced** | advanced_configuration.md | Buttons, power saving, disk images |
| **Complete setup** | README.md | Hardware paths, manual setup, full details |

---

## 💡 Common Tasks

### Task: I want to start recording locally
1. [QUICKSTART.md](QUICKSTART.md) - Choose prebuilt image or manual setup
2. [CONFIG.md](CONFIG.md) - Review recording parameters
3. [ARCHITECTURE.md](ARCHITECTURE.md) - Understand what's happening

### Task: I want to upload to cloud storage
1. [CLOUD_SETUP.md](CLOUD_SETUP.md) - Configure rclone
2. [CONFIG.md](CONFIG.md) - Enable online mode
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Verify and debug

### Task: My recording has no audio
1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md#recording-produces-silence-or-distorted-audio) - Solutions
2. [LOG_GUIDE.md](LOG_GUIDE.md) - Check logs for errors
3. [ARCHITECTURE.md](ARCHITECTURE.md#error-handling-strategy) - Understanding error recovery

### Task: I'm getting "overrun errors"
1. [TROUBLESHOOTING.md](TROUBLESHOOTING.md#overrun-error-or-dead-channels) - Root cause explanation
2. [CONFIG.md](CONFIG.md#recording-parameters-explained) - Check your settings
3. [advanced_configuration.md](advanced_configuration.md) - Hardware optimization

### Task: I want to understand the logs
1. [LOG_GUIDE.md](LOG_GUIDE.md) - Format and structure
2. [advanced_configuration.md](advanced_configuration.md#log-filter-examples-prefix-contract) - Filter examples
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md#getting-help) - Debug information

### Task: I want to save power for battery operation
1. [advanced_configuration.md](advanced_configuration.md#power-saving-configuration) - Power saving options
2. [CONFIG.md](CONFIG.md#recording-parameters-explained) - Optimize parameters
3. [ARCHITECTURE.md](ARCHITECTURE.md#performance-characteristics) - Understand resource use

### Task: I'm deploying multiple monitoring sites
1. [CLOUD_SETUP.md](CLOUD_SETUP.md#multiple-deployment-sites) - Multi-device setup
2. [CONFIG.md](CONFIG.md) - Configuration per site
3. [LOG_GUIDE.md](LOG_GUIDE.md#monitor-disk-usage-during-recording) - Monitoring tips

---

## 📁 File Organization

```
multi-channel-rpi-eco-monitoring/
├── 📖 Documentation/
│   ├── README.md                      (Main documentation)
│   ├── QUICKSTART.md                  (Get started fast)
│   ├── CONFIG.md                      (Configuration reference)
│   ├── CLOUD_SETUP.md                 (Cloud uploads)
│   ├── TROUBLESHOOTING.md             (Common issues)
│   ├── LOG_GUIDE.md                   (Log reference)
│   ├── ARCHITECTURE.md                (System design)
│   ├── advanced_configuration.md      (Advanced options)
│   └── INDEX.md                       (This file)
│
├── 🐍 Python Scripts/
│   ├── python_record.py               (Main recorder)
│   ├── setup_config.py                (Configuration wizard)
│   └── discover_serial.py             (Find audio devices)
│
├── 🔧 Bash Scripts/
│   ├── recorder_startup_script.sh     (Boot automation)
│   ├── rclone_upload.sh               (Cloud uploads)
│   ├── enable_system_shutdown_button.sh
│   ├── sync_rclone_config.sh
│   ├── update_time.sh
│   ├── clean_live_data.sh
│   ├── led_on.sh
│   └── led_off.sh
│
├── 📦 Sensors/
│   ├── sensors/SensorBase.py
│   ├── sensors/Sipeed7Mic.py
│   ├── sensors/Respeaker4Mic.py
│   ├── sensors/Respeaker6Mic.py
│   └── sensors/__init__.py
│
├── ⚙️ Configuration/
│   ├── config.json                    (Your settings)
│   ├── pyproject.toml                 (Python package info)
│   ├── requirements.txt               (Python dependencies)
│   └── .gitignore
│
└── 📂 Runtime Directories/
    ├── multichannel_audio/            (Recorded files)
    ├── logs/                          (Log files)
    └── .rclone_state.json             (Upload state)
```

---

## 🎯 Documentation Levels

### Level 1: Quick Reference
Perfect for: "Just tell me what to do"
- [QUICKSTART.md](QUICKSTART.md) - One-page quick start
- [CONFIG.md](CONFIG.md) examples - Copy-paste configs

### Level 2: User Guides
Perfect for: "I need to understand this"
- [CLOUD_SETUP.md](CLOUD_SETUP.md) - Step-by-step cloud setup
- [LOG_GUIDE.md](LOG_GUIDE.md) - Understanding logs
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Solving problems

### Level 3: Technical Reference
Perfect for: "How does this really work?"
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [advanced_configuration.md](advanced_configuration.md) - Advanced options
- [README.md](README.md) - Complete technical details

### Level 4: Source Code
Perfect for: "I need to modify this"
- `python_record.py` - Recording logic
- `setup_config.py` - Configuration
- `rclone_upload.sh` - Upload logic
- `sensors/*.py` - Sensor implementations

---

## ✅ Verification Checklist

### After initial setup
- [ ] Reviewed [QUICKSTART.md](QUICKSTART.md)
- [ ] Understood [ARCHITECTURE.md](ARCHITECTURE.md)
- [ ] Created config.json using [CONFIG.md](CONFIG.md) reference

### Before first deployment
- [ ] Recording test successful (see [QUICKSTART.md](QUICKSTART.md#check-its-working))
- [ ] Reviewed log format ([LOG_GUIDE.md](LOG_GUIDE.md))
- [ ] Confirmed SD card speed ([TROUBLESHOOTING.md](TROUBLESHOOTING.md#pi-very-slow-recording-stutters))

### If enabling cloud uploads
- [ ] Configured rclone ([CLOUD_SETUP.md](CLOUD_SETUP.md#step-1-install-and-configure-rclone))
- [ ] Tested upload manually ([CLOUD_SETUP.md](CLOUD_SETUP.md#step-4-test-upload))
- [ ] Understood upload workflow ([CLOUD_SETUP.md](CLOUD_SETUP.md#how-uploads-work))

### For field deployments
- [ ] Set up shutdown button ([advanced_configuration.md](advanced_configuration.md#shutdown-button-setup-for-sipeed-7-mic-array))
- [ ] Enabled power saving if needed ([advanced_configuration.md](advanced_configuration.md#power-saving-configuration))
- [ ] Made backup disk image ([advanced_configuration.md](advanced_configuration.md#make-a-new-disk-image))
- [ ] Reviewed diagnostics collection ([TROUBLESHOOTING.md](TROUBLESHOOTING.md#collect-diagnostic-information))

---

## 📞 Need Help?

1. **Check TROUBLESHOOTING.md** - 80% of issues are covered there
2. **Search LOG_GUIDE.md** - Find your error message and filtering tips
3. **Review ARCHITECTURE.md** - Understand how components interact
4. **Check CONFIG.md** - Verify your settings are correct
5. **Inspect logs** - Use patterns from LOG_GUIDE.md

---

## 📚 External References

- **Sipeed 7-Mic Array**: [Official Documentation](https://wiki.sipeed.com/)
- **Raspberry Pi**: [Official Docs](https://www.raspberrypi.com/documentation/)
- **Rclone**: [Complete Manual](https://rclone.org/docs/)
- **MAARU Project**: [Beckyheath MAARU](https://beckyheath.github.io/MAARU/)

---

**Last Updated**: 2024-07-01

For questions or documentation improvements, refer to [README.md](README.md) for contributing guidelines.

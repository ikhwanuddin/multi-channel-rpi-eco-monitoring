# Documentation Index

Quick reference for all documentation in this project.

## 🚀 Getting Started (Pick One)

### If you're in a hurry (5 minutes)
→ **[quickstart.md](quickstart.md)**
- Prebuilt image setup
- Manual setup
- Basic configuration
- Verification steps

### If you want full details
→ **[readme.md](readme.md)**
- Complete setup instructions
- Hardware options (Sipeed vs Respeaker)
- OS configuration
- Boot automation

---

## ⚙️ Configuration & Customization

### Understanding all config options
→ **[config.md](config.md)**
- Complete reference for config.json
- Recording parameters explained
- Upload settings
- System settings
- Best practices

### Setting up cloud uploads
→ **[cloud_setup.md](cloud_setup.md)**
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
→ **[architecture.md](architecture.md)**
- System components diagram
- Boot sequence
- Recording workflow
- Core scripts overview
- Data flow
- Performance characteristics
- Deployment models

### Understanding log files
→ **[log_guide.md](log_guide.md)**
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
→ **[troubleshooting.md](troubleshooting.md)**
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
|-------|----------|______________|
| **First-time setup** | quickstart.md | Prerequisites, 30-second setup, configuration |
| **Configuration** | config.md | All options, examples, best practices |
| **Cloud uploads** | cloud_setup.md | Rclone setup, testing, troubleshooting |
| **System overview** | architecture.md | Components, workflows, performance |
| **Log analysis** | log_guide.md | Format, filtering, patterns, parsing |
| **Debugging** | troubleshooting.md | Common issues, diagnostics, recovery |
| **Advanced** | advanced_configuration.md | Buttons, power saving, disk images |
| **Complete setup** | readme.md | Hardware paths, manual setup, full details |

---

## 💡 Common Tasks

### Task: I want to start recording locally
1. [quickstart.md](quickstart.md) - Choose prebuilt image or manual setup
2. [config.md](config.md) - Review recording parameters
3. [architecture.md](architecture.md) - Understand what's happening

### Task: I want to upload to cloud storage
1. [cloud_setup.md](cloud_setup.md) - Configure rclone
2. [config.md](config.md) - Enable online mode
3. [troubleshooting.md](troubleshooting.md) - Verify and debug

### Task: My recording has no audio
1. [troubleshooting.md](troubleshooting.md#recording-produces-silence-or-distorted-audio) - Solutions
2. [log_guide.md](log_guide.md) - Check logs for errors
3. [architecture.md](architecture.md#error-handling-strategy) - Understanding error recovery

### Task: I'm getting "overrun errors"
1. [troubleshooting.md](troubleshooting.md#overrun-error-or-dead-channels) - Root cause explanation
2. [config.md](config.md#recording-parameters-explained) - Check your settings
3. [advanced_configuration.md](advanced_configuration.md) - Hardware optimization

### Task: I want to understand the logs
1. [log_guide.md](log_guide.md) - Format and structure
2. [advanced_configuration.md](advanced_configuration.md#log-filter-examples-prefix-contract) - Filter examples
3. [troubleshooting.md](troubleshooting.md#getting-help) - Debug information

### Task: I want to save power for battery operation
1. [advanced_configuration.md](advanced_configuration.md#power-saving-configuration) - Power saving options
2. [config.md](config.md#recording-parameters-explained) - Optimize parameters
3. [architecture.md](architecture.md#performance-characteristics) - Understand resource use

### Task: I'm deploying multiple monitoring sites
1. [cloud_setup.md](cloud_setup.md#multiple-deployment-sites) - Multi-device setup
2. [config.md](config.md) - Configuration per site
3. [log_guide.md](log_guide.md#monitor-disk-usage-during-recording) - Monitoring tips

---

## 📁 File Organization

```
multi-channel-rpi-eco-monitoring/
├── 📖 Documentation/
│   ├── readme.md                 (Main documentation)
│   ├── quickstart.md             (Get started fast)
│   ├── config.md                 (Configuration reference)
│   ├── cloud_setup.md            (Cloud uploads)
│   ├── troubleshooting.md        (Common issues)
│   ├── log_guide.md              (Log reference)
│   ├── architecture.md           (System design)
│   └── index.md                  (This file)
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
- [quickstart.md](quickstart.md) - One-page quick start
- [config.md](config.md) examples - Copy-paste configs

### Level 2: User Guides
Perfect for: "I need to understand this"
- [cloud_setup.md](cloud_setup.md) - Step-by-step cloud setup
- [log_guide.md](log_guide.md) - Understanding logs
- [troubleshooting.md](troubleshooting.md) - Solving problems

### Level 3: Technical Reference
Perfect for: "How does this really work?"
- [architecture.md](architecture.md) - System design
- [advanced_configuration.md](advanced_configuration.md) - Advanced options
- [readme.md](readme.md) - Complete technical details

### Level 4: Source Code
Perfect for: "I need to modify this"
- `python_record.py` - Recording logic
- `setup_config.py` - Configuration
- `rclone_upload.sh` - Upload logic
- `sensors/*.py` - Sensor implementations

---

## ✅ Verification Checklist

### After initial setup
- [ ] Reviewed [quickstart.md](quickstart.md)
- [ ] Understood [architecture.md](architecture.md)
- [ ] Created config.json using [config.md](config.md) reference

### Before first deployment
- [ ] Recording test successful (see [quickstart.md](quickstart.md#check-its-working))
- [ ] Reviewed log format ([log_guide.md](log_guide.md))
- [ ] Confirmed SD card speed ([troubleshooting.md](troubleshooting.md#pi-very-slow-recording-stutters))

### If enabling cloud uploads
- [ ] Configured rclone ([cloud_setup.md](cloud_setup.md#step-1-install-and-configure-rclone))
- [ ] Tested upload manually ([cloud_setup.md](cloud_setup.md#step-4-test-upload))
- [ ] Understood upload workflow ([cloud_setup.md](cloud_setup.md#how-uploads-work))

### For field deployments
- [ ] Set up shutdown button ([advanced_configuration.md](advanced_configuration.md#shutdown-button-setup-for-sipeed-7-mic-array))
- [ ] Enabled power saving if needed ([advanced_configuration.md](advanced_configuration.md#power-saving-configuration))
- [ ] Made backup disk image ([advanced_configuration.md](advanced_configuration.md#make-a-new-disk-image))
- [ ] Reviewed diagnostics collection ([troubleshooting.md](troubleshooting.md#collect-diagnostic-information))

---

## 📞 Need Help?

1. **Check troubleshooting.md** - 80% of issues are covered there
2. **Search log_guide.md** - Find your error message and filtering tips
3. **Review architecture.md** - Understand how components interact
4. **Check config.md** - Verify your settings are correct
5. **Inspect logs** - Use patterns from log_guide.md

---

## 📚 External References

- **Sipeed 7-Mic Array**: [Official Documentation](https://wiki.sipeed.com/)
- **Raspberry Pi**: [Official Docs](https://www.raspberrypi.com/documentation/)
- **Rclone**: [Complete Manual](https://rclone.org/docs/)
- **MAARU Project**: [Beckyheath MAARU](https://beckyheath.github.io/MAARU/)

---

**Last Updated**: 2024-07-01

For questions or documentation improvements, refer to [readme.md](readme.md) for contributing guidelines.

# Documentation Index

Quick reference for all documentation in this project.

## 🚀 Getting Started (Pick One)

### If you're in a hurry
→ **[quickstart.md](quickstart.md)**
- Manual setup (no prebuilt image for the Sipeed version)
- `installer.py` full setup
- Basic configuration
- Verification steps

### If you want full details
→ **[README](../README.md)**
- Project overview and install commands
- Hardware options (Sipeed vs Respeaker)
- Credits and citations

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
- Remote folder layout
- Testing uploads
- Bandwidth limiting
- Multiple deployment sites
- Sharing rclone.conf via a GitHub Gist

### Advanced configurations
→ **[advanced_configuration.md](advanced_configuration.md)**
- Shutdown buttons
- Power saving options and field WiFi timer
- Runtime optimizations, time sync
- Shell shortcuts (`monitor`, `healtheco`, ...)
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

### Hardware and enclosure
→ **[physical-setup.md](physical-setup.md)**
- Components, enclosure layers, power budget, maintenance

### Understanding log files
→ **[log_guide.md](log_guide.md)**
- Log file locations
- Log format and prefixes
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
|-------|----------|--------------|
| **First-time setup** | quickstart.md | Prerequisites, manual setup, configuration |
| **Configuration** | config.md | All options, examples, best practices |
| **Cloud uploads** | cloud_setup.md | Rclone setup, testing, troubleshooting |
| **System overview** | architecture.md | Components, workflows, performance |
| **Log analysis** | log_guide.md | Format, filtering, patterns, parsing |
| **Debugging** | troubleshooting.md | Common issues, diagnostics, recovery |
| **Advanced** | advanced_configuration.md | Buttons, power saving, WiFi timer, disk images |
| **Hardware** | physical-setup.md | Components, enclosure, power budget |
| **Overview** | ../README.md | Hardware paths, install commands, credits |

---

## 💡 Common Tasks

### Task: I want to start recording locally
1. [quickstart.md](quickstart.md) - Manual setup and installer
2. [config.md](config.md) - Review recording parameters
3. [architecture.md](architecture.md) - Understand what's happening

### Task: I want to upload to cloud storage
1. [cloud_setup.md](cloud_setup.md) - Configure rclone
2. [config.md](config.md) - `upload_enabled`, `test_mode`, rclone settings
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
2. [advanced_configuration.md](advanced_configuration.md#log-filter-examples) - Filter examples
3. [troubleshooting.md](troubleshooting.md#getting-help) - Debug information

### Task: I want to save power for battery operation
1. [advanced_configuration.md](advanced_configuration.md#power-saving-configuration) - Power saving options
2. [config.md](config.md#recording-parameters-explained) - Optimize parameters
3. [architecture.md](architecture.md#performance-characteristics) - Understand resource use

### Task: I'm deploying multiple monitoring sites
1. [cloud_setup.md](cloud_setup.md#multiple-deployment-sites) - Multi-device setup
2. [config.md](config.md) - Configuration per site
3. [log_guide.md](log_guide.md#filtering-logs) - Monitoring tips

---

## 📁 File Organization

```
multi-channel-rpi-eco-monitoring/
├── README.md                          (Project overview)
├── 📖 docs/
│   ├── quickstart.md                  (Get started fast)
│   ├── config.md                      (Configuration reference)
│   ├── cloud_setup.md                 (Cloud uploads)
│   ├── troubleshooting.md             (Common issues)
│   ├── log_guide.md                   (Log reference)
│   ├── architecture.md                (System design)
│   ├── advanced_configuration.md      (Buttons, power saving, WiFi timer)
│   ├── physical-setup.md              (Hardware and enclosure)
│   └── index.md                       (This file)
│
├── 🐍 Python Scripts/
│   ├── installer.py                   (Interactive installer)
│   ├── record.py                      (Main recorder)
│   ├── state_manager.py               (Upload state tracking)
│   ├── offline_time_sync.py           (Time from WiFi gateway)
│   └── discover_serial.py             (Prints RPiID-<cpu serial>)
│
├── 🔧 Bash Scripts / systemd units/
│   ├── eco-monitor.service            (Main systemd unit template)
│   ├── wifi-field-timer.service       (WiFi timer unit template)
│   ├── wifi_field_timer.sh
│   ├── rclone_upload.sh               (Cloud uploads)
│   ├── sync_rclone_config.sh          (rclone.conf ↔ Gist)
│   ├── update_time.sh
│   ├── check_fs_expanded.sh
│   ├── enable_system_shutdown_button.sh
│   ├── clean_live_data.sh
│   ├── led_on.sh
│   └── led_off.sh
│
├── 📦 sensors/
│   ├── SensorBase.py
│   ├── Sipeed7Mic.py
│   ├── Respeaker4Mic.py
│   ├── Respeaker6Mic.py
│   ├── Respeaker_Custom.py
│   ├── UnixDevice.py
│   └── __init__.py
│
├── ⚙️ Configuration/
│   ├── config.json                    (Your settings, git-ignored)
│   ├── audio_sensor_scripts/asound.state (Mixer levels)
│   ├── pyproject.toml                 (Repository metadata only)
│   └── .gitignore
│
└── 📂 Runtime/
    ├── logs/logfile.log               (Recorder log)
    ├── /home/pi/tmp_dir/              (Recording in progress)
    ├── /home/pi/pre_upload_dir/       (Finished WAVs before compression)
    └── /home/pi/monitoring_data/live_data/
        ├── RPiID-<serial>/<date>/     (Recordings)
        ├── rclone_state.json          (Upload state)
        └── rclone.log                 (Upload log)
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
- [physical-setup.md](physical-setup.md) - Hardware details

### Level 4: Source Code
Perfect for: "I need to modify this"
- `record.py` - Recording logic
- `installer.py` - Configuration and installation
- `rclone_upload.sh`, `state_manager.py` - Upload logic
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
- [ ] Confirmed SD card speed ([troubleshooting.md](troubleshooting.md#overrun-error-or-dead-channels))

### If enabling cloud uploads
- [ ] Configured rclone ([cloud_setup.md](cloud_setup.md#step-1-install-and-configure-rclone))
- [ ] Tested upload manually ([cloud_setup.md](cloud_setup.md#step-4-test-upload))
- [ ] Understood upload workflow ([cloud_setup.md](cloud_setup.md#how-uploads-work))

### For field deployments
- [ ] Set up shutdown button ([advanced_configuration.md](advanced_configuration.md#shutdown-button-setup-for-sipeed-mic-array))
- [ ] Enabled the field WiFi timer if running on battery ([advanced_configuration.md](advanced_configuration.md))
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

- **Sipeed MA-USB8 Mic Array board**: [Official Documentation](https://wiki.sipeed.com/hardware/en/modules/micarray_usbboard_bl616.html)
- **Raspberry Pi**: [Official Docs](https://www.raspberrypi.com/documentation/)
- **Rclone**: [Complete Manual](https://rclone.org/docs/)
- **MAARU Project**: [Beckyheath MAARU](https://beckyheath.github.io/MAARU/)

---

For questions or documentation improvements, open an issue on [GitHub](https://github.com/ikhwanuddin/multi-channel-rpi-eco-monitoring).

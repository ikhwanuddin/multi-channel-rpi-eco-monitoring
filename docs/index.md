# Documentation Index

Start with [quickstart.md](quickstart.md) to install a unit. The [README](../README.md) has the project overview, hardware options, project structure and credits.

## Documents

| Document | What it covers |
|----------|----------------|
| [quickstart.md](quickstart.md) | Manual setup (no prebuilt image for the Sipeed version), `installer.py` full setup, first recording |
| [config.md](config.md) | Every `config.json` option, recording parameters, upload and system settings |
| [cloud_setup.md](cloud_setup.md) | rclone setup, remote folder layout, testing uploads, sharing `rclone.conf` via a GitHub Gist |
| [advanced_configuration.md](advanced_configuration.md) | Shutdown buttons, power saving, field WiFi timer, runtime optimizations, shell shortcuts, disk images |
| [architecture.md](architecture.md) | Software components, boot sequence, recording workflow, data flow, deployment models |
| [physical-setup.md](physical-setup.md) | Hardware components, enclosure and 3D-printed parts, field deployment scenario |
| [log_guide.md](log_guide.md) | Log locations, format, common patterns, filtering |
| [troubleshooting.md](troubleshooting.md) | Recording, upload, startup, performance and sensor issues; recovery |

## Common Tasks

- **Start recording locally**: [quickstart.md](quickstart.md), then [config.md](config.md) for recording parameters
- **Upload to cloud storage**: [cloud_setup.md](cloud_setup.md), then `upload_enabled` and `test_mode` in [config.md](config.md)
- **Recording has no audio**: [troubleshooting.md](troubleshooting.md#recording-produces-silence-or-distorted-audio)
- **Overrun errors**: [troubleshooting.md](troubleshooting.md#overrun-error-or-dead-channels)
- **Save power on a powerbank**: [advanced_configuration.md](advanced_configuration.md#power-saving-configuration) and the field WiFi timer
- **Several units / sites**: [cloud_setup.md](cloud_setup.md#multiple-deployment-sites)
- **Read the logs**: [log_guide.md](log_guide.md) and [log filter examples](advanced_configuration.md#log-filter-examples)

## External References

- **Sipeed MA-USB8 Mic Array board**: [Official Documentation](https://wiki.sipeed.com/hardware/en/modules/micarray_usbboard_bl616.html)
- **Raspberry Pi**: [Official Docs](https://www.raspberrypi.com/documentation/)
- **Rclone**: [Complete Manual](https://rclone.org/docs/)
- **MAARU Project**: [Becky Heath's MAARU](https://beckyheath.github.io/MAARU/)

For questions or documentation improvements, open an issue on [GitHub](https://github.com/ikhwanuddin/multi-channel-rpi-eco-monitoring).

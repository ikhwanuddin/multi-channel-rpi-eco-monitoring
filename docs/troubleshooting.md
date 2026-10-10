# Troubleshooting Guide

Solutions for common issues with multi-channel ecosystem monitoring setup.

Paths below assume the default layout: repository in `/home/pi/multi-channel-rpi-eco-monitoring`, log file `logs/logfile.log` inside it, recordings in `/home/pi/monitoring_data/live_data/RPiID-<serial>/`.

## Recording Issues

### "No such device" error / `arecord` fails

**Problem**: Audio device not found.

**Solutions**:
```bash
# List available capture devices
arecord -l
```

`Sipeed7Mic` picks the first card in `arecord -l` whose line contains `MicArray` or `USB`, and falls back to card `1` (logged as `find_usb_audio_card: no Sipeed/USB card found ...`). There is no device index in `config.json`. If another USB audio device is plugged in, it may be picked instead: unplug it.

Check connections:
- USB cable firmly connected
- Try a different USB port
- Restart the Pi

---

### Recording produces silence or distorted audio

**Problem**: Files record but contain no sound or noise.

**Check hardware**:
- [ ] Microphone array powered on
- [ ] No physical obstruction over mics
- [ ] Check for loose cables or poor connections

**Check recording settings**:
```bash
# See the arecord exit code, size and stderr for each recording
sudo journalctl -u eco-monitor.service | grep -E "arecord|Recorded"
```

Remember that on the Sipeed board CH6 is a beamformed channel and CH7 the centre mic ([Sipeed wiki](https://wiki.sipeed.com/hardware/en/modules/micarray_usbboard_bl616.html)).

**Audio level too low**:
```bash
# Adjust input gain (if your sensor supports it)
alsamixer
```

At start the sensor restores mixer levels from `audio_sensor_scripts/asound.state` (`alsactl --file ... restore`), so manual changes are overwritten on the next service start unless you save them into that file.

---

### "Overrun error" or dead channels

**Problem**: Some channels record, others don't, or `arecord stderr: overrun!!!` lines appear in the log.

**Root cause**: often a slow SD card.

**Solution**:
```bash
# Check SD card read speed
sudo hdparm -t /dev/mmcblk0

# If slow: replace with Class 10 SD card minimum 150 MB/s read/write
```

Other causes:
- Too many background processes
- Under-voltage (run `healtheco` and check the `vcgencmd get_throttled` section)
- USB device causing interference

```bash
# Restart sensor
sudo reboot
```

---

### Files not being created

**Problem**: Service runs but no audio files appear.

**Check**:
```bash
# Is the service running, and is it paused for upload?
sudo systemctl status eco-monitor.service
grep -E "pausing record|Recording started|Recording failed" ~/multi-channel-rpi-eco-monitoring/logs/logfile.log | tail

# Error markers written when a recording fails
find /home/pi/pre_upload_dir -name "*_ERROR_audio-record-failed"

# Look for errors
grep -i "error\|failed" ~/multi-channel-rpi-eco-monitoring/logs/logfile.log | tail -n 50
```

**Possible causes**:
- Internet is reachable and `upload_enabled` is true → recording is paused on purpose (`Upload in progress ...; pausing record.`). Use `"test_mode": 1` for bench tests
- Uploaded files are deleted locally after verification → check the remote
- Disk full → `df -h` to check. Below `min_free_storage_gb` (1 GB) the Pi shuts down
- Sensor not detected → see "No such device" above

Three failed or tiny (< 1 MB) recordings in a row trigger an automatic reboot (`Repeated tiny recordings detected`).

---

### Missing Python modules

The code needs `psutil` and `RPi.GPIO` from system packages (there is no PyAudio dependency):

```bash
sudo apt-get install -y python3-psutil python3-rpi.gpio
```

---

## Upload Issues

### Files not uploading to cloud

**Check**:
```bash
# Verify uploads are enabled and test mode is off
grep -E '"upload_enabled"|"test_mode"' ~/multi-channel-rpi-eco-monitoring/config.json

# Test rclone connection
rclone ls mybox:  # Should list your cloud folder

# Check internet (the code checks 8.8.8.8:53)
ping 8.8.8.8

# View upload logs
grep "\[upload" ~/multi-channel-rpi-eco-monitoring/logs/logfile.log | tail -n 100
tail -n 100 /home/pi/monitoring_data/live_data/rclone.log
```

Also check that `jq` is installed (`rclone_upload.sh` exits with `ERROR: jq binary not found` otherwise).

---

### "Remote not found" error

**Problem**: Rclone remote not configured.

**Solution**:
```bash
# List configured remotes
rclone listremotes

# If empty, configure:
rclone config

# Then update config.json with remote_name
```

---

### "Authentication failed" when uploading

**Problem**: Cloud service rejected credentials.

**Solution**:
```bash
# Re-authenticate with your cloud service
rclone config reconnect mybox:

# Then follow prompts to sign in again
```

If several Pis share `rclone.conf` through the Gist sync, a Pi with an old token may pull the newer one at its next service start (`[gist-sync]` lines in the journal).

---

### Uploads are very slow

**Check internet speed**:
```bash
# On Raspberry Pi
curl -o /dev/null -s -w '%{speed_download}\n' https://www.google.com

# Expected: > 1 Mbps for practical use
```

**Solutions**:
- Move Pi closer to WiFi router
- Use wired Ethernet where the Pi has a port
- Keep `compress_data: true` (FLAC)

---

### Disk fills up, upload stops

**Problem**: SD card full.

**Check**:
```bash
df -h  # Shows disk usage

# Monitoring folders (or use the `sizeeco` shortcut)
du -sh /home/pi/monitoring_data/live_data/ /home/pi/tmp_dir/ /home/pi/pre_upload_dir/
```

**Solution**:

Nothing is deleted automatically except files that were verified on the remote. Copy the data off the card first, then clear `live_data` with the helper (asks for confirmation, keeps the folder structure):

```bash
cd ~/multi-channel-rpi-eco-monitoring
./clean_live_data.sh /home/pi/monitoring_data/live_data
```

---

## Startup/Shutdown Issues

### Service not starting on boot

**Problem**: Recorder doesn't start when Pi powers on.

**Check**:
```bash
# Is the unit installed and enabled?
systemctl is-enabled eco-monitor.service
sudo systemctl status eco-monitor.service

# If not: sudo python3 installer.py → menu 2 (or 8 to show status)
```

**View startup logs**:
```bash
sudo journalctl -u eco-monitor.service -b --no-pager | head -100
```

If you are upgrading an old unit that still starts `recorder_startup_script.sh` from `/etc/profile`, run installer menu 6 to remove those lines, then menu 2.

---

### Shutdown button not working

**Problem**: GPIO button doesn't trigger shutdown.

**For Sipeed**:
- The button is handled by the `gpio-shutdown` device tree overlay, independent of the recorder
- Check the overlay is present: installer menu 8, or `grep gpio-shutdown /boot/firmware/config.txt /boot/config.txt`
- Verify wiring: Button connects GPIO 21 to GND
- A reboot is needed after adding the overlay

**For Respeaker 6-Mic**:
```bash
# Check whether the overlay or the Python listener is used
grep "use_system_shutdown_button" config.json

# If 0, button is handled by record.py on GPIO 26
# If 1, button is handled by device tree overlay
```

**Restart button detection**:
```bash
sudo reboot
```

---

## Performance Issues

### Pi very slow, recording stutters

**Check CPU usage**:
```bash
top
# Press 'q' to exit
```

`arecord` and, after each recording, `ffmpeg` are the main CPU users. The CPU governor is set to `powersave` between recordings and `ondemand` during capture.

**Check running processes**:
```bash
ps aux | grep -v grep
```

**Solutions**:
- Disable HDMI (saves power, improves stability): See [advanced_configuration.md](advanced_configuration.md)
- Disable Bluetooth: See [advanced_configuration.md](advanced_configuration.md)
- Use Raspberry Pi Zero 2 W for lower power consumption

---

### Pi freezes or crashes

**Likely cause**: Power supply insufficient.

**Check**:
```bash
# Decoded under-voltage / throttle flags (shell shortcut)
healtheco

# Or directly
vcgencmd get_throttled
dmesg | grep -i "voltage"
```

**Solutions**:
- Use 5V 2.5A+ power supply (not USB port)
- Use powered USB hub for sensors
- Enable the field WiFi timer to cut WiFi power when no network is in range

---

## Configuration Issues

### "config.json not found"

**Solution**:
```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py   # menu option 1
```

### config.json syntax error

**Error**: `json.decoder.JSONDecodeError`

**Fix**:
```bash
# Validate JSON syntax
python3 -m json.tool config.json

# If error shown, fix manually
nano config.json

# Common mistakes:
# - Missing commas between fields
# - Trailing commas (not allowed in JSON)
# - Unquoted strings
```

---

### Timezone not working

**Problem**: Logs and file names show the wrong time.

**Check configured timezone**:
```bash
# View system timezone and sync status
timedatectl

# Set it (there is no timezone key in config.json)
sudo timedatectl set-timezone Europe/London
```

The clock is set at service start from `/etc/fake-hwclock.data`, then `update_time.sh` tries NTP (if online) or the WiFi gateway (`offline_time_sync.py`). Without any network you can push the time over SSH:

```bash
ssh pi@<hostname>.local "sudo bash ~/multi-channel-rpi-eco-monitoring/update_time.sh --epoch $(date +%s)"
```

---

## Disk Space Management

### How much space does recording use?

**Rule of thumb** (per 20-minute Sipeed recording, 8 channels, 16 kHz, 16-bit):
- WAV: 16,000 × 8 × 2 bytes × 1,200 s ≈ 307 MB
- FLAC: smaller; the ratio depends on the sound content

**Calculate for your setup**:
```
WAV size = sample_rate × channels × (bits / 8) × duration
```

### Monitor disk usage

```bash
# Check available space
df -h

# Monitor in real-time during recording
watch -n 10 du -sh /home/pi/monitoring_data/live_data/ /home/pi/tmp_dir/ /home/pi/pre_upload_dir/
```

---

## Sensor-Specific Issues

### Sipeed 6+1 Mic Array (MA-USB8)

**No audio detected**:
- Check USB cable connection
- Try different USB port
- `arecord -l` should list the board (`MicArray` / `USB`)
- Check the `Detected USB audio card:` line in the log

**Multiple devices showing**:
- Only one should be active
- Disconnect other USB audio devices (the first `MicArray`/`USB` card is used)

**LEDs**: `led_off.sh` runs at every service start and switches the board LEDs off via `/dev/ttyACM0`. `./led_on.sh` turns them on again (needs read/write access to `/dev/ttyACM0`, e.g. user in the `dialout` group).

### Respeaker 4-Mic / 6-Mic (Legacy)

**No audio detected**:
```bash
# Check Voicecard driver loaded
lsmod | grep seeed

# Check audio device
arecord -l

# If not present, restart:
sudo reboot
```

**Audio driver not loading on boot**:
- Do not run OS updates (freezes kernel compatibility)
- Do not use `rpi-update`
- If kernel updated by accident, may need fresh install

---

## Getting Help

### Collect diagnostic information

When seeking help, provide:

```bash
# System info
uname -a

# Raspberry Pi model
cat /proc/device-tree/model

# Recording config (remove the github_token first)
cat ~/multi-channel-rpi-eco-monitoring/config.json

# Recent logs
tail -n 200 ~/multi-channel-rpi-eco-monitoring/logs/logfile.log
sudo journalctl -u eco-monitor.service -u wifi-field-timer.service -n 200 --no-pager

# Audio device info
arecord -l

# Pi ID
python3 ~/multi-channel-rpi-eco-monitoring/discover_serial.py

# Disk usage
df -h
```

### Verbose logging

There is no verbose flag. `record.py` logs at INFO level; the `arecord` command line and `ffmpeg` command are logged at DEBUG and are not shown. The journal (`journalctl -u eco-monitor.service`) also contains output that is not in `logfile.log`, such as the `ExecStartPre` steps and `update_time.sh`.

```bash
tail -f ~/multi-channel-rpi-eco-monitoring/logs/logfile.log  # Follow logs in real-time
```

---

## Quick Recovery

### Emergency shutdown (safe)

```bash
# Graceful shutdown
sudo shutdown -h now

# Then wait for the Pi to finish shutting down before removing power
```

### Reset configuration

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py  # menu 1, answer "y" to replace the existing config
```

### Clear old recordings

```bash
# List recordings
ls -lhR /home/pi/monitoring_data/live_data/

# Delete all files under live_data (asks for confirmation, keeps folders)
./clean_live_data.sh /home/pi/monitoring_data/live_data
```

Copy the data off first: this cannot be undone.

### View live logs

```bash
# Health snapshot + live journal (shell shortcut)
monitor

# Watch the log file as it is written
tail -f ~/multi-channel-rpi-eco-monitoring/logs/logfile.log

# Filter for errors only
tail -f ~/multi-channel-rpi-eco-monitoring/logs/logfile.log | grep -i error
```

---

## Still Need Help?

Check:
1. [advanced_configuration.md](advanced_configuration.md) - Advanced options
2. [config.md](config.md) - All configuration options
3. [cloud_setup.md](cloud_setup.md) - Upload troubleshooting
4. [log_guide.md](log_guide.md) - Understanding log format
5. [README](../README.md) - Project overview

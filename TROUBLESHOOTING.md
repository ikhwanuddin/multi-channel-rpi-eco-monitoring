# Troubleshooting Guide

Solutions for common issues with multi-channel ecosystem monitoring setup.

## Recording Issues

### "No such device" error

**Problem**: Audio device not found.

**Solutions**:
```bash
# List available audio devices
python discover_serial.py

# Update device_index in config.json with correct number
nano config.json
```

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
# Test with verbose output
python python_record.py --verbose

# Check sample rate isn't too high
nano config.json  # Verify sample_rate: 16000
```

**Audio level too low**:
```bash
# Adjust input gain (if your sensor supports it)
alsamixer
```

---

### "Overrun error" or dead channels

**Problem**: Some channels record, others don't. Usually: `ERR (Unknown Error)`

**Root cause**: SD card too slow.

**Solution**:
```bash
# Check SD card speed
sudo hdparm -t /dev/mmcblk0

# Expected: > 150 MB/s
# If slower: replace with Class 10 SD card minimum 150 MB/s read/write
```

Other causes:
- Too many background processes
- USB device causing interference
- Sensor needs restart

```bash
# Restart sensor
sudo reboot
```

---

### Files not being created

**Problem**: Script runs but no audio files appear.

**Check**:
```bash
# Is the recording directory writable?
ls -la ~/multichannel_audio/
touch ~/multichannel_audio/test  # Should succeed

# Are logs being created?
tail ~/logs/*.log

# Look for errors
grep -i "error\|failed" ~/logs/*.log
```

**Possible causes**:
- Disk full → `df -h` to check
- Wrong permissions → `chmod 755 ~/multichannel_audio/`
- Sensor not initialized → Check device_index

---

### "PyAudio installation failed"

See [advanced_configuration.md#troubleshooting-pyaudio-installation](advanced_configuration.md#troubleshooting-pyaudio-installation)

```bash
# Quick fix (Raspberry Pi)
sudo apt-get install python3-pyaudio
```

---

## Upload Issues

### Files not uploading to cloud

**Check**:
```bash
# Verify monitoring mode is online
grep "monitoring_mode" config.json

# Test rclone connection
rclone ls mybox:  # Should list your cloud folder

# Check internet
ping 8.8.8.8

# View upload logs
tail -n 100 ~/logs/*.log | grep upload
```

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
rclone config reconnect mybox

# Then follow prompts to sign in again
```

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
- Use wired Ethernet: `sudo apt-get install -y raspi-config` → Interface Options → Ethernet
- Reduce file size: Use FLAC codec, lower sample rate (16 kHz is standard)
- Schedule uploads during off-peak hours

---

### Disk fills up, upload stops

**Problem**: `/tmp` or `/home` partitions full.

**Check**:
```bash
df -h  # Shows disk usage

# Specifically check home directory
du -sh ~/*
```

**Solution**:
```bash
# Delete old recordings if keeping local copies
rm ~/multichannel_audio/old_files_*.flac

# Or enable automatic deletion in config.json:
# "keep_recorded_data": false
```

---

## Startup/Shutdown Issues

### Script not starting on boot

**Problem**: Recorder doesn't start when Pi powers on.

**Check**:
```bash
# Verify startup script is executable
ls -l ~/multi-channel-rpi-eco-monitoring/recorder_startup_script.sh
# Should show "rwxr-xr-x"

# If not:
chmod +x ~/multi-channel-rpi-eco-monitoring/recorder_startup_script.sh
```

**Check `/etc/profile` configuration**:
```bash
tail /etc/profile  # Should show startup script lines
```

**View startup logs**:
```bash
# Check if script is running
ps aux | grep python_record.py

# Check systemd journal
journalctl -xe | tail -50
```

---

### Shutdown button not working

**Problem**: GPIO button doesn't trigger shutdown.

**For Sipeed 7-Mic**:
- Device tree button is system-level, should work independently
- Check GPIO 21 is free: `raspi-gpio get 21`
- Verify wiring: Button connects GPIO 21 to GND

**For Respeaker 6-Mic**:
```bash
# Check if Python script is listening for button
grep "use_system_shutdown_button" config.json

# If 0, button is software-managed
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

# Expected: python_record.py ~30-50% CPU
# If higher: may indicate sensor or filesystem issue
```

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
# View voltage warnings in kernel logs
dmesg | grep -i "low volt"

# If you see warnings, upgrade power supply
```

**Solutions**:
- Use 5V 2.5A+ power supply (not USB port)
- Use powered USB hub for sensors
- Reduce recording sample rate to 16 kHz

---

## Configuration Issues

### "config.json not found"

**Solution**:
```bash
cd ~/multi-channel-rpi-eco-monitoring
python setup_config.py
```

### config.json syntax error

**Error**: `json.decoder.JSONDecodeError`

**Fix**:
```bash
# Validate JSON syntax
python -m json.tool config.json

# If error shown, fix manually
nano config.json

# Common mistakes:
# - Missing commas between fields
# - Trailing commas (not allowed in JSON)
# - Unquoted strings
```

---

### Timezone not working

**Problem**: Logs show wrong time.

**Check configured timezone**:
```bash
# View system timezone
timedatectl

# Configure timezone in config.json
python setup_config.py
# Or manually: "timezone": "Europe/London"
```

---

## Disk Space Management

### How much space does recording use?

**Rule of thumb** (per 20-minute session):
- Sample rate 16 kHz, 7 channels, 16-bit, FLAC: ~200-300 MB
- Sample rate 48 kHz, 7 channels, 24-bit, FLAC: ~1-1.5 GB

**Calculate for your setup**:
```
Size ≈ (sample_rate × channels × bit_depth / 8) × duration × (1 - compression_ratio)
```

For FLAC, compression ratio is typically 40-60% (final size = 40-60% of uncompressed).

### Monitor disk usage

```bash
# Check available space
df -h

# Monitor in real-time during recording
watch -n 1 du -sh ~/multichannel_audio/
```

---

## Sensor-Specific Issues

### Sipeed 7-Mic Array

**No audio detected**:
- Check USB cable connection
- Try different USB port
- `python discover_serial.py` to find device index
- Update `device_index` in config.json

**Multiple devices showing**:
- Only one should be active
- Disconnect unused sensors
- Update `device_index` to select correct one

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

# Recording config
cat ~/multi-channel-rpi-eco-monitoring/config.json

# Recent logs
tail -n 200 ~/logs/*.log

# Audio device info
python discover_serial.py

# Disk usage
df -h
```

### Enable verbose logging

Edit `recorder_startup_script.sh`, add `-v` flag to python calls:

```bash
# Change this:
python python_record.py

# To this:
python python_record.py -v  # if supported
```

Then check logs:
```bash
tail -f ~/logs/*.log  # Follow logs in real-time
```

---

## Quick Recovery

### Emergency shutdown (safe)

```bash
# Graceful shutdown
sudo halt

# Then wait for green LED to stop flashing before removing power
```

### Reset configuration

```bash
cd ~/multi-channel-rpi-eco-monitoring
rm config.json
python setup_config.py  # Start fresh
```

### Clear old recordings

```bash
# List recordings
ls -lh ~/multichannel_audio/

# Delete old ones
rm ~/multichannel_audio/older_than_X_days_*.flac

# Or use find:
find ~/multichannel_audio/ -mtime +7 -delete  # Older than 7 days
```

### View live logs

```bash
# Watch logs as they're written
tail -f ~/logs/*.log

# Filter for errors only
tail -f ~/logs/*.log | grep -i error
```

---

## Still Need Help?

Check:
1. [advanced_configuration.md](advanced_configuration.md) - Advanced options
2. [CONFIG.md](CONFIG.md) - All configuration options
3. [CLOUD_SETUP.md](CLOUD_SETUP.md) - Upload troubleshooting
4. [LOG_GUIDE.md](LOG_GUIDE.md) - Understanding log format
5. [README.md](README.md) - Full project documentation

# Advanced Configuration Guide

This document contains additional setup instructions for specialized configurations and optimizations for the multi-channel Raspberry Pi ecosystem monitoring system.

## Shutdown Button Setup for Sipeed 7-Mic Array

![GPIO Pin on Raspberry Pi Zero 2 W](https://i.sstatic.net/yHddo.png)

*GPIO Pin on Raspberry Pi Zero 2 W.*

If using Sipeed 7-Mic Array sensor, you can set up a hardware shutdown button using device tree overlay:

* Edit `/boot/config.txt` (or `/boot/firmware/config.txt` on newer OS versions):
  ```
  sudo nano /boot/config.txt
  ```

* Add this line at the end of the file:
  ```
  dtoverlay=gpio-shutdown,gpio_pin=21,active_low=1,gpio_pull=up
  ```

* Save and exit (Ctrl+X, Y, Enter)

* Reboot the Raspberry Pi:
  ```
  sudo reboot
  ```

This configures GPIO pin 21 as a shutdown button. Connect a momentary push button between GPIO 21 and GND. Pressing the button will trigger a safe system shutdown.

**Note**: This is a system-level configuration that works independently of the Python monitoring script.

## Shutdown Button Setup for Respeaker 6-Mic (System-Wide)

For Respeaker 6-Mic deployments, you can also use a system-level shutdown button so it still works even if the Python recorder is not running.

* Edit `/boot/config.txt` (or `/boot/firmware/config.txt` on newer OS versions):
  ```
  sudo nano /boot/config.txt
  ```

* Add this line at the end of the file:
  ```
  dtoverlay=gpio-shutdown,gpio_pin=26,active_low=1,gpio_pull=up
  ```

* Save and exit (Ctrl+X, Y, Enter)

* Reboot the Raspberry Pi:
  ```
  sudo reboot
  ```

This configures GPIO pin 26 as a shutdown button. Connect a momentary push button between GPIO 26 and GND.

To avoid duplicate handling with the Python GPIO listener, set this in your `config.json`:

```json
{
  "sys": {
    "use_system_shutdown_button": 1
  }
}
```

With `use_system_shutdown_button` enabled, `python_record.py` will skip registering the Python-side button callback for Respeaker sensors.

### One-command helper (recommended)

This repository provides `enable_system_shutdown_button.sh` to apply both changes automatically:

```bash
cd ~/multi-channel-rpi-eco-monitoring
chmod +x enable_system_shutdown_button.sh
sudo ./enable_system_shutdown_button.sh 26 ./config.json
sudo reboot
```

What it does:
* Adds (or replaces) `dtoverlay=gpio-shutdown,gpio_pin=26,active_low=1,gpio_pull=up` in boot config.
* Sets `sys.use_system_shutdown_button=1` in `config.json`.

## Power Saving Configuration

For long-term battery-powered monitoring deployments, you can reduce power consumption with these configurations:

### Disable HDMI Output
* **Option 1: Run on startup** (add to `recorder_startup_script.sh`):
  ```
  # Disable HDMI to save power
  tvservice -o
  ```

* **Option 2: Permanent configuration** (add to `/boot/config.txt`):
  ```
  hdmi_blanking=1
  hdmi_force_hotplug=0
  ```

### Disable Bluetooth
* Add to `/boot/config.txt`:
  ```
  dtoverlay=disable-bt
  ```

### Disable Activity LED
* **Option 1: Add to `/boot/config.txt`**:
  ```
  dtparam=act_led_trigger=none
  dtparam=act_led_activelow=on
  ```

* **Option 2: Run on startup** (add to `recorder_startup_script.sh`):
  ```
  # Disable activity LED to save power
  echo 0 > /sys/class/leds/led0/brightness
  ```

### Additional Power Saving Tips
* Use a quality power supply with appropriate voltage/current
* Disable unnecessary services: `sudo systemctl disable bluetooth.service`
* Consider using Raspberry Pi Zero 2 W for lower power consumption
* Monitor battery voltage if using battery power

## Troubleshooting PyAudio Installation

If PyAudio installation fails on Raspberry Pi, try these alternatives:

### Option 1: Use system package (recommended for Raspberry Pi)
```bash
sudo apt-get install python3-pyaudio
```

### Option 2: Manual installation with pip
```bash
# Ensure dependencies are installed
sudo apt-get install portaudio19-dev python3-dev

# Install PyAudio
pip install --no-cache-dir pyaudio
```

### Option 3: Force binary installation
```bash
pip install --only-binary=all pyaudio
```

### Test installation:
```bash
python3 -c "import pyaudio; print('PyAudio installed successfully')"
```

## Side Notes

* Be careful not to pull the power cable from the Pi (or pull the plug out the socket) - this has been known to corrupt the SD card, and requires a fresh install.
* Using a battery bank is a safe option - if it runs out of power, the Pi tends to shutdown safely.
* To safely power off, use the appropriate method for your sensor (e.g., button on Respeaker 6-Mic array or software shutdown), and wait for the green light (on the Pi) to stop flashing.

## Make a new disk image

* Take the microSD card from the Pi, and make a copy of it onto your computer [(How?)](https://howchoo.com/pi/create-a-backup-image-of-your-raspberry-pi-sd-card-in-mac-osx).
  * Note: May need to run ``sudo -i`` (before sudo dd...) - this puts the terminal into root mode
  * Note: After running sudo dd... it may take a while - You get no indication of how far through you are - as long as the no error appears in the terminal, or no new line for code entry, just wait (up to 1 hour for 32 GB SD card)
* Now you can clone as many of these SD cards as you need for your monitoring devices with no extra setup required - install on new SD card with Balena Etcher
# multi-channel-rpi-eco-monitoring

This is the code designed to run a MAARU (Multichannel Autonomous Acoustic Recording Unit), now focused on using the Sipeed 7-Mic Array for high-quality multichannel audio recording in ecosystem monitoring. Full details on applications and hardware setup [here](https://beckyheath.github.io/MAARU/).

**Original project by Becky Heath**: This repository is a fork and adaptation of the original work by Becky Heath and contributors. For the original repository, see [BeckyHeath/multi-channel-rpi-eco-monitoring](https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring).

Code adapted by Rifqi Ikhwanuddin from Neel Le Penru, James Skinner, Becky Heath, and Sarab Sethi's work on Autonomous Ecosystem Monitoring. More information on that project and full details at: https://github.com/sarabsethi/rpi-eco-monitoring.

## Hardware Paths

This project now has two practical deployment paths, depending on which microphone array you want to use.

### Legacy Path: Respeaker 4-Mic / 6-Mic

Choose this path if you want to keep using the older Respeaker hardware from the original MAARU workflow.

* Recommended reference repository: [BeckyHeath/multi-channel-rpi-eco-monitoring](https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring)
* Use an older Raspberry Pi OS / Raspbian Buster image from the 2020 era, because the Seeed audio driver stack is tied to older kernels.
* Install the Seeed Voicecard / soundcard driver as required by the Respeaker hardware.
* Do **not** update the kernel after the audio stack is working.
* Avoid `rpi-update`, `apt full-upgrade`, or any other upgrade path that changes the kernel or low-level audio driver stack.
* In practice, this is the "legacy" line and should be treated as a frozen deployment environment.

### Modern Path: Sipeed 7-Mic Array

Choose this path if you want to use the newer Sipeed 7-Mic Array, which is the primary focus of this fork.

* Recommended repository: this fork
* You can use newer Raspberry Pi OS releases.
* No Seeed Voicecard installation is required.
* You do not need to freeze the kernel just to support the microphone array.
* This is the recommended path for new deployments.

The setup steps below are primarily for the modern Sipeed path. If you are deploying Respeaker hardware, follow the legacy path constraints above first and use the original repository as your baseline.

Key changes include:
  1. Focus on Sipeed 7-Mic Array for multichannel recording and ecosystem monitoring.
  2. Additional staging step for postprocessing.
  3. Added fault removal timeout in recording.
  4. Sensor adaptation to include multichannel recording.
  5. Added code to safely power down device, compatible with sensors that have shutdown buttons (e.g., Respeaker 6-Mic array) - instead of cutting power to the device
  6. Added code to check for remaining storage space on SD card, before recording - trying to record past limit causes corruption
  7. Added pre-set config.json file, specifically for offline data capture...
      a. Set to offline mode (won't attempt to connect to internet / rclone upload).
      b. Set compression to flac (in config.json & sensor files)
  8. Old Data is deleted upon boot-up. Make sure that after the battery dies, DiskInternals Linux Reader - https://www.diskinternals.com/linux-reader/ - is used to recover the data.
  9. Migrated from FTP to rclone for cloud storage upload (more reliable and flexible).
  10. Improved subprocess calls to suppress unnecessary output and enhance error handling.
  11. Removed the legacy setup.py file; repository metadata now lives in pyproject.toml.
  12. Added support for Sipeed 7-Mic Array sensor (Sipeed7Mic.py).
    13. Separated interactive configuration logic into a dedicated installer (`installer.py`, formerly `setup_config.py`) for modularity and ease of use.
  14. Integrated systemd service installation (`eco-monitor.service`) and GPIO shutdown-button configuration into the installer under a single menu-driven umbrella. The installer now requires root (`sudo python3 installer.py`) and ships a committed `eco-monitor.service` template for reproducible deployments.

### Configuration & Operational Scenarios

The system behavior is controlled primarily via `config.json`.

#### Operational Scenarios

| Scenario | `offline_mode` | `test_mode` | Description |
| :--- | :---: | :---: | :--- |
| **Forest (Deployment)** | `1` | `0` | Records continuously, skips all network/upload attempts. |
| **Home (Upload)** | `0` | `0` | Connects to network, performs time-sync, uploads to cloud. |
| **Development/Testing** | `1` | `1` | Forces short recording intervals, adds debug logs, skips uploads. |

#### Editing `config.json`

**⚠️ CRITICAL WARNING:** When editing `config.json` manually:
- Use **strict JSON format**.
- **NO comments allowed** (i.e., do not add `#` or `//` inside the file).
- Ensure all keys and string values are enclosed in **double quotes** (`"`).
- **NO trailing commas** after the last item in a dictionary or list.

The system will fail to start (`JSONDecodeError`) if these rules are broken. It is recommended to use `sudo python3 installer.py` (menu option 1) for generating the file instead of manual editing whenever possible.

NOTE! SD card should have sufficiently fast read/write speed (Class 10, **minimum 150 mb/s**), otherwise you will get overrun errors during recording. This means data won't record properly - you may see dead channels with no data.

This code has been setup to run on a **Raspberry Pi Zero 2 W+**, **Raspberry Pi 3B+**, and **Raspberry Pi 4B+**

📖 **For advanced configuration options** (shutdown buttons, power saving, troubleshooting): see [advanced_configuration.md](advanced_configuration.md)

## Setup

### Prebuilt Image

We have made a new disk image for this fork. If using this image, clone the image to and SD card then skip ahead to the "RPI Configuration" steps below to customise your ecosystem monitoring protocol and finish install. This image can be found [here](https://drive.google.com/file/d/1sTKPgUOcT4SQeJqtF6wdd6rjtqFLZzfR/view?usp=sharing). If you'd like to set the Raspberry Pi up manually follow the manual setup below and *then* the Configuration procedure. 

### Manual Setup

If you would rather start using a stock Raspberry Pi OS image, pick the correct path first:

* **Respeaker legacy path**: use an older Raspbian Buster image from early 2020, install the Seeed soundcard stack, and do not update the kernel afterward.
* **Sipeed modern path**: use a current Raspberry Pi OS image and continue with the setup steps below. No Seeed Voicecard install is needed.

### Setup Overview

#### Legacy Respeaker Setup

Use this only if you are deliberately deploying Respeaker 4-Mic or 6-Mic hardware and are prepared to keep the system on the older software stack.

##### Legacy Respeaker OS Setup

* Use a clean SD card - to erase contents of prev SD card, use 'Disk Utility' program on Mac or you can format the SD card fresh.
* Download and extract the recommended older Raspberry Pi OS / Raspbian Buster image onto your computer.
* Flash the OS (.img file) to the SD card - you can use [Balena Etcher](https://www.balena.io/etcher/).
* Insert SD card into the Pi and power on.
* Make sure to use DEFAULT settings (don't change the password - keep as 'raspberry') - just click 'next'.
* Connect to your wifi network.
* Do **not** install general OS updates. Updated Raspbian / Raspberry Pi OS versions are known to break compatibility with the Respeaker sound card stack.
* Update only the Pi kernel headers:
  ```bash
  sudo apt-get install raspberrypi-kernel-headers
  sudo reboot
  ```
* After reboot, prevent further kernel-related updates:
  ```bash
  sudo apt-mark hold raspberrypi-kernel-headers raspberrypi-kernel
  sudo apt-mark showhold
  ```
* Check that Python3 is already installed.
  * `python3` in terminal should show Python 3.7.3.
  * Otherwise, install Python3:
    ```bash
    sudo apt-get install python3
    ```
* Install packages to read mounted drives:
  ```bash
  sudo apt-get install exfat-fuse
  sudo apt-get install exfat-utils
  ```

##### Legacy Respeaker Voicecard Setup

* Open a terminal.
* Install git if needed:
  ```bash
  sudo apt-get install git
  ```
* Clone the Seeed Voicecard repository into the home directory of the Raspberry Pi:
  ```bash
  git clone https://github.com/respeaker/seeed-voicecard.git
  ```
* Enter the repository:
  ```bash
  cd seeed-voicecard
  ```
* Install the sound card stack:
  ```bash
  sudo ./install.sh
  ```
* Reboot the Pi:
  ```bash
  sudo reboot
  ```

After that point, keep the deployment frozen. Do not remove the kernel hold and do not run broad system upgrades unless you are prepared to rebuild the legacy audio setup from scratch.

#### Sipeed 7-Mic Setup

* Use a clean SD card - to erase contents of prev SD card, use 'Disk Utility' program on Mac or you can format the SD card fresh. 
* Download and extract a current Raspberry Pi OS image onto your computer.
* Flash the OS (.img file) to the SD card - you can use [Balena Etcher](https://www.balena.io/etcher/)
* Insert SD card into the pi and power on
* Make sure to use DEFAULT settings (don't change the password - keep as 'raspberry') - just click 'next'
* Connect to your wifi network
* Check that Python3 is already installed
  * ``python3`` in terminal --> Should show an installed Python 3 version
  * Otherwise, install Python3 - 
    ```
    sudo apt-get install python3
    ```
* Install packages to read mounted drives
  ```
  sudo apt-get install exfat-fuse
  sudo apt-get install exfat-utils
  ```

##### Sipeed Recorder Setup

* Log in and open a terminal
* Clone this repository into the home directory of the Raspberry pi: 
  ```
  git clone https://github.com/ikhwanuddin/multi-channel-rpi-eco-monitoring.git
  ```
* This repository is run directly from source on the Raspberry Pi. There is no `pip install .` step.
* Install the required system packages:
  ```
  sudo apt-get -y install fswebcam ffmpeg usb-modeswitch ntpsec-ntpdate chrony rclone zip python3-rpi.gpio python3-numpy python3-pyaudio python3-psutil alsa-utils
  ```
* If you are intentionally deploying the old Respeaker path instead, stop here and switch to the legacy repository/instructions before installing newer OS-specific components.
* Set up rclone for cloud storage (optional for online upload):
  * **Note**: This step is optional. If you prefer offline mode (no cloud upload), you can skip this setup. The system will record audio locally without uploading to cloud storage. For online monitoring with cloud upload (e.g., to Box), follow these steps.
  * Run the rclone configuration:
    ```
    rclone config
    ```
  * Follow the prompts to create a new remote named "mybox" for Box:
    - Choose 'n' for new remote
    - Name: mybox
    - Storage: box
    - client_id: (leave blank for auto, or enter your Box app client ID if you have one)
    - client_secret: (leave blank for auto, or enter your Box app client secret)
    - box_config_file: (leave blank)
    - box_sub_type: (choose user for personal Box account)
    - Follow the authorization link in your browser, log in to Box, and grant permissions
    - Enter the authorization code when prompted
    - Confirm the remote is configured correctly
  * This sets up rclone to upload files to your Box account under the remote name "mybox"
* To configure the system and install the service:
  * Run the installer and follow the prompts. The recommended path is menu option **4 (Full setup)**, which generates ``config.json``, installs the systemd service, and configures the GPIO shutdown button in one guided flow. Alternatively, use individual menu options (1, 2, 3) for step-by-step control.
    ```
    sudo python3 installer.py
    ``` 
  * The setup supports one or two daily reboot times. The primary reboot defaults to ``02:00`` and the second reboot time is optional.
  * GPIO shutdown button configuration is integrated into the installer (menu option 3). It applies the ``dtoverlay=gpio-shutdown`` overlay to the boot config and sets ``sys.use_system_shutdown_button=1`` automatically, using the sensor-appropriate default pin (GPIO 21 for Sipeed, GPIO 26 for Respeaker).
* The installer (menu option 2) installs the ``eco-monitor.service`` systemd unit, which starts the monitoring automatically on boot — no ``/etc/profile`` edits or console autologin are required.
* If you are migrating from the older ``/etc/profile`` + ``recorder_startup_script.sh`` method, use the installer's menu option **5 (Migrate from legacy /etc/profile startup)** to remove the old lines, then reboot.
* Shutdown with 
  ```
  sudo shutdown -h now
  ```

### Raspberry Pi Configuration

* Boot the Raspberry Pi with our prepared SD card inserted
* On first boot, the RasPi should automatically reboot, to expand the file system to max capacity of the SD Card (image is only 8 GB)
* A config file has already been provided in the image
  * Uses Sipeed 7-Mic Array (default sensor)
  * 1200 second (20 min) record time intervals (configurable via setup)
  * No upload to cloud storage (fully offline)
**If you would like the Raspberry Pi to run online**...  press ``Ctrl+C`` when you see "Start of ecosystem monitoring startup script".
  * Type:
    ```
    cd ~/multi-channel-rpi-eco-monitoring
    ```
    * Run 
    ```
    sudo python3 installer.py
    ``` 
    and follow the prompts (menu option 4 for full setup, or individual options). This will create a ``config.json`` file which contains the sensor type, its configuration and the rclone cloud storage details (e.g., for Box or other providers). The config file can be created manually, or imported from external storage without running ``installer.py`` if preferred
  * Make sure the timezone is set correctly. Check by typing 
    ```
    sudo dpkg-reconfigure tzdata
    ``` 
    and following the prompts
  * Type 
    ```
    sudo halt
    ``` 
    to shut down the Pi
  * After reboot, the Pi should be good to go!

## Service Management (Recommended)

Running `record.py` as a `systemd` service is the recommended way to ensure your monitoring unit runs reliably. This method provides automatic restarts on failure, native logging, and better system integration.

### Setup Instructions

The recommended way to install the service is via the installer (menu option 2):

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py
# Select menu option 2 (Install systemd service)
```

The installer reads the `eco-monitor.service` template from the repository, substitutes the correct repo path and service user, writes it to `/etc/systemd/system/eco-monitor.service`, reloads the systemd daemon, and enables the service to start on boot. It can also start the service immediately if you choose.

For a full guided deployment (config + service + GPIO in one flow), use menu option **4 (Full setup)** instead.

**Reference: service unit file** (`eco-monitor.service` in the repository)

The template below is what the installer installs. Placeholders `__REPO_DIR__` and `__SERVICE_USER__` are substituted automatically:

```ini
[Unit]
Description=Eco Monitoring Service
After=network.target time-sync.target
Wants=time-sync.target

[Service]
User=__SERVICE_USER__
WorkingDirectory=__REPO_DIR__

# ── 1. Time sync ──
# Run update_time.sh to sync time via internet (NTP) or silently via offline gateway (Wi-Fi router)
# The '-' prefix makes it optional so the service starts even if no time source is found.
ExecStartPre=-/bin/bash -c 'cd __REPO_DIR__ && bash ./update_time.sh'

# ── 2. PI_ID dynamically from discover_serial.py ──
# No hardcoding — serial number is read automatically from the CPU
ExecStartPre=/bin/bash -c '/usr/bin/python3 __REPO_DIR__/discover_serial.py | sed "s/^/PI_ID=/" > /tmp/eco-monitor-pi-id.env'
EnvironmentFile=/tmp/eco-monitor-pi-id.env

# ── 3. Filesystem expansion (one-time) ──
# Check whether the root partition already uses >90% of the disk.
# If not, call raspi-config --expand-rootfs.
# Resize happens on the next reboot via the init script.
ExecStartPre=/bin/bash -c 'MARKER=/home/pi/.fs_expanded; if [ ! -f "$MARKER" ]; then ROOT_SIZE=$(df / | tail -1 | awk "{print \$2}"); DISK_SIZE=$(lsblk -b -o SIZE /dev/mmcblk0 2>/dev/null | head -2 | tail -1); if [ -n "$DISK_SIZE" ]; then DISK_SIZE_KB=$((DISK_SIZE / 1024)); if [ "$ROOT_SIZE" -lt $((DISK_SIZE_KB * 90 / 100)) ]; then sudo raspi-config --expand-rootfs 2>/dev/null; echo "FS expansion triggered (resize on next reboot)"; else echo "FS already expanded"; fi; else echo "Cannot determine disk size"; fi; touch "$MARKER"; fi'

# ── 4. Turn off Sipeed LEDs (power saving) ──
# Safe if Sipeed is not connected (prefix '-' = allow failure)
ExecStartPre=-/usr/bin/bash __REPO_DIR__/led_off.sh

# ── 5. Turn off ACT LED on the RPi board (power saving) ──
ExecStartPre=+/bin/bash -c 'for led in /sys/class/leds/ACT /sys/class/leds/led0; do if [ -d "$led" ]; then echo none > "$led/trigger" 2>/dev/null; echo 0 > "$led/brightness" 2>/dev/null; fi; done; exit 0'

# ── 6. Sync rclone.conf with Gist ──
# Requires gist.github_token & gist.gist_id in config.json.
# Non-critical — if it fails (offline / not configured) the service still runs.
ExecStartPre=-/bin/bash -c 'cd __REPO_DIR__ && bash sync_rclone_config.sh /dev/null ./config.json 2>&1 || true'

# ── 7. Main: record.py ──
ExecStart=/usr/bin/python3 -u __REPO_DIR__/record.py __REPO_DIR__/config.json logfile.log logs

# Automatic restart on crash (replaces the while-true loop in bash)
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**`ExecStartPre` prefix legend**:
- **No prefix**: runs as the service user (default `pi`).
- **Prefix `+`**: runs as `root` (required for `/sys/class/leds` access).
- **Prefix `-`**: failure is allowed — if Sipeed is not connected or there is no internet, the service continues.

**Manual installation** (if not using the installer):
```bash
sudo cp eco-monitor.service /etc/systemd/system/eco-monitor.service
# Edit the file to replace __REPO_DIR__ and __SERVICE_USER__ with your values
sudo systemctl daemon-reload
sudo systemctl enable eco-monitor.service
sudo systemctl start eco-monitor.service
```

### Service Commands

You can use the following commands to manage your monitoring service:

| Action | Command |
| :--- | :--- |
| **Check Status** | `sudo systemctl status eco-monitor.service` |
| **Start Service** | `sudo systemctl start eco-monitor.service` |
| **Stop Service** | `sudo systemctl stop eco-monitor.service` |
| **Restart Service** | `sudo systemctl restart eco-monitor.service` |
| **View Logs** | `journalctl -u eco-monitor.service -f` |

---
> **Legacy Note**: The previous method using `recorder_startup_script.sh` in `/etc/profile` is now considered legacy and is **not recommended** for new deployments. Please migrate to the `systemd` service method described above for better stability.

### Migration Checklist

When switching from `/etc/profile` + `recorder_startup_script.sh` to systemd service:

**Recommended: via the installer (menu option 5)**

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py
# Select menu option 5 (Migrate from legacy /etc/profile startup)
# Then select menu option 2 (Install systemd service)
sudo reboot
```

The installer automatically removes the two legacy lines (`chmod +x ...` and `recorder_startup_script.sh`) from `/etc/profile`, then installs and enables the systemd service.

**Manual migration** (if not using the installer):

1. Remove the old `/etc/profile` lines:
   ```bash
   sudo nano /etc/profile
   # Remove the 2 lines containing chmod +x ... and recorder_startup_script.sh
   ```
2. Create and enable the service (see setup above)
3. Reboot to verify:
   ```bash
   sudo reboot
   # After logging in, check status:
   sudo systemctl status eco-monitor.service
   ```
4. **Note**: `recorder_startup_script.sh` has been removed from the repository — its functionality has been replaced by the systemd service (`eco-monitor.service`). The script can still be found in git history for reference.

---

### Log Prefix Contract

Runtime logs now follow a structured prefix contract so they are easy to filter by source, mode, and phase.

Contract summary:

| Source | Prefix format | Notes |
|---|---|---|
| Startup orchestration | `[startup][mode=<value>][phase=<value>]` | Main boot, mode detection, recording/upload loop control |
| Upload pipeline | `[upload][phase=<value>]` | Upload flow state (scan, copy, verify, finalize, error) |
| Time synchronization | `[time-sync][mode=<value>][phase=<value>]` | NTP or SSH-epoch time sync path |
| Optional subcomponent tag | `[component=<value>]` | Added inside message for finer filtering (for example rclone, verify, upload-helper) |

Current mode values in startup logs:

* `boot`
* `online`
* `offline`

Common startup phase values:

* `init`
* `bootstrap`
* `detect-mode`
* `recording`
* `recording-loop`
* `upload-init`
* `upload-loop`
* `shutdown`

Common upload phase values:

* `init`
* `scan-local`
* `mark-uploading`
* `rclone-copy`
* `verify`
* `finalize`
* `error`

Upload logging note:

* During `rclone-copy`, rclone one-line stats are emitted every `30s` (`--stats 30s --stats-one-line`).

For ready-to-use grep filters based on this contract, see [advanced_configuration.md](advanced_configuration.md).

### System-Wide Shutdown Button (Recommended)

Use system-wide shutdown handling so the button still works even if the recorder Python process is not running.

**Recommended: via the installer (menu option 3)**

```bash
cd ~/multi-channel-rpi-eco-monitoring
sudo python3 installer.py
# Select menu option 3 (Configure GPIO shutdown button)
sudo reboot
```

The installer detects the sensor type from `config.json` and suggests the appropriate default pin (GPIO 21 for Sipeed, GPIO 26 for Respeaker). It applies the `dtoverlay=gpio-shutdown` overlay to the boot config and sets `sys.use_system_shutdown_button=1` in `config.json` automatically.

**Manual method (alternative): using the helper script**

1. Choose GPIO pin by sensor:
   - Respeaker: use GPIO 26 (default)
   - Sipeed: use your wired shutdown pin (for example GPIO 21)
2. Run helper script from repository root:

```bash
cd ~/multi-channel-rpi-eco-monitoring
chmod +x enable_system_shutdown_button.sh
sudo ./enable_system_shutdown_button.sh 26 ./config.json
sudo reboot
```

3. What this command does:
   - Adds/replaces `dtoverlay=gpio-shutdown,...` in boot config (`/boot/config.txt` or `/boot/firmware/config.txt`)
   - Sets `sys.use_system_shutdown_button=1` in `config.json`

4. Verify after reboot:
   - Check overlay line exists:

```bash
grep -n "dtoverlay=gpio-shutdown" /boot/config.txt /boot/firmware/config.txt 2>/dev/null
```

   - Check config flag:

```bash
python3 -c "import json; print(json.load(open('config.json'))['sys'].get('use_system_shutdown_button'))"
```

For detailed wiring examples and sensor-specific notes, see [advanced_configuration.md](advanced_configuration.md).

## To Do
- [x] Add configuration option to always delete recorded data clean or always keep the files in ```installer.py```.
- [x] Integrate systemd service installation and GPIO shutdown-button configuration into `installer.py` under a single menu.

## Authors
This is a cross disciplinary research project based at Imperial College London, across the Faculties of Engineering, Natural Sciences and Life Sciences.

Work on this repo has been contributed by Rifqi Ikhwanuddin, Neel P L Penru, James Skinner, Becky Heath, Sarab Sethi, Rob Ewers, Nick Jones, David Orme, Lorenzo Picinali.


## Citations
Please cite the below papers when referring to this work:

Heath, BE, Suzuki, R, Le Penru, NP, Skinner, J, Orme, CDL, Ewers, RM, Sethi, SS, Picinali, L. Spatial ecosystem monitoring with a Multichannel Acoustic Autonomous Recording Unit (MAARU) [https://doi.org/10.1111/2041-210X.14390](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.14390)

Le Penru, NP, Heath, BE, Dunning, J, Picinali, L, Ewers, RM, Sethi, SS. Towards using virtual acoustics for evaluating spatial ecoacoustic monitoring technologies.  [https://doi.org/10.1111/2041-210X.14405](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.14405)

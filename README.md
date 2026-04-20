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
  13. Separated interactive configuration logic into setup_config.py for modularity and ease of use.

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
  sudo apt-get -y install fswebcam ffmpeg usb-modeswitch ntpsec-ntpdate chrony rclone zip python3-rpi.gpio python3-numpy python3-pyaudio alsa-utils
  ```
  (note: rclone for cloud upload, chrony for enhanced time synchronization)
* Install the Python package used by the recorder scripts:
  ```
  python3 -m pip install -r requirements.txt
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
* To configure the system:
  * Run and follow the prompts. This will create a ``config.json`` file which contains the sensor type, its configuration and the rclone cloud storage details (e.g., for Box or other providers). (Note: setup_config.py is the interactive configuration script.)
    ```
    python setup_config.py
    ``` 
  * The setup now supports one or two daily reboot times. The primary reboot defaults to ``02:00`` and the second reboot time is optional.
  * For Respeaker deployments, setup now includes ``sys.use_system_shutdown_button``. Keep this at ``1`` if you enabled ``dtoverlay=gpio-shutdown`` in boot config.
* Make sure all the scripts in the repository are executable, and that ``recorder_startup_script.sh`` runs on startup...
  * Open a new terminal and type this from the root directory:
    ```
    sudo nano /etc/profile
    ``` 
  * Add the following 2 lines to the end of the file:
    ```
    chmod +x ~/multi-channel-rpi-eco-monitoring/*;
    sudo -u pi ~/multi-channel-rpi-eco-monitoring/recorder_startup_script.sh;
    ```
* Make sure Pi boots to command line upon login (without login required)...
  * Open new terminal and type:
    ```
    sudo raspi-config
    ```
  * _3 Boot Options_ -> _B1 Desktop / CLI_ -> _B2 Console Autologin_
  * Press ``Esc`` when this is complete -> Say No to reboot
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
    python setup_config.py
    ``` 
    and follow the prompts. This will create a ``config.json`` file which contains the sensor type, its configuration and the rclone cloud storage details (e.g., for Box or other providers). The config file can be created manually, or imported from external storage without running ``setup_config.py`` if preferred
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

### Additional Configuration

For advanced configuration options including shutdown button setup, power saving configurations, troubleshooting, and additional notes, see [advanced_configuration.md](advanced_configuration.md).

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

For ready-to-use grep filters based on this contract, see [advanced_configuration.md](advanced_configuration.md).

### System-Wide Shutdown Button (Recommended)

Use system-wide shutdown handling so the button still works even if recorder Python process is not running.

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
- [x] Add configuration option to always delete recorded data clean or always keep the files in ```setup_config.py```.

## Authors
This is a cross disciplinary research project based at Imperial College London, across the Faculties of Engineering, Natural Sciences and Life Sciences.

Work on this repo has been contributed by Rifqi Ikhwanuddin, Neel P L Penru, James Skinner, Becky Heath, Sarab Sethi, Rob Ewers, Nick Jones, David Orme, Lorenzo Picinali.


## Citations
Please cite the below papers when referring to this work:

Heath, BE, Suzuki, R, Le Penru, NP, Skinner, J, Orme, CDL, Ewers, RM, Sethi, SS, Picinali, L. Spatial ecosystem monitoring with a Multichannel Acoustic Autonomous Recording Unit (MAARU) [https://doi.org/10.1111/2041-210X.14390](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.14390)

Le Penru, NP, Heath, BE, Dunning, J, Picinali, L, Ewers, RM, Sethi, SS. Towards using virtual acoustics for evaluating spatial ecoacoustic monitoring technologies.  [https://doi.org/10.1111/2041-210X.14405](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.14405)


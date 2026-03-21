# multi-channel-rpi-eco-monitoring

This is the code designed to run a MAARU (Multichannel Autonomous Acoustic Recording Unit), now focused on using the Sipeed 7-Mic Array for high-quality multichannel audio recording in ecosystem monitoring. Full details on applications and hardware setup [here](https://beckyheath.github.io/MAARU/).

**Original project by Becky Heath**: This repository is a fork and adaptation of the original work by Becky Heath and contributors. For the original repository, see [BeckyHeath/multi-channel-rpi-eco-monitoring](https://github.com/BeckyHeath/multi-channel-rpi-eco-monitoring).

Code adapted by Rifqi Ikhwanuddin from Neel Le Penru, James Skinner, Becky Heath, and Sarab Sethi's work on Autonomous Ecosystem Monitoring. More information on that project and full details at: https://github.com/sarabsethi/rpi-eco-monitoring.

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
  11. Migrated to modern pyproject.toml packaging (replacing setup.py) for better compatibility and to avoid deprecation warnings.
  12. Added support for Sipeed 7-Mic Array sensor (Sipeed7Mic.py).
  13. Separated interactive configuration logic into setup_config.py for modularity and ease of use.

NOTE! SD card should have sufficiently fast read/write speed (Class 10, **minimum 150 mb/s**), otherwise you will get overrun errors during recording. This means data won't record properly - you may see dead channels with no data.

This code has been setup to run on a **Raspberry Pi 3B+** and **Raspberry Pi 4B+**

## Setup 

### Pre setup image: 

We have made a new disk image for this fork. If using this image, clone the image to and SD card then skip ahead to the "RPI Configuration" steps below to customise your ecosystem monitoring protocol and finish install. This image can be found [here](https://drive.google.com/file/d/1sTKPgUOcT4SQeJqtF6wdd6rjtqFLZzfR/view?usp=sharing). If you'd like to set the Raspberry Pi up manually follow the manual setup below and *then* the Configuration procedure. 

### Manual Setup 

If you would rather start using a stock Raspbian image, there's an extra couple of steps before you start the setup process. The seeed soundcard only works on older versions of Raspbian Buster (Rasbian Buster, 13th Feb 2020 works well). 

### Setup overview

#### Pi OS setup: 

* Use a clean SD card - to erase contents of prev SD card, use 'Disk Utility' program on Mac or you can format the SD card fresh. 
* Download and extract the [recommended OS](https://downloads.raspberrypi.org/raspbian_full/images/raspbian_full-2020-02-14/) (the zip file) onto your computer.
* Flash the OS (.img file) to the SD card - you can use [Balana Etcher](https://www.balena.io/etcher/)
* Insert SD card into the pi and power on
* Make sure to use DEFAULT settings (don't change the password - keep as 'raspberry') - just click 'next'
* Connect to your wifi network
* Check that Python3 is already installed
  * ``python3`` in terminal --> Should show Python 3.7.3
  * Otherwise, install Python3 - 
    ```
    sudo apt-get install python3
    ```
* Install packages to read mounted drives
  ```
  sudo apt-get install exfat-fuse
  sudo apt-get install exfat-utils
  ```

##### Set up Multi-Channel Eco Monitoring

* Log in and open a terminal
* Clone this repository into the home directory of the Raspberry pi: 
  ```
  git clone https://github.com/ikhwanuddin/multi-channel-rpi-eco-monitoring.git
  ```
* Install the package and dependencies: 
  ```
  cd multi-channel-rpi-eco-monitoring
  
  # Install system audio libraries (required for PyAudio)
  sudo apt-get install portaudio19-dev python3-dev
  
  # Install Python packages
  pip install . --break-system-packages
  ``` 
  (installs psutil for system monitoring, pyaudio for audio processing, and numpy for signal processing; uses --break-system-packages for system-wide installation)
* Install the required system packages: 
  ```
  sudo apt-get -y install fswebcam ffmpeg usb-modeswitch ntpsec-ntpdate chrony rclone zip python3-rpi.gpio alsa-utils
  ```
  (note: rclone for cloud upload, chrony for enhanced time synchronization)
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
* Make sure all the scripts in the repository are executable, and that ``recorder_startup_script.sh`` runs on startup...
  * Open a new terminal and type this from the root directory:
    ```
    sudo nano ../../etc/profile
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

### RPI Configuration

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

### Make a new disk image

* Take the microSD card from the Pi, and make a copy of it onto your computer [(How?)](https://howchoo.com/pi/create-a-backup-image-of-your-raspberry-pi-sd-card-in-mac-osx). 
  * Note: May need to run ``sudo -i`` (before sudo dd...) - this puts the terminal into root mode
  * Note: After running sudo dd... it may take a while - You get no indication of how far through you are - as long as the no error appears in the terminal, or no new line for code entry, just wait (up to 1 hour for 32 GB SD card)
* Now you can clone as many of these SD cards as you need for your monitoring devices with no extra setup required - install on new SD card with Balena Etcher


### Side Notes

* Be careful not to pull the power cable from the Pi (or pull the plug out the socket) - this has been known to corrupt the SD card, and requires a fresh install.
* Using a battery bank is a safe option - if it runs out of power, the Pi tends to shutdown safely.
* To safely power off, use the appropriate method for your sensor (e.g., button on Respeaker 6-Mic array or software shutdown), and wait for the green light (on the Pi) to stop flashing.

### Troubleshooting PyAudio Installation

If PyAudio installation fails on Raspberry Pi, try these alternatives:

**Option 1: Use system package (recommended for Raspberry Pi)**
```bash
sudo apt-get install python3-pyaudio
```

**Option 2: Manual installation with pip**
```bash
# Ensure dependencies are installed
sudo apt-get install portaudio19-dev python3-dev

# Install PyAudio
pip install --no-cache-dir pyaudio
```

**Option 3: Force binary installation**
```bash
pip install --only-binary=all pyaudio
```

**Test installation:**
```bash
python3 -c "import pyaudio; print('PyAudio installed successfully')"
```

## List To Do
- [ ] Add configuration option to always delete recorded data clean or always keep the fles in ```setup_config.py```.
- [ ] More efficient raspberry pi with better scheduling.

## Authors
This is a cross disciplinary research project based at Imperial College London, across the Faculties of Engineering, Natural Sciences and Life Sciences.

Work on this repo has been contributed by Rifqi Ikhwanuddin, Neel P L Penru, James Skinner, Becky Heath, Sarab Sethi, Rob Ewers, Nick Jones, David Orme, Lorenzo Picinali.


## Citations
Please cite the below papers when referring to this work:

Heath, BE, Suzuki, R, Le Penru, NP, Skinner, J, Orme, CDL, Ewers, RM, Sethi, SS, Picinali, L. Spatial ecosystem monitoring with a Multichannel Acoustic Autonomous Recording Unit (MAARU) [https://doi.org/10.1111/2041-210X.14390](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.14390)

Le Penru, NP, Heath, BE, Dunning, J, Picinali, L, Ewers, RM, Sethi, SS. Towards using virtual acoustics for evaluating spatial ecoacoustic monitoring technologies.  [https://doi.org/10.1111/2041-210X.14405](https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.14405)


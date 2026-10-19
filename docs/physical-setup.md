# MAARU Physical Setup & Hardware Components

## Overview

MAARU (Multichannel Acoustic Autonomous Recording Unit) is an ecosystem monitoring system. This document describes the hardware of this fork's build as deployed in tropical rainforest: what each component does and how the unit is protected from rain and humidity.

**Diagram**: See [maaru-physical-setup.svg](./maaru-physical-setup.svg) for the layered structure and physical connections (editable source: `maaru-physical-setup.af`, Affinity Designer).

---

## Layered Structure

```
PLASTIC ROOF
    ↓
FOOD BOX (Main Enclosure: plastic food container)
    ├─ 3D-printed Pi mount + mic cover ring
    ├─ Raspberry Pi
    ├─ Mic Sensor Array
    ├─ Micro SD Card
    ├─ USB WiFi Adapter (only on Pi models without onboard WiFi)
    ├─ Silica Gel
    └─ Membrane vents over mic holes (SEL-3254)
    ↓
DRY BAG (Power Protection)
    └─ Powerbank
        ↓
    USB Cable
        ↓
    [Connected to Pi]

Mounting:
    Rope & Rubber → Tree
```

### Enclosure and 3D-printed parts

The main enclosure used in the field is an ordinary plastic food container (about £1–2 from Poundland, London); any similar box works. The container is drilled near the mic ring, and the holes are covered with adhesive oleophobic membrane vents (SEL-3254) on all units. The vents let sound through while keeping water out.

Inside the box sit two 3D-printed parts per configuration: a Raspberry Pi support/mount with legs, and a mic cover ring for the mic array. They were designed in SolidWorks by ikhwanuddin (Feb–Mar 2026), starting from Neel Le Penru's CaseV4 design.

| Configuration | Pi mount | Mic cover ring |
|---------------|----------|----------------|
| ReSpeaker + Raspberry Pi | CaseV6-MainFrameV13-minimalis | CaseV6_MicCoverV6 |
| Raspberry Pi Zero 2 W + Sipeed | CaseV6-PiZero2Wv2 | CaseV6_MicCoverSipeedV3 |

The SolidWorks parts (`.SLDPRT`) and printable meshes (`.STL`) are in [`hardware/case/`](../hardware/case/).

### Other protection

- **Silica gel** inside the food box absorbs humidity.
- **Plastic roof** above the food box keeps direct rain off.
- **Dry bag** holds the powerbank, outside the food box.
- **Rope & rubber** tie the unit to a tree.

### Connections at a glance

- **Power**: powerbank (in dry bag) → USB cable → Pi power port (5V)
- **ReSpeaker** → GPIO header (I2S)
- **Sipeed** → USB port (USB Audio Class, MA-USB8 board)
- **WiFi**: onboard on most models; a USB WiFi adapter on models without it (e.g. Pi 2B)
- **Micro SD card** → Pi card slot

---

## Hardware Components

### Raspberry Pi

Tested with this fork: Raspberry Pi Zero 2 W, 3B+ and 4B. The field units at Way Canguk also include a Raspberry Pi 2B with the ReSpeaker. The runtime tuning (rclone limits, GC thresholds) targets the Zero 2 W's 512 MB RAM, so larger models simply have more headroom.

The Pi records WAV with `arecord`, compresses each finished file to FLAC with `ffmpeg`, keeps the files on the microSD card, uploads them with rclone when a network is available, and logs every step.

### Microphone array

#### Option A: ReSpeaker 6-Mic Circular Array (legacy)

- 6 recorded channels, `S32_LE`, 16 kHz
- Connects to the GPIO header (I2S)
- Needs the Seeed voicecard driver, so in practice an old Raspbian Buster image with the kernel frozen
- [Discontinued by Seeed Studio](https://www.seeedstudio.com/ReSpeaker-6-Mic-Circular-Array-Kit-for-Raspberry-Pi.html); the remaining units sold online are expensive

#### Option B: Sipeed 6+1 Mic Array + MA-USB8 board (sensor `Sipeed7Mic`)

- 8 recorded channels: CH0–CH5 ring mics, CH6 beamformed output (time-aligned average of CH0–CH5, not a physical mic), CH7 centre mic ([Sipeed wiki](https://wiki.sipeed.com/hardware/en/modules/micarray_usbboard_bl616.html))
- Recorded format: 16 kHz, 16-bit (`S16_LE`); the board streams 48 kHz and ALSA `plughw` resamples. 16 kHz is kept for consistency with earlier monitoring data
- Beamforming is done on the board (CH6); its direction can be steered in 30° steps over the serial port. The recorder does not change it
- Connects over USB as a standard USB Audio Class device, so it works on current Raspberry Pi OS without an extra driver
- The board's blue LEDs are switched off over the serial port (`led_off.sh`)
- Records at a noticeably lower level than the ReSpeaker. Raising the gain on the board has not been tested

### Micro SD card

Local storage for the OS and recordings. Size per recording (WAV upper bound; FLAC is smaller, depending on content):

```
Channels: 8 (Sipeed)
Sample Rate: 16 kHz
Bit Depth: 16 bits
Duration per recording: 20 minutes

Size per recording ≈ 307 MB as WAV

64 GB card → at least ~200 recordings (~67 hours)
128 GB card → at least ~400 recordings (~133 hours)
256 GB card → at least ~800 recordings (~267 hours)
(ignoring the space used by the OS; the recorder shuts the Pi down below 1 GB free)
```

### WiFi

WiFi is used for SSH and uploads. Most Pi models have onboard WiFi; a USB WiFi adapter is needed on models without it (e.g. Pi 2B). In the forest there is no network, so the [field WiFi timer](advanced_configuration.md#field-wifi-timer-keep-alive-while-linked-sleep-20-min-after-wlan-lost) puts WiFi to sleep after 20 minutes without a link instead of letting it scan for days.

### Powerbank

An ordinary powerbank is the only power source; see the deployment scenario below.

---

## Field Deployment Scenario (Way Canguk)

This fork is tailored to the field site at Way Canguk, Bukit Barisan Selatan National Park, Lampung, Indonesia. The original MAARU setup uses a solar panel with a deep-cycle battery and a 4G USB dongle. Neither works there. The canopy is over 40 m tall, so a solar panel would have to be carried above it to reach open sky. Instead each unit is mounted 6–8 m above the ground, below the canopy, and powered by an ordinary powerbank. With a powerbank sold as 100,000 mAh a unit runs for about two days; that capacity is the seller's claim and has not been measured.

There is no internet in the forest, so data are uploaded by hand: the unit is carried out to the village, where a network is available, and uploads from there. Each unit therefore alternates between two phases. In the forest it records and cannot upload; in the village it uploads and does not record. The code supports this directly: with `upload_enabled`, the recorder pauses when it detects internet, uploads through rclone, and resumes recording when the upload is finished or the connection is gone (see [cloud_setup.md](cloud_setup.md#how-uploads-work)).

### Village upload procedure

1. In the village, connect the unit to a network with internet and SSH in (`pi@rpi-<station>` over Tailscale).
2. `cd ~/multi-channel-rpi-eco-monitoring && git fetch origin && git reset --hard origin/master` (same as the auto-update on service start; `git pull` fails after a history rewrite).
3. Set `"upload_enabled": true` in `config.json` and run `restarteco` (or `sudo systemctl restart eco-monitor.service`) so the upload thread starts. Recording pauses while the unit is online.
4. When the upload cycle has finished, set `"upload_enabled"` back to `false` and leave the service alone. The running process keeps its old setting; the next boot in the forest reads `false` and only records.

With `upload_enabled: false` the unit keeps recording even when it has internet, so recordings made in the village or at home are not field data.

The Way Canguk ReSpeaker units recorded in shorter cycles than the defaults (e.g. 2A400: `record_length` 240 s, `capture_delay` 60 s; defaults 1200 s and 300 s).

This is very situational. If the conditions change (for example a reliable power source or a network in the forest), the code has to be changed to fit.

---

## Setup Checklist

### Pre-deployment

- [ ] OS flashed (current Raspberry Pi OS for Sipeed; Raspbian Buster with the Seeed driver for ReSpeaker), user `pi`, repository installed (`sudo python3 installer.py`)
- [ ] Sensor (ReSpeaker or Sipeed) connected and a short test recording checked (e.g. `test_mode: 1` and a small `record_length`, then restore the deployment values)
- [ ] Powerbank fully charged
- [ ] Silica gel placed inside the food box
- [ ] Membrane vents (SEL-3254) stuck over all mic holes
- [ ] Plastic roof attached, dry bag sealed, rope and rubber ready

### At the deployment site

- [ ] Unit tied securely to the tree
- [ ] Location and date marked on the unit

---

## References

- [Raspberry Pi Official Specs](https://www.raspberrypi.com/products/)
- [ReSpeaker 6-Mic Array Docs](https://wiki.seeedstudio.com/ReSpeaker_6-Mic_Array_for_Raspberry_Pi/)
- [Sipeed MA-USB8 Mic Array USB board](https://wiki.sipeed.com/hardware/en/modules/micarray_usbboard_bl616.html)

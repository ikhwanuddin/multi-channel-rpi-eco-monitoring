#!/bin/bash
# =============================================================================
# Script: Sipeed MicArray USB Board LED Controller
# Author: [Rifqi Ikhwanuddin / @ikhwanuddin]
# Repository: https://github.com/ikhwanuddin/multi-channel-rpi-eco-monitoring
# License: MIT
#
# Purpose
# -------
# Turn the 12 RGB LEDs on the Sipeed MicArray USB Board OFF via the
# USB CDC ACM virtual serial port. No firmware flashing required.
#
# Tested on:
#   • Raspberry Pi 3B+, 4B
#   • Raspberry Pi OS (Bookworm / Bullseye)
#   • Kernel 5.15 – 6.6
#
# Device: /dev/ttyACM0  (USB CDC ACM)
# Baud rate: 9600  (critical – 2000000 is for physical UART only!)
# =============================================================================

# --------------------------- CONFIGURATION ------------------------------------
DEVICE="/dev/ttyACM0"          # USB CDC ACM virtual serial port
BAUD_RATE=9600                 # Correct baud rate for command interface
SOUND_MAP_CMD="f"              # Enable sound field map (required for LED control)
LED_OFF_CMD="e"                # Turn LEDs OFF
LED_ON_CMD="E"                 # Turn LEDs ON
# -----------------------------------------------------------------------------

# --------------------------- VALIDATION --------------------------------------
# Check if the device node exists
if [ ! -c "$DEVICE" ]; then
    echo "ERROR: Device $DEVICE not found!" >&2
    echo "  → Is the Sipeed MicArray plugged in?" >&2
    echo "  → Run: ls /dev/ttyACM*" >&2
    exit 1
fi

# Verify read/write permissions
if [ ! -r "$DEVICE" ] || [ ! -w "$DEVICE" ]; then
    echo "ERROR: Insufficient permissions on $DEVICE" >&2
    echo "  → Fix (temporary): sudo chmod 666 $DEVICE" >&2
    echo "  → Fix (permanent): sudo usermod -aG dialout \$USER && reboot" >&2
    exit 1
fi
# -----------------------------------------------------------------------------

# --------------------------- MAIN CONTROL ------------------------------------
# Step 1: Enable sound field map – LED direction indicator only works when map is active
echo "Enabling sound field map (command: '$SOUND_MAP_CMD')..."
echo "$SOUND_MAP_CMD" > "$DEVICE"
sleep 0.1   # Small delay to ensure the command is processed

# Step 2: Turn OFF all 12 LEDs
echo "Turning LEDs OFF (command: '$LED_OFF_CMD')..."
echo "$LED_OFF_CMD" > "$DEVICE"

echo "LEDs turned OFF successfully!"
echo "  → Visual check: All 12 LEDs on the mic array should be dark."
echo "  → To turn ON again: echo '$LED_ON_CMD' > $DEVICE"
# -----------------------------------------------------------------------------

# --------------------------- USAGE TIPS --------------------------------------
# • Auto-run on boot (add before 'exit 0' in /etc/rc.local):
#     (sleep 5; stty -F /dev/ttyACM0 9600 raw -echo; \
#      echo 'f' > /dev/ttyACM0; echo 'e' > /dev/ttyACM0) &
#
# • Monitor sound map output (hex dump):
#     timeout 5 cat /dev/ttyACM0 | hexdump -C
#
# • Common mistake: Using 2000000 baud → garbled data or no response.
#     2000000 is for physical UART (USB-to-TTL adapter) only.
# =============================================================================

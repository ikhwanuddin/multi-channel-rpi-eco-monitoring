#!/bin/bash

set -e

GPIO_PIN="${1:-26}"
CONFIG_FILE="${2:-./config.json}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run as root (use sudo)."
  exit 1
fi

if [ -f /boot/firmware/config.txt ]; then
  BOOT_CONFIG=/boot/firmware/config.txt
elif [ -f /boot/config.txt ]; then
  BOOT_CONFIG=/boot/config.txt
else
  echo "Could not find /boot/config.txt or /boot/firmware/config.txt"
  exit 1
fi

OVERLAY_LINE="dtoverlay=gpio-shutdown,gpio_pin=${GPIO_PIN},active_low=1,gpio_pull=up"

if grep -qE "^dtoverlay=gpio-shutdown" "$BOOT_CONFIG"; then
  echo "Existing gpio-shutdown overlay found in $BOOT_CONFIG"
  sed -i.bak '/^dtoverlay=gpio-shutdown/d' "$BOOT_CONFIG"
  echo "Replaced old gpio-shutdown entry (backup: ${BOOT_CONFIG}.bak)"
fi

echo "$OVERLAY_LINE" >> "$BOOT_CONFIG"
echo "Added overlay: $OVERLAY_LINE"

if [ -f "$CONFIG_FILE" ]; then
  python3 - "$CONFIG_FILE" <<'PY'
import json
import sys

config_file = sys.argv[1]
with open(config_file, 'r', encoding='utf-8') as f:
    config = json.load(f)

config.setdefault('sys', {})['use_system_shutdown_button'] = 1

with open(config_file, 'w', encoding='utf-8') as f:
    json.dump(config, f, indent=4)
    f.write('\n')

print('Updated {}: sys.use_system_shutdown_button=1'.format(config_file))
PY
else
  echo "Config file not found: $CONFIG_FILE"
  echo "Skipping config update."
fi

echo "Done. Reboot required."
echo "Run: sudo reboot"

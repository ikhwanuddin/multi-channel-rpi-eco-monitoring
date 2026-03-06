#!/bin/bash

# Update time from internet using systemd-timesyncd (default NTP on Raspberry Pi OS)
sudo systemctl restart systemd-timesyncd
sleep 10  # Wait for sync to complete

# Optional: Check if chrony is available and use it as fallback
if command -v chronyc &> /dev/null; then
    printf "Chrony available, using chronyc makestep as additional sync\n"
    sudo chronyc makestep
else
    printf "Chrony not available, relying on systemd-timesyncd\n"
fi

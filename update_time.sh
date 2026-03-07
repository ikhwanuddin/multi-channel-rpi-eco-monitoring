#!/bin/bash

# Update time from internet using timedatectl (works on systemd-based systems)
sudo timedatectl set-ntp true
sleep 10  # Wait for sync to complete

# Optional: Check if chrony is available and use it as additional sync
if command -v chronyc &> /dev/null; then
    printf "Chrony available, using chronyc makestep as additional sync\n"
    sudo chronyc makestep
else
    printf "Chrony not available, relying on timedatectl NTP\n"
fi

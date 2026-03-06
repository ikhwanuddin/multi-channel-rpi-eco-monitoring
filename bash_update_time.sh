#!/bin/bash

# Update time from internet using chrony (modern alternative to ntpdate)
# Ensure chrony is installed: sudo apt install chrony
sudo chronyc makestep

if (($? != 0)); then
  printf "chronyc makestep failed, trying systemd-timesyncd\n"
  sudo systemctl restart systemd-timesyncd
  sleep 10  # Wait for sync
fi

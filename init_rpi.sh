#!/bin/sh

# Exit script on error.
set -e

# Update apt as normal.
sudo apt update
sudo apt -y update

# Gotta have vim.
sudo apt install vim -y

# Enable serial port and enable interactive login.
sudo raspi-config nonint do_serial 0

echo "You should reboot now..."
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

# Install Python/Pip and installed required modules.
sudo apt install python3 python3-pip -y
pip install -r requirements.txt

echo "You should reboot now..."

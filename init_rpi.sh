#!/bin/sh

# Exit script on error.
set -e

if [ ! -f ./gardenmon.py ] ; then
	echo "ERROR: Must run in gardenmon directory" 1>&2
	exit 1
fi

# Update apt as normal.
sudo apt update
sudo apt -y update

# Gotta have vim.
sudo apt install vim -y

# Setup git.
git config --global core.editor "vim"
git config --global credential.helper store

# Enable serial port and enable interactive login.
sudo raspi-config nonint do_serial 0

# Install smbus library for I2C in Python.
sudo apt install python3-smbus -y

# Install Python/Pip and installed required modules.
sudo apt install python3 python3-pip -y
pip install -r requirements.txt

# Enable I2C.
sudo raspi-config nonint do_i2c 0

# Create gardenmon service and enable to start after reboot.
sudo sh -c "sed -e 's?\${GARDENMON_PATH}?`pwd`?' gardenmon.service.template > /etc/systemd/system/gardenmon.service"
sudo systemctl enable gardenmon

echo "You should reboot now..."

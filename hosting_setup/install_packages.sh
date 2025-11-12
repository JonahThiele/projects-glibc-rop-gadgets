#!/bin/bash

#this should be manually run each time a package needs to be added or a new vm is used
#this needs to be run with sudo

set -e #exit on error

apt update
apt install python3 -y
apt install zstd -y
apt install  rpm2cpio -y
apt install cron -y

#create and activate new virtual environment for python
python3 -m venv ./venv
source ./venv/bin/activate

#install python packages
pip install --upgrade pip
pip install -r requirements.txt

#enable and start cron
systemctl enable cron
systemctl start cron
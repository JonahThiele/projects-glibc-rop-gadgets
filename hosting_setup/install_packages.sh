#!/bin/bash

#this should be manually run each time a package needs to be added or a new vm is used
#this needs to be run with sudo

set -e #exit on error

apt update
apt install python3 -y
apt install zstd -y
apt install  rpm2cpio -y
apt install cron -y
apt install git -y
apt install python-venv

#create and activate new virtual environment for python
python3 -m venv ./venv
source ./venv/bin/activate

#install python packages
pip install --upgrade pip
pip install -r requirements.txt

#enable and start cron
systemctl enable cron
systemctl start cron

#clone the repo we might have to move this to another repo so I can authenicate and add it to another repo

git clone https://github.com/dsu-cs/projects-glibc-rop-gadgets.git

#setup the origin
if git remote | grep -q origin; then
    git remote set-url origin https://github.com/dsu-cs/projects-glibc-rop-gadgets.git
else
    git remote add origin https://github.com/dsu-cs/projects-glibc-rop-gadgets.git
fi

#somewhere along here we need to figure out authenication

#pull the latest main branch
git pull origin main

#add the script to the cron job
crontab crontab.txt
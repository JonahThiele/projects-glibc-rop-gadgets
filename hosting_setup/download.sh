#!/bin/bash

# Use explicit paths to setup everything
export HOME=/home/downloader
export PATH=/usr/local/bin:/usr/bin:/bin

# Move to project directory instead of cron's default /
cd /home/downloader/projects-glibc-rop-gadgets/webscraping || exit

# sh does have source so use .
. /home/downloader/venv/bin/activate

#pull main
/usr/bin/git pull origin main

#run all web scraping scripts
for f in *.py; do
    /home/downloader/venv/bin/python "$f"
done

# add all changes and push to repo
/usr/bin/git add --all
/usr/bin/git commit -m "download from repos" || true
/usr/bin/git push origin main

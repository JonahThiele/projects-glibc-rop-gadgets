#!/bin/bash

source /home/user/venv/bin/activate
P=$(pwd)

cd ../webscraping

git pull origin

#run every python file in here
#this might not be secure but I don't know yet
for f in *.py; 
do 
    python "$f"; 
done

# commit and push back to origin also probably really dangerous
git add .
git commit -m "download from repos"
git push origin

#return back
cd $P

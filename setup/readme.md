# overview of steps to setup development environment

1. install wsl or use a linux based machine (sorry windows and mac)
2. install vscode and the ssh extension if you are using wsl on windows
3. connect via ssh to your wsl instance (if on wsl)
4. install python3 onto wsl or your linux environment
5. go to source control and clone the project to your workspace
6. add the url of the project as remote origin to source control
7. run the install_dev.sh file in your project workspace (need to use bash for this, haven't tried with other shells)
8. you are now ready to develop

## when running the python code locally

1. make sure that you have activated venv
    -  source ./venv/bin/activate
2. run the scripts

## when tweaking the digital ocean function
1. check out this guide to get locally setup:
https://docs.digitalocean.com/products/functions/getting-started/quickstart/


## steps to create a pr and get code to the repo

1. make sure that you are currently on main
2. pull main
3. create a local branch from main
    - make sure the naming scheme includes the title of the ticket from jira
4. switch to the newly created branch
5. make your changes and then commit
6. when you are ready switch to main
7. pull main again
8. switch back to the branch you created
9. merge main into this branch and then push the branch
    - you may have merge conflicts so address those and then commit and re-push
## Deployment

## Setup Remote access
We use Raspberry Connect to remote control the bridge. Follow instructions at https://www.raspberrypi.com/documentation/services/connect.html

## Get the code 

generate an ssh key: https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

run `git clone git@github.com:Schwank-Lab/evoflow-reactor.git`


## Install bridge code. 
1. install pyenv
2. run `sudo apt install build-essential libbz2-dev libncurses5-dev libncursesw5-dev libffi-dev libreadline-dev libssl-dev zlib1g-dev libsqlite3-dev tk-dev liblzma-dev libgdbm-dev libgdbm-compat-dev uuid-dev libnss3-dev libdb-dev libedit-dev libc6-dev`
3. run `pyenv install 3.12 & pyenv global 3.12`
4. run `pip install poetry`
5. run `poetry install`
6. run `sudo cp evo-bridge.service /etc/systemd/system/evo-bridge.service`
7. run `sudo systemctl enable evo-bridge.service`
8. run `sudo systemctl start evo-bridge.service`

To check status of the service run `sudo systemctl status evo-bridge.service`

To check service logs run `sudo journalctl -u evo-bridge.service`


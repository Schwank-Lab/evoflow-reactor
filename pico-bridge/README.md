## Deployment

1. install pyenv and python3.12
2. set python3.12 as system python
3. run `pip install poetry`
4. run `poetry install`
5. run `sudo cp evo-bridge.service /etc/systemd/system/evo-bridge.service`
6. run `sudo systemctl enable evo-bridge.service`
7. run `sudo systemctl start evo-bridge.service`

To check status of the service run `sudo systemctl status evo-bridge.service`

To check service logs run `sudo systemctl status evo-bridge.service`


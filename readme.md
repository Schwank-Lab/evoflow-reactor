## Reactor onboarding

Below are the steps required to setup an evoflow reactor. 

### Requirements
You need the evoflow reactor, a laptop/PC (host) and a usb cable connecting the two. 

 1. Install micropython on RPI Pico following instructions at [https://micropython.org/download/RPI_PICO/](https://micropython.org/download/RPI_PICO/)
 2. Host needs python 3.12 and poetry
   2.1 Install python, following instructions at https://github.com/pyenv/pyenv
   2.2 Install pipx following instructions at https://pipx.pypa.io/stable/installation/ 
   2.3 Install poetry using `pipx install poetry`
 3. Download the code (either using `git clone` or by downloading the archive from github)
 4. Navigate to the code folder and run `poetry install`
      
### Reactor setup

 1. Run `poetry run python setup-tool/find_pico.py`. Copy the port to use for later commands. 
 2. Run `poetry run python setup-tool/main.py --reactor_id XX --pico_port YY ZZ`.
      XX - reactor id, when in doubt remove the `--reactor_id XX` part of the command and a new reactor will  be registered in the database
      YY - pico port that you obtained in the previous command.
      ZZ - reactor name, should be written on the reactor itself, e.g. Alpha
 4. Run `poetry run sh tmp/commands.sh`. Make sure there's no errors 

### Reactor diagnostics 
In all the commands below, replace X with the pico port you obtained before. 

1. Run `poetry run ampy -p XX run diagnostics/diagnostics_pumps.py`. This will activate pumps from left to right, rotation should be clock-wise
2. Run `poetry run ampy -p XX run diagnostics/diagnostics_stirrers.py`. Before running, but the glass tubes with stirring bars into the reactor. Stirring bards should turn.
3. Run `poetry run ampy -p XX run diagnostics/diagnostics_heaters.py`. This will turn on the heaters and will write temperature to the console. You should observe the temperature slowly increasing.
4. Run `poetry run ampy -p XX run diagnostics/diagnostics_od.py`. Follow instructions on the screen, you'll need to put different probes to measeure OD. You should observe OD of the turbid probe being higher.
5. Run `poetry run ampy -p XX run diagnostics/diagnostics_stepper.py`. You should observe stepper shaft rotating. 


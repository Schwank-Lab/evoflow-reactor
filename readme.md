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

 1. Run `poetry shell`
 2. Run `python setup-tool/find_pico.py`
 3. Run `export PICO_PORT=$(<tmp/pico_port.txt)` 
 4. Run `poetry run python setup-tool/main.py --reactor_id XX --pico_port $PICO_PORT REACTOR_NAME`.
      XX - reactor id, when in doubt remove the `--reactor_id XX` part of the command and a new reactor will  be registered in the database
      REACTOR_NAME - reactor name, should be written on the reactor itself, e.g. Alpha
 5. Run `sh /tmp/commands.sh`. Make sure there's no errors 

### Reactor diagnostics 

1. Run `ampy -p $PICO_PORT run diagnostics/diagnostics_pumps.py`. This will activate pumps from left to right, rotation should be clock-wise
2. Run `ampy -p $PICO_PORT run diagnostics/diagnostics_stirrers.py`. Before running, but the glass tubes with stirring bars into the reactor. Stirring bards should turn.
3. Run `ampy -p $PICO_PORT run diagnostics/diagnostics_heaters.py`. This will turn on the heaters and will write temperature to the console. You should observe the temperature slowly increasing.
4. Run `ampy -p $PICO_PORT run diagnostics/diagnostics_od.py`. Follow instructions on the screen, you'll need to put different probes to measeure OD. You should observe OD of the turbid probe being higher.
5. Run `ampy -p $PICO_PORT run diagnostics/diagnostics_stepper.py`. You should observe stepper shaft rotating.

### Reactor calibration 

1. Run `export EXP_NAME=your_experiment_name`, e.g. `export EXP_NAME=20240405_bravo`
2. Run `mkdir -p experiments/$EXP_NAME`  
3. Run `ampy -p $PICO_PORT get configs/reactor_config.json experiments/$EXP_NAME/old_reactor_config.json`.

Open a new terminal window and run the following commands: 
1. Start a jupyter server by running `poetry run jupyter lab`. This should launch the browser with a jupyter instance.
2. Navigate to calibration/calibration.ipynb

Now, go back to the previous terminal tab and continue executing commands there. 

#### Temperature Calibration

To calibrate the temperature, we need to heat both lagoon and tubribostat to a pre-defined temperature and then measure the actual temperature. 
Recommended set of temperature to use are: 27, 30, 35, 39

1. Run `python calibration/calibration_temp.py YOUR_TEMP`
2. Run `ampy -p $PICO_PORT run temp/calibrate_temp.py`
3. Monitor the output, after you see that `T(inc)` and `T(lagoon)` have reached the defined temperature, measure the actual temperature in the glass tubes and note it in the jupyter notebook.

#### OD Calibration 

To calibrate OD, we need to measure ODs of the probes with the known OD value. We have such probes, use some of them. Recommended is OD0.1, OD0.4, OD0.6, OD0.8, OD1.0

1. Run `ampy -p $PICO_PORT run calibration/calibration_od.py` and follow instructions.
2. Run `ampy -p $PICO_PORT get tmp/od_calibration.csv experiments/$EXP_NAME/od.csv`

#### Pump Calibration 

The only pump we care about is the turbidostat -> lagoon pump. To calibrate it, we're going to pump a known volume.

1. Attach tubing to the turbidostat -> lagoon pump (3rd pump). Add ~100ml of liquid into a bottle, dip the input tube into that bottle.
2. Prime the tube by manually activating the pump, until the wholte tubing is filled water.
3. Put the outlet into an empty bottle, measure the weight of the empty bottle beforehand.
4. Run `ampy -p $PICO_PORT run calibration/calibration_pumps.py`
5. Measure the volume after pumping is finished, write results to the jupyter notebook.

#### Stirrer Calibration 

1. Put the probe with removed lid into the incubator stirrer.
2. Run `python calibration/calibration_inc_stirrer.py 0.25`, where 0.25 is the fraction of the top motor speed used for steering. 
3. Run `ampy -p $PICO_PORT run tmp/calibrate_inc_stirrer.py`
4. Observe the vortex in the probe.

#### Stepper calibration 

We need to calibrate the direction of the stepper motor. 

1. Run `python calibration/calibration_stepper.py 1`
2. Run `ampy -p $PICO_PORT run tmp/calibrate_stepper.py`
3. Observe the rotation of the stepper shaft, it should be turning counter-clockwise, when looked from the direction of the motor.  If that's not the case, execute two more commands: 
4. Run `python calibration/calibration_stepper.py -1`
5. Run `ampy -p $PICO_PORT run tmp/calibrate_stepper.py`
6. Now the shaft should be turning in the correct direction.



#### Run calibration 

1. In the jupyter notebook, click on `Run All`
2. Run `ampy -p $PICO_PORT put experiments/$EXP_NAME/new_reactor_config.json configs/reactor_config.json`


## Development

Manually insert a new experiment to the database: 

```
INSERT INTO experiment (name, reactor_id, status, timestamp) 
VALUES ('2024.07.30_idec_TadA', 12, 'stop', EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::INTEGER);
```


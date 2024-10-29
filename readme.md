## Reactor onboarding

Below are the steps required to setup an evoflow reactor. 

### Requirements
You need the evoflow reactor, a laptop/PC (host) and a usb cable connecting the two. 

 1. Install micropython on RPI Pico following instructions at [https://micropython.org/download/RPI_PICO/](https://micropython.org/download/RPI_PICO/)
 2. Host needs python 3.12 and poetry
   2.1 Install python, following instructions at https://github.com/pyenv/pyenv
   2.2 Install pipx following instructions at https://pipx.pypa.io/stable/installation/ 
   2.3 Install poetry using `pipx install poetry`
 3. Run `git clone git@github.com:Schwank-Lab/evoflow-reactor.git` (you might have to register your laptop with github, follow instructions [here](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) 
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

1. Run `python evotool.py diagnose pumps`. This will activate pumps from left to right, rotation should be clock-wise
2. Run `python evotool.py diagnose stirrers`. Before running, but the glass tubes with stirring bars into the reactor. Stirring bards should turn.
3. Run `python evotool.py diagnose temp`. This will turn on the heaters and will write temperature to the console. You should observe the temperature slowly increasing.
4. Run `python evotool.py diagnose od_left`. Follow instructions on the screen, you'll need to put different probes to measeure OD. You should observe OD of the turbid probe being higher.
5. Run `python evotool.py diagnose od_right`. Follow instructions on the screen, you'll need to put different probes to measeure OD. You should observe OD of the turbid probe being higher.
6. Run `python evotool.py diagnose stepper angle 180`. You should observe stepper shaft rotating 180 degrees.

### Reactor calibration 

Run `python evotool.py calibrate new <your_experiment_name>` (e.g. `python evotool calibrate new calibration_logs/20240405_bravo`) to start a new calibration session.

Follow the instructions below to calibrate individual hardware parts. Note that you can choose to skip the calibration of a certain part, e.g. stirrers. In that case, the reactor config that is currently stored on the evoflow reactor will be used. If you would like to use values from the default config instead, run `python evotool calibrate new <your_experiment_name> --default_config`. 

#### Stirrer Calibration 

1. Put a probe with removed lid into the left incubator.
2. Run `python evotool.py calibrate inc_left_stirrer <speed>`, e.g. `python evotool.py calibrate inc_left_stirrer 0.25`
3. Observe the vortex in the probe. Vortex should be present but not too deep, to not obstruct the OD sensor. 
4. Calibrate the right incubator: `python evotool.py calibrate inc_right_stirrer <speed>`
5. Calibrate the lagoon: `python evotool.py calibrate lagoon_stirrer <speed>`


#### OD Calibration 

To calibrate OD, we need to measure ODs of the probes with the known OD value. We have such probes, use some of them. Recommended is 

1. Run `python evotool.py calibrate inc_left_od <od1> <od2> <od3>` and follow instructions.
2. Run `python evotool.py calibrate inc_right_od <od1> <od2> <od3>` and follow instructions.

Recommended ODs to use are `python evotool.py calibrate inc_left_od 0.1 0.4 0.6 0.8 1.0`


#### Bacterial Stepper Calibration 

Bacterial stepper motors pump bacteria from incubators into the lagoon at a specified flow rate. We only calibrate the front left stepper pump and assume that the front right stepper pump works the same way.

1. Attach tubing to the inc_left -> lagoon pump (front left stepper pump). Add ~100ml of liquid into a bottle, dip the input tube into that bottle.
2. Prime the pump by running `python evotool.py calibrate bact_stepper`. Once you see liquid coming out from the other end of the tube, interrupt the screen using `Ctrl+C`. 
3. Put the outlet into an empty bottle, measure the weight of the empty bottle beforehand.
4. Run `python evotool.py calibrate bact_stepper`. This will run 10,000 steps, you can change the default by supplying `--num_steps <value>` flag. 
5. Measure the volume after pumping is finished.

Note: you can specify custom PWM value by using `--pwm <value>` flag, e.g. `python evotool.py calibrate bact_stepper 50 --pwm 1000`

#### Induction Stepper calibration 

We need to calibrate the direction of the induction stepper motor. 

1. Run `python evotool.py calibrate induction_stepper 1`
2. Observe the rotation of the stepper shaft, it should be turning **clockwise**, when looked from the direction of the motor.
 
If that's not the case, execute two more commands: 
3. Run `python evotool.py calibrate induction_stepper -1`
4. Now the shaft should be turning in the correct direction.

#### Temperature Calibration

To calibrate the temperature, we need to heat both lagoon and tubribostats to a pre-defined temperature and then measure the actual temperature. 
Recommended set of temperature to use are: 27, 30, 35, 39

1. Run `python evotool.py calibrate temp <YOUR_TEMP>`, e.g. `python evotool.py calibrate temp 25`
2. Run `ampy -p $PICO_PORT run temp/calibrate_temp.py`
3. Monitor the output, after you see that `T(inc_left)`, `T(lagoon)` and `T(inc_right)` have all reached the defined temperature, measure the actual temperature in the glass tubes as well as the values `T_raw(inc_left)`, `T_raw(lagoon)` and `T_raw(inc_right)`
4. Repeat for every target temperature.s


#### Calculate new config based on the calibrated values. 

Run `python evotool.py calibrate compute_config`.

If you calibrated bacterial stepper motor, provide the pumped volume that you measured by specifying `--bact_stepper_volume <volume_ml>`
If you calibrated temperature, provide `--inc_left_measured_temps <t1> <t2> <t3>` for the temperatures you read from `T_raw(inc_left)` and `--inc_left_target_temps <t1> <t2> <t3>` for the temperatures you measured using an external therometer. Do the same for `--inc_right_measured_temps`, `--inc_right_target_temps`, `--lagoon_measured_temps`, and `--lagoon_target_temps`.


## Development

Manually insert a new experiment to the database: 

```
INSERT INTO experiment (name, reactor_id, status, timestamp) 
VALUES ('2024.07.30_idec_TadA', 12, 'stop', EXTRACT(EPOCH FROM CURRENT_TIMESTAMP)::INTEGER);
```

Manually update an experiment in the database: 

```
UPDATE experiment set status = 'stop'
WHERE experiment_id = 28;
```


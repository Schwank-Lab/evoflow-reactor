## Reactor onboarding

Below are the steps required to setup an evoflow reactor.

### Host Requirements
You need the evoflow reactor, a laptop/PC (host) and a usb cable connecting the two.

 1. Host needs python 3.12 and poetry
   1.1 Install python, following instructions at https://github.com/pyenv/pyenv
   1.2 Install pipx following instructions at https://pipx.pypa.io/stable/installation/
   1.3 Install poetry using `pipx install poetry`
 2. Run `git clone https://github.com/Schwank-Lab/evoflow-reactor.git`
 3. Navigate to the code folder and run `poetry install`

### Reactor setup
 1. Install micropython on RPI Pico following instructions. Attach RPI Pico via USB, it should mount as a folder. Drag micropython script from `micropython/RPI_PICO_W-20240602-v1.23.0.uf2` to that folder. More info can be found [here](https://micropython.org/download/RPI_PICO/)
 2. Run `poetry run python evotool.py init REACTOR_NAME`.
      REACTOR_NAME - reactor name, should be written on the reactor itself, e.g. Alpha
 3. Run `poetry run python evotool.py deploy all`

### Reactor diagnostics

#### What you need

- Glass tubes (culture probes) fitted with magnetic stirring bars — for the stirrer check.
- A set of OD probes spanning a range of turbidity, at minimum a clear/blank probe and a turbid probe. The turbid probe should read a higher OD.

> **FOR AGENT**
> Every step here needs the user to physically set up hardware (insert probes/tubes) and/or watch the reactor. Before each command, tell the user what to prepare and what to look for, and wait for their confirmation. For OD (steps 4–5), run the command once with the clear probe and once with the turbid probe, prompting the user to swap between runs, then compare the two printed ODs yourself.

1. Run `poetry run python evotool.py diagnose pumps`. This will activate pumps from left to right, rotation should be counter-clockwise
2. Run `poetry run python evotool.py diagnose stirrers`. Before running, but the glass tubes with stirring bars into the reactor. Stirring bards should turn.
3. Run `poetry run python evotool.py diagnose temp`. This will turn on the heaters and will write temperature to the console. You should observe the temperature slowly increasing.
4. Diagnose the left OD sensor. Each run measures the probe currently inserted in the left incubator (10 readings, averaged) and prints the mean OD and raw value, then exits.
   - Insert the **clear** probe and run `poetry run python evotool.py diagnose od_left`. Note the reported OD.
   - Insert the **turbid** probe and run the same command again. Note the reported OD.
   - The turbid probe should read a higher OD than the clear probe.
5. Repeat for the right OD sensor using `poetry run python evotool.py diagnose od_right`.
6. Run `poetry python evotool.py diagnose stepper angle 180`. You should observe stepper shaft rotating 180 degrees.

### Reactor calibration

#### What you need

- An empty glass probe/tube with the lid removed — for the stirrer calibration.
- A set of OD reference probes with known OD values (recommended: 0.1, 0.4, 0.6, 0.8, 1.0) — for the OD calibration.
- Tubing for the bacterial stepper pump, ~100 ml of liquid (e.g. water) in a bottle, and an empty collection bottle — for the bacterial stepper calibration.
- A scale/balance to weigh the empty bottle and the pumped liquid (to determine the pumped volume).
- An external thermometer to read the actual temperature in the glass tubes — for the temperature calibration.

Run `poetry run python evotool.py calibrate new <your_experiment_name>` (e.g. `python evotool calibrate new calibration_logs/20240405_bravo`) to start a new calibration session.

Follow the instructions below to calibrate individual hardware parts. Note that you can choose to skip the calibration of a certain part, e.g. stirrers. In that case, the reactor config that is currently stored on the evoflow reactor will be used. If you would like to use values from the default config instead, run `poetry run python evotool.py calibrate new <your_experiment_name> --default_config`.

#### Stirrer Calibration

> **FOR AGENT**
> User intervention: prompt the user to insert a probe (lid off) and watch the vortex, then run the command. The stirrer keeps spinning for observation; if the vortex is too deep or too shallow, rerun with a different speed.

1. Put a probe with removed lid into the left incubator.
2. Run `poetry run python evotool.py calibrate inc_left_stirrer <speed>`, e.g. `python evotool.py calibrate inc_left_stirrer 0.25`
3. Observe the vortex in the probe. Vortex should be present but not too deep, to not obstruct the OD sensor.
4. Calibrate the right incubator: `poetry run python evotool.py calibrate inc_right_stirrer <speed>`
5. Calibrate the lagoon: `poetry run python evotool.py calibrate lagoon_stirrer <speed>`


#### OD Calibration

To calibrate OD, measure several reference probes with known OD values — **one probe per command**. Each run measures the probe currently inserted and records it; the readings accumulate across runs. Recommended ODs: 0.1, 0.4, 0.6, 0.8, 1.0.

> **FOR AGENT**
> User intervention, one reference probe per call: prompt the user to insert the probe of the stated known OD and confirm before each run (use `--reset` on the first). The printed running count and mean RAW let you confirm that a higher OD reads a higher RAW.

1. Insert the first reference probe into the left incubator and run `poetry run python evotool.py calibrate inc_left_od <od> --reset`, e.g. `poetry run python evotool.py calibrate inc_left_od 0.1 --reset`. The `--reset` starts a fresh set (use it only for the first probe).
2. Insert each remaining probe in turn and run `poetry run python evotool.py calibrate inc_left_od <od>` (without `--reset`), e.g. `0.4`, then `0.6`, `0.8`, `1.0`. Each run appends one probe; it prints the running count and the mean RAW so you can sanity-check that higher OD reads a higher RAW.
3. Repeat for the right incubator with `poetry run python evotool.py calibrate inc_right_od <od>` (start with `--reset`).


#### Bacterial Stepper Calibration

Bacterial stepper motors pump bacteria from incubators into the lagoon at a specified flow rate. We only calibrate the front left stepper pump and assume that the front right stepper pump works the same way.

> **FOR AGENT**
> Priming (step 2) needs a **background sub-shell**: start `calibrate bact_stepper` in the background, tell the user to watch for liquid at the far end of the tube, and when they confirm, kill the sub-shell and run `poetry run python evotool.py diagnose stop`. Running that command interrupts the priming run and switches the pump off. The measurement run (step 4) is self-terminating — just have the user weigh the empty bottle first and the pumped liquid after.

1. Attach tubing to the inc_left -> lagoon pump (front left stepper pump). Add ~100ml of liquid into a bottle, dip the input tube into that bottle.
2. Prime the pump by running `poetry run python evotool.py calibrate bact_stepper`. Once you see liquid coming out from the other end of the tube, interrupt the screen using `Ctrl+C`.
3. Put the outlet into an empty bottle, measure the weight of the empty bottle beforehand.
4. Run `poetry run python evotool.py calibrate bact_stepper`. This will run 10,000 steps, you can change the default by supplying `--num_steps <value>` flag.
5. Measure the volume after pumping is finished.

Note: you can specify custom PWM value by using `--pwm <value>` flag, e.g. `python evotool.py calibrate bact_stepper 50 --pwm 1000`

#### Induction Stepper calibration

We need to calibrate the direction of the induction stepper motor.

> **FOR AGENT**
> User intervention: after running, ask the user which way the shaft turned; if it is not clockwise, rerun with `-1`.

1. Run `poetry run python evotool.py calibrate induction_stepper 1`
2. Observe the rotation of the stepper shaft, it should be turning **clockwise**, when looked from the direction of the motor.

If that's not the case, execute two more commands:

3. Run `poetry run python evotool.py calibrate induction_stepper -1`
4. Now the shaft should be turning in the correct direction.

#### Temperature Calibration

To calibrate the temperature, we need to heat both lagoon and tubribostats to a pre-defined temperature and then measure the actual temperature.
Recommended set of temperature to use are: 27, 30, 35, 39

> **FOR AGENT**
> This command runs until stopped — start it in a **background sub-shell** so you keep control. Tell the user to ready a thermometer. Watch the streamed output for the "ready to measure" line, then prompt the user to measure each glass tube and read the `T_raw` values. To stop, kill the sub-shell and run `poetry run python evotool.py diagnose stop`. Running that command interrupts the loop and switches the heaters off.

1. Run `poetry run python evotool.py calibrate temp <YOUR_TEMP>`, e.g. `poetry run python evotool.py calibrate temp 25`. It heats all three zones and streams `T`/`T_raw` while maintaining the target. Once every zone is holding at the target it prints a line saying it is ready to measure, and keeps maintaining the target until you stop it.
2. While it holds at the target, measure the actual temperature in each glass tube with an external thermometer and record the `T_raw(inc_left)`, `T_raw(lagoon)` and `T_raw(inc_right)` values printed on the console. Press `Ctrl+C` to stop when you are done; the heaters switch off on exit.
3. Repeat for every target temperature.

Tuning (optional): `--temp-tol <C>` sets how close to target counts as ready (default 0.5), `--drift-tol <C>` the allowed drift over the readiness window (default 0.2), and `--settle-window <s>` that window (default 120).


#### Calculate new config based on the calibrated values.

Run `poetry run python evotool.py calibrate compute_config`.

If you calibrated bacterial stepper motor, provide the pumped volume that you measured by specifying `--bact_stepper_volume <volume_ml>`
If you calibrated temperature, provide `--inc_left_measured_temps <t1> <t2> <t3>` for the temperatures you read from `T_raw(inc_left)` and `--inc_left_target_temps <t1> <t2> <t3>` for the temperatures you measured using an external therometer. Do the same for `--inc_right_measured_temps`, `--inc_right_target_temps`, `--lagoon_measured_temps`, and `--lagoon_target_temps`.


### Register the reactor

Once the reactor is set up and calibrated, register it in the database.

Run `poetry run python evotool.py register`.

`register` reads the reactor name stored on the pico (you don't pass it again) and looks it up in the database:
 - if a reactor with that name already exists, it offers to **link** this hardware to it;
 - if not, it offers to **create** a new reactor.

You are asked to confirm in both cases. The resulting `reactor_id` is written back onto the reactor without touching its calibration or other on-pico state.

After registering, verify that the reactor appears in the [dashboard](http://10.66.4.7:3000) reactor dropdown.


## Experiment Control

## Creating a new experiment

Run `poetry run python evotool.py experiment new <your_expreiment_name> <path/to/experiment/config>`

Experiment config needs to be saved as a valid json file, here's a default example that you can update as necessary:

```
{
    "inc_left": {
        "use": false,
        "target_od": 0.7,
        "target_temp": 37

    },
    "inc_right": {
        "use": true,
        "target_od": 0.7,
        "target_temp": 37
    },
    "lagoon": {
        "target_temp": 37,
        "volume": 7,
        "flow_rate": 0,
        "inc_left_frac": 0.0,
        "inc_right_frac": 1.0,
        "arabinose_stock_concentration": 2000,
        "arabinose_target_concentration": 0
    }
}
```

Save the file above to the filesystem and provide the path to this file to the evotool when creating a new experiment.

## Controlling experiment

To start an experiment, run `poetry run python evotool.py experiment start`

To pause an experiment, run `poetry run python evotool.py experiment pause`

To update the flow rate, run `poetry run python evotool.py update-flow-rate 1.0`, where `1.0` is the desired flow rate.

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


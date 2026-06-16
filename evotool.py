import argparse
import subprocess
from pathlib import Path
import json
import glob
from sys import exit
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime
import serial.tools.list_ports
import shutil
from evoflow_db.idec import Reactor, Experiment, ExperimentConfig
from evoflow_db import idec_engine
from sqlalchemy.orm import Session
from sqlalchemy import select, update, insert
import time



from diagnostics import diagnostics_od

DIR_DIAGNOSTICS = Path('diagnostics')
DIR_TMP = Path('tmp')
DIR_TMP.mkdir(exist_ok=True)
CFG_EVOTOOL = Path('.evotool.json')

# Sentinel reactor_id for a reactor that has been set up but not yet registered in the database.
REACTOR_ID_UNREGISTERED = -1

CALIBRATION_INC_LEFT_OD_MEASURED = 'inc_left_od_measured.csv'
CALIBRATION_INC_LEFT_OD_EXPECTED = 'inc_left_od_expected.txt'
CALIBRATION_INC_RIGHT_OD_MEASURED = 'inc_right_od_measured.csv'
CALIBRATION_INC_RIGHT_OD_EXPECTED = 'inc_right_od_expected.txt'

CALIBRATION_INDUCTION_STEPPER_DIRECTION = 'induction_stepper_rotation_direction.txt'
CALIBRATION_BACT_STEPPER_NUM_STEPS = 'bact_stepper_num_steps.txt'
CALIBRATION_INC_LEFT_STIRRER_SPEED = 'inc_left_stirrer_speed_frac.txt'
CALIBRATION_INC_RIGHT_STIRRER_SPEED = 'inc_right_stirrer_speed_frac.txt'
CALIBRATION_LAGOON_STIRRER_SPEED = 'lagoon_stirrer_speed_frac.txt'

def find_pico_port():
    """ Automatically detects usb port to which pico is attached."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Pico" in port.description or "Board" in port.description:
            return port.device
    return None

def find_pico_mount():
    """ Automatically finds location in the file system where pico is mounted.

    Returns:
        String path to the mounted folder.
    Throws:
        ValueError: If pico is not found.
    """
    mount_folder = Path('/Volumes')
    hits = []
    if not mount_folder.exists():
        raise ValueError(f'Could not find {mount_folder}.')
    for folder in mount_folder.iterdir():
        if 'RPI-RP2' in folder.name:
            hits.append(folder)
    if len(hits) == 0:
        raise ValueError('Could not find Pico mount.')
    if len(hits) > 1:
        raise ValueError('Found multiple Pico mounts: ', ' '.join(hits))
    return hits[0]


##############################
#  Calibration commands
##############################



def run_inc_left_stirrer_calibration(speed_frac, port):
    script_content = f"""from calibration import stop_all, calibrate_inc_left_stirrer

stop_all()
calibrate_inc_left_stirrer(top_speed_frac={speed_frac})
"""
    script = DIR_TMP / 'calibrate_inc_left_stirrer.py'
    with open(script, 'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

def run_inc_right_stirrer_calibration(speed_frac, port):
    script_content = f"""from calibration import stop_all, calibrate_inc_right_stirrer

stop_all()
calibrate_inc_right_stirrer(top_speed_frac={speed_frac})
"""
    script = DIR_TMP / 'calibrate_inc_right_stirrer.py'
    with open(script, 'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

def run_lagoon_stirrer_calibration(speed_frac, port):
    script_content = f"""from calibration import stop_all, calibrate_lagoon_stirrer

stop_all()
calibrate_lagoon_stirrer(top_speed_frac={speed_frac})
"""
    script = DIR_TMP / 'calibrate_lagoon_stirrer.py'
    with open(script, 'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)


def run_inc_left_od_calibration(num_probes, port):
    script_content = f"""from calibration import stop_all, calibrate_inc_left_od

stop_all()
calibrate_inc_left_od(num_probes={num_probes})"""
    script = DIR_TMP / 'calibrate_inc_left_od.py'
    with open(script, 'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

def run_inc_right_od_calibration(num_probes, port):
    script_content = f"""from calibration import stop_all, calibrate_inc_right_od

stop_all()
calibrate_inc_right_od(num_probes={num_probes})"""
    script = DIR_TMP / 'calibrate_inc_right_od.py'
    with open(script, 'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

def run_temp_calibration(target_temp, port):
    script_content = f"""from calibration import stop_all, calibrate_temp

stop_all()
calibrate_temp({target_temp})
"""
    script = DIR_TMP / 'calibrate_temp.py'
    with open(script, 'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

def run_bact_stepper_calibration(num_steps, pwm, port):
    script_content = f"""from calibration import stop_all, calibrate_pump_incubator_to_lagoon

stop_all()
calibrate_pump_incubator_to_lagoon(num_steps={num_steps}, pwm={pwm})
"""
    script = DIR_TMP / 'calibrate_bact_stepper.py'
    with open(script, 'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

def run_induction_stepper_calibration(rotation_direction, port):
    script_content = f"""from calibration import stop_all, calibrate_stepper

stop_all()
calibrate_stepper(rotation_dir={rotation_direction})
"""
    script = DIR_TMP / 'calibrate_induction_stepper.py'
    with open(script, 'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

def linear_fit_1d(df, x, y):
    X = df[[x]]  # Feature matrix
    Y = df[y]  # Target variable
    model = LinearRegression().fit(X, Y)
    y_pred = model.predict(X)
    slope = model.coef_[0]  # Assuming there's only one feature
    intercept = model.intercept_
    return slope, intercept, y_pred

def compute_temp_calibration(measured_temps, target_temps):
    if measured_temps is not None or target_temps is not None:
        if measured_temps is None:
            print('Please provide measured temperatures.')
            exit(1)
        if target_temps is None:
            print('Please provide target temperatures.')
            exit(1)
        if len(target_temps) != len(measured_temps):
            print('Number of target and measured temperatures must be the same.')
            exit(1)
        vals = pd.DataFrame({'target': target_temps, 'measured': measured_temps})
        inc_temp_slope, inc_temp_intercept, pred = linear_fit_1d(vals, 'measured', 'target')
        vals['predicted'] = pred
        print(f'Inferred: T = {inc_temp_slope:.5f} * RAW + {inc_temp_intercept:.2f}')
        print(vals)
        return inc_temp_slope, inc_temp_intercept
    else:
        print('Temperature not provided, re-using values from the old config.')
        return None, None

def compute_od_calibration(path_od_measured: Path, path_od_expected: Path):
    if path_od_measured.exists() and path_od_expected.exists():
        od_measured = pd.read_csv(path_od_measured, header=None).mean(axis=1)
        with open(path_od_expected, 'r') as f:
            od_expected = list(map(float, f.readlines()))
        vals = pd.DataFrame({'measured': od_measured, 'expected': od_expected})
        od_slope, od_intercept, pred = linear_fit_1d(vals, 'measured', 'expected')
        print(f'Inferred: OD = {od_slope:.6f} * RAW + {od_intercept:.2f}')
        vals['predicted'] = pred
        print(vals)
        return od_slope, od_intercept
    else:
        return None, None

def compute_new_config(calibration_folder, args, port):
    """ Computes new reactor config based on all calibrated values."""
    with open(calibration_folder / 'old_reactor_config.json') as f:
        cfg = json.load(f)

    # re-use old calibration values.
    inc_left_temp_slope, inc_left_temp_intercept = cfg['inc_left']['temp']['slope'], cfg['inc_right']['temp']['intercept']
    inc_left_od_slope, inc_left_od_intercept = cfg['inc_left']['od']['slope'], cfg['inc_right']['od']['intercept']
    inc_left_stirrer_top_speed_frac = cfg['inc_left']['stirrer_top_speed_frac']

    inc_right_temp_slope, inc_right_temp_intercept = cfg['inc_right']['temp']['slope'], cfg['inc_right']['temp']['intercept']
    inc_right_od_slope, inc_right_od_intercept = cfg['inc_right']['od']['slope'], cfg['inc_right']['od']['intercept']
    inc_right_stirrer_top_speed_frac = cfg['inc_right']['stirrer_top_speed_frac']

    lagoon_temp_slope, lagoon_temp_intercept = cfg['lagoon_temp']['slope'], cfg['lagoon_temp']['intercept']
    bact_stepper_ml_per_step = cfg['bact_stepper_ml_per_step']
    lagoon_stirrer_top_speed_frac = cfg['lagoon_stirrer_top_speed_frac']
    induction_stepper_direction = cfg['induction_stepper_direction']

    print('\n\n\nLeft Incubator temperature sensor')
    new_slope, new_intercept = compute_temp_calibration(args.inc_left_measured_temps, args.inc_left_target_temps)
    if new_slope is not None:
        inc_left_temp_slope, inc_left_temp_intercept = new_slope, new_intercept

    print('\n\n\nRight Incubator temperature sensor')
    new_slope, new_intercept = compute_temp_calibration(args.inc_right_measured_temps, args.inc_right_target_temps)
    if new_slope is not None:
        inc_right_temp_slope, inc_right_temp_intercept = new_slope, new_intercept

    print('\n\n\nLagoon temperature sensor')
    new_slope, new_intercept = compute_temp_calibration(args.lagoon_measured_temps, args.lagoon_target_temps)
    if new_slope is not None:
        lagoon_temp_slope, lagoon_temp_intercept = new_slope, new_intercept

    print('\n\n\nLeft incubator OD calibration')
    new_slope, new_intercept = compute_od_calibration(calibration_folder / CALIBRATION_INC_LEFT_OD_MEASURED, calibration_folder / CALIBRATION_INC_LEFT_OD_EXPECTED)
    if new_slope is not None:
        inc_left_od_slope, inc_left_od_intercept = new_slope, new_intercept
    else:
        print('OD calibration not provided. Re-using old values.')

    print('\n\n\nRight incubator OD calibration')
    new_slope, new_intercept = compute_od_calibration(calibration_folder / CALIBRATION_INC_RIGHT_OD_MEASURED, calibration_folder / CALIBRATION_INC_RIGHT_OD_EXPECTED)
    if new_slope is not None:
        inc_right_od_slope, inc_right_od_intercept = new_slope, new_intercept
    else:
        print('OD calibration not provided. Re-using old values.')

    print('\n\n\nLeft incubator stirrer calibration')
    inc_left_stirrer_top_speed = calibration_folder / CALIBRATION_INC_LEFT_STIRRER_SPEED
    if inc_left_stirrer_top_speed.exists():
        with open(inc_left_stirrer_top_speed, 'r') as f:
            inc_left_stirrer_top_speed_frac = float(f.read())
        print('Set new incubator stirrer top speed to:', inc_left_stirrer_top_speed_frac)
    else:
        print('Incubator stirrer calibration not provided. Re-using old values.')

    print('\n\n\nRight incubator stirrer calibration')
    inc_right_stirrer_top_speed = calibration_folder / CALIBRATION_INC_RIGHT_STIRRER_SPEED
    if inc_right_stirrer_top_speed.exists():
        with open(inc_right_stirrer_top_speed, 'r') as f:
            inc_right_stirrer_top_speed_frac = float(f.read())
        print('Set new incubator stirrer top speed to:', inc_right_stirrer_top_speed_frac)
    else:
        print('Incubator stirrer calibration not provided. Re-using old values.')

    print('\n\n\nLagoon stirrer calibration')
    lagoon_stirrer_top_speed = calibration_folder / CALIBRATION_LAGOON_STIRRER_SPEED
    if lagoon_stirrer_top_speed.exists():
        with open(lagoon_stirrer_top_speed, 'r') as f:
            lagoon_stirrer_top_speed_frac = float(f.read())
        print('Set new lagoon stirrer top speed to:', lagoon_stirrer_top_speed_frac)
    else:
        print('Lagoon stirrer calibration not provided. Re-using old values.')

    print('\n\n\nBacteria stepper calibration')
    if args.bact_stepper_volume is not None:
        with open(calibration_folder / CALIBRATION_BACT_STEPPER_NUM_STEPS, 'r') as f:
            bact_stepper_num_steps = float(f.read())
        bact_stepper_ml_per_step = args.bact_stepper_volume / bact_stepper_num_steps
        print(f'Inferred bacteria stepper volume per step = {bact_stepper_ml_per_step:.6f}mL')
        pwm_prediction = pd.DataFrame({'vol_per_h': [7, 14, 21]})
        pwm_prediction['required_pwm'] = pwm_prediction['vol_per_h'] / 3600 / bact_stepper_ml_per_step
        pwm_prediction['required_pwm'] = pwm_prediction['required_pwm'].apply(lambda x: int(np.ceil(x))).astype(int)
        print('PWM required for different flow rates:')
        print(pwm_prediction)
        if pwm_prediction.loc[2, 'required_pwm'] > 10000:
            print('Warning: PWM required to achieve 21mL/h is too high. Consider adjusting the tubing.')
        if pwm_prediction.loc[0, 'required_pwm'] < 100:
            print('Warning: PWM required to achieve 7mL/h is too low. Consider adjusting the tubing.')
    else:
        print('Bacteria stepper calibration not provided. Re-using old values. Make sure to set --bact_stepper_volume flag.')

    print('\n\n\nInduction stepper calibration')
    induction_stepper_dir_file = calibration_folder / CALIBRATION_INDUCTION_STEPPER_DIRECTION
    if induction_stepper_dir_file.exists():
        with open(induction_stepper_dir_file, 'r') as f:
            induction_stepper_direction = int(f.read())
        print('Set new induction stepper direction to:', induction_stepper_direction)
    else:
        print('Induction stepper calibration not provided. Re-using old values.')

    new_cfg = cfg.copy()
    new_cfg['inc_left']['temp']['slope'] = inc_left_temp_slope
    new_cfg['inc_left']['temp']['intercept'] = inc_left_temp_intercept
    new_cfg['inc_left']['od']['slope'] = inc_left_od_slope
    new_cfg['inc_left']['od']['intercept'] = inc_left_od_intercept
    new_cfg['inc_left']['stirrer_top_speed_frac'] = inc_left_stirrer_top_speed_frac
    new_cfg['inc_right']['temp']['slope'] = inc_right_temp_slope
    new_cfg['inc_right']['temp']['intercept'] = inc_right_temp_intercept
    new_cfg['inc_right']['od']['slope'] = inc_right_od_slope
    new_cfg['inc_right']['od']['intercept'] = inc_right_od_intercept
    new_cfg['inc_right']['stirrer_top_speed_frac'] = inc_right_stirrer_top_speed_frac
    new_cfg['lagoon_temp']['slope'] = lagoon_temp_slope
    new_cfg['lagoon_temp']['intercept'] = lagoon_temp_intercept
    new_cfg['bact_stepper_ml_per_step'] = bact_stepper_ml_per_step
    new_cfg['lagoon_stirrer_top_speed_frac'] = lagoon_stirrer_top_speed_frac
    new_cfg['induction_stepper_direction'] = induction_stepper_direction

    print('\n\n\nComputed new reactor config:')
    print(json.dumps(new_cfg, indent=2))

    with open(calibration_folder / 'new_reactor_config.json', 'w') as f:
        json.dump(new_cfg, f)

    put_ampy(calibration_folder / 'new_reactor_config.json', 'configs/reactor_config.json', port)



##############################
# Diagnostics commands
##############################


def run_free_space_diagnostic(port):
    script_content = """
import gc
import os

def bytes_to_kb(n_bytes):
    return n_bytes >> 10

stats = os.statvfs('/')
total_space = stats[0] * stats[2]
free_space = stats[0] * stats[3]
used_space = total_space - free_space
print('Free space: ', bytes_to_kb(free_space))
print('Used space: ', bytes_to_kb(used_space))
"""
    script = DIR_TMP / 'diagnostics_space.py'
    with open(script,  'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

def run_inc_left_od_diagnostic(port):
    diagnostics_od.generate_script('inc_left', temp_dir=DIR_TMP, script_name='diagnostics_left_od.py')
    run_script(DIR_TMP / 'diagnostics_left_od.py', port)

def run_inc_right_od_diagnostic(port):
    diagnostics_od.generate_script('inc_right', temp_dir=DIR_TMP, script_name='diagnostics_right_od.py')
    run_script(DIR_TMP / 'diagnostics_right_od.py', port)

def run_stepper_diagnostic(movement_type, movement_amount, port):
    stepper_fucntion_map = {
        'angle': 'test_stepper_rotation',
        'displacement': 'test_stepper_displacement',
        'vol': 'test_stepper_vol'
    }
    script_content = f"""from diagnostics import stop_all, test_stepper_rotation, test_stepper_displacement, test_stepper_vol

stop_all()
{stepper_fucntion_map[movement_type]}({movement_amount})
"""
    script = DIR_TMP / 'diagnostics_stepper.py'
    with open(script,  'w') as script_file:
        script_file.write(script_content)
    run_script(script, port)

##############################
#  Experiment commands
##############################

def update_experiment_state(new_state, port):
    # get experiment id from pico
    get_ampy('/configs/experiment_config.json', DIR_TMP / 'experiment_config.json', port)
    with open(DIR_TMP / 'experiment_config.json', 'r') as f:
        experiment_config = json.load(f)
        experiment_id = experiment_config['experiment_id']

    print(f'Setting experiment(experiment_id={experiment_id}) state to {new_state}')

    # update experiment state in db
    with Session(idec_engine()) as session:
        update_stmt = (
            update(Experiment)
            .where(Experiment.experiment_id == experiment_id)
            .values(status=new_state)
        )
        session.execute(update_stmt)
        session.commit()

    # store new experiment state on pico
    state = {
        "status": 'running' if new_state == 'start' else 'idle',
    }
    with open(DIR_TMP / 'experiment_state.json', 'w') as f:
        json.dump(state, f)
    put_ampy(DIR_TMP / 'experiment_state.json',  '/state/reactor_state.json', port)


def _push_new_config(new_config_json, port):
    experiment_id = new_config_json['experiment_id']
     # update experiment config in db
    with Session(idec_engine()) as session:
        update_stmt = (
            update(ExperimentConfig)
            .where(ExperimentConfig.experiment_id == experiment_id)
            .values(exp_config_json=json.dumps(new_config_json))
        )
        session.execute(update_stmt)
        session.commit()

    # store new experiment config on pico
    with open(DIR_TMP / 'experiment_config.json', 'w') as f:
        json.dump(new_config_json, f)
    put_ampy(DIR_TMP / 'experiment_config.json', '/configs/experiment_config.json', port)


def update_experiment_config(new_config, port):
    with open(new_config, 'r') as f:
        new_config_json = json.load(f)

    # get experiment id from pico
    get_ampy('/configs/experiment_config.json', DIR_TMP / 'experiment_config.json', port)
    with open(DIR_TMP / 'experiment_config.json', 'r') as f:
        experiment_config = json.load(f)
        experiment_id = experiment_config['experiment_id']
        new_config_json['experiment_id'] = experiment_id

    print(f'Updating experiment(experiment_id={experiment_id}) config')
    _push_new_config(new_config_json, port)


def update_flow_rate(flow_rate, port):
    """ Update lagoon dilution rate, leaving the rest of the config unchanged."""
    tmp_config = DIR_TMP / 'copy_experiment_config.json'
    download_experiment_config(port, tmp_config)
    with open(tmp_config, 'r') as f:
        experiment_config = json.load(f)
        old_flow_rate = experiment_config['lagoon']['flow_rate']
        print(f'Updating lagoon flow rate from {old_flow_rate} to {flow_rate}')
        experiment_config['lagoon']['flow_rate'] = flow_rate
        _push_new_config(experiment_config, port)



def new_experiment(experiment_config, experiment_name, port):
    # get reactor id from pico
    get_ampy('/configs/network_config.json', DIR_TMP / 'network_config.json', port)
    with open(DIR_TMP / 'network_config.json', 'r') as f:
        network_config = json.load(f)
        reactor_id = network_config['reactor_id']

    print(f'Creating new experiment for reactor_id={reactor_id}')

    with open(experiment_config, 'r') as f:
        config_json = json.load(f)

    current_timestamp = int(time.time())

    # Store data to db.
    with Session(idec_engine()) as session:
        stmt = insert(Experiment).values(
            reactor_id=reactor_id,
            name=experiment_name,
            timestamp=current_timestamp,
            status="pause",
            inserted_at=datetime.now()
        )
        result = session.execute(stmt)
        exp_id = result.inserted_primary_key[0]  # Access the newly inserted experiment_id
        print('Inserted experiment id: ', exp_id)

        stmt_config = insert(ExperimentConfig).values(
            experiment_id=exp_id,
            exp_config_json=json.dumps(config_json),
            timestamp=current_timestamp,
            inserted_at=datetime.now(),
        )

        session.execute(stmt_config)
        session.commit()

    # store new experiment id on pico
    config_json['experiment_id'] = exp_id
    with open(DIR_TMP / 'experiment_config.json', 'w') as f:
        json.dump(config_json, f)
    put_ampy(DIR_TMP / 'experiment_config.json', '/configs/experiment_config.json', port)


def download_experiment_config(port, local_path):
    """Downloads experiment config from the pico."""
    get_ampy('/configs/experiment_config.json', local_path, port)
    print(f'Downloaded experiment config to {local_path}')


##############################
# Helper commands
##############################

def run_script(script: Path, port):
    return run_ampy(f'run {script}', port)

def run_ampy(command, port):
    ampy_command = f'ampy -p {port} {command}'
    print(f'Running command: {command}')
    res = subprocess.run(ampy_command, shell=True)
    if res.returncode != 0:
        print(f'Error running command: {res.stderr}')


def get_ampy(pico_path, local_path, port):
    ampy_command = f'ampy -p {port} get {pico_path} {local_path}'
    print(f'Running command: {ampy_command}')
    res = subprocess.run(ampy_command, shell=True)
    if res.returncode != 0:
        print(f'Error running command: {res.stderr}')


def put_ampy(local_path, pico_path, port):
    ampy_command = f'ampy -p {port} put {local_path} {pico_path}'
    print(f'Running command: {ampy_command}')
    res = subprocess.run(ampy_command, shell=True)
    if res.returncode != 0:
        print(f'Error running command: {res.stderr}')


def rm_ampy(remote_path, port, check_exists=True):
    if check_exists:
        parent_folder  = Path(remote_path).parent
        if not remote_path in list_ampy(parent_folder, port):
            print(f'Path {remote_path} does not exist, return.')
            return
    ampy_command = f'ampy -p {port} rm {remote_path}'
    print(f'Running command: {ampy_command}')
    res = subprocess.run(ampy_command, shell=True)
    if res.returncode != 0:
        print(f'Error running command: {res.stderr}')


def rmdir_ampy(remote_path, port):
    ampy_command = f'ampy -p {port} rmdir {remote_path}'
    print(f'Running command: {ampy_command}')
    res = subprocess.run(ampy_command, shell=True)
    if res.returncode != 0:
        print(f'Error running command: {res.stderr}')


def mkdir_ampy(remote_path, port):
    ampy_command = f'ampy -p {port} mkdir {remote_path}'
    print(f'Running command: {ampy_command}')
    res = subprocess.run(ampy_command, shell=True)
    if res.returncode != 0:
        print(f'Error running command: {res.stderr}')

def list_ampy(remote_path, port, print_results=False):
    ampy_command = f'ampy -p {port} ls {remote_path}'
    print(f'Running command: {ampy_command}')
    res = subprocess.run(ampy_command, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f'Error running command: {res.stderr}')
    list_res = res.stdout.split('\n')
    if print_results:
        print('\n'.join(list_res))
    return list_res

def load_evotool_config():
    CFG_EVOTOOL.touch(exist_ok=True)
    with open(CFG_EVOTOOL, 'r') as cfg_file:
        contents = cfg_file.read()
        if contents != '':
            return json.loads(contents)
        else:
            return {}


def get_reactor_id_by_name(reactor_name):
    """Returns the reactor_id of the reactor with the given name, or None if it does not exist.

    Raises if more than one reactor shares the name (ambiguous, resolve manually).
    """
    with Session(idec_engine()) as session:
        rows = session.execute(select(Reactor.reactor_id)
                               .where(Reactor.name.ilike(reactor_name))).fetchall()
    if len(rows) == 0:
        return None
    if len(rows) > 1:
        raise RuntimeError(
            f"Multiple reactors named '{reactor_name}' in the database "
            f"(ids: {[row[0] for row in rows]}). Resolve manually.")
    return rows[0][0]


def create_reactor_db_entry(reactor_name):
    reactor = Reactor(name=reactor_name, network_id='0.0.0.0', reactor_config=[], experiment=[])
    with Session(idec_engine()) as session:
        session.add(reactor)
        session.commit()
        return reactor.reactor_id


def generate_network_config(reactor_id):
    with open('pico/configs/default-network_config.json', 'r') as f:
        network_config = json.load(f)
        network_config['reactor_id'] = reactor_id
    return network_config


def setup_new_reactor(reactor_name, port):
    """Bootstraps a reactor on the attached pico.

    The reactor's name is stored on the pico (configs/reactor_name.json) and reused later by
    `register`. Its reactor_id stays REACTOR_ID_UNREGISTERED until `register` assigns one.
    """
    network_config = generate_network_config(reactor_id=REACTOR_ID_UNREGISTERED)
    temp_path_network_config = DIR_TMP / 'network_config.json'
    with open(temp_path_network_config, 'w') as nw_file:
        json.dump(network_config, nw_file)

    temp_path_reactor_name = DIR_TMP / 'reactor_name.json'
    with open(temp_path_reactor_name, 'w') as name_file:
        json.dump({'name': reactor_name}, name_file)

    rmdir_ampy('/', port)
    mkdir_ampy('/configs', port)
    mkdir_ampy('/logs', port)
    mkdir_ampy('/state', port)
    mkdir_ampy('/tmp', port)
    put_ampy(temp_path_network_config, '/configs/network_config.json', port)
    put_ampy(temp_path_reactor_name, '/configs/reactor_name.json', port)
    put_ampy('pico/configs/default-reactor_config.json', '/configs/reactor_config.json', port)
    put_ampy('pico/configs/default-experiment_config.json', '/configs/experiment_config.json', port)
    put_ampy('pico/configs/default-reactor_state.json', '/state/reactor_state.json', port)
    put_ampy('pico-libs', '/libs', port)
    print(f"Reactor '{reactor_name}' initialized.")


def confirm(prompt):
    """Asks the user a yes/no question on the console. Returns True only on an explicit yes."""
    return input(f'{prompt} [y/N] ').strip().lower() in {'y', 'yes'}


def register_reactor(port):
    """Registers the attached reactor in the database, reusing the name stored on the pico.

    Reads the reactor name from configs/reactor_name.json, then links to an existing database
    reactor of the same name or creates a new one (confirming either way). The resulting
    reactor_id is written back into configs/network_config.json without disturbing any other
    on-pico state (e.g. calibration).
    """
    temp_path_reactor_name = DIR_TMP / 'reactor_name.json'
    if temp_path_reactor_name.exists():
        temp_path_reactor_name.unlink()
    get_ampy('/configs/reactor_name.json', temp_path_reactor_name, port)
    if not temp_path_reactor_name.exists():
        print('Could not read configs/reactor_name.json from the reactor. Run `init <REACTOR_NAME>` first.')
        exit(1)
    with open(temp_path_reactor_name) as name_file:
        reactor_name = json.load(name_file).get('name')
    if not reactor_name:
        print('No reactor name stored on the reactor. Run `init <REACTOR_NAME>` first.')
        exit(1)

    temp_path_network_config = DIR_TMP / 'network_config.json'
    if temp_path_network_config.exists():
        temp_path_network_config.unlink()
    get_ampy('/configs/network_config.json', temp_path_network_config, port)
    if not temp_path_network_config.exists():
        print('Could not read configs/network_config.json from the reactor. Run `init <REACTOR_NAME>` first.')
        exit(1)
    with open(temp_path_network_config) as nw_file:
        network_config = json.load(nw_file)

    current_id = network_config.get('reactor_id', REACTOR_ID_UNREGISTERED)
    if current_id != REACTOR_ID_UNREGISTERED:
        if not confirm(f"Reactor '{reactor_name}' is already registered with id {current_id}. Re-register?"):
            print('Aborted.')
            return

    existing_id = get_reactor_id_by_name(reactor_name)
    if existing_id is not None:
        if not confirm(f"Reactor '{reactor_name}' already exists in the database with id {existing_id}. "
                       "Link this reactor to it?"):
            print('Aborted.')
            return
        new_reactor_id = existing_id
    else:
        if not confirm(f"No reactor named '{reactor_name}' found in the database. Create a new one?"):
            print('Aborted.')
            return
        new_reactor_id = create_reactor_db_entry(reactor_name)
        print(f"Created new reactor '{reactor_name}' with id {new_reactor_id}.")

    network_config['reactor_id'] = new_reactor_id
    with open(temp_path_network_config, 'w') as nw_file:
        json.dump(network_config, nw_file)
    put_ampy(temp_path_network_config, '/configs/network_config.json', port)
    print(f"Reactor '{reactor_name}' registered with id {new_reactor_id}.")


def deploy(scripts: list[str], port: str, dev_mode: bool):
    # copy all python scripts.
    if scripts == ['all']:
        scripts = glob.glob('pico/*.py')
        print('Deploying all scripts:', scripts)
    else:
        for script in scripts:
            if not Path(script).exists():
                print(f'Script {script} does not exist.')
                exit(1)
    has_main = any('main.py' in script for script in scripts)
    if has_main:
        rm_ampy('/main.py', port)
        pico_main = '/dev_main.py' if dev_mode else '/main.py'
        put_ampy('pico/main.py', pico_main, port)

    non_main = [script for script in scripts if 'main.py' not in script]
    for script in non_main:
        put_ampy(script, Path('/') / Path(script).name, port)


def download_logs(local_path: Path, port: str):
    """ Downloads all logs from the pico."""
    log_files = list_ampy('/logs', port)
    for log_file in log_files:
        get_ampy(log_file, local_path / Path(log_file).name, port)


def clear_logs(port: str):
    """ Clears logs folder on pico."""
    log_files = list_ampy('/logs', port)
    for log_file in log_files:
        rm_ampy(log_file, port)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Command line tool for working with EvoFlow reactors.')
    parser.add_argument('--port', type=str, help='The port of the Pico W. If not provided, will be inferred automatically.', default=None)

    command_parsers = parser.add_subparsers(dest='command')

    command_parsers.add_parser('stop', help='Stop all reactor hardware')

    install_parser = command_parsers.add_parser('install', help='Install a micropython')
    install_parser.add_argument('--micropython', '-p', type=str, default='micropython/RPI_PICO_W-20240602-v1.23.0.uf2', help='Path to the micropython file.')
    install_parser.add_argument('--pico', '-d', type=str, default=None, help='Path to the pico device.')

    init_parser = command_parsers.add_parser('init', help='Initialize a new reactor')
    init_parser.add_argument('reactor_name', type=str, help='The name of the reactor to be created')

    command_parsers.add_parser('register', help='Register the attached reactor in the database (link existing or create new)')

    deploy_parser = command_parsers.add_parser('deploy', help='Deploy reactor software')
    deploy_parser.add_argument('--dev', action='store_true', help='If specified, main.py will be stored on pico as dev_main.py, to prevent auto-run')
    deploy_parser.add_argument('scripts', type=str, nargs='+', help="Scripts to deploy, 'all' for all")

    command_parsers.add_parser('ping', help='Ping the reactor')

    ## Commands for working with pico logs.
    log_parser = command_parsers.add_parser('logs', help='Helper commands for working with logs on the pico')
    log_commands = log_parser.add_subparsers(dest='logs_command')
    log_commands.add_parser('clear', help='Clear all logs on the pico')
    parsers_logs_dump = log_commands.add_parser('dump', help='Download all logs from the pico')
    parsers_logs_dump.add_argument('--local', type=str, default=None, help='Local folder to save logs to. If not provided, will stored to a temp directory.')

    ## Commands for running diagnostics
    parser_diagnose = command_parsers.add_parser('diagnose', help='Diagnose reactor hardware', aliases=['d'])
    diagnose_hardware_parsers = parser_diagnose.add_subparsers(dest='part')
    diagnose_hardware_parsers.add_parser('free_space', help='Diagnose free space')
    diagnose_hardware_parsers.add_parser('pumps', help='Diagnose pumps')
    parser_stepper = diagnose_hardware_parsers.add_parser('stepper', help='Diagnose stepper motor')
    parser_stepper.add_argument('type', choices=['angle', 'displacement', 'vol'], help='Specify the type of movement: angle, displacement, or volume')
    parser_stepper.add_argument('amount', type=int, help='Specify the amount: degrees, mm, or mL, depending on the type')
    diagnose_hardware_parsers.add_parser('stirrers', help='Diagnose stirrers')
    diagnose_hardware_parsers.add_parser('temp', help='Diagnose temperature sensors')
    diagnose_hardware_parsers.add_parser('od_left', help='Diagnose optical density sensors on the left turbidostat')
    diagnose_hardware_parsers.add_parser('od_right', help='Diagnose optical density sensors on the right turbidostat')
    diagnose_hardware_parsers.add_parser('stop', help='Stop all hardware')

    ## Commands for running calibration
    parser_calibrate = command_parsers.add_parser('calibrate', help='Calibrate reactor hardware', aliases=['c'])
    calibrate_hardware_parsers = parser_calibrate.add_subparsers(dest='part')
    parser_calibrate_new = calibrate_hardware_parsers.add_parser('new', help='Calibrate new reactor')
    parser_calibrate_new.add_argument('folder', type=str, help='Folder where the calibration data will be stored')
    parser_calibrate_new.add_argument('--default_config', action='store_true', help='Overwrite pico config with the default config.')

    parser_calibrate_inc_left_stirrer =  calibrate_hardware_parsers.add_parser('inc_left_stirrer', help='Calibrate left incubator stirrer speed')
    parser_calibrate_inc_left_stirrer.add_argument('speed_frac', type=float, help='Speed fraction, from 0 to 1')
    parser_calibrate_lagoon_stirrer = calibrate_hardware_parsers.add_parser('lagoon_stirrer', help='Calibrate lagoon stirrer speed')
    parser_calibrate_lagoon_stirrer.add_argument('speed_frac', type=float, help='Speed fraction, from 0 to 1')
    parser_calibrate_inc_right_stirrer = calibrate_hardware_parsers.add_parser('inc_right_stirrer', help='Calibrate right incubator stirrer speed')
    parser_calibrate_inc_right_stirrer.add_argument('speed_frac', type=float, help='Speed fraction, from 0 to 1')


    parser_calibrate_inc_left_od = calibrate_hardware_parsers.add_parser('inc_left_od', help='Calibrate optical density sensors on left incubator')
    parser_calibrate_inc_left_od.add_argument('expected_ods', type=float, nargs='+', help='Expected OD values for each probe')
    parser_calibrate_inc_right_od = calibrate_hardware_parsers.add_parser('inc_right_od', help='Calibrate optical density sensors on right incubator')
    parser_calibrate_inc_right_od.add_argument('expected_ods', type=float, nargs='+', help='Expected OD values for each probe')

    parser_calibrate_temp = calibrate_hardware_parsers.add_parser('temp', help='Calibrate temperature sensors')
    parser_calibrate_temp.add_argument('target_temp', type=float, help='Target temperature for calibration')

    parser_calibrate_bact_stepper = calibrate_hardware_parsers.add_parser('bact_stepper', help='Calibrate step volume of the bacteria stepper motor.\nNote: we only use stepper of the left incubator.')
    parser_calibrate_bact_stepper.add_argument('--num_steps', type=int, default=10000, help='Number of steps to use during calibration')
    parser_calibrate_bact_stepper.add_argument('--pwm', type=int, default=1000, help='PWM frequency for the stepper motor')

    parser_calibrate_induction_stepper = calibrate_hardware_parsers.add_parser('induction_stepper', help='Calibrate roation direction of the induction stepper motor. Either +1 or -1')
    parser_calibrate_induction_stepper.add_argument('rotation_direction', type=int, choices=[+1, -1], help='Rotation direction of the induction stepper motor, either +1 or -1')

    parser_calibrate_new_config = calibrate_hardware_parsers.add_parser('compute_config', help='Compute a new calibration config')
    parser_calibrate_new_config.add_argument('--inc_left_measured_temps', type=float, nargs='+', default=None,
                                             help='Measured temperatures for the left incubator')
    parser_calibrate_new_config.add_argument('--inc_left_target_temps', type=float, nargs='+', default=None,
                                             help='Target temperatures for the left incubator')
    parser_calibrate_new_config.add_argument('--inc_right_measured_temps', type=float, nargs='+', default=None,
                                             help='Measured temperatures for the right incubator')
    parser_calibrate_new_config.add_argument('--inc_right_target_temps', type=float, nargs='+', default=None,
                                             help='Target temperatures for the right incubator')
    parser_calibrate_new_config.add_argument('--lagoon_measured_temps', type=float, nargs='+', default=None, help
                                             ='Measured temperatures for the lagoon')
    parser_calibrate_new_config.add_argument('--lagoon_target_temps', type=float, nargs='+', default=None,
                                             help='Target temperatures for the lagoon')
    parser_calibrate_new_config.add_argument('--bact_stepper_volume', type=float, default=None,
                                             help='Volume of liquid dispensed by the bacteria stepper motor.')

    ## Commands to control pico exeriment.
    parser_experiment = command_parsers.add_parser('experiment', help='Control experiment')
    experiment_subparsers = parser_experiment.add_subparsers(dest='experiment_command')

    experiment_subparsers.add_parser('start', help='Start the experiment')
    experiment_subparsers.add_parser('stop', help='Stop the experiment')
    experiment_subparsers.add_parser('pause', help='Pause the experiment')

    parser_experiment_update = experiment_subparsers.add_parser('update', help='Update experiment config')
    parser_experiment_update.add_argument('config', type=str, help='Path to the new config file')

    parser_experiment_download = experiment_subparsers.add_parser('get-config', help='Download experiment config')
    parser_experiment_download.add_argument('local_path', type=str, help='Local path to save the config file')

    parser_experiment_update_flow_rate = experiment_subparsers.add_parser('update-flow-rate', help='Update lagoon flow rate')
    parser_experiment_update_flow_rate.add_argument('flow_rate', type=float, help='New flow rate')

    parser_experiment_new = experiment_subparsers.add_parser('new', help='Start a new experiment')
    parser_experiment_new.add_argument('name', type=str, help='Name of the new experiment')
    parser_experiment_new.add_argument('config', type=str, help='Path to the new experiment config file')

    args = parser.parse_args()

    ## Load config
    cfg = load_evotool_config()
    if 'calibration_folder' in cfg.keys():
        calibration_folder = Path(cfg['calibration_folder'])
    else:
        calibration_folder = None

    ## Handle micropython install command
    if args.command == 'install':
        micro_path = Path(args.micropython)
        if not micro_path.exists():
            print(f'Micropython file {micro_path} not found.')
            exit(1)
        if args.pico is None:
            try:
                pico_path = find_pico_mount()
            except ValueError as e:
                print('Error while looking for the pico path:')
                print(e)
                print('You can supply path to the mounted pico via --pico flag.')
                exit(1)
        shutil.copy(micro_path, pico_path)
        print('Successfully copied micropython to the pico.')
        exit(0)

    ## Find pico
    port = args.port
    if port is None:
        port = find_pico_port()
        if port is None:
            print('Could not find the pico attached. Re-plug or provide correct port via --port')
            exit(1)
        # TODO: try to communicate with pico.
    if args.command == 'stop':
        run_script(DIR_DIAGNOSTICS / 'diagnostics_stop.py', port)
    elif args.command == 'ping':
        list_ampy('/', port)
        print(f'Reactor responsive at port {port}')
    elif args.command == 'init':
        setup_new_reactor(args.reactor_name, port)
    elif args.command == 'register':
        register_reactor(port)
    elif args.command == 'deploy':
        deploy(args.scripts, port,  args.dev)
    elif args.command == 'logs':
        if args.logs_command == 'clear':
            clear_logs(port)
        elif args.logs_command == 'dump':
            if args.local is None:
                local_path = Path('logs') / datetime.now().strftime('%Y-%m-%d')
            else:
                local_path = Path(args.local)
            local_path.mkdir(exist_ok=True, parents=True)
            print(f'Downloading pico logs to {local_path}')
            download_logs(local_path, port)
        else:
            log_parser.print_help()
    elif args.command == 'diagnose':
        if args.part == 'free_space':
            run_free_space_diagnostic(port)
        elif args.part == 'pumps':
            run_script(DIR_DIAGNOSTICS / 'diagnostics_pumps.py', port)
        elif args.part == 'stepper':
            run_stepper_diagnostic(args.type, args.amount, port)
        elif args.part == 'stirrers':
            run_script(DIR_DIAGNOSTICS / 'diagnostics_stirrers.py', port)
        elif args.part == 'temp':
            run_script(DIR_DIAGNOSTICS / 'diagnostics_heaters.py', port)
        elif args.part == 'od_left':
            run_inc_left_od_diagnostic(port)
        elif args.part == 'od_right':
            run_inc_right_od_diagnostic(port)
        elif args.part == 'stop':
            run_script(DIR_DIAGNOSTICS / 'diagnostics_stop.py', port)
        else:
            parser_diagnose.print_help()
    elif args.command == 'calibrate':
        if args.part == 'new':
            with open(CFG_EVOTOOL, 'w') as cfg_file:
                Path(args.folder).mkdir(exist_ok=True, parents=True)
                cfg['calibration_folder'] = args.folder
                json.dump(cfg, cfg_file)
                if args.default_config:
                    shutil.copy('pico/configs/default-reactor_config.json', args.folder + '/old_reactor_config.json')
                else:
                    get_ampy('configs/reactor_config.json', args.folder + '/old_reactor_config.json', port)
                exit(0) # TODO: refactor
        else:
            if calibration_folder is None:
                print('Please run `python evotool.py calibrate new <folder>` first')
                exit(1)
            if not calibration_folder.exists():
                print(f'Calibration folder {calibration_folder} does not exist. Please run `evotool calibrate new <folder>`')
                exit(1)
            else:
                print('Using calibration folder:', calibration_folder)
        if args.part == 'inc_left_stirrer':
            run_inc_left_stirrer_calibration(args.speed_frac, port)
            with open(calibration_folder / CALIBRATION_INC_LEFT_STIRRER_SPEED, 'w') as speed_file:
                speed_file.write(str(args.speed_frac))
        elif args.part == 'inc_right_stirrer':
            run_inc_right_stirrer_calibration(args.speed_frac, port)
            with open(calibration_folder / CALIBRATION_INC_RIGHT_STIRRER_SPEED, 'w') as speed_file:
                speed_file.write(str(args.speed_frac))
        elif args.part == 'lagoon_stirrer':
            run_lagoon_stirrer_calibration(args.speed_frac, port)
            with open(calibration_folder / CALIBRATION_LAGOON_STIRRER_SPEED, 'w') as speed_file:
                speed_file.write(str(args.speed_frac))
        elif args.part == 'inc_left_od':
            expected_ods = args.expected_ods
            run_inc_left_od_calibration(len(expected_ods), port)
            get_ampy('tmp/od_calibration.csv', calibration_folder / CALIBRATION_INC_LEFT_OD_MEASURED, port)
            with open(calibration_folder / CALIBRATION_INC_LEFT_OD_EXPECTED, 'w') as ods_file:
                ods_file.write('\n'.join(map(str, expected_ods)))
        elif args.part == 'inc_right_od':
            expected_ods = args.expected_ods
            run_inc_right_od_calibration(len(expected_ods), port)
            get_ampy('tmp/od_calibration.csv', calibration_folder / CALIBRATION_INC_RIGHT_OD_MEASURED, port)
            with open(calibration_folder / CALIBRATION_INC_RIGHT_OD_EXPECTED, 'w') as ods_file:
                ods_file.write('\n'.join(map(str, expected_ods)))
        elif args.part == 'temp':
            run_temp_calibration(args.target_temp, port)
        elif args.part == 'bact_stepper':
            run_bact_stepper_calibration(args.num_steps, args.pwm, port)
            with open(calibration_folder / CALIBRATION_BACT_STEPPER_NUM_STEPS, 'w') as steps_file:
                steps_file.write(str(args.num_steps))
        elif args.part == 'induction_stepper':
            run_induction_stepper_calibration(args.rotation_direction, port)
            with open(calibration_folder / CALIBRATION_INDUCTION_STEPPER_DIRECTION, 'w') as speed_file:
                speed_file.write(str(args.rotation_direction))
        elif args.part == 'compute_config':
            compute_new_config(calibration_folder, args, port)
        else:
            parser_calibrate.print_help()
    elif args.command == 'experiment':
        if args.experiment_command in {'start', 'stop', 'pause'}:
            update_experiment_state(args.experiment_command, port)
        elif args.experiment_command == 'update':
            path = Path(args.config)
            if not path.exists():
                print(f'Config file {path} does not exist.')
                exit(1)
            update_experiment_config(path, port)
        elif args.experiment_command == 'new':
            path = Path(args.config)
            if not path.exists():
                print(f'Config file {path} does not exist.')
                exit(1)
            new_experiment(path, args.name, port)
        elif args.experiment_command == 'get-config':
            path = Path(args.local_path)
            if not path.exists():
                print(f'Local path {path} does not exist.')
                exit(1)
            download_experiment_config(port, path)
        elif args.experiment_command == 'update-flow-rate':
            if args.flow_rate < 0:
                print('Flow rate cannot be negative.')
                exit(1)
            if args.flow_rate > 3:
                print('Warning: setting flow rate about 3 volums/hour is not recommended.')
            update_flow_rate(args.flow_rate, port)
        else:
            parser_experiment.print_help()
    else:
        parser.print_help()
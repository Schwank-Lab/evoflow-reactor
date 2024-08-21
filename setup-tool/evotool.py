import argparse 
import subprocess
from pathlib import Path
import json 
import glob
from sys import exit
import pandas as pd 
import numpy as np  
from sklearn.linear_model import LinearRegression



import find_pico
from diagnostics import diagnostics_stepper, diagnostics_od
from calibration import calibration_inc_stirrer, calibration_induction_stepper, calibration_bact_stepper, calibration_lagoon_stirrer, calibration_od, calibration_temp

DIR_DIAGNOSTICS = Path('diagnostics')
DIR_TMP = Path('tmp')
CFG_EVOTOOL = Path('.evotool.json')

CALIBRATION_OD_MEASURED = 'od_measured.csv'
CALIBRATION_OD_EXPECTED = 'od_expected.txt'
CALIBRATION_INDUCTION_STEPPER_DIRECTION = 'induction_stepper_rotation_direction.txt'
CALIBRATION_BACT_STEPPER_NUM_STEPS = 'bact_stepper_num_steps.txt'
CALIBRATION_INC_STIRRER_SPEED = 'inc_stirrer_speed_frac.txt'
CALIBRATION_LAGOON_STIRRER_SPEED = 'lagoon_stirrer_speed_frac.txt'

## Calibration commands 
def run_inc_stirrer_calibration(speed_frac, port): 
    calibration_inc_stirrer.generate_script(speed_frac, tmp_dir=DIR_TMP, script_name='calibrate_inc_stirrer.py')
    run_script(DIR_TMP / 'calibrate_inc_stirrer.py', port)

def run_lagoon_stirrer_calibration(speed_frac, port):
    calibration_lagoon_stirrer.generate_script(speed_frac, tmp_dir=DIR_TMP, script_name='calibrate_lagoon_stirrer.py')
    run_script(DIR_TMP / 'calibrate_lagoon_stirrer.py', port)

def run_od_calibration(num_probes, port): 
    calibration_od.generate_script(num_probes, tmp_dir=DIR_TMP, script_name='calibrate_od.py')
    run_script(DIR_TMP / 'calibrate_od.py', port)

def run_temp_calibration(target_temp, port):
    calibration_temp.generate_script(target_temp, tmp_dir=DIR_TMP, script_name='calibrate_temp.py')
    run_script(DIR_TMP / 'calibrate_temp.py', port)

def run_bact_stepper_calibration(num_steps, port): 
    calibration_bact_stepper.generate_script(num_steps, tmp_dir=DIR_TMP, script_name='calibrate_bact_stepper.py')
    run_script(DIR_TMP / 'calibrate_bact_stepper.py', port)

def run_induction_stepper_calibration(rotation_deg, port):
    calibration_induction_stepper.generate_script(rotation_deg, tmp_dir=DIR_TMP, script_name='calibrate_induction_stepper.py')
    run_script(DIR_TMP / 'calibrate_induction_stepper.py', port)

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
        print(f'Inferred: T = {inc_temp_slope:.2f} * RAW + {inc_temp_intercept:.2f}')
        print(vals)
        return inc_temp_slope, inc_temp_intercept
    else: 
        print('Temperature not provided, re-using values from the old config.')
        return None, None

def compute_new_config(calibration_folder, args, port):
    """ Computes new reactor config based on all calibrated values."""
    with open(calibration_folder / 'old_reactor_config.json') as f: 
        cfg = json.load(f)

    # re-use old calibration values.
    inc_temp_slope, inc_temp_intercept = cfg['incubator_temp']['slope'], cfg['incubator_temp']['intercept']
    lagoon_temp_slope, lagoon_temp_intercept = cfg['lagoon_temp']['slope'], cfg['lagoon_temp']['intercept']
    od_slope, od_intercept = cfg['incubator_od']['slope'], cfg['incubator_od']['intercept']
    bact_stepper_ml_per_step = cfg['bact_stepper_ml_per_step']
    lagoon_stirrer_top_speed_frac = cfg['lagoon_stirrer_top_speed_frac']
    inc_stirrer_top_speed_frac = cfg['incubator_stirrer_top_speed_frac']
    induction_stepper_direction = cfg['induction_stepper_direction']

    print('\n\n\nIncubator temperature sensor')
    new_slope, new_intercept = compute_temp_calibration(args.inc_measured_temps, args.inc_target_temps)
    if new_slope is not None:
        inc_temp_slope, inc_temp_intercept = new_slope, new_intercept

    print('\n\n\nLagoon temperature sensor')
    new_slope, new_intercept = compute_temp_calibration(args.lagoon_measured_temps, args.lagoon_target_temps)
    if new_slope is not None:
        lagoon_temp_slope, lagoon_temp_intercept = new_slope, new_intercept
    
    print('\n\n\nOptical density calibration')
    od_measured = calibration_folder / CALIBRATION_OD_MEASURED
    od_expected = calibration_folder / CALIBRATION_OD_EXPECTED
    if od_measured.exists() and od_expected.exists(): 
        od_measured = pd.read_csv(od_measured).mean(axis=1)
        with open(od_expected, 'r') as f: 
            od_expected = list(map(float, f.readlines()))
        vals = pd.DataFrame({'od': od_measured, 'expected': od_expected})
        od_slope, od_intercept, pred = linear_fit_1d(od_measured, 'od', 'expected')
        print(f'Inferred: OD = {od_slope:.2f} * RAW + {od_intercept:.2f}')
        vals['predicted'] = pred
        print(vals)
    else:
        print('OD calibration not provided. Re-using old values.')

    print('\n\n\nBacteria stirrer calibration')
    inc_stirrer_top_speed = calibration_folder / CALIBRATION_INC_STIRRER_SPEED
    if inc_stirrer_top_speed.exists(): 
        with open(inc_stirrer_top_speed, 'r') as f: 
            inc_stirrer_top_speed_frac = float(f.read())
        print('Set new incubator stirrer top speed to:', inc_stirrer_top_speed_frac)
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
    if args.inc_stepper_volume is not None:
        with open(calibration_folder / CALIBRATION_BACT_STEPPER_NUM_STEPS, 'r') as f: 
            bact_stepper_num_steps = float(f.read())
        bact_stepper_ml_per_step = args.inc_stepper_volume / bact_stepper_num_steps
        print(f'Inferred bacteria stepper volume per step = {bact_stepper_ml_per_step:.6f}mL')
    else:
        print('Bacteria stepper calibration not provided. Re-using old values. Make sure to set --inc_stepper_volume flag.')
    
    print('\n\n\nInduction stepper calibration')
    induction_stepper_dir_file = calibration_folder / CALIBRATION_INDUCTION_STEPPER_DIRECTION
    if induction_stepper_dir_file.exists():
        with open(induction_stepper_dir_file, 'r') as f: 
            induction_stepper_direction = int(f.read())
        print('Set new induction stepper direction to:', induction_stepper_direction)
    else:
        print('Induction stepper calibration not provided. Re-using old values.')

    new_cfg = cfg.copy()
    new_cfg['incubator_temp']['slope'] = inc_temp_slope
    new_cfg['incubator_temp']['intercept'] = inc_temp_intercept
    new_cfg['lagoon_temp']['slope'] = lagoon_temp_slope
    new_cfg['lagoon_temp']['intercept'] = lagoon_temp_intercept
    new_cfg['incubator_od']['slope'] = od_slope
    new_cfg['incubator_od']['intercept'] = od_intercept
    new_cfg['bact_stepper_ml_per_step'] = bact_stepper_ml_per_step
    new_cfg['incubator_stirrer_top_speed_frac'] = inc_stirrer_top_speed_frac
    new_cfg['lagoon_stirrer_top_speed_frac'] = lagoon_stirrer_top_speed_frac
    new_cfg['induction_stepper_direction'] = induction_stepper_direction

    print('\n\n\nComputed new reactor config:')
    print(json.dumps(new_cfg, indent=2))

    with open(calibration_folder / 'new_reactor_config.json', 'w') as f: 
        json.dump(new_cfg, f)

    put_ampy(calibration_folder / 'new_reactor_config.json', 'configs/reactor_config.json', port)


## Diagnostics commands
def run_inc_left_od_diagnostic(port): 
    diagnostics_od.generate_script('inc_left', temp_dir=DIR_TMP, script_name='diagnostics_left_od.py')
    run_script(DIR_TMP / 'diagnostics_left_od.py', port)

def run_inc_right_od_diagnostic(port): 
    diagnostics_od.generate_script('inc_right', temp_dir=DIR_TMP, script_name='diagnostics_right_od.py')
    run_script(DIR_TMP / 'diagnostics_right_od.py', port)

def run_stepper_diagnostic(rotation_deg, port): 
    diagnostics_stepper.generate_script(rotation_deg, temp_dir=DIR_TMP, script_name='diagnostics_stepper.py')
    run_script(DIR_TMP / 'diagnostics_stepper.py', port)


## Helper functions
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

def rm_ampy(remote_path, port): 
    ampy_command = f'ampy -p {port} rm {remote_path}'
    print(f'Running command: {ampy_command}')
    res = subprocess.run(ampy_command, shell=True)
    if res.returncode != 0: 
        print(f'Error running command: {res.stderr}')


def load_evotool_config():
    CFG_EVOTOOL.touch(exist_ok=True)
    with open(CFG_EVOTOOL, 'r') as cfg_file: 
        contents = cfg_file.read()
        if contents != '': 
            return json.loads(contents)
        else:
            return {}
        

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
        rm_ampy('main.py', port)
        pico_main = 'dev_main.py' if dev_mode else 'main.py'
        put_ampy('pico/main.py', pico_main, port)
    
    non_main = [script for script in scripts if 'main.py' not in script]
    for script in non_main: 
        put_ampy(script, Path(script).name, port)
    
        

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Command line tool for working with EvoFlow reactors.')
    parser.add_argument('--port', type=str, help='The port of the Pico W. If not provided, will be inferred automatically.', default=None)

    command_parsers = parser.add_subparsers(dest='command')

    command_parsers.add_parser('stop', help='Stop all reactor hardware')
    deploy_parser = command_parsers.add_parser('deploy', help='Deploy reactor software')

    deploy_parser.add_argument('--dev', action='store_true', help='If specified, main.py will be stored on pico as dev_main.py, to prevent auto-run')
    deploy_parser.add_argument('scripts', type=str, nargs='+', help="Scripts to deploy, 'all' for all")

    ## Commands for running diagnostics
    parser_diagnose = command_parsers.add_parser('diagnose', help='Diagnose reactor hardware', aliases=['d'])
    diagnose_hardware_parsers = parser_diagnose.add_subparsers(dest='part')
    diagnose_hardware_parsers.add_parser('pumps', help='Diagnose pumps')
    parser_stepper = diagnose_hardware_parsers.add_parser('stepper', help='Diagnose stepper motor')
    parser_stepper.add_argument('rotation_deg', type=int, help='Rotation degrees')
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
    parser_calibrate_inc_stirrer =  calibrate_hardware_parsers.add_parser('inc_stirrer', help='Calibrate incubator stirrer speed')
    parser_calibrate_inc_stirrer.add_argument('speed_frac', type=float, help='Speed fraction, from 0 to 1')
    parser_calibrate_lagoon_stirrer = calibrate_hardware_parsers.add_parser('lagoon_stirrer', help='Calibrate lagoon stirrer speed')
    parser_calibrate_lagoon_stirrer.add_argument('speed_frac', type=float, help='Speed fraction, from 0 to 1')

    parser_calibrate_od = calibrate_hardware_parsers.add_parser('od', help='Calibrate optical density sensors')
    parser_calibrate_od.add_argument('expected_ods', type=float, nargs='+', help='Expected OD values for each probe')

    parser_calibrate_temp = calibrate_hardware_parsers.add_parser('temp', help='Calibrate temperature sensors')
    parser_calibrate_temp.add_argument('target_temp', type=float, help='Target temperature for calibration')

    parser_calibrate_bact_stepper = calibrate_hardware_parsers.add_parser('bact_stepper', help='Calibrate step volume of the bacteria stepper motor')
    parser_calibrate_bact_stepper.add_argument('--num_steps', type=int, default=10000, help='Number of steps to use during calibration')
    
    parser_calibrate_induction_stepper = calibrate_hardware_parsers.add_parser('induction_stepper', help='Calibrate roation direction of the induction stepper motor. Either +1 or -1')
    parser_calibrate_induction_stepper.add_argument('rotation_direction', type=int, choices=[+1, -1], help='Rotation direction of the induction stepper motor, either +1 or -1')

    parser_calibrate_new_config = calibrate_hardware_parsers.add_parser('compute_config', help='Compute a new calibration config')
    parser_calibrate_new_config.add_argument('--inc_measured_temps', type=float, nargs='+', default=None, 
                                             help='Measured temperatures for the incubator')
    parser_calibrate_new_config.add_argument('--inc_target_temps', type=float, nargs='+', default=None, 
                                             help='Target temperatures for the incubator')
    parser_calibrate_new_config.add_argument('--lagoon_measured_temps', type=float, nargs='+', default=None, help
                                             ='Measured temperatures for the lagoon')
    parser_calibrate_new_config.add_argument('--lagoon_target_temps', type=float, nargs='+', default=None, 
                                             help='Target temperatures for the lagoon')
    parser_calibrate_new_config.add_argument('--inc_stepper_volume', type=float, default=None, 
                                             help='Volume of liquid dispensed by the bacteria stepper motor')
    
    args = parser.parse_args()

    ## Load config
    cfg = load_evotool_config()
    if 'calibration_folder' in cfg.keys(): 
        calibration_folder = Path(cfg['calibration_folder'])
    else:
        calibration_folder = None

    ## Find pico
    port = args.port
    if port is None: 
        port = find_pico.find_pico_port()
        if port is None: 
            print('Could not find the pico attached. Re-plug or provide correct port via --port')
            exit(1)
        # TODO: try to communicate with pico.
    if args.command == 'stop': 
        run_script(DIR_DIAGNOSTICS / 'diagnostics_stop.py', port)
    elif args.command == 'deploy': 
        deploy(args.scripts, port,  args.dev)

    elif args.command == 'diagnose':
        if args.part == 'pumps':
            run_script(DIR_DIAGNOSTICS / 'diagnostics_pumps.py', port)
        elif args.part == 'stepper':
            run_stepper_diagnostic(args.rotation_deg, port)
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
                get_ampy('config/reactor_config.json', args.folder + '/old_reactor_config.json', port)
                exit(0) # TODO: refactor
        else: 
            if calibration_folder is None: 
                print('Please run `evotool calibrate new <folder>` first')
                exit(1)
            if not calibration_folder.exists():
                print(f'Calibration folder {calibration_folder} does not exist. Please run `evotool calibrate new <folder>`')
                exit(1)
            else: 
                print('Using calibration folder:', calibration_folder)
        if args.part == 'inc_stirrer': 
            run_inc_stirrer_calibration(args.speed_frac, port)
            with open(calibration_folder / CALIBRATION_INC_STIRRER_SPEED, 'w') as speed_file:
                speed_file.write(str(args.speed_frac))
        elif args.part == 'lagoon_stirrer':
            run_lagoon_stirrer_calibration(args.speed_frac, port)
            with open(calibration_folder / CALIBRATION_LAGOON_STIRRER_SPEED, 'w') as speed_file:
                speed_file.write(str(args.speed_frac))
        elif args.part == 'od': 
            expected_ods = args.expected_ods
            run_od_calibration(len(expected_ods), port)
            get_ampy('tmp/od_calibration.csv', calibration_folder / CALIBRATION_OD_MEASURED, port)
            with open(calibration_folder / CALIBRATION_OD_EXPECTED, 'w') as ods_file:
                ods_file.write('\n'.join(map(str, expected_ods)))
        elif args.part == 'temp': 
            run_temp_calibration(args.target_temp, port)
        elif args.part == 'bact_stepper': 
            run_bact_stepper_calibration(args.num_steps, port)
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
    else: 
        parser.print_help() 
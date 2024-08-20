import argparse 
import subprocess
from pathlib import Path
import json 
import glob
from sys import exit 


import find_pico
from diagnostics import diagnostics_stepper
from calibration import calibration_inc_stirrer, calibration_lagoon_stirrer, calibration_od, calibration_temp, calibration_stepper

DIR_DIAGNOSTICS = Path('diagnostics')
DIR_TMP = Path('tmp')
CFG_EVOTOOL = Path('.evotool.json')

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

def run_stepper_calibration(rotation_deg, port):
    calibration_stepper.generate_script(rotation_deg, tmp_dir=DIR_TMP, script_name='calibrate_stepper.py')
    run_script(DIR_TMP / 'calibrate_stepper.py', port)

## Diagnostics commands
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
    diagnose_hardware_parsers.add_parser('od', help='Diagnose optical density sensors')
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

    parser_calibrate_stepper = calibrate_hardware_parsers.add_parser('stepper', help='Calibrate stepper motor rotation direction. Either +1 or -1')
    parser_calibrate_stepper.add_argument('rotation_direction', type=int, choices=[+1, -1], help='Rotation direction of the stepper motor, either +1 or -1')

    args = parser.parse_args()

    ## Load config
    cfg = load_evotool_config()
    if 'calibration_folder' in cfg.keys(): 
        calibration_folder = Path(cfg['calibration_folder'])
        if not calibration_folder.exists():
            print(f'Calibration folder {calibration_folder} does not exist. Please run `evotool calibrate new <folder>`')
            exit(1)
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
        elif args.part == 'od':
            run_script(DIR_DIAGNOSTICS / 'diagnostics_od.py', port)
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
                exit(0) # TODO: refactor
        else: 
            if calibration_folder is None: 
                print('Please run `evotool calibrate new <folder>` first')
                exit(1)
            else: 
                print('Using calibration folder:', calibration_folder)
        if args.part == 'inc_stirrer': 
            run_inc_stirrer_calibration(args.speed_frac, port)
            with open(calibration_folder / 'inc_stirrer_speed_frac.txt', 'w') as speed_file:
                speed_file.write(str(args.speed_frac))
        elif args.part == 'lagoon_stirrer':
            run_lagoon_stirrer_calibration(args.speed_frac, port)
            with open(calibration_folder / 'lagoon_stirrer_speed_frac.txt', 'w') as speed_file:
                speed_file.write(str(args.speed_frac))
        elif args.part == 'od': 
            expected_ods = args.expected_ods
            with open(calibration_folder / 'od_expected.txt', 'w') as ods_file:
                ods_file.write('\n'.join(map(str, expected_ods)))
            run_od_calibration(len(expected_ods), port)
            get_ampy('tmp/od_calibration.csv', calibration_folder / 'od_measured.csv', port)
        elif args.part == 'temp': 
            run_temp_calibration(args.target_temp, port)
        elif args.part == 'stepper': 
            run_stepper_calibration(args.rotation_direction, port)
            with open(calibration_folder / 'stepper_rotation_direction.txt', 'w') as speed_file:
                speed_file.write(str(args.rotation_direction))
        else: 
            parser_calibrate.print_help()
    else: 
        parser.print_help() 
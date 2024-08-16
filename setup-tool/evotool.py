import argparse 
import subprocess
from pathlib import Path


import find_pico
from diagnostics import diagnostics_stepper

DIR_DIAGNOSTICS = Path('diagnostics')
DIR_TMP = Path('tmp')

def run_stepper_diagnostic(rotation_deg, port): 
    diagnostics_stepper.generate_script(rotation_deg, temp_dir=DIR_TMP, script_name='diagnostics_stepper.py')
    run_script(DIR_TMP / 'diagnostics_stepper.py', port)

def run_script(script: Path, port): 
    return run_ampy(f'run {script}', port)

def run_ampy(command, port): 
    ampy_command = f'ampy -p {port} {command}'
    print(f'Running command: {command}')
    res = subprocess.run(ampy_command, shell=True)
    if res.returncode != 0: 
        print(f'Error running command: {res.stderr}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Command line tool for working with EvoFlow reactors.')
    parser.add_argument('--port', type=str, help='The port of the Pico W. If not provided, will be inferred automatically.', default=None)

    command_parsers = parser.add_subparsers(dest='command')

    parser_diagnose = command_parsers.add_parser('diagnose', help='Diagnose reactor hardware', aliases=['d'])
    diagnose_hardware_parsers = parser_diagnose.add_subparsers(dest='part')
    diagnose_hardware_parsers.add_parser('pumps', help='Diagnose pumps')
    parser_stepper = diagnose_hardware_parsers.add_parser('stepper', help='Diagnose stepper motor')
    parser_stepper.add_argument('rotation_deg', type=int, help='Rotation degrees')
    diagnose_hardware_parsers.add_parser('stirrers', help='Diagnose stirrers')
    diagnose_hardware_parsers.add_parser('temp', help='Diagnose temperature sensors')
    diagnose_hardware_parsers.add_parser('od', help='Diagnose optical density sensors')
    diagnose_hardware_parsers.add_parser('stop', help='Stop all hardware')
    

    args = parser.parse_args()

    port = args.port
    if port is None: 
        port = find_pico.find_pico_port()
        if port is None: 
            print('Could not find the pico attached. Re-plug or provide correct port via --port')
            exit(1)

    if args.command == 'diagnose':
        if args.part == 'pumps':
            run_script(DIR_DIAGNOSTICS / 'diagnostics_pumps.py', port)
        elif args.part == 'stepper':
            run_stepper_diagnostic(args.rotation_deg, port)
            # TODO: change
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
    else: 
        parser.print_help() 
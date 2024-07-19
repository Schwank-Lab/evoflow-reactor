from pathlib import Path 
import glob 
import argparse 

def generate_commands(port: str, dev_mode: bool):
    # copy all python scripts. 
    scripts = glob.glob('pico/*.py')
    scripts = [script for script in scripts if 'main.py' not in script]
    pico_main = "dev_main.py" if dev_mode else "main.py"
    commands = ["rm main.py", f"put pico/main.py /{pico_main}"]
    commands += [f"put {script} /{Path(script).name}" for script in scripts]
    ampy_commands = [f"ampy -p {port} {cmd}" for cmd in commands]
    sh_commands = [f'echo "{cmd}"; {cmd}' for cmd in ampy_commands]
    return '\n'.join(sh_commands)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a reactor and execute commands.')
    parser.add_argument('--pico_port', type=str, help='The port of the Pico W. If not provided, will be inferred automatically.', default=None)
    parser.add_argument('--dev', action='store_true', help='Development mode (main.py is remained to dev_main.py, to avoid auto-start.)')
    args = parser.parse_args()
    port = args.pico_port

    commands = generate_commands(port, dev_mode=args.dev)

    with open('tmp/deploy.sh', 'w') as cmd_file:
        cmd_file.write(commands)
        cmd_path = Path(cmd_file.name)

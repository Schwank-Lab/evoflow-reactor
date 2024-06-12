from pathlib import Path
import json 
import tempfile
import os
import subprocess
from evoflow_db.idec import Reactor
from evoflow_db import idec_engine
from sqlalchemy.orm import Session
import argparse
import glob


def ensure_tmp_dir():
    tmp_dir = tempfile.gettempdir()
    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)
    return tmp_dir

def create_reactor_db_entry(reactor_name):
    reactor = Reactor(name=reactor_name, network_id='0.0.0.0', experiments=[])
    with Session(idec_engine()) as session: 
        session.add(reactor)
        session.commit()
        return reactor.reactor_id

def generate_network_config(reactor_id):
    with open('pico/configs/default-network_config.json', 'r') as f:
        network_config = json.load(f) 
        network_config['reactor_id'] = reactor_id
    return network_config

def get_port():
    raise NotImplementedError()

def generate_commands(network_config: Path, port: str):
    commands = [
        "rmdir /",
        "mkdir /configs",
        "mkdir /logs",
        "mkdir /state",
        "mkdir /tmp",
        f"put {network_config} /configs/network_config.json",
        "put pico/configs/default-reactor_config.json /configs/reactor_config.json",
        "put pico/configs/default-experiment_config.json /configs/experiment_config.json",
        "put pico/configs/default-reactor_state.json /state/reactor_state.json",
        "put libs /libs"
    ] 
    # copy all python scripts. 
    scripts = glob.glob('pico/*.py')
    commands += [f"put {script} /{Path(script).name}" for script in scripts]
    ampy_commands = [f"ampy -p {port} {cmd}" for cmd in commands]
    sh_commands = [f'echo "{cmd}"; {cmd}' for cmd in ampy_commands]
    return '\n'.join(sh_commands)
    # ampy -p {port} put pico/*.py /pyboard

def execute_commands(command_file_path):
    try:
        subprocess.run(['poetry', 'run', 'rshell', '-f', command_file_path], check=True)
        print("Commands executed successfully on Pico W")
    except subprocess.CalledProcessError as e:
        print(f"Failed to execute commands on Pico W: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a reactor and execute commands.')
    parser.add_argument('reactor_name', type=str, help='The name of the reactor to be created')
    parser.add_argument('--reactor_id', type=int, help='The ID of an existing reactor to use', default=None)
    parser.add_argument('--pico_port', type=str, help='The port of the Pico W. If not provided, will be inferred automatically.', default=None)

    args = parser.parse_args()
    if args.reactor_id is None: 
        new_reactor_id = create_reactor_db_entry(args.reactor_name)
        print(f'Reactor create with id {new_reactor_id}')
    else: 
        new_reactor_id = args.reactor_id
        print(f'Using existing reactor with id {new_reactor_id}')

    if args.pico_port is None:
        port = get_port()
        print(f'Detected pico W at port {port}')
    else: 
        port = args.pico_port

    network_config = generate_network_config(reactor_id=new_reactor_id) 
    tmp_dir = ensure_tmp_dir()

    with open('/tmp/network_config.json', 'w') as nw_file:
        json.dump(generate_network_config(new_reactor_id), nw_file)
        nw_path = Path(nw_file.name)

    commands = generate_commands(nw_path, port)

    with open('/tmp/commands.sh', 'w') as cmd_file:
        cmd_file.write(commands)
        cmd_path = Path(cmd_file.name)

    




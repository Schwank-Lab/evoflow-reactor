from pathlib import Path
import json 
import tempfile
import subprocess
from db.idec import Reactor
from db import idec_engine
from sqlalchemy.orm import Session
import argparse

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

def generate_commands(network_config: Path):

    return f"""mkdir /pyboard/configs
mkdir /pyboard/logs
mkdir /pyboard/state
cp {network_config} /pyboard/configs/network_config.json
cp pico/configs/default-reactor_config.json /pyboard/configs/reactor_config.json
cp pico/configs/default-experiment_config.json /pyboard/configs/experiment_config.json
cp pico/configs/default-reactor_state.json /pyboard/state/reactor_state.json
cp pico/*.py /pyboard
"""

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

    args = parser.parse_args()
    if args.reactor_id is None: 
        new_reactor_id = create_reactor_db_entry(args.reactor_name)
        print(f'Reactor create with id {new_reactor_id}')
    else: 
        new_reactor_id = args.reactor_id
        print(f'Using existing reactor with id {new_reactor_id}')
    network_config = generate_network_config(reactor_id=new_reactor_id) 
    
    with open('tmp/network_config.json', 'w') as nw_file:
        json.dump(generate_network_config(new_reactor_id), nw_file)
        nw_path = Path(nw_file.name)

    commands = generate_commands(nw_path)

    with open('tmp/commands.txt', 'w') as cmd_file:
        cmd_file.write(commands)
        cmd_path = Path(cmd_file.name)

    




import hardware_config
from hardware import Hardware, Clock
import pace_controller
from pace_controller import PaceController
from logger import FileLogger, ConsoleLogger, MqttLogger, CompositeLogger
import logger
from network_client import WiFiClient, MqttClient
from state_recorder import MqttStateRecorder, FileStateRecorder
from commands import CommandsDispatcher

import time 
import _thread
import json


""""
Create and start controller 
"""

with open('configs/network_config.json') as f: 
    network_config = json.load(f)
with open('state/reactor_state.json') as f:
    reactor_state = json.load(f)

reactor_id = network_config['mqtt_client_id']
wifi_client = WiFiClient(network_config)
mqtt_client = MqttClient(wifi_client, network_config)

clock = Clock()
console_logger = ConsoleLogger(clock, level=logger.L_INFO)
# TODO: fix mqtt logger before re-enabling it.
# mqtt_logger = MqttLogger(reactor_id, mqtt_client, clock, level=logger.L_INFO) 
file_logger = FileLogger(clock)
local_logger = CompositeLogger([console_logger, file_logger])

thread = lambda fn, *args: _thread.start_new_thread(fn, args)
controller = PaceController(Clock(), thread, logger=local_logger)


with open('configs/experiment_config.json') as f:
    experiment_config = json.load(f)

experiment_id = experiment_config['experiment_id']
reactor_config = hardware_config.load_hardware_config('configs/reactor_config.json')
hardware = Hardware(reactor_config)
controller.init(hardware, reactor_config, experiment_config)

if reactor_state['status'] == 'running':
    local_logger.info('[MAIN] Starting experiment...')
    controller.start()
else:
    local_logger.info('[MAIN] Experiment is idle, reactor not started.')

wifi_client.request_wifi_connection()
mqtt_client.request_mqtt_connection()

# state_recorder = FileStateRecorder(clock, experiment_id, record_every_s = 5*60)
state_recorder = MqttStateRecorder(reactor_id, mqtt_client, local_logger)
commads_dispatcher = CommandsDispatcher(reactor_id, controller, local_logger)
mqtt_client.add_subscriber('commands', commads_dispatcher._process_commands) # TODO: refactor

try: 
    while True:
        if controller.is_running():
            reactor_state = controller.current_state()
            state_recorder.record(reactor_state)
            console_logger.info(json.dumps(reactor_state))
            
        mqtt_client.receive()
        time.sleep(1)

except KeyboardInterrupt:
    print('Aborting the run...')
except Exception as e:
    local_logger.critical('[MAIN] unhandled exception', e)
finally: 
    controller.stop()
    mqtt_client._mqtt_client.disconnect() # TODO: refactor.




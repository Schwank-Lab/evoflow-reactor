import hardware_config
from hardware import Hardware, Clock
from pace_controller import PaceController
from logger import FileLogger, ConsoleLogger, MqttLogger, CompositeLogger
import logger
from network_client import WiFiClient, MqttClient, sync_time
from state_recorder import MqttStateRecorder, FileStateRecorder
from commands import CommandsDispatcher
import utils

import time 
import _thread
import json
import sys 


def init_hardware():
    global hardware, reactor_config
    reactor_config = hardware_config.load_hardware_config('configs/reactor_config.json')
    hardware = Hardware(reactor_config)
    
def init_logger():
    global clock, local_logger, console_logger
    clock = Clock()
    console_logger = ConsoleLogger(clock, level=logger.L_INFO)
    # TODO: fix mqtt logger before re-enabling it.
    # mqtt_logger = MqttLogger(reactor_id, mqtt_client, clock, level=logger.L_INFO) 
    file_logger = FileLogger(clock)
    local_logger = CompositeLogger([console_logger, file_logger])


def start_controller():
    global controller, file_state_recorder
    thread = lambda fn, *args: _thread.start_new_thread(fn, args)
    controller = PaceController(clock, thread, logger=local_logger)

    experiment_config = utils.load_json('configs/experiment_config.json')
    controller.init(hardware, reactor_config, experiment_config)
    
    reactor_state = utils.load_json('state/reactor_state.json')
    local_logger.info('[MAIN] Reactor state:', reactor_state['status'])
    if reactor_state['status'] == 'running':
        controller.start()
    
    file_state_recorder = FileStateRecorder(clock, experiment_config['experiment_id'], record_every_s = 5*60)
    
        
def connect_to_network():
    global mqtt_client, mqtt_state_recorder, commads_dispatcher

    network_config = utils.load_json('configs/network_config.json')

    wifi_client = WiFiClient(network_config)
    wifi_client.request_wifi_connection()
    sync_time(clock, network_config, local_logger)

    mqtt_client = MqttClient(wifi_client, network_config, local_logger)
    mqtt_client.request_mqtt_connection(force_topic_resubscribe=True)

    reactor_id = network_config['reactor_id']
    mqtt_state_recorder = MqttStateRecorder(reactor_id, mqtt_client, local_logger)
    commads_dispatcher = CommandsDispatcher(reactor_id, controller, local_logger)
    mqtt_client.add_subscriber('commands', commads_dispatcher._process_commands) # TODO: refactor
    

def receive_mqtt_commands(): 
    try: 
         mqtt_client.receive()
    except OSError as ex: 
        local_logger.exception('Mqtt Client: Error receiving message', ex)
        mqtt_client.restore_connection()


def run():
     while True:
        if controller.is_running():
            reactor_state = controller.current_state()
            file_state_recorder.record(reactor_state)
            console_logger.info(json.dumps(reactor_state))
            if network_connected: 
                mqtt_state_recorder.record(reactor_state)
            
        if network_connected:
            receive_mqtt_commands()
        time.sleep(1)


try: 
    init_hardware()
    local_logger.info('[MAIN] Hardware initialized.')
except Exception as e:
    pass 
    # sys.exit()

init_logger() # should never fail.

try: 
    start_controller()
    local_logger.info('[MAIN] controller started.')
except Exception as e:
    local_logger.exception('[MAIN] Error starting controller', e)
    # sys.exit()

try:
    network_connected = False 
    connect_to_network()
    network_connected = True
    local_logger.info('[MAIN] Network connected')
except Exception as e:
    local_logger.exception('[MAIN] Error connecting to network', e)
   
try: 
   run()
except KeyboardInterrupt:
    print('Aborting the run...')
except Exception as e:
    local_logger.exception('[MAIN] unhandled exception', e)
finally: 
    controller.stop()
    mqtt_client.disconnect() # TODO: refactor.


import hardware_config
from hardware import Hardware, Clock
import pace_controller
from pace_controller import PaceController
from logger import FileLogger, ConsoleLogger, MqttLogger, CompositeLogger
import logger
from network_client import WiFiClient, MqttClient
from state_recorder import MqttStateRecorder
from commands import Commands

import time 
import _thread
import json


""""
Create and start controller 
"""

EXPERIMENT_CONFIG = 'configs/experiment_config.json'
experiment_config = json.load(open(EXPERIMENT_CONFIG))

network_config = json.load(open('configs/network_config.json'))
wifi_client = WiFiClient(network_config)
mqtt_client = MqttClient(wifi_client, network_config)

clock = Clock()
console_logger = ConsoleLogger(clock, level=logger.L_INFO)
mqtt_logger = MqttLogger(mqtt_client, clock, level=logger.L_DEBUG)
logger = CompositeLogger([console_logger, mqtt_logger])

reactor_config = hardware_config.default_config()
hardware = Hardware(reactor_config)

thread = lambda fn, *args: _thread.start_new_thread(fn, args)
 
controller = PaceController(hardware, reactor_config, experiment_config, Clock(), thread, logger=logger)
# TODO: this shouldn't happen out of the box. Instead look at the state, stored in the flash drive.
controller.start() # TODO: instead, load the last state of the controller.




wifi_client.request_wifi_connection()
time.sleep(1)
mqtt_client.request_mqtt_connection()
time.sleep(1)

state_recorder = MqttStateRecorder(mqtt_client)
try: 
    while True:
        state = controller.current_state()
        state_recorder.record(state)
        time.sleep(1)

except KeyboardInterrupt:
    mqtt_client._mqtt_client.disconnect() # TODO: refactor
    controller.stop()



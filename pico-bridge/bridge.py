from serial_comm import SerialComm
from network_client import MqttClient
from logging import Logger
import json 

from state_recorder import FileExpStateRecorder, FileReactorStateRecorder

class EvoBridge:
    
    def __init__(self, serial: SerialComm, mqtt: MqttClient, logger: Logger):
        self._serial = serial
        self._logger = logger

        self._exp_state_recorder = FileExpStateRecorder()
        self._reactor_state_recorder = FileReactorStateRecorder()
        
    def forward_reactor_state(self, state):
        """ Forwards reactor status from the Pico to the MQTT broker. """
        try: 
            state = json.loads(state)
            self._reactor_state_recorder.record(state)
        except json.JSONDecodeError as e:
            self._logger.critical('Failed to parse reactor state.', e)


    def forward_experiment_state(self, state): 
        """ Forwards experiment status from the Pico to the MQTT broker. """
        try: 
            state = json.loads(state)
            self._exp_state_recorder.record(state)
        except json.JSONDecodeError as e:
            self._logger.critical('Failed to parse experiment state.', e)


    def forward_command(self, cmd): 
        """ Forwards commands from the MQTT broker to the Pico. """
        self._logger.info('Forwarded command to Pico', cmd)
        self._serial.send_message('commands', cmd)
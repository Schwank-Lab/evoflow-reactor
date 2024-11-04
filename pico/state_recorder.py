import json 

from serial_comm import SerialComm
from pace_controller import PaceController

class SerialStateRecorder:
    
    EXP_TOPIC_STATE = 'status/experiment'
    REACTOR_TOPIC_STATE = 'status/reactor'

    STATE_RECORD_INTERVAL = 5 * 1000 # 5 seconds

    def __init__(self, reactor_id, serial: SerialComm, controller: PaceController, topic: str):
        self._reactor_id = reactor_id
        self._serial = serial
        self._topic = topic
        self._controller = controller

    def record(self, state): 
        """ Publish reactor state to the MQTT broker. 

        Note: this method is blocking and should not be called on the same thread as the controller.
        """
        msg = state.copy()
        msg['reactor_id'] = self._reactor_id
        msg = json.dumps(msg)
        self._serial.send_message(self._topic, msg) 
        


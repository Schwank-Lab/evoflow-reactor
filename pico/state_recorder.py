import json 

class MqttStateRecorder:
    
    TOPIC_STATE = 'monitor'

    def __init__(self, reactor_id, mqtt_client):
        self._mqtt_client = mqtt_client
        self._reactor_id = reactor_id

    def record(self, state): 
        # TODO: try to reconnect if not connected 
        msg = json.dumps({
            'reactor_id': self._reactor_id,
            'state': state
        })
        self._mqtt_client.publish(MqttStateRecorder.TOPIC_STATE, msg) 


class FileStateRecorder: 

    def __init__(self): 
        self.state_log = "logs/state_log.csv"
        # Write headers to the state_log file
        # TODO: don't re-create state log every time.
        with open(self.state_log, 'w') as f:
            # f.write(f"# Experiment started at: {self._clock.localtime()}\n")
            f.write('timestamp,inc_od,inc_temp,inc_dilution,lagoon_temp,lagoon_flow_rate\n')

    def _store_state(self, state):
        with open(self.state_log, 'a') as f:
            f.write("{},{},{},{},{},{}\n".format(
                state['timestamp'], state['inc_od'], state['inc_temp'], state['inc_dilution'], 
                state['lagoon_temp'], state['lagoon_flow_rate']))
    


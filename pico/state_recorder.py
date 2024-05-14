import json 

class MqttStateRecorder:
    
    TOPIC_STATE = 'status/experiment'

    def __init__(self, reactor_id, mqtt_client, logger):
        self._mqtt_client = mqtt_client
        self._reactor_id = reactor_id
        self._logger = logger

    def record(self, state): 
        """ Publish reactor state to the MQTT broker. 

        Note: this method is blocking and should not be called on the same thread as the controller.
        """
        msg = state.copy()
        msg['reactor_id'] = self._reactor_id
        msg= json.dumps(msg)
        try: 
            self._mqtt_client.publish(MqttStateRecorder.TOPIC_STATE, msg) 
        except OSError as e: 
            self._logger.info('MqttStateRecorder: failed to publish state to MQTT broker.', e)
            self._mqtt_client.restore_connection()


class FileStateRecorder: 

    def __init__(self, clock, experiment_id, record_every_s=-1): 
        self._clock = clock
        self._record_every_s = record_every_s 
        self.t_last_record = clock.time_since_epoch()
        self.state_log = f"logs/state_log_{experiment_id}.csv"
        # Write headers to the state_log file
        try:
            with open(self.state_log, 'r') as f:
                pass
        except Exception:
            with open(self.state_log, 'w') as f:
                f.write('timestamp,inc_od,inc_temp,inc_dilution,lagoon_temp,lagoon_flow_rate\n')

            
    def record(self, state):
        if state is None: 
            return 
        if self._clock.time_since_epoch() - self.t_last_record < self._record_every_s:
            # skip recording
            return
        self.t_last_record = self._clock.time_since_epoch()
        with open(self.state_log, 'a') as f:
            f.write("{},{},{},{},{},{}\n".format(
                state['timestamp'], state['inc_od'], state['inc_temp'], state['inc_tot_dil'], 
                state['lagoon_temp'], state['lagoon_flow_rate']))
    


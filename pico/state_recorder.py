import json 
from logger import FileLogger

class MqttStateRecorder:
    
    EXP_TOPIC_STATE = 'status/experiment'
    REACTOR_TOPIC_STATE = 'status/reactor'

    def __init__(self, reactor_id, mqtt_client, logger, topic):
        self._mqtt_client = mqtt_client
        self._reactor_id = reactor_id
        self._logger = logger
        self._topic = topic

    def record(self, state): 
        """ Publish reactor state to the MQTT broker. 

        Note: this method is blocking and should not be called on the same thread as the controller.
        """
        msg = state.copy()
        msg['reactor_id'] = self._reactor_id
        msg= json.dumps(msg)
        try: 
            self._mqtt_client.publish(self._topic, msg) 
        except OSError as e: 
            self._logger.info('MqttStateRecorder: failed to publish state to MQTT broker.', self._topic, e)
            self._mqtt_client.restore_connection()


class FileExpStateRecorder(FileLogger): 

    def __init__(self, clock, experiment_id, record_every_s=-1): 
        super().__init__(clock, prefix=f'exp-state-{experiment_id}')
        self._clock = clock
        self._record_every_s = record_every_s 
        self.t_last_record = clock.time_since_epoch()
        self._record_log_message('timestamp,inc_od,inc_temp,inc_dilution,lagoon_temp,lagoon_flow_rate')

            
    def record(self, state):
        if state is None: 
            return 
        if self._clock.time_since_epoch() - self.t_last_record < self._record_every_s:
            # skip recording
            return
        self.t_last_record = self._clock.time_since_epoch()
        state_str = "{},{},{},{},{},{}\n".format(
            state['timestamp'], state['inc_od'], state['inc_temp'], state['inc_tot_dil'], 
            state['lagoon_temp'], state['lagoon_flow_rate'])
        self._record_log_message(state_str)

class FileReactorStateRecorder(FileLogger): 

    def __init__(self, clock, record_every_s=-1): 
        super().__init__(clock, prefix=f'reactor-state')
        self._clock = clock
        self._record_every_s = record_every_s 
        self.t_last_record = clock.time_since_epoch()
        self._record_log_message('free_memory,used_memory,free_space,used_space')

            
    def record(self, state):
        if state is None: 
            return 
        if self._clock.time_since_epoch() - self.t_last_record < self._record_every_s:
            # skip recording
            return
        self.t_last_record = self._clock.time_since_epoch()
        state_str = "{},{},{}\n".format(
            state['free_memory'], state['used_memory'], state['free_space'], state['used_space'])
        self._record_log_message(state_str)

    


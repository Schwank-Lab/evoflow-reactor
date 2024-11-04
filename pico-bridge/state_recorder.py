import json 
from datetime import datetime


class FileExpStateRecorder: 

    def __init__(self, record_every_s=-1, file_path='exp_state_log.txt'): 
        self._record_every_s = record_every_s 
        self.t_last_record = datetime.now().timestamp()
        self.file_path = file_path
        self.file = open(self.file_path, 'w')
        self.file.write('timestamp,reactor_id,inc_left_od,inc_left_temp,inc_left_dilution,inc_right_od,inc_right_temp,inc_right_dilution,lagoon_temp,lagoon_flow_rate\n')

    def __del__(self):
        self.file.close()
            
    def record(self, state):
        if state is None: 
            return 
        current_time = datetime.now().timestamp()
        if current_time - self.t_last_record < self._record_every_s:
            # skip recording
            return
        self.t_last_record = current_time
        timestamp = datetime.now().isoformat()
        state_str = "{},{},{},{},{},{},{},{},{},{}\n".format(
            timestamp, state['reactor_id'], state['inc_left_od'], state['inc_left_temp'], state['inc_left_dilution'], 
            state['inc_right_od'], state['inc_right_temp'], state['inc_right_dilution'], 
            state['lagoon_temp'], state['lagoon_flow_rate'])
        self.file.write(state_str)
        self.file.flush()


class FileReactorStateRecorder: 

    def __init__(self, record_every_s=-1, file_path='reactor_state_log.txt'): 
        self._record_every_s = record_every_s 
        self.t_last_record = datetime.now().timestamp()
        self.file_path = file_path
        self.file = open(self.file_path, 'w')
        self.file.write('timestamp,reactor_id,free_memory,used_memory\n')

    def __del__(self):
        self.file.close()
            
    def record(self, state: dict):
        if state is None: 
            return 
        current_time = datetime.now().timestamp()
        if current_time - self.t_last_record < self._record_every_s:
            # skip recording
            return
        self.t_last_record = current_time
        timestamp = datetime.now().isoformat()
        state_str = "{},{},{},{}\n".format(
            timestamp, state['reactor_id'], state['free_memory'], state['used_memory'])
        self.file.write(state_str)
        self.file.flush()

    


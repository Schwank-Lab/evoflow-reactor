import json 
import time 

import hardware_config
from hardware import Hardware

class CommandsDispatcher:

    def __init__(self, reactor_id, pace_controller, logger): 
        self._reactor_id = reactor_id
        self._pace_controller = pace_controller
        self._logger = logger
        
    def _recreate_pace_controller(self):
        with open('configs/experiment_config.json') as f:
            experiment_config = json.load(f)

        reactor_config = hardware_config.load_hardware_config('configs/reactor_config.json')
        hardware = Hardware(reactor_config) 
        self._pace_controller.stop()
        self._pace_controller.init(hardware, reactor_config, experiment_config)
        

    def _stop_controller(self): 
        with open('state/reactor_state.json', 'w') as f:
                json.dump({'status': 'idle'}, f)
        self._pace_controller.stop()

    def _start_controller(self): 
        with open('state/reactor_state.json', 'w') as f:
                json.dump({'status': 'running'}, f)
        self._pace_controller.start()
        
    def _process_commands(self, msg):
        self._logger.info('CommandDispatcher: received message', msg)
        msg = json.loads(msg)
        if msg['reactor_id'] != str(self._reactor_id):
            self._logger.info('CommandDispatche: ignore message, wrong reactor id')
            return 
        cmd = msg['command']
        self._logger.info('CommandDispatcher: received command: ', cmd)
        if cmd == 'start':
            self._start_controller()
        elif cmd == 'stop' or cmd == 'pause':
            self._stop_controller()
        elif cmd == 'new_experiment' or cmd == 'update_experiment':
            self._logger.info('Command Dispatcher: udpating experiment config')
            msg['experiment_config']['experiment_id'] = int(msg['experiment_id'])
            self._logger.info(json.dumps(msg['experiment_config']))
            with open('configs/experiment_config.json', 'w') as f:
                 json.dump(msg['experiment_config'], f)
            self._recreate_pace_controller()
            time.sleep(2) # give thread some time to finish.
            self._start_controller()
        elif cmd == 'update_reactor_config': 
            with open('configs/reactor_config.json', 'w') as f:
                 json.dump(msg['reactor_config'], f)
            self._recreate_pace_controller()
        elif cmd == 'stepper_forward': 
            self._stop_controller()
            time.sleep(2) # give thread some time to finish.
            self._pace_controller.reset_stepper_forward()
        elif cmd == 'stepper_reverse': 
            self._stop_controller()
            time.sleep(2)
            self._pace_controller.reset_stepper_reverse()
        elif cmd == 'stepper_stop':
            self._stop_controller()
            # controller has to be resarted manually.
        else:
            self._logger.critical('CommandDispatcher: unknown command', cmd)




    
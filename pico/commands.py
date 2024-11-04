import json 
import time 

import hardware_config
from hardware import Hardware
from pace_controller import PaceController
from logger import Logger

class CommandsDispatcher:

    def __init__(self, reactor_id, pace_controller: PaceController, logger: Logger): 
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
    
    def process_command(self, msg):
        self._logger.info('CommandDispatcher: received message', msg)
        msg = json.loads(msg)
        if msg['reactor_id'] != str(self._reactor_id):
            self._logger.info('CommandDispatche: ignore message, wrong reactor id')
            return 
        cmd = msg['command']
        self._logger.info('CommandDispatcher: received command: ', cmd)
        if cmd == 'start':
            self._pace_controller.stop()
            self._pace_controller.start()
        elif cmd == 'stop' or cmd == 'pause':
            self._pace_controller.stop()
        elif cmd == 'stepper_forward':
            vol_ml = msg['stepper_volume'] 
            self._pace_controller.stop()
            self._pace_controller.reset_stepper_forward(vol_ml)
        elif cmd == 'stepper_reverse': 
            vol_ml = msg['stepper_volume']
            self._pace_controller.stop()
            self._pace_controller.reset_stepper_reverse(vol_ml)
        elif cmd == 'stepper_stop':
            self._pace_controller.stop()
            # controller has to be restarted manually.
        elif cmd == 'new_experiment' or cmd == 'update_experiment':
            self._logger.info('Command Dispatcher: udpating experiment config')
            msg['experiment_config']['experiment_id'] = int(msg['experiment_id'])
            self._logger.info(json.dumps(msg['experiment_config']))
            with open('configs/experiment_config.json', 'w') as f:
                 json.dump(msg['experiment_config'], f)
            self._recreate_pace_controller()
            self._pace_controller.start()
        elif cmd == 'update_reactor_config': 
            with open('configs/reactor_config.json', 'w') as f:
                 json.dump(msg['reactor_config'], f)
            self._recreate_pace_controller()
            self._pace_controller.start()
        else:
            self._logger.critical('CommandDispatcher: unknown command', cmd)
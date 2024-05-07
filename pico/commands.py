import json 
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
        self._pace_controller.init(hardware, reactor_config, experiment_config)
        
    def _process_commands(self, msg):
        self._logger.debug('CommandDispatcher: received message', msg)
        msg = json.loads(msg)
        if msg['reactor_id'] != self._reactor_id:
            self._logger.debug('CommandDispatche: ignore message, wrong reactor id')
            return 
        cmd = msg['command']
        self._logger.info('CommandDispatcher: received command: ', cmd)
        if cmd == 'start':
            self._pace_controller.start()
            with open('state_reactor_state.json', 'w') as f:
                json.dump({'status': 'running'}, f)
        elif cmd == 'stop' or cmd == 'pause':
            with open('state/reactor_state.json', 'w') as f:
                json.dump({'status': 'idle'}, f)
            self._pace_controller.stop()
        elif cmd == 'new_experiment' or cmd == 'update_experiment_config':
            with open('configs/experiment_config.json', 'w') as f:
                 json.dump(msg['experiment_config'], f)
            with open('state/reactor_state.json', 'w') as f:
                json.dump({'status': 'running', 'experiment_id': msg['experiment_id']}, f)
            self._recreate_pace_controller()
        elif cmd == 'update_reactor_config': 
            with open('configs/reactor_config.json', 'w') as f:
                 json.dump(msg['reactor_config'], f)
            self._recreate_pace_controller()
        else:
            self._logger.error('CommandDispatcher: unknown command', cmd)




    
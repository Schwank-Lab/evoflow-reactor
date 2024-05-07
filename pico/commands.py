import json 

class Commands:

    def __init__(self, reactor_id, pace_controller, logger): 
        self._reactor_id = reactor_id
        self._pace_controller = pace_controller
        self._logger = logger
        
    def _process_commands(self, msg):
        msg = json.loads(msg)
        if msg['reactor_id'] != self._reactor_id:
            return 
        cmd = msg['command']
        if cmd == 'start':
            self._pace_controller.start()
        elif cmd == 'stop':
            self._pace_controller.stop()
        elif cmd == 'pause': 
            self._pace_controller.stop()


    

class PaceServer: 

    def __init__(self, pace_ctl):
        self._pace_ctl = pace_ctl
        
    def handle_request(self, request, server):
        if request == 'new_experiment':
            self.new_experiment(server)
        elif request == 'start':
            self.start(server)
        elif request == 'stop':
            self._pace_ctl.stop()
            server.response_ok()
        elif request == 'experiment_info':
            server.response_ok(self._pace_ctl.experiment_info())
        elif request == 'current_state':
            self.current_state(server)
        elif request == 'load_state_history':
            server.response_stream(self._pace_ctl.load_state_history)
        else:
            server.response_error('unknown request: ' + request)

    def new_experiment(self, server):
        try:
            self._pace_ctl.new_experiment()
            return server.response_ok()
        except Exception as e:
            return server.response_error(e.message)
            
    def start(self, server):
        try:
            self._pace_ctl.start() # TODO: this should happen off the main thread. 
            return server.response_ok()
        except Exception as e:
            return server.response_error(e.message)
    
    def current_state(self, server):
        try: 
            return server.response_ok(self._pace_ctl.current_state())
        except Exception as e:
            return server.response_error(e.message)

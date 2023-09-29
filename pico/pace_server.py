def response_ok(data=None):
    return {
        'status': 'ok',
        'data': data,
    }

def response_error(message):
    return {
        'status': 'error',
        'message': message,
    }

class PaceServer: 

    def __init__(self, pace_ctl):
        self._pace_ctl = pace_ctl
        
    def handle_request(self, request):
        if request == 'start':
            self._pace_ctl.start()
            return response_ok()
        elif request == 'stop':
            self._pace_ctl.stop()
            return response_ok()
        elif request == 'current_state':
            return response_ok(self._pace_ctl.current_state())
        else:
            return response_error('unknown request: ' + request)
    

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
import json 
import threading
import csv
import io


from pace_controller import PaceController, s, ms
from pace_server import PaceServer
import time 

class FakePin:
    def __init__(self, name):
        self._name = name
    
    def on(self):
        print(self._name, "on")
    
    def off(self):
        print(self._name, "off")


class FakeSensor:

    def __init__(self, val):
        self._val = val

    def read(self):
        return self._val


class Clock:

    def __init__(self):
        self._start = s(time.time()) 
    
    def time_ms(self):
        """ Time in milliseconds since start"""
        return s(time.time()) - self._start
    
    def time_since_epoch(self):
        """ Time in seconds since epoch"""
        return int(time.time())
    
    def set_start_time(self, start):
        """ Set start time in seconds since epoch"""
        self._start = s(start)

    def sleep_ms(self, ms):
        time.sleep(ms/1000)
    
class FakeHardware:

    inc_led = FakePin("inc_led")
    inc_od_sensor = FakeSensor(10)
    temp_sensor_inc = FakeSensor(36)
    heater_inc = FakePin("inc_heater")
    stirrer_inc = FakePin("stirrer_inc")

    temp_sensor_lagoon = FakeSensor(36)
    heater_lagoon = FakePin("heater_lagoon")
    stirrer_lagoon = FakePin("stirrer_lagoon")

    pump_medium_to_incubator = FakePin("pump_medium_to_incubator")
    pump_incubator_to_waste = FakePin("pump_incubator_to_waste")    
    pump_incubator_to_lagoon = FakePin("pump_incubator_to_lagoon")
    pump_lagoon_to_waste = FakePin("pump_lagoon_to_waste")

class WebServer(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(404)
            return

        query_components = parse_qs(urlparse(self.path).query)
        command = query_components.get("command", [None])[0]
        print('WebServer#do_GET', 'Command received: ', command)
        pace_server.handle_request(command, self)
        
    def response_json(self, data):
        print(data)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        json_str = json.dumps(data)
        self.wfile.write(json_str.encode('utf-8'))

    def response_stream(self, stream):
        self.send_response(200)
        self.send_header('Content-Type', 'text/csv')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Disposition', 'attachment; filename=data.csv')
        self.end_headers()

        for row in stream(): 
            self.wfile.write(row.encode('utf-8'))
            
    def response_ok(self, data=None):
        self.response_json( {
            'status': 'ok',
            'data': data,
        })

    def response_error(self, message):
        self.response_json( {
            'status': 'error',
            'message': message,
        })


if __name__ == '__main__':
    hardware = FakeHardware()
    config = {
            'target_od': 5, 
            'lagoon_flow_rate': 3, # v/h
            'record_state_interval_ms': 1000,
            'store_state_interval_ms': 3000}
    thread = lambda fn, *args: threading.Thread(target=fn, args=args).start()
    controller = PaceController(hardware, config, Clock(), thread)
    controller.new_experiment()
    controller.start()
    # pace_server = PaceServer(controller)

    # httpd = HTTPServer(('localhost', 8000), WebServer)
    # httpd.serve_forever()

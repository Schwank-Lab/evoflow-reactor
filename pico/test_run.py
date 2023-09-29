
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
import json 
import threading


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
        return s(time.time()) - self._start
    
    def sleep_ms(self, ms):
        time.sleep(ms/1000)
    
class FakeHardware: 

    inc_led = FakePin("inc_led")
    inc_od_sensor = FakeSensor(10)
    inc_temp_sensor = FakeSensor(36)
    inc_heater = FakePin("inc_heater")
    inc_medium_pump = FakePin("inc_medium_pump")    
    inc_waste_pump = FakePin("inc_waste_pump")

class WebServer(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(404)
            return

        query_components = parse_qs(urlparse(self.path).query)
        command = query_components.get("command", [None])[0]
        print('WebServer#do_GET', 'Command received: ', command)
        response = pace_server.handle_request(command)
        print(response)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        json_str = json.dumps(response)
        self.wfile.write(json_str.encode('utf-8'))

if __name__ == '__main__':
    hardware = FakeHardware()
    config = {'target_od': 5}
    controller = PaceController(hardware, config, Clock())
    threading.Thread(target=controller.start).start()

    pace_server = PaceServer(controller)

    httpd = HTTPServer(('localhost', 8000), WebServer)
    httpd.serve_forever()


from urllib.parse import parse_qs, urlparse
import json 
import threading
import csv
import io


import hardware_config
import pace_controller
from pace_controller import PaceController, s_to_ms, ms
from logger import FileLogger, ConsoleLogger, L_DEBUG
import time 

class FakePin:
    def __init__(self, name, value=0):
        self._name = name
        self._value = value
    
    def on(self):
        self._value = 1
        print(self._name, "on")
    
    def off(self):
        self._value = 0
        print(self._name, "off")

    def value(self): 
        return self._value

class FakeSensor:

    def __init__(self, val):
        self._val = val

    def read(self):
        return self._val
    
    def read_od(self):
        return self._val

class FakeStepper: 

    def __init__(self, name): 
        self._name = name
    
    def step(self):
        print(self._name, "step")

    def step_forward(self): 
        print(self._name, "step forward")

    def step_reverse(self):
        print(self._name, "step reverse")

class FakePump:

    def __init__(self, name):
        self._name = name

    def set_speed(self, speed_frac):
        print(self._name, "speed set to", speed_frac)

    def on(self): 
        print(self._name, "on")

    def off(self):
        print(self._name, "off")

class FakeStirrer:

    def __init__(self, name):
        self._name = name

    def set_speed(self, speed_frac):
        print(self._name, "speed set to", speed_frac)


class Clock:

    def __init__(self):
        self._start = s_to_ms(time.time()) 
    
    def ticks_ms(self):
        """ Time in milliseconds since start"""
        return s_to_ms(time.time()) - self._start
    
    def time_since_epoch(self):
        """ Time in seconds since epoch"""
        return int(time.time())
    
    def set_start_time(self, start):
        """ Set start time in seconds since epoch"""
        self._start = s_to_ms(start)

    def sleep_ms(self, ms):
        time.sleep(ms/1000)

    def localtime(self):
        return  time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
class FakeHardware:

    def __init__(self): 
        self.inc_led = FakePin("inc_led")
        self.inc_od_sensor = FakeSensor(10)
        self.temp_sensor_inc = FakeSensor(36)
        self.heater_inc = FakePin("inc_heater")
        self.stirrer_inc = FakeStirrer("stirrer_inc")

        self.temp_sensor_lagoon = FakeSensor(36)
        self.heater_lagoon = FakePin("heater_lagoon")
        self.stirrer_lagoon = FakeStirrer("stirrer_lagoon")

        self.pump_medium_to_incubator = FakePump("pump_medium_to_incubator")
        self.pump_incubator_to_waste = FakePump("pump_incubator_to_waste")    
        self.pump_incubator_to_lagoon = FakePump("pump_incubator_to_lagoon")
        self.pump_lagoon_to_waste = FakePump("pump_lagoon_to_waste")
        self.stepper_arabinose_to_lagoon = FakeStepper("stepper_bacteria_to_lagoon")

        self.button_left = FakePin("button_arabinose_stepper_forward", value=1)
        self.button_right = FakePin("button_arabinose_stepper_reverse", value=1)


if __name__ == '__main__':
    hardware = FakeHardware()
    experiment_config = {
            'experiment_id': 'test_experiment',
            'target_od': 0.8, 
            'lagoon_flow_rate': 3, # v/h
            'lagoon_volume': 7, # ml
            'arabinose_stock_concentration': 2000, # mM
            'arabinose_target_concentration': 40, # mM
            }
    thread = lambda fn, *args: threading.Thread(target=fn, args=args).start()
    clk = Clock()
    controller = PaceController(clk, thread, ConsoleLogger(clk, level=L_DEBUG))
    controller.init(hardware, hardware_config.default_config(), experiment_config)

    controller.start()
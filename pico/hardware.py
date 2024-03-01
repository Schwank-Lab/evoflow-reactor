from machine import ADC, Pin, Timer, PWM
import onewire
import ds18x20
import time 

class Clock:

    def __init__(self):
        self._start = time.ticks_ms()
    
    def time_ms(self):
        """ Time in milliseconds since start"""
        return time.ticks_ms() - self._start
    
    def time_since_epoch(self):
        """ Time in seconds since epoch"""
        return int(time.ticks_ms()) # TODO: change
    
    def set_start_time(self, start):
        """ Set start time in milliseconds"""
        self._start = start

    def sleep_ms(self, ms):
        time.sleep_ms(ms)


class ODSensor:

    def __init__(self, adc): 
        self._adc = adc

    def mapReverse(x): ## Map values to reverse: from a,b to c,d (since OD measurement is inverse)
        #y=(x-a)/(b-a)*(d-c)+c
        y=(x-1)/(65535-1)*(1-65535)+65535
        return y

    def read(self):
        return ODSensor.mapReverse(self._adc.read_u16())
        
class TempSensor: 

    def __init__(self, pin):
        self._sensor = ds18x20.DS18X20(onewire.OneWire(pin))
        self._device = self._sensor.scan()

    def read(self):
        self._sensor.convert_temp()
        return self._sensor.read_temp(self._device[0])


class Stirrer: 

    Stir_DutyCycle = 50 ## 50% duty cycle

    def __init__(self, pin): 
        self._motor = PWM(pin) ## use PWM to set speed of stirrer
        self._motor.freq(1000) ## test a few, to see which frequency works best with fan. 500hz works on Duet2 boards. 

    def on(self):
        self._motor.duty_u16(int((Stirrer.Stir_DutyCycle/100)*65_535)) ## write duty cycle to Pin.

    def off(self):
        self._motor.duty_u16(0)


class Hardware:

    inc_led = Pin(10, Pin.OUT, value=0)
    inc_od_sensor = ODSensor(ADC(Pin(27, Pin.IN)))
    temp_sensor_inc = TempSensor(Pin(16, Pin.IN))
    heater_inc = Pin(9, Pin.OUT, value=0)
    stirrer_inc = Stirrer(Pin(21, Pin.OUT))

    temp_sensor_lagoon = TempSensor(Pin(17, Pin.IN))
    heater_lagoon = Pin(8, Pin.OUT, value=0)
    stirrer_lagoon = Stirrer(Pin(20, Pin.OUT))

    pump_medium_to_incubator = Pin(6, Pin.OUT, value=0)
    pump_incubator_to_waste = Pin(7, Pin.OUT, value=0)
    pump_incubator_to_lagoon = Pin(26, Pin.OUT, value=0)
    pump_lagoon_to_waste = Pin(22, Pin.OUT, value=0) 

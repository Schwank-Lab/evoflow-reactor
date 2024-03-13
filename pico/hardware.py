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
        return time.time()

    def  set_start_time(self, start):
        """ Set start time in milliseconds"""
        self._start = start

    def sleep_ms(self, ms):
        time.sleep_ms(int(ms))

    def localtime(self):
        """Get local time as a formatted string.

        Returns:
            str: Formatted local time in the format YYYY-MM-DD_HH-MM-SS.
        """
        # Convert epoch time to a local time tuple
        localtime_tuple = time.localtime()
        # Format the local time as a string
        return "{:04d}-{:02d}-{:02d}_{:02d}-{:02d}-{:02d}".format(*localtime_tuple[0:6])


class ODSensor:

    def __init__(self, adc): 
        self._adc = adc

    def mapReverse(x): ## Map values to reverse: from a,b to c,d (since OD measurement is inverse)
        return 65536 - x

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
    
    FULL_SPEED = 65_535
    
    def __init__(self, pin): 
        self._motor = PWM(pin) ## use PWM to set speed of stirrer
        self._motor.freq(1000) ## test a few, to see which frequency works best with fan. 500hz works on Duet2 boards. 

    def on(self):
        self.set_speed(speed_frac=1.0)

    def set_speed(self, speed_frac):
        # print('setting speed', top_speed_frac)
        self._motor.duty_u16(int(speed_frac * Stirrer.FULL_SPEED))
                  
    def off(self):
        self._motor.duty_u16(0)

class Pump:
    
    FULL_SPEED = 65_535
    
    def __init__(self, pin):
        self._motor = PWM(pin) ## use PWM to set speed of stirrer
        self._motor.freq(1000) ## test a few, to see which frequency works best with fan. 500hz works on Duet2 boards. 

    def on(self):
        self.set_speed(speed_frac=1.0)
    
    def set_speed(self, speed_frac):
        self._motor.duty_u16(int(Pump.FULL_SPEED*speed_frac))
    
    def off(self):
        self._motor.duty_u16(0)
    

class StepperMotor:
    
    FULL_STEP_SEQUENCE = [ ## this are 4 steps
            [1,0,0,0],
            [0,1,0,0],
            [0,0,1,0],
            [0,0,0,1]
    ]
    
    def __init__(self, pins):
        self._stepper = pins 

    def step(self):
        self.step_forward()

    def step_forward(self):
        self._step(StepperMotor.FULL_STEP_SEQUENCE)

    def step_reverse(self): 
        self._step(StepperMotor.FULL_STEP_SEQUENCE[::-1])
    
    def _step(self, step_seq):
        for step in step_seq:
            for i in range(len(self._stepper)):
                self._stepper[i].value(step[i])
                time.sleep_ms(1)


class Hardware:

    inc_led = Pin(10, Pin.OUT, value=0)
    inc_od_sensor = ODSensor(ADC(Pin(27, Pin.IN)))
    temp_sensor_inc = TempSensor(Pin(16, Pin.IN))
    heater_inc = Pin(9, Pin.OUT, value=0)
    stirrer_inc = Stirrer(Pin(21, Pin.OUT))

    temp_sensor_lagoon = TempSensor(Pin(17, Pin.IN))
    heater_lagoon = Pin(8, Pin.OUT, value=0)
    stirrer_lagoon = Stirrer(Pin(20, Pin.OUT))

    pump_medium_to_incubator = Pump(Pin(6, Pin.OUT, value=0))
    pump_incubator_to_waste = Pump(Pin(7, Pin.OUT, value=0))
    pump_incubator_to_lagoon = Pump(Pin(26, Pin.OUT, value=0))
    pump_lagoon_to_waste = Pump(Pin(22, Pin.OUT, value=0)) 

    stepper_arabinose_to_lagoon = StepperMotor([
                                        Pin(12, Pin.OUT), #IN1
                                        Pin(13, Pin.OUT), #IN2
                                        Pin(14, Pin.OUT), #IN3
                                        Pin(15, Pin.OUT) #IN4
                                    ])
    
    button_left = Pin(18, Pin.IN, Pin.PULL_UP) 
    button_right = Pin(19, Pin.IN, Pin.PULL_UP)




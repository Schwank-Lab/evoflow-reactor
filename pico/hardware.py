from hardware_config import HardwareConfig

from machine import ADC, Pin, Timer, PWM
import onewire
import ds18x20
import time 

class Clock:

    def __init__(self):
        pass
        
    def ticks_ms(self):
        """ Time in milliseconds since start"""
        return time.ticks_ms()
    
    def time_since_epoch(self):
        """ Time in seconds since epoch"""
        return time.time()

    def set_start_time(self, start):
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
        localtime_tuple = time.localtime(self.time_since_epoch())
        # Format the local time as a string
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*localtime_tuple[0:6])
    
    


class ODSensor:

    SENSOR_MAX_VAL = 1 << 16
    
    def __init__(self, adc, f_od_convert): 
        self._adc = adc
        self._f_od_convert = f_od_convert

    def read_od(self): 
        return self._f_od_convert(self.read_raw())
      
    def read_raw(self):
        return ODSensor.SENSOR_MAX_VAL -  self._adc.read_u16() # invert the readding
    
        
class TempSensor: 

    def __init__(self, pin, f_temp_convert):
        self._driver = ds18x20.DS18X20(onewire.OneWire(pin))
        self._sensor = self._driver.scan()
        if len(self._sensor) == 0:
            raise ValueError(f'No sensor found on the pin {pin}')
        elif len(self._sensor) > 1:
            raise ValueError(f'Multiple sensors found on the pin {pin}')
        self._sensor = self._sensor[0]
        self._f_temp_convert = f_temp_convert

    def read_raw(self): 
        self._driver.convert_temp() 
        # Note: it's recommended for the conversion to finish before reading the temperature
        # In our case, the first measurement might be screwed up. 
        return self._driver.read_temp(self._sensor)
    
    def convert_raw(self, raw):
        return self._f_temp_convert(raw)
    
    def read(self):
        return self.convert_raw(self.read_raw())
        

class Stirrer: 

    Stir_DutyCycle = 50 ## 50% duty cycle
    
    FULL_SPEED = 65_535
    
    def __init__(self, pin): 
        self._motor = PWM(pin) ## use PWM to set speed of stirrer
        self._motor.freq(200) ## test a few, to see which frequency works best with fan. 500hz works on Duet2 boards. 

    def on(self):
        self.set_speed(speed_frac=1.0)

    def set_speed(self, speed_frac):
        # print('setting speed', top_speed_frac)
        self._motor.duty_u16(int(speed_frac * Stirrer.FULL_SPEED))
                  
    def off(self):
        self._motor.duty_u16(0)

class Pump:
    
    FULL_SPEED = 65_535
    
    MODE_PWM = 0
    MODE_PIN = 1
     
    def __init__(self, pin, mode=0, speed=1.0):
        self._mode = mode
        if mode == Pump.MODE_PIN:
            if speed != 1.0: 
                raise ValueError('Cannot set speed for pump in PIN mode.')
            self._pin = pin
        elif mode == Pump.MODE_PWM:
            self._motor = PWM(pin) ## use PWM to set speed of stirrer
            self._motor.freq(1000) ## test a few, to see which frequency works best with fan. 500hz works on Duet2 boards. 
            self._speed = speed
        else:
            raise ValueError('Uknown pump mode', mode)
        
    def on(self):
        if self._mode == Pump.MODE_PWM:
            self.set_speed(speed_frac=self._speed)
        else:
            self._pin.value(1)
    
    def set_speed(self, speed_frac):
        if self._mode != Pump.MODE_PWM:
            raise ValueError('Cannot regulate pump speed unless in PWM mode.')
        self._motor.duty_u16(int(Pump.FULL_SPEED*speed_frac))
    
    def off(self):
        if self._mode == Pump.MODE_PWM:
            self._motor.duty_u16(0)
        else:
            self._pin.value(0)


class TMC2208Stepper: 

    MODE_PWM = 0
    MODE_STEP = 1 

    def __init__(self, step_pin, dir_pin, forward_direction=1, mode=MODE_PWM): 
        self._step_pin = step_pin 
        self._mode = mode 
        self._dir_pin = dir_pin
        self.set_direction(forward_direction)
        if mode == TMC2208Stepper.MODE_PWM: 
            self._motor = PWM(step_pin)
            self._motor.freq(2000) 

    def set_direction(self, forward_direction):
        fw_dr = 1 if forward_direction == 1 else 0
        self._dir_pin.value(fw_dr)
        
    def on(self): 
        if self._mode != TMC2208Stepper.MODE_PWM:
            raise ValueError('Cannot turn pump on unless in PWM mode.')
        self._motor.duty_u16(65_535 // 2)

    def step(self):
        if self._mode != TMC2208Stepper.MODE_STEP:
            raise ValueError('Cannot step pump in STEP mode.')
        self._step_pin.on()
        time.sleep_ms(1)
        self._step_pin.off()

    def off(self):
        if self._mode != TMC2208Stepper.MODE_PWM:
            raise ValueError('Cannot turn pump off unless in PWM mode.')
        self._motor.duty_u16(0)


class StepperMotor:
    
    FULL_STEP_SEQUENCE = [ ## this are 4 steps
            [1,1,0,0],
            [0,1,1,0],
            [0,0,1,1],
            [1,0,0,1] # TODO: this is very ugly.
    ]
    
    def __init__(self, pins, forward_direction=1):
        self._stepper = pins 
        self.set_direction(forward_direction)

    def set_direction(self, forward_direction):
        self._step_seq = StepperMotor.FULL_STEP_SEQUENCE if forward_direction == 1 else StepperMotor.FULL_STEP_SEQUENCE[::-1]

    def step(self):
        self.step_forward()

    def step_forward(self):
        self._step(self._step_seq)

    def step_reverse(self): 
        self._step(self._step_seq[::-1])
    
    def _step(self, step_seq):
        for step in step_seq:
            for i in range(len(self._stepper)):
                self._stepper[i].value(step[i])
                time.sleep_ms(1)


class Hardware:

    def __init__(self, config: HardwareConfig): 

        # left incubator

        self.inc_left_led = Pin(2, Pin.OUT, value=0)
        self.inc_left_od_sensor = ODSensor(ADC(Pin(27, Pin.IN)), config.incubator_od_convert)
        self.inc_left_temp_sensor = TempSensor(Pin(22, Pin.IN), config.incubator_temp_convert)
        self.inc_left_heater = Pin(7, Pin.OUT, value=0)
        self.inc_left_stirrer = Stirrer(Pin(0, Pin.OUT))

        # right incubator

        self.inc_right_led = Pin(3,  Pin.OUT, value=0)
        self.inc_right_od_sensor = ODSensor(ADC(Pin(28, Pin.IN)), config.incubator_od_convert)
        self.inc_right_temp_sensor = TempSensor(Pin(16, Pin.IN), config.incubator_temp_convert)
        self.inc_right_heater = Pin(15, Pin.OUT, value=0)
        self.inc_right_stirrer = Stirrer(Pin(6, Pin.OUT))

        # lagoon 

        self.temp_sensor_lagoon = TempSensor(Pin(26, Pin.IN), config.lagoon_temp_convert)
        self.heater_lagoon = Pin(14, Pin.OUT, value=0)
        self.stirrer_lagoon = Stirrer(Pin(1, Pin.OUT))

        # pumps 

        self.pump_medium_to_inc_left = Pump(Pin(18, Pin.OUT, value=0), speed=config.pump_medium_to_incubator_speed_frac)
        self.pump_inc_left_to_waste = Pump(Pin(17, Pin.OUT, value=0), mode=Pump.MODE_PIN)
        self.pump_inc_left_to_lagoon = Pump(Pin(20, Pin.OUT, value=0), speed=config.pump_incubator_to_lagoon_speed_frac)
        self.pump_medium_to_inc_right = Pump(Pin(21, Pin.OUT, value=0), speed=config.pump_medium_to_incubator_speed_frac)
        self.stepper_front_left = TMC2208Stepper(step_pin=Pin(12, Pin.OUT, value=0), dir_pin=Pin(11, Pin.OUT, value=0))
        self.stepper_front_right = TMC2208Stepper(step_pin=Pin(8, Pin.OUT, value=0), dir_pin=Pin(9, Pin.OUT, value=0))
        #self.pump_incubator_to_lagoon = TMC2208Stepper(step_pin=Pin(12, Pin.OUT, value=0), dir_pin=Pin(11, Pin.OUT, value=0))
        #self.pump_incubator_to_lagoon = TMC2208Stepper(step_pin=Pin(8, Pin.OUT, value=0), dir_pin=Pin(9, Pin.OUT, value=0))
        
        self.pump_lagoon_to_waste = Pump(Pin(19, Pin.OUT, value=0), mode=Pump.MODE_PIN) 


        self.stepper_arabinose_to_lagoon = TMC2208Stepper(step_pin=Pin(10, Pin.OUT, value=0), dir_pin=Pin(13, Pin.OUT, value=0), mode=TMC2208Stepper.MODE_STEP)
        
        self.button_left = Pin(4, Pin.IN, Pin.PULL_UP) 
        self.button_right = Pin(5, Pin.IN, Pin.PULL_UP)





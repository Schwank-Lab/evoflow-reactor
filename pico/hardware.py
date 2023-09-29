from machine import ADC, Pin, Timer, PWM
import onewire
import ds18x20

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
        self._device = self._b_temp.scan()

    def read(self):
        self._b_temp.convert_temp()
        return self._sensor.read_temp(self._device[0])

class Hardware:

    inc_led = Pin(10, Pin.OUT, value=0)
    inc_od_sensor = ODSensor(ADC(Pin(27, Pin.IN)))
    inc_temp_sensor = TempSensor(Pin(16, Pin.IN))
    inc_heater = Pin(9, Pin.OUT, value=0)

    inc_medium_pump = Pin(6, Pin.OUT, value=0)
    inc_waste_pump= Pin(7, Pin.OUT, value=0)

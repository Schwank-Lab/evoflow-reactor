from machine import Pin, Timer
import utime

## Pump 6
dir_pin1 = Pin(9, Pin.OUT)
step1 = Pin(8, Pin.OUT)

## Pump 7
dir_pin2 = Pin(11, Pin.OUT)
step2 = Pin(12, Pin.OUT)

## Syringe
dir_pin3 = Pin(13, Pin.OUT)
step3 = Pin(10, Pin.OUT)

dir_pin1.value(1)
dir_pin2.value(1)
dir_pin3.value(1)

def stepOne():
    step1.high()
    step2.high()
    step3.high()
    utime.sleep(0.001)
    step1.low()
    step2.low()
    step3.low()


while True:
    for i in range(3000): ## At 1/8 steps (MS1 0, MS2 0), 3000 steps = 3000steps/200steps/rev*1/8steps*2mm/step = 3.75mm
        stepOne()
        utime.sleep(0.001)
    dir_pin1.toggle()
    dir_pin2.toggle()
    dir_pin3.toggle()
    print("STEP ") 



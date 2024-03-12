from machine import ADC, Pin, Timer, PWM
import utime, time
import onewire
import ds18x20

####### Changeable Paramters: ########

LV = 7 # Lagoon Volume in mL
L_FlowRate = 0.5 # LV/h Initial flow rate is 0.5
B_OD = 58000 # Target OD for Bioreactor in u16 units (1-65'535). OD 0.5 = xx
L_Pump = 15 ## number of seconds the lagoon pumps are activated. Calibrate flow here. currently 2s pump on. Volume = xx
Syringe_ml_per_mm = 30/78 ## amount of ML extruded per mm of syringe movement. Measure distance for e.g. 10mm, calculate per mm. in our case: 30ml per 78mm.
B_Stir_DutyCycle = 50 # duty cycle of Bioreactor stirrer. Value between 0 to 100%
L_Stir_DutyCycle = 50 # duty cycle of Lagoon stirrer. Value between 0 to 100%
C_Arabinose = 1000 # Arabinose molarity in syringe (in mM)
C_T_Arabinose = 40 # Target Arabinose molarity in Lagoon (in mM)
## ideally: calibrate mapping function to OD and work with "real ODs"

####### --------------------- ########

# Not yet used, but potentially useful Parameters?



Medium_DRM = True
Medium_LB = False


Timer_L = 0
Timer_Arabinose = 0
Timer_Stir = 0
Timer_OD = 0

Arabinose_delay_remainder = 0

led = Pin("LED", Pin.OUT, value=0) ## Can be used to indicate some functions. 

P_Pump1 = Pin(6, Pin.OUT, value=0)
P_Pump2 = Pin(7, Pin.OUT, value=0)
P_Pump3 = Pin(26, Pin.OUT, value=0)
P_Pump4 = Pin(22, Pin.OUT, value=0)

P_B_Heat = Pin(9, Pin.OUT, value=0)
P_L_Heat = Pin(8, Pin.OUT, value=0)

P_B_LED = Pin(10, Pin.OUT, value=0)
P_L_LED = Pin(11, Pin.OUT, value=0)

P_B_IR = ADC(Pin(27, Pin.IN))
P_L_IR = ADC(Pin(28, Pin.IN))

P_B_STIR = Pin(21, Pin.OUT, value=0)
#P_B_STIR = PWM(Pin(21, Pin.OUT)) ## use PWM to set speed of stirrer
#P_B_STIR.freq(1000) ## test a few, to see which frequency works best with fan. 500hz works on Duet2 boards. 
#P_B_STIR.duty_u16(int((B_Stir_DutyCycle/100)*65_535)) ## write duty cycle to Pin.
P_L_STIR = Pin(20, Pin.OUT, value=0)
#P_L_STIR = PWM(Pin(20, Pin.OUT))
#P_L_STIR.freq(1000)
#P_L_STIR.duty_u16(int((L_Stir_DutyCycle/100)*65_535))

P_IN1 = Pin(12, Pin.OUT, value=0)
P_IN2 = Pin(13, Pin.OUT, value=0)
P_IN3 = Pin(14, Pin.OUT, value=0)
P_IN4 = Pin(15, Pin.OUT, value=0)

P_BUTTON1 = Pin(18, Pin.IN, Pin.PULL_UP)
P_BUTTON2 = Pin(19, Pin.IN, Pin.PULL_UP)

## Stepper:

P_STEPPER = [
    Pin(12, Pin.OUT), #IN1
    Pin(13, Pin.OUT), #IN2
    Pin(14, Pin.OUT), #IN3
    Pin(15, Pin.OUT) #IN4
    ]
full_step_sequence = [ ## this are 4 steps
    [1,0,0,0],
    [0,1,0,0],
    [0,0,1,0],
    [0,0,0,1]
    ]

P_B_TEMP = onewire.OneWire(Pin(16))
B_TEMP = ds18x20.DS18X20(P_B_TEMP)
device_B = B_TEMP.scan()

P_L_TEMP = onewire.OneWire(Pin(17))
L_TEMP = ds18x20.DS18X20(P_L_TEMP)
device_L = L_TEMP.scan()

#utime.sleep(2) ## time to stop everything. Can be removed later.

def callback(P_BUTTON): ## Interrupt to the two buttons to control the stepper motor. Very slow process, consider programming button press to move specific direction.
    while P_BUTTON1.value() == 0: ## Turn Stepper Forward
        for step in full_step_sequence:
            for i in range(len(P_STEPPER)):
                P_STEPPER[i].value(step[i])
                utime.sleep(0.001)
    while P_BUTTON2.value() == 0: ## Turn Stepper Reverse
        for step in full_step_sequence[::-1]:
            for i in range(len(P_STEPPER)):
                P_STEPPER[i].value(step[i])
                utime.sleep(0.001)

def mapReverse(x): ## Map values to reverse: from a,b to c,d (since OD measurement is inverse)
    #y=(x-a)/(b-a)*(d-c)+c
    y=(x-1)/(65535-1)*(1-65535)+65535
    return y

while True: ## Test OD measurements
    # Interrupts for stepper buttons:
    P_BUTTON1.irq(trigger=P_BUTTON1.IRQ_FALLING, handler=callback)
    P_BUTTON2.irq(trigger=P_BUTTON2.IRQ_FALLING, handler=callback)
    
    
    # Controller for constant OD in Bioreactor. Ideally, stirrer would be turned off for precise OD measurement.
    ## in theory, one could also fit a curve and determine growth rate, to not have to sample OD too frequently.
    print("Testing OD: ")
    P_B_LED.on()
    P_L_LED.on()
    utime.sleep_ms(2000)
    print("ON")
    print("Bioreactor: ",P_B_IR.read_u16())
    print("Lagoon: ", P_L_IR.read_u16())
    P_B_LED.off()
    P_L_LED.off()
    utime.sleep_ms(2000) ## try not to sleep...
    print("OFF")
    print("Bioreactor: ",P_B_IR.read_u16())
    print("Lagoon: ", P_L_IR.read_u16())
    print("Testing stirring: ")
    print("Bioreactor")
    P_B_STIR.toggle()
    utime.sleep(1)
    P_B_STIR.toggle()
    print("Lagoon:")
    P_L_STIR.toggle()
    utime.sleep(1)
    P_L_STIR.toggle()

    print("Pump 1")
    P_Pump1.toggle()
    utime.sleep(1)
    P_Pump1.toggle()
    print("Pump 2")
    P_Pump2.toggle()
    utime.sleep(1)
    P_Pump2.toggle()
    print("Pump 3")
    P_Pump3.toggle()
    utime.sleep(1)
    P_Pump3.toggle()
    print("Pump 4")
    P_Pump4.toggle()
    utime.sleep(1)
    P_Pump4.toggle()

    print("Testing Temperature:")
    B_TEMP.convert_temp()
    L_TEMP.convert_temp()
    print("TempB:", B_TEMP.read_temp(device_B[0]))
    print("TempL:", L_TEMP.read_temp(device_L[0]))
    utime.sleep(1)
    P_B_Heat.toggle()
    P_L_Heat.toggle()


    
while False: ## test motors
    led.toggle()
    P_Pump1.toggle()
    P_Pump2.toggle()
    P_Pump3.toggle()
    P_Pump4.toggle()
    
    P_B_STIR.toggle()
    P_L_STIR.toggle()
    utime.sleep_ms(2000)
    




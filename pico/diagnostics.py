import hardware_config
from hardware import Hardware
import time
import math

PUMP_ON_DURATION_SEC = 5
STEPPER_ON_DURATION_SEC = 20
STIRRER_ON_DURATION_SEC = 10
OD_MEASURE_DURATION_SEC = 10
OD_MEASURE_INTERVAL_SEC = 1

TEMP_MEASURE_INTERVAL_SEC = 10
TEMP_MEASURE_DURATION_SEC = 60

# TODO: do I really want to use the calibrate config here? 
hw_config = hardware_config.load_hardware_config('configs/reactor_config.json')
hw = Hardware(hw_config)

STIRRERS = [
    ('Left Inc Stirrer', hw.inc_left.stirrer),
    ('Lagoon Stirrer', hw.stirrer_lagoon),
    ('Right Inc Stirrer', hw.inc_right.stirrer)
]

PUMPS = [
    ('pump_medium_to_inc_left', hw.inc_left.medium_pump),
    ('pump_inc_left_to_waste', hw.inc_left.waste_pump),
    ('pump_inc_left_to_lagoon', hw.pump_inc_left_to_lagoon),
    ('pump_lagoon_to_waste', hw.pump_lagoon_to_waste),
    ('pump_inc_right_to_lagoon', hw.pump_inc_right_to_lagoon),
    ('pump_inc_right_to_waste',  hw.inc_right.waste_pump),
    ('pump_medium_to_inc_right', hw.inc_right.medium_pump),
]

HEATERS = [
    ('Temp Inc Left', hw.inc_left.heater, hw.inc_left.temp_sensor),
    ('Temp Lagoon', hw.heater_lagoon, hw.temp_sensor_lagoon),
    ('Temp Inc Right', hw.inc_right.heater, hw.inc_right.temp_sensor)
]

def stop_all():
    for _, pump in PUMPS:
        pump.off()
        
    for _, heater, _ in HEATERS:
        heater.off()
        
    for _, stirrer in STIRRERS:
        stirrer.off()

    hw.stepper_arabinose_to_lagoon.off()
        
        
def test_pumps():
    print('Testing pumps 1 to 4 (numbering left to right)')
    for pos, (name, pump) in enumerate(PUMPS):
        print(f"Pump_{pos+1} '{name}' on for {PUMP_ON_DURATION_SEC}s")
        pump.on()
        time.sleep(PUMP_ON_DURATION_SEC)
        pump.off()
    
def test_stepper():
    print('Testing stepper motor')
    print(f'Stepper stepper_arabinose_to_lagoon on for {STEPPER_ON_DURATION_SEC}')
    t_start = time.time()
    while (time.time() - t_start) < STEPPER_ON_DURATION_SEC:
        # TODO: add progress update.
        hw.stepper_arabinose_to_lagoon.step()

    
    
def test_stepper_vol(vol_ml, pwm = 1000):
    displacement_mm = vol_ml / hardware_config.SYRINGE_LARGE_ML_PER_MM
    print(f'Making a {vol_ml}ml displacement on the stepper motor')
    test_stepper_displacement(displacement_mm, pwm) 


def test_stepper_displacement(displacement_mm, pwm = 1000):
    num_revolutions = displacement_mm / hardware_config.SHAFT_LEAD_MM # TODO: can I avoid this hardcoding?
    print(f'Making a {displacement_mm}mm displacement on the stepper motor')
    test_stepper_rotation(num_revolutions * 360, pwm)


def test_stepper_rotation(rotation_deg, pwm = 1000):
    num_revolutions = rotation_deg / 360 
    num_steps = int(hardware_config.STEPS_PER_REVOLUTION_BULLDOG * num_revolutions)
    print(f'Making a {rotation_deg} rotation on the stepper motor, {num_revolutions} revolutions.')
    test_stepper_steps(num_steps, pwm)


def test_stepper_steps(num_steps, pwm = 1000): 
    """ make the specified number of steps at specified PWM. 
    
    Args:
        num_steps: int, number of steps to make. If positive, rotation in positive direction, if negative, rotation in negative direction.
    """
    stepper = hw.stepper_arabinose_to_lagoon
    if num_steps < 0: 
        stepper.set_direction(-1) 
        num_steps = -num_steps
    else: 
        stepper.set_direction(1)
    time_s = num_steps / pwm
    print(f'Making {num_steps} steps, {time_s:.4f}s')
    stepper.set_frequency(pwm)
    stepper.on()
    # TODO: periodically write the progress, otherwise ampy will detach.
    time.sleep(time_s)
    stepper.off()

def test_stirrers():
    print('Testing Stirrers')
    for name, stirrer in STIRRERS:
        print(f'{name} is on for {STIRRER_ON_DURATION_SEC}s')
        stirrer.on()
        time.sleep(STIRRER_ON_DURATION_SEC)
        stirrer.off()


def compute_stats(measurements):
    measurements = [m for m in measurements if m is not None]
    N = len(measurements)
    if N == 0:
        return None, None
    mean = sum(measurements) / N
    std = math.sqrt(1/N * sum([(m-mean) ** 2 for m in measurements]))
    return mean, std

def measure_od_inc_left():
    print(f'Measuring OD every {OD_MEASURE_INTERVAL_SEC}s for {OD_MEASURE_DURATION_SEC}s')
    raws = []
    ods = []
    
    for _ in range(OD_MEASURE_DURATION_SEC // OD_MEASURE_INTERVAL_SEC):
        hw.inc_left.led.on()
        time.sleep_ms(50) # todo: share the config with the controller
        curr_raw = hw.inc_left.od_sensor.read_raw()
        curr_od = hw.inc_left.od_sensor.read_od()
        print(f'RAW={curr_raw:.2f}, OD={curr_od:.2f}')
        raws.append(curr_raw)
        ods.append(curr_od)
        hw.inc_left.led.off()
        time.sleep_ms(50) # todo: share the config with the controller
        time.sleep(OD_MEASURE_INTERVAL_SEC)
    
    return compute_stats(raws), compute_stats(ods)

def measure_od_inc_right():
    print(f'Measuring OD every {OD_MEASURE_INTERVAL_SEC}s for {OD_MEASURE_DURATION_SEC}s')
    raws = []
    ods = []
    
    for _ in range(OD_MEASURE_DURATION_SEC // OD_MEASURE_INTERVAL_SEC):
        hw.inc_right.led.on()
        time.sleep_ms(50) # todo: share the config with the controller
        curr_raw = hw.inc_right.od_sensor.read_raw()
        curr_od = hw.inc_right.od_sensor.read_od()
        print(f'RAW={curr_raw:.2f}, OD={curr_od:.2f}')
        raws.append(curr_raw)
        ods.append(curr_od)
        hw.inc_right.led.off()
        time.sleep_ms(50) # todo: share the config with the controller
        time.sleep(OD_MEASURE_INTERVAL_SEC)
    
    return compute_stats(raws), compute_stats(ods)
    
    
def test_od(measure_od):
    print('Testing OD measurement')
    print('Put clear probe')
    for i in range(3, 0, -1):
        print(f'Measuring in {i}')
        time.sleep(1)
    
    (clear_raw_mean, clear_raw_std), (clear_od_mean, clear_od_std) = measure_od()
        
    print('Put turbid probe')
    for i in range(3, 0, -1):
        print(f'Measuring in {i}')
        time.sleep(1)
        
    (turbid_raw_mean, turbid_raw_std), (turbid_od_mean, turbid_od_std) = measure_od()

    print(f'Clear\t od_mean={clear_od_mean:.2f}\t od_std={clear_od_std:.2f}\t raw_mean={clear_raw_mean:.2f}\t raw_std={clear_raw_std:.2f}')
    print(f'Turbid\t od_mean={turbid_od_mean:.2f}\t od_std={turbid_od_std:.2f}\t raw_mean={turbid_raw_mean:.2f}\t raw_std={turbid_raw_std:.2f}')
        
def test_heaters():
    print('Testing Heaters')
    for (name, heater, _) in HEATERS:
        print(f'{name}:\t Heater ON')
        heater.on()
        
    
    num_measurements = TEMP_MEASURE_DURATION_SEC // TEMP_MEASURE_INTERVAL_SEC
    for i in range(1, num_measurements+1):
        time.sleep(TEMP_MEASURE_INTERVAL_SEC)        
        print(f'Measurement #{i}')
        for (name, _, sensor) in HEATERS:
            t = sensor.read()
            print(f'{name}:\t T={t:.2f}')
        
    
    for (name, heater, _) in HEATERS:
        print(f'{name}:\t Heater OFF')
        heater.off()





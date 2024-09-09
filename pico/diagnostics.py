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

hw = Hardware(hardware_config.default_config())

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

def test_stepper_rotation(rotation_deg):
    stepper = hw.stepper_arabinose_to_lagoon
    if rotation_deg < 0: 
        stepper.set_direction(-1) 
        rotation_deg = -rotation_deg
    num_revolutions = abs(rotation_deg) / 360 
    num_steps = int(hardware_config.STEPS_PER_REVOLUTION_BULLDOG * num_revolutions)
    report_every = 10
    print(f'Making a {rotation_deg} rotation on the stepper motor, {num_steps} steps')
    for i in range(num_steps):
        stepper.step()
        if i % report_every == 0:
            print(f'{i}/{num_steps} steps')
    

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





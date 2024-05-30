import hardware_config
from hardware import Hardware
import time
import math

PUMP_ON_DURATION_SEC = 10
STEPPER_ON_DURATION_SEC = 20
STIRRER_ON_DURATION_SEC = 10
OD_MEASURE_DURATION_SEC = 10
OD_MEASURE_INTERVAL_SEC = 1

TEMP_MEASURE_INTERVAL_SEC = 10
TEMP_MEASURE_DURATION_SEC = 60

hw = Hardware(hardware_config.default_config())

STIRRERS = [
    ('Inucbator Stirrer', hw.stirrer_inc),
    ('Lagoon Stirrer', hw.stirrer_lagoon),
]

PUMPS = [
    ('pump_medium_to_incubator', hw.pump_medium_to_incubator),
    ('pump_incubator_to_waste', hw.pump_incubator_to_waste),
    ('pump_incubator_to_lagoon', hw.pump_incubator_to_lagoon),
    ('pump_lagoon_to_waste', hw.pump_lagoon_to_waste )
    ]

HEATERS = [
    ('Temp Incubator', hw.heater_inc, hw.temp_sensor_inc),
    ('Temp Lagoon', hw.heater_lagoon, hw.temp_sensor_lagoon)
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
        hw.stepper_arabinose_to_lagoon.step_reverse()

def test_stepper_rotation(rotation_deg):
    num_revolutions = rotation_deg / 360 
    num_steps = int(hardware_config.STEPS_PER_REVOLUTION * num_revolutions)
    report_every = 10
    print(f'Making a {rotation_deg} rotation on the stepper motor, {num_steps} steps')
    for i in range(num_steps):
        hw.stepper_arabinose_to_lagoon.step_forward()
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

def measure_od():
    print(f'Measuring OD every {OD_MEASURE_INTERVAL_SEC}s for {OD_MEASURE_DURATION_SEC}s')
    raws = []
    ods = []
    
    for _ in range(OD_MEASURE_DURATION_SEC // OD_MEASURE_INTERVAL_SEC):
        hw.inc_led.on()
        time.sleep_ms(50) # todo: share the config with the controller
        curr_raw = hw.inc_od_sensor.read_raw()
        curr_od = hw.inc_od_sensor.read_od()
        print(f'RAW={curr_raw:.2f}, OD={curr_od:.2f}')
        raws.append(curr_raw)
        ods.append(curr_od)
        hw.inc_led.off()
        time.sleep_ms(50) # todo: share the config with the controller
        time.sleep(OD_MEASURE_INTERVAL_SEC)
    
    return compute_stats(raws), compute_stats(ods)
    
    
def test_od():
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
    

def run_diagnostics():
    stop_all()
    # test_pumps()
    # test_stepper()
    test_stepper_rotation(90)
    # test_stirrers()
    # test_od()
    # test_heaters()
    
    

run_diagnostics()





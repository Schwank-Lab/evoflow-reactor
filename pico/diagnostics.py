from hardware import Hardware, sensor_to_od
import time
import math

PUMP_ON_DURATION_SEC = 10
STEPPER_ON_DURATION_SEC = 20
STIRRER_ON_DURATION_SEC = 10
OD_MEASURE_DURATION_SEC = 10
OD_MEASURE_INTERVAL_SEC = 1

TEMP_MEASURE_INTERVAL_SEC = 10
TEMP_MEASURE_DURATION_SEC = 60

STIRRERS = [
    ('Inucbator Stirrer', Hardware.stirrer_inc),
    ('Lagoon Stirrer', Hardware.stirrer_lagoon),
]

PUMPS = [
    ('pump_medium_to_incubator', Hardware.pump_medium_to_incubator),
    ('pump_incubator_to_waste', Hardware.pump_incubator_to_waste),
    ('pump_incubator_to_lagoon', Hardware.pump_incubator_to_lagoon),
    ('pump_lagoon_to_waste', Hardware.pump_lagoon_to_waste )
    ]

HEATERS = [
    ('Temp Incubator', Hardware.heater_inc, Hardware.temp_sensor_inc),
    ('Temp Lagoon', Hardware.heater_lagoon, Hardware.temp_sensor_lagoon)
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
        Hardware.stepper_arabinose_to_lagoon.step_reverse()
    

def test_stirrers():
    print('Testing Stirrers')
    for name, stirrer in STIRRERS:
        print(f'{name} is on for {STIRRER_ON_DURATION_SEC}s')
        stirrer.on()
        time.sleep(STIRRER_ON_DURATION_SEC)
        stirrer.off()

def compute_stats(measurements):
    N = len(measurements)
    mean = sum(measurements) / N
    std = math.sqrt(1/N * sum([(m-mean) ** 2 for m in measurements]))
    return mean, std

def measure_od():
    print(f'Measuring OD every {OD_MEASURE_INTERVAL_SEC}s for {OD_MEASURE_DURATION_SEC}s')
    raws = []
    ods = []
    
    t_start = time.time()
    for _ in range(OD_MEASURE_DURATION_SEC // OD_MEASURE_INTERVAL_SEC):
        curr_raw = Hardware.inc_od_sensor.read()
        curr_od = sensor_to_od(curr_raw)
        print(f'RAW={curr_raw:.2f}, OD={curr_od:.2f}')
        raws.append(curr_raw)
        ods.append(curr_od)
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
        print(f'Measurement #{i}')
        for (name, _, sensor) in HEATERS:
            t = sensor.read()
            print(f'{name}:\t T={t:.2f}')
        time.sleep(TEMP_MEASURE_INTERVAL_SEC)        
        
    
    for (name, heater, _) in HEATERS:
        print(f'{name}:\t Heater OFF')
        heater.off()
    

def run_diagnostics():
    stop_all()
    # test_pumps()
    # test_stepper()
    # test_stirrers()
    # test_od()
    test_heaters()
    

run_diagnostics()


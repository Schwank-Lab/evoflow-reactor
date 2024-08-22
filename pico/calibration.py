import time 
import math 

from hardware import Hardware, Clock
import hardware_config
import pace_controller
from logger import FileLogger, ConsoleLogger
import logger


hw_config = hardware_config.load_hardware_config('configs/reactor_config.json')
hw = Hardware(hw_config)
clk = Clock()
log =  ConsoleLogger(clk, level=logger.L_INFO)
pace_controller._logger = log


def compute_stats(measurements):
    measurements = [m for m in measurements if m is not None]
    N = len(measurements)
    if N == 0:
        return -1, -1
    mean = sum(measurements) / N
    std = math.sqrt(1/N * sum([(m-mean) ** 2 for m in measurements]))
    return mean, std

def stop_all(): 
    hw.inc_left_stirrer.off()
    hw.inc_right_stirrer.off()
    hw.stirrer_lagoon.off()
    hw.pump_inc_left_to_lagoon.off()


def calibrate_inc_right_stirrer(top_speed_frac):
    _calibrate_stirrer(top_speed_frac, hw.inc_right_stirrer)

def calibrate_inc_left_stirrer(top_speed_frac):
    _calibrate_stirrer(top_speed_frac, hw.inc_left_stirrer)

def calibrate_lagoon_stirrer(top_speed_frac): 
    _calibrate_stirrer(top_speed_frac, hw.stirrer_lagoon)

def _calibrate_stirrer(top_speed_frac, stirrer):
    print(f'Restarting lagoon stirrer at top speed fraction {top_speed_frac:.2f}')
    q = pace_controller.TaskQueue(clk)
    ctl = pace_controller.StirrerController(stirrer, top_speed_frac, q, priority=1)
    ctl.__bg__restart_motor()
    i = 0
    while not q.empty():
        print(f'Starting the stirrer {i}...')
        q.cycle()
        i += 1 


def calibrate_temp(target_temp):
    print('Calibrating temperature sensors')
    adjust_temp_interval_s = 1
    report_temp_every = 10
    num_temps_to_avg = 20
    inc_left_temps = [0.0 for _ in range(num_temps_to_avg)]
    inc_right_temps = [0.0 for _ in range(num_temps_to_avg)]
    lagoon_temps = [0.0 for _ in range(num_temps_to_avg)]
    inc_left_temps_raw = [0.0 for _ in range(num_temps_to_avg)]
    inc_right_temps_raw = [0.0 for _ in range(num_temps_to_avg)]
    lagoon_temps_raw = [0.0 for _ in range(num_temps_to_avg)]
    
    print(f'Setting target temperature to {target_temp}C.')
    inc_left_ctl = pace_controller.TempController(hw.inc_left_temp_sensor, hw.inc_left_heater, target_temp)
    inc_right_ctl = pace_controller.TempController(hw.inc_right_temp_sensor, hw.inc_right_heater, target_temp)
    lagoon_ctl = pace_controller.TempController(hw.temp_sensor_lagoon, hw.heater_lagoon, target_temp)
    i = 0
    while True:
        inc_left_temps[i % num_temps_to_avg] = inc_left_ctl.current_temp()
        inc_right_temps[i % num_temps_to_avg] = inc_right_ctl.current_temp()
        lagoon_temps[i % num_temps_to_avg] = lagoon_ctl.current_temp()
        inc_left_temps_raw[i % num_temps_to_avg] = inc_left_ctl.current_temp_raw()
        inc_right_temps_raw[i % num_temps_to_avg] = inc_right_ctl.current_temp_raw()
        lagoon_temps_raw[i % num_temps_to_avg] = lagoon_ctl.current_temp_raw()
        if i > 0  and i % report_temp_every == 0:
            mean_inc_left, std_inc_left = compute_stats(inc_left_temps)
            mean_inc_right, std_inc_right = compute_stats(inc_right_temps)
            mean_lagoon, std_lagoon = compute_stats(lagoon_temps) 
            mean_raw_inc_left, std_raw_inc_left = compute_stats(inc_left_temps_raw)
            mean_raw_inc_right, std_raw_inc_right = compute_stats(inc_right_temps_raw)
            mean_raw_lagoon, std_raw_lagoon = compute_stats(lagoon_temps_raw)
            print(f'Measurement time {i*adjust_temp_interval_s}s.')
            print(f'T(inc_left) =\t{mean_inc_left:.2f} (std={std_inc_left:.2f})\tT(lagoon) = \t{mean_lagoon:.2f} (std={std_lagoon:.2f})\tT(inc_right) = \t{mean_inc_right:.2f} (std={std_inc_right:.2f})')
            print(f'T_raw(inc_left) =\t{mean_raw_inc_left:.2f} (std={std_raw_inc_left:.2f})\tT_raw(lagoon) = \t{mean_raw_lagoon:.2f} (std={std_raw_lagoon:.2f})\tT_raw(inc_right) = \t{mean_raw_inc_right:.2f} (std={std_raw_inc_right:.2f})')
        inc_left_ctl.__bg__maintain_temp()
        inc_right_ctl.__bg__maintain_temp()
        lagoon_ctl.__bg__maintain_temp()
        time.sleep(adjust_temp_interval_s)
        i += 1

def calibrate_od_inc_left(num_probes=5):
    q = pace_controller.TaskQueue(clk)
    stirrer = pace_controller.StirrerController(hw.inc_left_stirrer, hw_config.inc_left.stirrer_top_speed_frac, q, priority=1)
    _calibrate_od(num_probes, stirrer, hw.inc_left_led, hw.inc_left_od_sensor, q)


def calibrate_od_inc_right(num_probes=5):
    q = pace_controller.TaskQueue(clk)
    stirrer = pace_controller.StirrerController(hw.inc_right_stirrer, hw_config.inc_right.stirrer_top_speed_frac, q, priority=1)
    _calibrate_od(num_probes, stirrer, hw.inc_right_led, hw.inc_right_od_sensor, q)


def _calibrate_od(num_probes, stirrer_ctl, led, sensor, task_queue):
    measure_od_interval_s = 5
    num_measurements_per_probe = 5
    measure_od_delay_s = 5
    
    
    measurements = [[] for _ in range(num_probes)] 
    for num_probe in range(num_probes):
        # Give user time to switch out the probe.
        print(f'Insert probe {num_probe}')
        for t in range(measure_od_delay_s, 0, -1):
            print(f'Measruing OD in {t}s')
            time.sleep(0.3)

        # Start the stirrer
        stirrer_ctl.__bg__restart_motor()
        while not task_queue.empty():
            task_queue.cycle()
            print('Starting the motor...')

        # Measure OD
        for num_measurement in range(num_measurements_per_probe):
            led.on()
            time.sleep_ms(pace_controller.ODController.TIME_OD_DELAY)
            raw = sensor.read_raw()
            measurements[num_probe].append(raw)
            led.off()
            time.sleep(measure_od_interval_s)
            print(f'Probe {num_probe+1}/{num_probes} Measurement {num_measurement+1}/{num_measurements_per_probe} RAW={raw:.2f}')
        
        stirrer_ctl._stirrer.off()

    with open('tmp/od_calibration.csv', 'w') as f: 
        for probe_measurements in measurements:
            f.write(','.join(map(str, probe_measurements)))
            f.write('\n')

def calibrate_pump_incubator_to_lagoon(num_steps=10000): 
    freq = 1000
    time_s = num_steps / freq
    print(f'Taking {num_steps} steps, should take {time_s:.2f} seconds')
    print('!!!! MAKE SURE THAT THE PUMP IS PRIMED !!!!')
    hw.pump_inc_left_to_lagoon.set_frequency(1000)
    hw.pump_inc_left_to_lagoon.on()
    time.sleep(time_s)
    hw.pump_inc_left_to_lagoon.off()


def calibrate_stepper(rotation_dir, rotation_deg=180): 
    assert rotation_deg >= 0
    stepper = hw.stepper_arabinose_to_lagoon
    stepper.set_direction(rotation_dir)
    num_revolutions = abs(rotation_deg) / 360 
    num_steps = int(hardware_config.STEPS_PER_REVOLUTION_BULLDOG * num_revolutions)
    report_every = 10
    print(f'Making a {rotation_deg} rotation on the stepper motor, {num_steps} steps, direction {rotation_dir}')
    for i in range(num_steps):
        stepper.step()
        if i % report_every == 0:
            print(f'{i}/{num_steps} steps')
    


        



    
# stop_all()
# calibrate_temp(36)
# calibrate_od(num_probes=6)
# calibrate_lagoon_stirrer()
# calibrate_pump_incubator_to_lagoon(target_vol=50)
# calibrate_clock()
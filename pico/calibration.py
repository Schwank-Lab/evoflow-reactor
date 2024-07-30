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
    hw.stirrer_inc.off()
    hw.stirrer_lagoon.off()
    hw.pump_incubator_to_lagoon.off()

def calibrate_inc_stirrer(top_speed_frac):
    print(f'Restarting incubator stirrer at top speed fraction {top_speed_frac:.2f}')
    q = pace_controller.TaskQueue(clk)
    ctl = pace_controller.StirrerController(hw.stirrer_inc, top_speed_frac)
    ctl.__bg__restart_motor(q, priority=1)
    i = 0
    while not q.empty():
        print(f'Starting the stirrer {i}...')
        q.cycle()
        i += 1 

def calibrate_lagoon_stirrer(top_speed_frac): 
    print(f'Restarting lagoon stirrer at top speed fraction {top_speed_frac:.2f}')
    q = pace_controller.TaskQueue(clk)
    ctl = pace_controller.StirrerController(hw.stirrer_lagoon, top_speed_frac)
    ctl.__bg__restart_motor(q, priority=1)
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
    inc_temps = [0.0 for _ in range(num_temps_to_avg)]
    lagoon_temps = [0.0 for _ in range(num_temps_to_avg)]
    inc_temps_raw = [0.0 for _ in range(num_temps_to_avg)]
    lagoon_temps_raw = [0.0 for _ in range(num_temps_to_avg)]
    
    print(f'Setting target temperature to {target_temp}C.')
    inc_ctl = pace_controller.TempController(hw.temp_sensor_inc, hw.heater_inc, target_temp)
    lagoon_ctl = pace_controller.TempController(hw.temp_sensor_lagoon, hw.heater_lagoon, target_temp)
    i = 0
    while True:
        inc_temps[i % num_temps_to_avg] = inc_ctl.current_temp()
        lagoon_temps[i % num_temps_to_avg] = lagoon_ctl.current_temp()
        inc_temps_raw[i % num_temps_to_avg] = inc_ctl._temp_sensor.read_raw()
        lagoon_temps_raw[i % num_temps_to_avg] = lagoon_ctl._temp_sensor.read_raw()
        if i > 0  and i % report_temp_every == 0:
            mean_inc, std_inc = compute_stats(inc_temps)
            mean_lagoon, std_lagoon = compute_stats(lagoon_temps) 
            mean_raw_inc, std_raw_inc = compute_stats(inc_temps_raw)
            mean_raw_lagoon, std_raw_lagoon = compute_stats(lagoon_temps_raw)
            print(f'Measurement time {i*adjust_temp_interval_s}s.')
            print(f'T(inc) =\t{mean_inc:.2f} (std={std_inc:.2f})\tT(lagoon) = \t{mean_lagoon:.2f} (std={std_lagoon:.2f})')
            print(f'T_raw(inc) =\t{mean_raw_inc:.2f} (std={std_raw_inc:.2f})\tT_raw(lagoon) = \t{mean_raw_lagoon:.2f} (std={std_raw_lagoon:.2f})')
        inc_ctl.__bg__maintain_temp()
        lagoon_ctl.__bg__maintain_temp()
        time.sleep(adjust_temp_interval_s)
        i += 1

   
def calibrate_od(num_probes=5):
    measure_od_interval_s = 5
    num_measurements_per_probe = 5
    measure_od_delay_s = 5
    stirrer = pace_controller.StirrerController(hw.stirrer_inc, hw_config.incubator_stirrer_top_speed_frac)
    q = pace_controller.TaskQueue(clk)
    measurements = [[] for _ in range(num_probes)] 
    for num_probe in range(num_probes):
        # Give user time to switch out the probe.
        print(f'Insert probe {num_probe}')
        for t in range(measure_od_delay_s, 0, -1):
            print(f'Measruing OD in {t}s')
            time.sleep(1)

        # Start the stirrer
        stirrer.__bg__restart_motor(task_queue=q, priority=1)
        while not q.empty():
            q.cycle()
            print('Starting the motor...')

        # Measure OD
        for num_measurement in range(num_measurements_per_probe):
            hw.inc_led.on()
            time.sleep_ms(pace_controller.ODController.TIME_OD_DELAY)
            raw = hw.inc_od_sensor.read_raw()
            measurements[num_probe].append(raw)
            hw.inc_led.off()
            time.sleep(measure_od_interval_s)
            print(f'Probe {num_probe+1}/{num_probes} Measurement {num_measurement+1}/{num_measurements_per_probe} RAW={raw:.2f}')
        
        hw.stirrer_inc.off()

    with open('tmp/od_calibration.csv', 'w') as f: 
        for probe_measurements in measurements:
            f.write(','.join(map(str, probe_measurements)))
            f.write('\n')


def calibrate_pump_incubator_to_lagoon(target_vol): 
    burst_vol = hw_config.pump_incubator_to_lagoon_burst_vol_ml
    num_bursts = target_vol // burst_vol
    burst_on_s = hw_config.pump_incubator_to_lagoon_burst_duration_s
    burst_off_s = max(0.5, burst_on_s)
    report_every = 10 
    print(f'Pumping {target_vol} mL will take {num_bursts * (burst_on_s + burst_off_s)}s')
    print('Make sure that pump is primed.')
    try:
        for i in range(num_bursts):
            if i % report_every == 0: 
                print(f'Pumped {i*burst_vol:.2f}/{target_vol}mL')
            hw.pump_incubator_to_lagoon.on()
            time.sleep(burst_on_s)
            hw.pump_incubator_to_lagoon.off()
            time.sleep(burst_off_s)
    except KeyboardInterrupt:
        hw.pump_incubator_to_lagoon.off()


def calibrate_stepper(rotation_dir, rotation_deg=180): 
    stepper = hw.stepper_arabinose_to_lagoon
    stepper.set_direction(rotation_dir)
    step = stepper.step_forward if rotation_deg > 0 else stepper.step_reverse
    num_revolutions = abs(rotation_deg) / 360 
    num_steps = int(hardware_config.STEPS_PER_REVOLUTION * num_revolutions)
    report_every = 10
    print(f'Making a {rotation_deg} rotation on the stepper motor, {num_steps} steps, direction {rotation_dir}')
    for i in range(num_steps):
        step()
        if i % report_every == 0:
            print(f'{i}/{num_steps} steps')
    


        



    
# stop_all()
# calibrate_temp(36)
# calibrate_od(num_probes=6)
# calibrate_lagoon_stirrer()
# calibrate_pump_incubator_to_lagoon(target_vol=50)
# calibrate_clock()
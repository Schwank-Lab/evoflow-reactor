import time 
import math 

from hardware import Hardware, Clock, TMC2208Stepper
import hardware_config
import pace_controller
from logger import ConsoleLogger
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
    hw.inc_left.stirrer.off()
    hw.inc_right.stirrer.off()
    hw.stirrer_lagoon.off()
    hw.pump_inc_left_to_lagoon.off()
    hw.pump_inc_right_to_lagoon.off()


def calibrate_inc_right_stirrer(top_speed_frac):
    _calibrate_stirrer(top_speed_frac, hw.inc_right.stirrer)

def calibrate_inc_left_stirrer(top_speed_frac):
    _calibrate_stirrer(top_speed_frac, hw.inc_left.stirrer)

def calibrate_lagoon_stirrer(top_speed_frac): 
    _calibrate_stirrer(top_speed_frac, hw.stirrer_lagoon)

def _calibrate_stirrer(top_speed_frac, stirrer):
    print(f'Restarting lagoon stirrer at top speed fraction {top_speed_frac:.2f}')
    q = pace_controller.TaskQueue(clk)
    ctl = pace_controller.StirrerController(stirrer, top_speed_frac, q, logger=log)
    ctl.restart_motor()
    i = 0
    while not q.empty():
        print(f'Starting the stirrer {i}...')
        q.cycle()
        i += 1 


def calibrate_temp(target_temp, max_duration_s=600, temp_tol=0.5, drift_tol=0.2, settle_window_s=30):
    """Heat all three zones to target_temp and stop automatically once settled.

    The loop streams T / T_raw every report_temp_every seconds (so a human can
    watch), and stops on its own -- no Ctrl+C needed -- when every zone is settled
    or when max_duration_s is reached (cap). Heaters are turned off on exit.

    Stabilization is judged on the internal (calibrated) T over a rolling window
    of the last settle_window_s samples. A zone is settled when both:
      * accuracy: |mean(window) - target_temp| <= temp_tol
      * flatness: |mean(2nd half) - mean(1st half)| <= drift_tol  (not drifting)
    """
    print('Calibrating temperature sensors')
    adjust_temp_interval_s = 1
    report_temp_every = 10
    n_window = int(settle_window_s)

    print(f'Setting target temperature to {target_temp}C.')
    print(f'Auto-stop when every zone stays within +/-{temp_tol}C of target and '
          f'drifts < {drift_tol}C over {n_window}s, or after {max_duration_s}s (cap).')

    zones = [
        ('inc_left', pace_controller.TempController(hw.inc_left.temp_sensor, hw.inc_left.heater, target_temp, logger=log)),
        ('lagoon', pace_controller.TempController(hw.temp_sensor_lagoon, hw.heater_lagoon, target_temp, logger=log)),
        ('inc_right', pace_controller.TempController(hw.inc_right.temp_sensor, hw.inc_right.heater, target_temp, logger=log)),
    ]
    temps = {name: [] for name, _ in zones}
    raws = {name: [] for name, _ in zones}

    def settled(window):
        if len(window) < n_window:
            return False
        mean = sum(window) / len(window)
        if abs(mean - target_temp) > temp_tol:
            return False
        half = len(window) // 2
        first = sum(window[:half]) / half
        second = sum(window[half:]) / (len(window) - half)
        return abs(second - first) <= drift_tol

    i = 0
    stabilized = False
    while True:
        for name, ctl in zones:
            t = ctl.current_temp()
            t_raw = ctl.current_temp_raw()
            if t is not None:
                temps[name] = (temps[name] + [t])[-n_window:]
            if t_raw is not None:
                raws[name] = (raws[name] + [t_raw])[-n_window:]

        elapsed = i * adjust_temp_interval_s
        if i > 0 and i % report_temp_every == 0:
            line_t = []
            line_raw = []
            for name, _ in zones:
                tm, ts = compute_stats(temps[name])
                rm, rs = compute_stats(raws[name])
                line_t.append(f'T({name})={tm:.2f}(std={ts:.2f})')
                line_raw.append(f'T_raw({name})={rm:.2f}(std={rs:.2f})')
            print(f'[{elapsed}s]\t' + '\t'.join(line_t))
            print(f'[{elapsed}s]\t' + '\t'.join(line_raw))

        if all(settled(temps[name]) for name, _ in zones):
            stabilized = True
            break
        if elapsed >= max_duration_s:
            break

        for _, ctl in zones:
            ctl.maintain_temp()
        time.sleep(adjust_temp_interval_s)
        i += 1

    # Heaters off on exit -- never leave the reactor heating.
    hw.inc_left.heater.off()
    hw.inc_right.heater.off()
    hw.heater_lagoon.off()

    print()
    if stabilized:
        print(f'STABILIZED after {i * adjust_temp_interval_s}s. Heaters off.')
    else:
        print(f'TIMEOUT after {max_duration_s}s -- not all zones settled. Heaters off.')
    print('Final readings (measure the actual temperature with your thermometer now):')
    for name, _ in zones:
        tm, ts = compute_stats(temps[name])
        rm, rs = compute_stats(raws[name])
        flag = '' if abs(tm - target_temp) <= temp_tol else '  <-- did not reach target'
        print(f'  {name}:\tT={tm:.2f} (std={ts:.2f})\tT_raw={rm:.2f} (std={rs:.2f}){flag}')

def calibrate_inc_left_od(num_probes=5):
    q = pace_controller.TaskQueue(clk)
    stirrer = pace_controller.StirrerController(hw.inc_left.stirrer, hw_config.inc_left.stirrer_top_speed_frac, q, logger=log)
    _calibrate_od(num_probes, stirrer, hw.inc_left.led, hw.inc_left.od_sensor, q)


def calibrate_inc_right_od(num_probes=5):
    q = pace_controller.TaskQueue(clk)
    stirrer = pace_controller.StirrerController(hw.inc_right.stirrer, hw_config.inc_right.stirrer_top_speed_frac, q, logger=log)
    _calibrate_od(num_probes, stirrer, hw.inc_right.led, hw.inc_right.od_sensor, q)


def _calibrate_od(num_probes, stirrer_ctl, led, sensor, task_queue):
    measure_od_interval_s = 5
    num_measurements_per_probe = 5
    measure_od_delay_s = 5
    
    
    measurements = [[] for _ in range(num_probes)] 
    for num_probe in range(num_probes):
        # Give user time to switch out the probe.
        print(f'Insert probe {num_probe+1} out of {num_probes}')
        for t in range(measure_od_delay_s, 0, -1):
            print(f'Measruing OD in {t}s')
            time.sleep(1)

        # Start the stirrer
        stirrer_ctl.restart_motor()
        while not task_queue.empty():
            task_queue.cycle()
            print('Starting the motor...')

        # Measure OD
        for num_measurement in range(num_measurements_per_probe):
            led.on()
            time.sleep(pace_controller.ODController.TIME_OD_DELAY / 1000)
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

def calibrate_pump_incubator_to_lagoon(num_steps=10000, pwm=1000): 
    time_s = num_steps / pwm
    print(f'Taking {num_steps} steps, should take {time_s:.2f} seconds')
    print('!!!! MAKE SURE THAT THE PUMP IS PRIMED !!!!')
    hw.pump_inc_left_to_lagoon.set_frequency(pwm)
    hw.pump_inc_left_to_lagoon.on()
    report_every_s = 3
    n_intervals = int(time_s // report_every_s)
    for i in range(n_intervals):
        time.sleep(report_every_s)
        print(f'{(i+1)*report_every_s}/{time_s}s')
        
    time.sleep(time_s - n_intervals * report_every_s)
    hw.pump_inc_left_to_lagoon.off()


def calibrate_stepper(rotation_dir, rotation_deg=180, pwm=1000): 
    assert rotation_deg >= 0
    stepper = hw.stepper_arabinose_to_lagoon
    stepper._direction_mapping = stepper.calculate_direction_mapping(rotation_dir)
    stepper.set_direction(TMC2208Stepper.DIRECTION_FORWARD)
    num_revolutions = abs(rotation_deg) / 360 
    num_steps = int(hardware_config.STEPS_PER_REVOLUTION_BULLDOG * num_revolutions)
    num_steps = int(hardware_config.STEPS_PER_REVOLUTION_BULLDOG * num_revolutions)
    time_s = num_steps / pwm
    print(f'Making a {rotation_deg} rotation on the stepper motor, {num_steps} steps, {time_s:.4f}s')
    stepper.set_frequency(pwm)
    stepper.on()
    time.sleep(time_s)
    stepper.off()


        



    
# stop_all()
# calibrate_temp(36)
# calibrate_od(num_probes=6)
# calibrate_lagoon_stirrer()
# calibrate_pump_incubator_to_lagoon(target_vol=50)
# calibrate_clock()
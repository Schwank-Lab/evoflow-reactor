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


def calibrate_temp(target_temp, temp_tol, drift_tol, settle_window_s):
    """Heat all three zones to target_temp and maintain it until the script stops.

    Streams T / T_raw every report_temp_every seconds. When every zone is holding
    within temp_tol of target with under drift_tol of drift across the last
    settle_window_s samples, it prints a one-time notice that it is ready to
    measure. The reactor keeps maintaining the target until interrupted, and the
    heaters are switched off on exit.

    Readiness is judged on the internal (calibrated) T over a rolling window of
    the last settle_window_s samples; a zone is ready when both hold:
      * accuracy: |mean(window) - target_temp| <= temp_tol
      * flatness: |mean(2nd half) - mean(1st half)| <= drift_tol
    """
    print('Calibrating temperature sensors')
    adjust_temp_interval_s = 1
    report_temp_every = 10
    n_window = int(settle_window_s)

    print(f'Setting target temperature to {target_temp}C.')

    zones = [
        ('inc_left', pace_controller.TempController(hw.inc_left.temp_sensor, hw.inc_left.heater, target_temp, logger=log)),
        ('lagoon', pace_controller.TempController(hw.temp_sensor_lagoon, hw.heater_lagoon, target_temp, logger=log)),
        ('inc_right', pace_controller.TempController(hw.inc_right.temp_sensor, hw.inc_right.heater, target_temp, logger=log)),
    ]
    temps = {name: [] for name, _ in zones}
    raws = {name: [] for name, _ in zones}

    def ready(window):
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
    announced = False
    try:
        while True:
            for name, ctl in zones:
                t = ctl.current_temp()
                t_raw = ctl.current_temp_raw()
                if t is not None:
                    temps[name] = (temps[name] + [t])[-n_window:]
                if t_raw is not None:
                    raws[name] = (raws[name] + [t_raw])[-n_window:]

            if i > 0 and i % report_temp_every == 0:
                line_t = []
                line_raw = []
                for name, _ in zones:
                    tm, ts = compute_stats(temps[name])
                    rm, rs = compute_stats(raws[name])
                    line_t.append(f'T({name})={tm:.2f}(std={ts:.2f})')
                    line_raw.append(f'T_raw({name})={rm:.2f}(std={rs:.2f})')
                print(f'[{i * adjust_temp_interval_s}s]\t' + '\t'.join(line_t))
                print(f'[{i * adjust_temp_interval_s}s]\t' + '\t'.join(line_raw))

            if not announced and all(ready(temps[name]) for name, _ in zones):
                announced = True
                print()
                print(f'>>> Holding at {target_temp}C. Measure the actual temperature in each glass tube now,')
                print('>>> reading the T_raw values above. The reactor keeps holding until you stop it. <<<')

            for _, ctl in zones:
                ctl.maintain_temp()
            time.sleep(adjust_temp_interval_s)
            i += 1
    finally:
        hw.inc_left.heater.off()
        hw.inc_right.heater.off()
        hw.heater_lagoon.off()
        print('Heaters off.')

def calibrate_inc_left_od():
    q = pace_controller.TaskQueue(clk)
    stirrer = pace_controller.StirrerController(hw.inc_left.stirrer, hw_config.inc_left.stirrer_top_speed_frac, q, logger=log)
    _calibrate_od(stirrer, hw.inc_left.led, hw.inc_left.od_sensor, q)


def calibrate_inc_right_od():
    q = pace_controller.TaskQueue(clk)
    stirrer = pace_controller.StirrerController(hw.inc_right.stirrer, hw_config.inc_right.stirrer_top_speed_frac, q, logger=log)
    _calibrate_od(stirrer, hw.inc_right.led, hw.inc_right.od_sensor, q)


def _calibrate_od(stirrer_ctl, led, sensor, task_queue):
    """Measure the raw OD of the probe currently inserted and write it to tmp/od_calibration_probe.csv.

    The host pairs this measurement with the known OD of the inserted probe and
    accumulates one row per probe across calls.
    """
    measure_od_interval_s = 5
    num_measurements = 5

    stirrer_ctl.restart_motor()
    while not task_queue.empty():
        task_queue.cycle()

    raws = []
    for num_measurement in range(num_measurements):
        led.on()
        time.sleep(pace_controller.ODController.TIME_OD_DELAY / 1000)
        raw = sensor.read_raw()
        raws.append(raw)
        led.off()
        time.sleep(measure_od_interval_s)
        print(f'Measurement {num_measurement+1}/{num_measurements} RAW={raw:.2f}')

    stirrer_ctl._stirrer.off()

    mean, std = compute_stats(raws)
    print(f'Inserted probe RAW over {num_measurements} readings: mean={mean:.2f} std={std:.2f}')

    with open('tmp/od_calibration_probe.csv', 'w') as f:
        f.write(','.join(map(str, raws)))
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
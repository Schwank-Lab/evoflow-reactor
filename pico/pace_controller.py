from hardware_config import HardwareConfig, IncubatorConfig
from logger import ConsoleLogger
from task_queue import TaskQueue
import time
import json

_logger = ConsoleLogger(None)  

def ms(milliseconds):
    return int(milliseconds)

def s_to_ms(seconds):
    return ms(seconds * 1000)

def m_to_ms(mins):
    return s_to_ms(60*mins)

def h_to_ms(hours):
    return m_to_ms(60*hours)

def h_to_s(hours):
    return 60 * 60 * hours

def median(arr):
    sorted_arr = sorted(arr)
    l = len(arr)
    if l % 2 == 0:
        return (sorted_arr[l//2] + sorted_arr[l//2 - 1]) / 2
    else:
        return sorted_arr[l//2]


class PaceController():

    CHECK_STEPPER_BUTTONS_INTERVAL = s_to_ms(1)
    RECORD_STATE_EVERY = s_to_ms(1)
    PRIORITY_BACT_STIRRER = 9
    PRIORITY_LAGOON_STIRRER = 6

    def __init__(self, clock, task_queue: TaskQueue, logger=None):
        global _logger
        _logger = logger if logger else ConsoleLogger(clock)
        self._task_queue = task_queue
    
        self._is_running = False
        self._is_initialzed = False
        self._is_resetting_stepper = False
        self._state_time = None
        self._clock = clock
        self._background_thread_running = False
        self.run_error = False
        self.is_alive = False

    def init(self, hardware, hardware_config, experiment_config):
        global _logger
        self._experiment_id = experiment_config['experiment_id']
        self._hardware = hardware

        if 'inc_left' in experiment_config and experiment_config['inc_left'].get('use', True):
            self._inc_left = IncabatorController(
                hardware.inc_left,
                hardware_config.inc_left,
                experiment_config['inc_left'],
                self._task_queue,
                priority=10,
                prefix='IncLeft',
                logger=_logger
            )
        else:
            _logger.info('PaceController: left incubator is not used.')
            self._inc_left = None

        if 'inc_right' in experiment_config and experiment_config['inc_right'].get('use', True):
            self._inc_right = IncabatorController(
                hardware.inc_right,
                hardware_config.inc_right,
                experiment_config['inc_right'],
                self._task_queue,
                priority=9,
                prefix='IncRight',
                logger=_logger
            )
        else:
            _logger.info('PaceController: right incubator is not used.')
            self._inc_right = None

        self._lagoon_temp_ctl = TempController(
            hardware.temp_sensor_lagoon,
            hardware.heater_lagoon,
            target_temp=experiment_config['lagoon']['target_temp'],
            prefix='Lagoon',
            logger=_logger
        )
        self._lagoon_stirrer_ctl = StirrerController(
            hardware.stirrer_lagoon,
            hardware_config.lagoon_stirrer_top_speed_frac,
            self._task_queue,
            logger=_logger
        )
        self._lagoon_flow_ctl = LagoonFlowController(
            hardware,
            hardware_config,
            experiment_config['lagoon'],
            logger=_logger
        )

        self._ara_stepper = hardware.stepper_arabinose_to_lagoon
        self._ara_stepper_vol_per_step = hardware_config.induction_stepper_ml_per_step
        self._is_initialzed = True

        # control buttons
        self._btn_left = hardware.button_left
        self._btn_right = hardware.button_right

        # set up state variable
        self._current_state = self.default_state()

    def start(self):
        assert not self._is_running
        assert not self._is_resetting_stepper
        assert self._is_initialzed
        if self._inc_left:
            self._inc_left.start()
        if self._inc_right:
            self._inc_right.start()
        self._lagoon_temp_ctl.start(self._task_queue)
        self._lagoon_stirrer_ctl.start()
        self._lagoon_flow_ctl.start(self._task_queue)
        self._task_queue.repeat(PaceController.RECORD_STATE_EVERY, self._record_state)
        self._task_queue.repeat(PaceController.CHECK_STEPPER_BUTTONS_INTERVAL,
                                self._handle_buttons)
        self._is_running = True
        self._write_current_status('running')

    def reset_stepper_forward(self, vol_ml, pwm=1000):
        self._reset_stepper(vol_ml, pwm, direction=1)

    def reset_stepper_reverse(self, vol_ml, pwm=1000):
        self._reset_stepper(vol_ml, pwm, direction=-1)

    def _reset_stepper(self, vol_ml, pwm, direction, report_progress_every_s=1):
        assert not self._is_running
        self._is_resetting_stepper = True
        n_steps = int(vol_ml / self._ara_stepper_vol_per_step)
        time_s = n_steps / pwm
        _logger.info(f'PaceController: resetting induction syringe {vol_ml}mL, {n_steps} steps, {time_s:.4f}s')
        self._ara_stepper.set_frequency(pwm)
        self._ara_stepper.set_direction(direction)
        self._ara_stepper.on()
        for i in range(1, int(time_s // report_progress_every_s)):
            self._task_queue.put(
                s_to_ms(report_progress_every_s*i),
                self._reset_stepper_report_progress,
                i*report_progress_every_s,
                time_s,
                priority=0
            )
        # No need to explicitly stop the controller, it will stop automatically once the stepper is done
        # and there're no more events in the task queue.

    def _reset_stepper_report_progress(self, time_spent, time_total):
        _logger.info(f'PaceController: reset induction syringe progress: {time_spent:.2f}s / {time_total:.2f}s')

    def stop(self, update_status=True):
        if not self._is_running and not self._is_resetting_stepper:
            print('PaceController#stop: already stopped, nothing to do')
            return
        
        self._is_running = False
        self._is_resetting_stepper = False
        self._stop_all_hardware()
        _logger.info('PaceController#stop: stopped')
        if update_status:
            self._write_current_status('idle')
        

    def is_running(self):
        return self._is_running

    def is_resetting_stepper(self):
        return self._is_resetting_stepper

    def _stop_all_hardware(self):
        hw = self._hardware

        hw.inc_left.stirrer.off()
        hw.inc_left.led.off()
        hw.inc_left.heater.off()
        hw.inc_left.medium_pump.off()
        hw.inc_left.waste_pump.off()

        hw.inc_right.stirrer.off()
        hw.inc_right.led.off()
        hw.inc_right.heater.off()
        hw.inc_right.medium_pump.off()
        hw.inc_right.waste_pump.off()

        hw.stirrer_lagoon.off()
        hw.heater_lagoon.off()

        hw.pump_inc_left_to_lagoon.off()
        hw.pump_inc_right_to_lagoon.off()
        hw.pump_lagoon_to_waste.off()
        hw.stepper_arabinose_to_lagoon.off()

    def _handle_buttons(self):
        btn_left = self._btn_left.value()
        btn_right = self._btn_right.value()
        if btn_left == 0 and btn_right == 0:
            _logger.info('Restarting the motors')
            # Pressing two buttons simultaneously will re-start the stirrers
            if self._inc_left:
                self._inc_left._inc_stirrer_ctl.restart_motor()
            if self._inc_right:
                self._inc_right._inc_stirrer_ctl.restart_motor()
            self._lagoon_stirrer_ctl.restart_motor()

    def default_state(self):
        return {
            'experiment_id': self._experiment_id,
            'timestamp': self._clock.time_since_epoch(),
            'lagoon_temp': -1,
            'lagoon_flow_rate': -1,
            'inc_left_temp': -1,
            'inc_left_od': -1,
            'inc_left_dilution': -1,
            'inc_right_temp': -1,
            'inc_right_od': -1,
            'inc_right_dilution': -1,
        }
    
    def _record_state(self):
        _logger.debug('PaceController#record_state')
        state = {
            'experiment_id': self._experiment_id,
            'timestamp': self._clock.time_since_epoch(),
            'lagoon_temp': self._lagoon_temp_ctl.current_temp(),
            'lagoon_flow_rate': self._lagoon_flow_ctl.flow_rate(),
        }
        if self._inc_left:
            state['inc_left_temp'] = self._inc_left._inc_temp_ctl.current_temp()
            state['inc_left_od'] = self._inc_left._inc_od_ctl.current_od()
            state['inc_left_dilution'] = self._inc_left._inc_od_ctl.total_dilution()
        else:
            state['inc_left_temp'] = -1
            state['inc_left_od'] = -1
            state['inc_left_dilution'] = -1
        if self._inc_right:
            state['inc_right_temp'] = self._inc_right._inc_temp_ctl.current_temp()
            state['inc_right_od'] = self._inc_right._inc_od_ctl.current_od()
            state['inc_right_dilution'] = self._inc_right._inc_od_ctl.total_dilution()
        else:
            state['inc_right_temp'] = -1
            state['inc_right_od'] = -1
            state['inc_right_dilution'] = -1
        self._current_state = state

    def _write_current_status(self, status):
        with open('state/reactor_state.json', 'w') as f:
            json.dump({'status': status}, f)

    def current_state(self):
        """ Current state of the reactor sensors. """
        return self._current_state

class IncabatorController:

    def __init__(self, inc, inc_cfg: IncubatorConfig, exp_config, task_queue: TaskQueue, priority, prefix='', logger=None):
        self._task_queue = task_queue
        self._logger = logger
        self._inc_temp_ctl = TempController(
            inc.temp_sensor,
            inc.heater,
            exp_config['target_temp'],
            prefix=prefix,
            logger=self._logger
        )
        self._inc_stirrer_ctl = StirrerController(
            inc.stirrer,
            inc_cfg.stirrer_top_speed_frac,
            task_queue,
            prefix=prefix,
            logger=self._logger
        )
        self._inc_od_ctl = ODController(
            inc,
            self._inc_stirrer_ctl,
            exp_config['target_od'],
            prefix=prefix,
            logger=self._logger
        )

    def start(self):
        self._inc_temp_ctl.start(self._task_queue)
        self._inc_stirrer_ctl.start()
        self._inc_od_ctl.start(self._task_queue)


class ODController:

    OD_UPDATE_INTERVAL = s_to_ms(3)
    TIME_LED_ON = ms(100)
    TIME_OD_DELAY = ms(50)
    TIME_MEDIUM_PUMP_ON = s_to_ms(2)
    TIME_WASTE_PUMP_ON = s_to_ms(2.2)
    NUM_OD_OUTLIERS_FOR_RESTART = 3

    def __init__(self, hardware, stirrer_ctrl, target_od, logger, filter_window_size=5, filter_deviation_th=0.3, prefix=''):
        self._stirrer_ctrl = stirrer_ctrl
        self._led = hardware.led
        self._od_sensor = hardware.od_sensor
        self._medium_pump = hardware.medium_pump
        self._waste_pump = hardware.waste_pump
        self._target_od = target_od
        self._last_ods = [-1 for _ in range(filter_window_size)]
        self._filter_deviation_th = filter_deviation_th
        self._current_od = -1
        self._measurement_counter = 0
        self._total_dilution = 0
        self._num_od_outliers = 0
        self._prefix = prefix
        self._logger = logger

    def start(self, task_queue: TaskQueue):
        task_queue.repeat(ODController.OD_UPDATE_INTERVAL, self.maintain_od, task_queue)

    def maintain_od(self, task_queue):
        self._logger.debug(self._prefix+'ODController#maintain_od')
        self._led.on()
        task_queue.put(ODController.TIME_OD_DELAY, self.read_od)
        task_queue.put(ODController.TIME_LED_ON, self._led.off)
        task_queue.put(ODController.TIME_MEDIUM_PUMP_ON, self._medium_pump.off)
        task_queue.put(ODController.TIME_WASTE_PUMP_ON, self._waste_pump.off)

    def read_od(self):
        od = self._od_sensor.read_od()
        self._last_ods[self._measurement_counter % len(self._last_ods)] = od
        self._measurement_counter += 1
        if self._measurement_counter < len(self._last_ods):
            # Not enough measurements to decide whether to dilute or not
            return

        median_od = median(self._last_ods)
        if abs(od - median_od) < self._filter_deviation_th:
            self._current_od = od
        else:
            self._logger.info(f'{self._prefix}ODController: measured OD = {od:.2f} is an outlier, median OD = {median_od:.2f}')
            # potentially this is a problem with the motors and they need to be restarted
            self._num_od_outliers += 1
            if self._num_od_outliers >= ODController.NUM_OD_OUTLIERS_FOR_RESTART:
                self._logger.info(self._prefix+'ODController: too many outliers, restarting the motors')
                self._stirrer_ctrl.__bg__restart_motor()
                self._num_od_outliers = 0

        self._logger.debug(f'{self._prefix}ODController: measured OD = {od:.2f}, filtered OD = {self._current_od:.2f}')

        if self._current_od > self._target_od:
            self._logger.debug(self._prefix+'ODController pumps on')
            self._total_dilution += 1
            self._medium_pump.on()
            self._waste_pump.on()

    def current_od(self):
        """ Current incubator OD, refreshed periodically. """
        return self._current_od

    def total_dilution(self):
        """ Total dilution of the incubator.

        Measured as the number of times the waste pump has been activated.
        """
        return self._total_dilution


class TempController:

    TEMP_UPDATE_INTERVAL = s_to_ms(1)

    def __init__(self, temp_sensor, heater, target_temp, logger, prefix=''):
        self._temp_sensor = temp_sensor
        self._heater = heater
        self._target_temp = target_temp
        self._current_temp = -1.0
        self._current_temp_raw = -1.0
        self._prefix = prefix
        self._logger = logger

    def start(self, task_queue: TaskQueue):
        task_queue.repeat(TempController.TEMP_UPDATE_INTERVAL, self.maintain_temp)

    def maintain_temp(self):
        try:
            temp_raw = self._temp_sensor.read_raw()
            temp = self._temp_sensor.convert_raw(temp_raw)
            self._current_temp_raw = temp_raw
            self._current_temp = temp
            if temp < self._target_temp:
                self._heater.on()
            else:
                self._heater.off()
        except Exception as ex:
            self._logger.exception(self._prefix+'TempController: Error in maintaining temp', ex)
            self._heater.off()

    def current_temp(self) -> float:
        """ Current temp (in C), refreshed periodically. """
        return self._current_temp

    def current_temp_raw(self) -> float:
        return self._current_temp_raw


class StirrerController:

    STIRRER_RESTART_INTERVAL = m_to_ms(5)
    NUM_STEPS = 10
    STEP_DELAY = s_to_ms(1)

    def __init__(self, stirrer, top_speed_frac, task_queue: TaskQueue, logger, prefix=''):
        self._stirrer = stirrer
        self._top_speed_frac = top_speed_frac
        self._task_queue = task_queue
        self._is_starting = False
        self._prefix = prefix
        self._logger = logger

    def start(self):
        self._task_queue.repeat(StirrerController.STIRRER_RESTART_INTERVAL, self.restart_motor)

    def __bg__restart_finished(self):
        self._is_starting = False

    def restart_motor(self):
        if self._is_starting:
            self._logger.info(self._prefix+'StirrerController: motor is already starting, don\'t restart')
            return
        self._is_starting = True
        for speed_step in range(StirrerController.NUM_STEPS):
            speed_frac = self._top_speed_frac * speed_step / (StirrerController.NUM_STEPS - 1)
            self._task_queue.put(
                StirrerController.STEP_DELAY*speed_step,
                self._stirrer.set_speed,
                speed_frac
            )

        # Add a speed ramp
        self._task_queue.put(
            StirrerController.STEP_DELAY*StirrerController.NUM_STEPS,
            self._stirrer.set_speed,
            self._top_speed_frac * 1.1,
        )
        self._task_queue.put(
            StirrerController.STEP_DELAY*(StirrerController.NUM_STEPS+1),
            self._stirrer.set_speed,
            self._top_speed_frac,
        )
        self._task_queue.put(
            StirrerController.STEP_DELAY*(StirrerController.NUM_STEPS+2),
            self.__bg__restart_finished,
        )

class LagoonFlowController():

    WASTE_BURST_DURATION = s_to_ms(3)
    WASTE_BURST_INTERVAL = m_to_ms(1)

    def __init__(self, hardware, hardware_config: HardwareConfig, experiment_config, logger):
        self._inc_left_stepper = hardware.pump_inc_left_to_lagoon
        self._inc_right_stepper = hardware.pump_inc_right_to_lagoon
        self._waste_pump = hardware.pump_lagoon_to_waste
        self._ara_stepper = hardware.stepper_arabinose_to_lagoon
        self._flow_rate = experiment_config['flow_rate']
        self._lagoon_volume = experiment_config['volume']
        self._bact_ml_per_step = hardware_config.bact_stepper_ml_per_step
        self._logger = logger

        if self._flow_rate > 0 and experiment_config['arabinose_target_concentration'] > 0:
            self._ara_conc = experiment_config['arabinose_target_concentration'] / experiment_config['arabinose_stock_concentration']
            if self._ara_conc >= 0.2:
                self._logger.critical(f'Arabinose concentration of {self._ara_conc:.2f} is too high, consider increasing stock molarity.')

            ara_flow_ml_per_hour = self._flow_rate * self._lagoon_volume * self._ara_conc
            self._ara_steps_per_sec = ara_flow_ml_per_hour / h_to_s(1)  / hardware_config.induction_stepper_ml_per_step

            self._logger.info(f'LagoonFlowController: arabinose induction {experiment_config["arabinose_target_concentration"]}mM == {ara_flow_ml_per_hour:.2f}mL/h == {self._ara_steps_per_sec:.2f} steps/s')
        else:
            self._ara_conc = 0
            self._logger.info('LagoonFlowController: no arabinose induction.')

        if self._flow_rate > 0:
            self._bact_left_frac = experiment_config.get('inc_left_frac', 0.0)
            self._bact_right_frac = experiment_config.get('inc_right_frac', 0.0)
            if self._bact_left_frac + self._bact_right_frac != 1.0:
                self._logger.critical('LagoonFlowController: bacteria fractions do not sum to 1.0')
            # convert flow rate from 1/h to steps/s
            bact_left_ml_per_hour = self._flow_rate * self._lagoon_volume * self._bact_left_frac
            self._bact_left_steps_per_sec = bact_left_ml_per_hour / h_to_s(1) / self._bact_ml_per_step
            self._logger.info(f'LagoonFlowController: inc_left flow {bact_left_ml_per_hour}mL/h == {self._bact_left_steps_per_sec:.2f} steps/s')
            bact_right_ml_per_hour = self._flow_rate * self._lagoon_volume * self._bact_right_frac
            self._bact_right_steps_per_sec = bact_right_ml_per_hour / h_to_s(1) / self._bact_ml_per_step
            self._logger.info(f'LagoonFlowController: inc_right flow {bact_right_ml_per_hour}mL/h == {self._bact_right_steps_per_sec:.2f} steps/s')
        else:
            self._bact_left_steps_per_sec = 0
            self._bact_right_steps_per_sec = 0
            self._logger.info('LagoonFlowController: no bacteria flow.')

    def start(self, task_queue):
        if self._bact_left_steps_per_sec > 0:
            self._inc_left_stepper.set_frequency(int(self._bact_left_steps_per_sec))
            self._inc_left_stepper.on()
        if self._bact_right_steps_per_sec > 0:
            self._inc_right_stepper.set_frequency(int(self._bact_right_steps_per_sec))
            self._inc_right_stepper.on()
        if self._flow_rate > 0:
            task_queue.repeat(self.WASTE_BURST_INTERVAL,
                              self.waste_pump, task_queue)
        if self._ara_conc > 0:
            self._ara_stepper.set_frequency(int(self._ara_steps_per_sec))
            self._ara_stepper.on()

    def waste_pump(self, task_queue: TaskQueue):
        self._waste_pump.on()
        task_queue.put(LagoonFlowController.WASTE_BURST_DURATION, self._waste_pump.off)

    def flow_rate(self):
        return self._flow_rate
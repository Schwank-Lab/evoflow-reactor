from hardware_config import HardwareConfig
from logger import ConsoleLogger

_logger = None

def ms(milliseconds):
    return int(milliseconds)

def s_to_ms(seconds):
    return ms(seconds * 1000)

def m_to_ms(mins): 
    return s_to_ms(60*mins)

def h_to_ms(hours): 
    return m_to_ms(60*hours)

def median(arr): 
    sorted_arr = sorted(arr)
    l = len(arr)
    if l % 2 == 0: 
        return (sorted_arr[l//2] + sorted_arr[l//2 - 1]) / 2
    else:
        return sorted_arr[l//2]

class Task:

    def __init__(self, fn, args: list, interval_ms=-1):
        """
        Params: 
            interval_ms: if specified, task will be executed repeatedly at the given interval. 
        """
        self.fn = fn
        self.args = args
        self.interval = interval_ms
        self.repeat = interval_ms > 0

    def run(self):
        self.fn(*self.args)

class PriorityQueue:    
    def __init__(self):
        self.queue = []

    def put(self, item):
        # Find the right position to insert the new item to maintain order
        index = 0
        for i, q_item in enumerate(self.queue):
            if item < q_item:  # Compare items directly
                index = i
                break
        else:
            index = len(self.queue)

        self.queue.insert(index, item)

    def get(self):
        if not self.queue:
            raise ValueError("The queue is empty")
        # Remove and return the item with the highest priority (smallest item)
        return self.queue.pop(0)

    def empty(self):
        return len(self.queue) == 0

    def qsize(self):
        return len(self.queue)


class TaskQueue:
    
    def __init__(self, clock):
        self._clock = clock
        self._task_queue = PriorityQueue() 

    def _put_task(self, t_ms, priority, task):
        """Adds task to the queue.
        
        Params: 
            t_ms (int): time at which the task has to be executed. """
        self._task_queue.put((t_ms, priority, task))
    
    def put(self, delay_ms, task, *args,  priority=1):
        """ Schedule a task to be executed at after a given delay. 
        
        Args:
            dalay: time in milliseconds after which the task should be executed (from the current timepoint)
            priority: if two tasks are scheduled to be executed at the same timepoint, order is determined by priority.
        """
        self._put_task(self._clock.time_ms()+delay_ms, priority, Task(task, args))

    def repeat(self, interval, task, *args, priority=1):
        """ Schedule a task to be executed at a given interval. 
        
        Args:
            priority: if two tasks are scheduled to be executed at the same timepoint, order is determined by priority.
        """
        repeat_task = Task(task, args, interval_ms=interval)
        self._put_task(self._clock.time_ms(), priority, repeat_task)

    def cycle(self):
        """ Retrieve next task from the priority queue and execute it. """
        t = self._clock.time_ms()
        t_next_ms, priority, task = self._task_queue.get()
        if t_next_ms > t: 
            self._clock.sleep_ms(t_next_ms - t)
        _logger.debug(f"TaskQueue#cycle {t_next_ms/1000:.3f}")
        task.run()
        if task.repeat:
            t = self._clock.time_ms()
            self._put_task(t+task.interval, priority, task)

    def empty(self):
        return self._task_queue.empty()
    
    def clear(self):
        self._task_queue = PriorityQueue()
    

class PaceController():

    CHECK_STEPPER_BUTTONS_INTERVAL = s_to_ms(1)
    RECORD_STATE_EVERY = s_to_ms(1)
    PRIORITY_BACT_STIRRER = 9
    PRIORITY_LAGOON_STIRRER = 6

    def __init__(self, clock, thread, logger=None):
        global _logger 
        _logger = logger if logger else ConsoleLogger(clock)
        self._thread = thread
       
        self._task_queue = TaskQueue(clock)
        self._is_running = False
        self._is_initialzed = False
        self._state_time = None
        self._clock = clock
        self._current_state = None
 
    def init(self, hardware, hardware_config, experiment_config):
        self._experiment_id = experiment_config['experiment_id']
        self._hardware = hardware
        self._inc_temp_ctl = TempController(hardware.temp_sensor_inc, 
                hardware.heater_inc, target_temp=37) # TODO: move target temp to the experiment config
        self._inc_stirrer_ctl = StirrerController(hardware.stirrer_inc, hardware_config.incubator_stirrer_top_speed_frac)
        self._inc_od_ctl = ODController(hardware, experiment_config)
        
        self._lagoon_temp_ctl = TempController(hardware.temp_sensor_lagoon,
                hardware.heater_lagoon, target_temp=35)  # TODO: move target temp to the experiment config
        self._lagoon_stirrer_ctl = StirrerController(hardware.stirrer_lagoon, hardware_config.lagoon_stirrer_top_speed_frac)
        self._lagoon_flow_ctl = LagoonFlowController(hardware, hardware_config, experiment_config) 

        # control buttons 
        self._btn_left = hardware.button_left
        self._btn_right = hardware.button_right
        self._ara_stepper = hardware.stepper_arabinose_to_lagoon
        self._is_initialzed = True


    def start(self):
        assert not self._is_running
        assert self._is_initialzed
        self._is_running = True 
        self._inc_temp_ctl.start(self._task_queue, priority=10)
        self._inc_stirrer_ctl.start(self._task_queue, priority=PaceController.PRIORITY_BACT_STIRRER)
        self._inc_od_ctl.start(self._task_queue, priority=8)
        self._lagoon_temp_ctl.start(self._task_queue, priority=7)
        self._lagoon_stirrer_ctl.start(self._task_queue, priority=PaceController.PRIORITY_LAGOON_STIRRER)
        self._lagoon_flow_ctl.start(self._task_queue, priority=5)
        self._task_queue.repeat(PaceController.RECORD_STATE_EVERY, self._record_state, priority=1)
        self._task_queue.repeat(PaceController.CHECK_STEPPER_BUTTONS_INTERVAL, 
                          self._handle_buttons, priority=3)
        
        self._thread(self._run)

    def stop(self):
        self._is_running = False
    
    def is_running(self): 
        return self._is_running
    
    def _run(self):
        while not self._task_queue.empty() and self._is_running:
            self._task_queue.cycle()
        self._task_queue.clear()
        self._stop_all_hardware()

    def _stop_all_hardware(self):
          hw = self._hardware
          hw.stirrer_inc.off()
          hw.heater_inc.off()
          hw.stirrer_lagoon.off()
          hw.heater_lagoon.off()

          hw.pump_medium_to_incubator.off()
          hw.pump_incubator_to_waste.off()
          hw.pump_incubator_to_lagoon.off()
          hw.pump_lagoon_to_waste.off()
    
    def _handle_buttons(self):
        btn_left = self._btn_left.value()
        btn_right = self._btn_right.value()
        if btn_left == 0 and btn_right == 0:
            _logger.info('Restarting the motors')
            # Pressing two buttons simultaneously will re-start the stirrers
            self._inc_stirrer_ctl.restart_motor(self._task_queue, priority=PaceController.PRIORITY_BACT_STIRRER)
            self._lagoon_stirrer_ctl.restart_motor(self._task_queue, priority=PaceController.PRIORITY_LAGOON_STIRRER)
        elif btn_left == 0: 
            self._handle_button_left()
        elif btn_right == 0:
            self._handle_button_right()
            
            
    def _handle_button_left(self):
        """ Pressing left button will drain ara from the syringe. """
        _logger.info('PaceController: resetting arabinose syringe forward.')
        while self._btn_left.value() == 0:
            self._ara_stepper.step_forward()
        
    def _handle_button_right(self): 
        """ Pressing right button will re-fill the syringe. """
        _logger.info('PaceController: resetting arabinose syringe backward.')
        while self._btn_right.value() == 0: 
            self._ara_stepper.step_reverse()

    def _record_state(self):
        _logger.debug('PaceController#record_state')
        state = {
            'experiment_id': self._experiment_id, 
            'timestamp': self._clock.time_since_epoch(),
            'inc_od': self._inc_od_ctl.current_od(), 
            'inc_temp': self._inc_temp_ctl.current_temp(),
            'inc_dilution': self._inc_od_ctl.total_dilution(),
            'lagoon_temp': self._lagoon_temp_ctl.current_temp(),
            'lagoon_flow_rate': self._lagoon_flow_ctl.flow_rate(),
        }
        self._current_state = state
        
    
    def current_state(self):
        return self._current_state

class ODController():
    
    OD_UPDATE_INTERVAL = s_to_ms(3)
    TIME_LED_ON = ms(100)
    TIME_OD_DELAY = ms(50)
    TIME_MEDIUM_PUMP_ON = s_to_ms(2)
    TIME_WASTE_PUMP_ON = s_to_ms(2.2)

    def __init__(self, hardware, experiment_config, filter_window_size=5):
        self._led = hardware.inc_led
        self._od_sensor = hardware.inc_od_sensor
        self._medium_pump = hardware.pump_medium_to_incubator
        self._waste_pump = hardware.pump_incubator_to_waste
        self._target_od = experiment_config['target_od']
        self._last_ods = [None for _ in range(filter_window_size)]
        self._current_od = None 
        self._measurement_counter = 0 
        self._total_dilution = 0

    def start(self, task_queue: TaskQueue, priority):
        task_queue.repeat(ODController.OD_UPDATE_INTERVAL, self.maintain_od, task_queue, priority, priority=priority)

    def maintain_od(self, task_queue: TaskQueue, priority):
        _logger.debug('ODController#maintain_od')
        self._led.on()
        task_queue.put(ODController.TIME_OD_DELAY, self._read_od, priority=priority)
        task_queue.put(ODController.TIME_LED_ON, self._led.off, priority=priority)
        task_queue.put(ODController.TIME_MEDIUM_PUMP_ON, self._medium_pump.off, priority=priority)
        task_queue.put(ODController.TIME_WASTE_PUMP_ON, self._waste_pump.off, priority=priority)
        

    def _read_od(self):
        od = self._od_sensor.read_od()
        self._last_ods[self._measurement_counter % len(self._last_ods)] = od
        self._measurement_counter += 1
        if self._measurement_counter < len(self._last_ods):
            # Not enough measurements to decide whether to dilute or not 
            return
        
        self._current_od = median(self._last_ods)
        _logger.debug(f'ODController: measured OD = {od:.2f}, filtered OD = {self._current_od:.2f}')
        
        if od > self._target_od:
            _logger.debug('ODController pumps on')
            self._total_dilution += 1
            self._medium_pump.on()
            self._waste_pump.on()

    def current_od(self):
        """ Current incubator OD, refreshed periocially. """ 
        return self._current_od
    
    def total_dilution(self):
        """ Total dilution of the incubator.
        
        Measured as the number of times the waste pump has been activated. 
        """
        return self._total_dilution

    
class TempController:

    TEMP_UPDATE_INTERVAL = s_to_ms(1)
    
    def __init__(self, temp_sensor, heater, target_temp):
        self._temp_sensor = temp_sensor
        self._heater = heater
        self._target_temp = target_temp
        self._current_temp = None 

    def start(self, task_queue: TaskQueue, priority):
        task_queue.repeat(TempController.TEMP_UPDATE_INTERVAL, self.maintain_temp, priority=priority)

    def maintain_temp(self):
        temp = self._temp_sensor.read()
        self._current_temp = temp
        _logger.debug('TempController: measured temp', temp)
        if temp < self._target_temp:
            self._heater.on()
        else:
            self._heater.off()

    def current_temp(self) -> float:
        """ Current temp (in C), refreshed periocially. """ 
        return self._current_temp


class StirrerController:

    STIRRER_RESTART_INTERVAL = m_to_ms(5)
    NUM_STEPS = 10
    STEP_DELAY = s_to_ms(1)
    
    def __init__(self, stirrer, top_speed_frac):
        self._stirrer = stirrer
        self._top_speed_frac = top_speed_frac

    def start(self, task_queue: TaskQueue, priority):
        task_queue.repeat(StirrerController.STIRRER_RESTART_INTERVAL, self.restart_motor, task_queue, priority, priority=priority)

    def restart_motor(self, task_queue: TaskQueue, priority): 
        
        for speed_step in range(StirrerController.NUM_STEPS):
            speed_frac = self._top_speed_frac * speed_step / (StirrerController.NUM_STEPS - 1)
            task_queue.put(StirrerController.STEP_DELAY*speed_step, self._stirrer.set_speed, speed_frac, priority=priority)
        
        # Add a speed ramp
        task_queue.put(StirrerController.STEP_DELAY*StirrerController.NUM_STEPS, 
                       self._stirrer.set_speed, self._top_speed_frac * 1.1, priority=priority)
        task_queue.put(StirrerController.STEP_DELAY*(StirrerController.NUM_STEPS+1),
                       self._stirrer.set_speed, self._top_speed_frac, priority=priority)

class LagoonFlowController():
    
    def __init__(self, hardware, hardware_config: HardwareConfig, experiment_config): 
        self._bacteria_pump = hardware.pump_incubator_to_lagoon
        self._waste_pump = hardware.pump_lagoon_to_waste
        self._ara_stepper = hardware.stepper_arabinose_to_lagoon
        self._flow_rate = experiment_config['lagoon_flow_rate']
        self._lagoon_volume = experiment_config['lagoon_volume']
        if experiment_config['arabinose_target_concentration'] > 0: 
            self._ara_conc = experiment_config['arabinose_target_concentration'] / experiment_config['arabinose_stock_concentration']
            if self._ara_conc >= 0.2: 
                raise ValueError(f'Arabinose concentration of {self._ara_conc:.2f} is too high, consider increasing stock molarity.')
            ara_flow_ml_per_hour = self._flow_rate * self._lagoon_volume * self._ara_conc
            ara_steps_per_hour = ara_flow_ml_per_hour / hardware_config.induction_ml_per_step
            self._ara_step_interval = h_to_ms(1) // ara_steps_per_hour 
            _logger.info(f'LagoonFlowController: ara step every {(self._ara_step_interval / 1000):.1f}s')
        else:
            self._ara_conc = 0

       
        
        # convert flow rate from lv/h to ml/h
        bact_flow_ml_per_hour = self._flow_rate * self._lagoon_volume * (1 - self._ara_conc)
        # calculate how many bursts we have to do per hour to achieve the flow rate
        bact_bursts_per_hour = bact_flow_ml_per_hour / hardware_config.pump_incubator_to_lagoon_burst_vol_ml
        # calculate how often to we have to do bursts
        self._bact_burst_interval = h_to_ms(1) // bact_bursts_per_hour
        self._bact_burst_duration = s_to_ms(hardware_config.pump_incubator_to_lagoon_burst_duration_s)
        self._waste_burst_duration = s_to_ms(hardware_config.pump_lagoon_to_waste_burst_duration_s)
        _logger.info(f'LagoonFlowController: bacteria pump burst for {(self._bact_burst_duration / 1000):.1f}s every {(self._bact_burst_interval / 1000):.1f}s')
        if self._bact_burst_interval < self._bact_burst_duration:
            raise ValueError('Bacteria pump burst interval too short, smaller than burst duration')
        
       

    def start(self, task_queue, priority):
        task_queue.repeat(self._bact_burst_interval, 
                          self._maintain_bact_flow, task_queue, priority, priority=priority)
        if self._ara_conc > 0: 
            task_queue.repeat(self._ara_step_interval, 
                            self._maintain_ara_flow, task_queue, priority, priority=priority+0.5)
        
    def _maintain_bact_flow(self, task_queue: TaskQueue, priority): 
        self._bacteria_pump.on()
        self._waste_pump.on()
        task_queue.put(self._bact_burst_duration, self._bacteria_pump.off, priority=priority)
        task_queue.put(self._waste_burst_duration, self._waste_pump.off, priority=priority)
        
    def _maintain_ara_flow(self, task_queue: TaskQueue, priority): 
        self._ara_stepper.step()

    def flow_rate(self): 
        return self._flow_rate


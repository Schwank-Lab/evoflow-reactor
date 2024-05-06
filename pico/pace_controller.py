from hardware_config import HardwareConfig

logger = None 


def ms(milliseconds):
    return int(milliseconds)

def s(seconds):
    return ms(seconds * 1000)

def m(mins): 
    return s(60*mins)

def h(hours): 
    return m(60*hours)

class Task:

    def __init__(self, fn, args: list, interval=-1):
        self.fn = fn
        self.args = args
        self.interval = interval
        self.repeat = interval > 0

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

    def _put_task(self, t, priority, task):
        self._task_queue.put((t, priority, task))
    
    def put(self, delay, task, *args,  priority=1):
        """ Schedule a task to be executed at after a given delay. 
        
        Args:
            priority: if two tasks are scheduled to be executed at the same timepoint, order is determined by priority.
        """
        self._put_task(self._clock.time_ms()+delay, priority, Task(task, args))

    def repeat(self, interval, task, *args, priority=1):
        """ Schedule a task to be executed at a given interval. 
        
        Args:
            priority: if two tasks are scheduled to be executed at the same timepoint, order is determined by priority.
        """
        repeat_task = Task(task, args, interval=interval)
        self._put_task(self._clock.time_ms(), priority, repeat_task)

    def cycle(self):
        """ Retrieve next task from the priority queue and execute it. """
        t = self._clock.time_ms()
        t_next, priority, task = self._task_queue.get()
        if t_next > t: 
            self._clock.sleep_ms(t_next - t)
        logger.debug(f"TaskQueue#cycle {t_next/1000:.3f}")
        task.run()
        if task.repeat:
            t = self._clock.time_ms()
            self._put_task(t+task.interval, priority, task)

    def empty(self):
        return self._task_queue.empty()
    
    def clear(self):
        self._task_queue = PriorityQueue()
    

class PaceController():

    CHECK_STEPPER_BUTTONS_INTERVAL = s(1)
    PRIORITY_BACT_STIRRER = 9
    PRIORITY_LAGOON_STIRRER = 6
    

    def __init__(self, hardware, hardware_config: HardwareConfig, config, clock, thread):
        self._thread = thread
        self._inc_temp_ctl = TempController(hardware.temp_sensor_inc, 
                hardware.heater_inc, target_temp=37) # TODO: move target temp to the experiment config
        self._inc_stirrer_ctl = StirrerController(hardware.stirrer_inc, hardware_config.incubator_stirrer_top_speed_frac)
        self._inc_od_ctl = ODController(hardware, config)
        
        self._lagoon_temp_ctl = TempController(hardware.temp_sensor_lagoon,
                hardware.heater_lagoon, target_temp=35)  # TODO: move target temp to the experiment config
        self._lagoon_stirrer_ctl = StirrerController(hardware.stirrer_lagoon, hardware_config.lagoon_stirrer_top_speed_frac)
        self._lagoon_flow_ctl = LagoonFlowController(hardware, hardware_config, config) 

        # control buttons 
        self._btn_left = hardware.button_left
        self._btn_right = hardware.button_right
        self._ara_stepper = hardware.stepper_arabinose_to_lagoon

        self._task_queue = TaskQueue(clock)
        self._is_running = False
        self._experiment_loaded = False
        self._state_time = None
        self._clock = clock
        self._current_state = None
        self._store_state_interval_ms = config['store_state_interval_ms']
        self._record_state_interval_ms = config['record_state_interval_ms']

        self._new_experiment()
        
    def _new_experiment(self):
        assert not self._is_running

        timestamp = self._clock.time_since_epoch()  
        
        # Use the timestamp in the filenames
        state_log_filename = f"logs/state_log_{timestamp}.csv"
        self.state_log = state_log_filename
 
        # Write headers to the state_log file
        with open(self.state_log, 'w') as f:
            f.write(f"# Experiment started at: {self._clock.localtime()}\n")
            f.write('timestamp,inc_od,inc_temp,inc_dilution,lagoon_temp,lagoon_flow_rate\n')

    # def load_experiment(self):
    #     try:
    #         with open(self.exp_file, 'r') as f:
    #             start_time = float(f.readline().split(':')[1])
    #             self._clock.set_start_time(start_time)
    #             self._experiment_loaded = True
    #             return True
    #     except OSError:
    #         return False  
        
    # def experiment_info(self): 
    #     return {
    #         'start_time': self._start_time,
    #         'is_running': self._is_running
    #     }

    def start(self):
        assert not self._is_running
        self._is_running = True 
        self._inc_temp_ctl.start(self._task_queue, priority=10)
        self._inc_stirrer_ctl.start(self._task_queue, priority=PaceController.PRIORITY_BACT_STIRRER)
        self._inc_od_ctl.start(self._task_queue, priority=8)
        self._lagoon_temp_ctl.start(self._task_queue, priority=7)
        self._lagoon_stirrer_ctl.start(self._task_queue, priority=PaceController.PRIORITY_LAGOON_STIRRER)
        self._lagoon_flow_ctl.start(self._task_queue, priority=5)
        self._task_queue.repeat(self._record_state_interval_ms, self._record_state, priority=1)
        self._task_queue.repeat(self._store_state_interval_ms, self._store_state, priority=2)
        self._task_queue.repeat(PaceController.CHECK_STEPPER_BUTTONS_INTERVAL, 
                          self._handle_buttons, priority=3)
        
        self._thread(self._run)

    def stop(self):
        assert self._is_running
        self._is_running = False
    
    def _run(self):
        while not self._task_queue.empty() and self._is_running:
            self._task_queue.cycle()
        # Note: it's ungraceful and we might end up in a broken state, e.g. with LED turned on 
        self._task_queue.clear()    
    
    def _handle_buttons(self):
        btn_left = self._btn_left.value()
        btn_right = self._btn_right.value()
        if btn_left == 0 and btn_right == 0:
            logger.info('Restarting the motors')
            # Pressing two buttons simultaneously will re-start the stirrers
            self._inc_stirrer_ctl.restart_motor(self._task_queue, priority=PaceController.PRIORITY_BACT_STIRRER)
            self._lagoon_stirrer_ctl.restart_motor(self._task_queue, priority=PaceController.PRIORITY_LAGOON_STIRRER)
        elif btn_left == 0: 
            self._handle_button_left()
        elif btn_right == 0:
            self._handle_button_right()
            
            
    def _handle_button_left(self):
        """ Pressing left button will drain ara from the syringe. """
        while self._btn_left.value() == 0:
            self._ara_stepper.step_forward()
        
    def _handle_button_right(self): 
        """ Pressing right button will re-fill the syringe. """
        while self._btn_right.value() == 0: 
            self._ara_stepper.step_reverse()

    def _record_state(self):
        logger.debug('PaceController#record_state')
        state = {
            'timestamp': self._clock.time_since_epoch(),
            'inc_od': self._inc_od_ctl.current_od(), 
            'inc_temp': self._inc_temp_ctl.current_temp(),
            'inc_dilution': self._inc_od_ctl.total_dilution(),
            'lagoon_temp': self._lagoon_temp_ctl.current_temp(),
            'lagoon_flow_rate': self._lagoon_flow_ctl.flow_rate(),
        }
        self._current_state = state
        
    def _store_state(self):
        logger.debug('Calling PaceController#store_state')
        state = self._current_state
        with open(self.state_log, 'a') as f:
            f.write("{},{},{},{},{},{}\n".format(
                state['timestamp'], state['inc_od'], state['inc_temp'], state['inc_dilution'], state['lagoon_temp'], state['lagoon_flow_rate']))
    
    def current_state(self):
        return self._current_state
    
    def load_state_history(self): 
        with open(self.state_log, 'r') as f:
            for l in f:
                yield l
    

class ODController():
    
    OD_UPDATE_INTERVAL = s(3)
    TIME_LED_ON = ms(100)
    TIME_OD_DELAY = ms(50)
    TIME_MEDIUM_PUMP_ON = s(2)
    TIME_WASTE_PUMP_ON = s(2.2)
    UPPER_OD_THRESHOLD = 1.4

    def __init__(self, hardware, config):
        self._led = hardware.inc_led
        self._od_sensor = hardware.inc_od_sensor
        self._medium_pump = hardware.pump_medium_to_incubator
        self._waste_pump = hardware.pump_incubator_to_waste
        self.load_config(config)
        self._current_od = None 
        self._total_dilution = 0

    def start(self, task_queue: TaskQueue, priority):
        task_queue.repeat(ODController.OD_UPDATE_INTERVAL, self.maintain_od, task_queue, priority, priority=priority)

    def maintain_od(self, task_queue: TaskQueue, priority):
        logger.debug('ODController#maintain_od')
        self._led.on()
        task_queue.put(ODController.TIME_OD_DELAY, self._read_od, priority=priority)
        task_queue.put(ODController.TIME_LED_ON, self._led.off, priority=priority)
        task_queue.put(ODController.TIME_MEDIUM_PUMP_ON, self._medium_pump.off, priority=priority)
        task_queue.put(ODController.TIME_WASTE_PUMP_ON, self._waste_pump.off, priority=priority)
        

    def _read_od(self):
        od = self._od_sensor.read_od()
        self._current_od = od
        logger.debug('ODController: measured od', od)
        if od > ODController.UPPER_OD_THRESHOLD:
            logger.debug('ODController: OD too high, not pumping')
        elif od > self._target_od:
            logger.debug('ODController pumps on')
            self._total_dilution += 1
            self._medium_pump.on()
            self._waste_pump.on()

    def load_config(self, config):
        self._target_od = config['target_od']

    def current_od(self):
        """ Current incubator OD, refreshed periocially. """ 
        return self._current_od
    
    def total_dilution(self):
        """ Total dilution of the incubator.
        
        Measured as the number of times the waste pump has been activated. 
        """
        return self._total_dilution

    
class TempController:

    TEMP_UPDATE_INTERVAL = s(1)
    
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
        logger.debug('TempController: measured temp', temp)
        if temp < self._target_temp:
            self._heater.on()
        else:
            self._heater.off()

    def current_temp(self):
        """ Current temp (in C), refreshed periocially. """ 
        return self._current_temp


class StirrerController:

    STIRRER_RESTART_INTERVAL = m(5)
    NUM_STEPS = 10
    STEP_DELAY = s(1)
    
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
    
    def __init__(self, hardware, hardware_config, experiment_config): 
        self._bacteria_pump = hardware.pump_incubator_to_lagoon
        self._waste_pump = hardware.pump_lagoon_to_waste
        self._ara_stepper = hardware.stepper_arabinose_to_lagoon
        self._flow_rate = experiment_config['lagoon_flow_rate']
        self._lagoon_volume = experiment_config['lagoon_volume']
        self._ara_conc = experiment_config['arabinose_target_concentration'] / experiment_config['arabinose_stock_concentration']
        
        # convert flow rate from lv/h to ml/h
        bact_flow_ml_per_hour = self._flow_rate * self._lagoon_volume * (1 - self._ara_conc)
        # calculate how many bursts we have to do per hour to achieve the flow rate
        bact_bursts_per_hour = bact_flow_ml_per_hour / hardware_config.pump_incubator_to_lagoon_burst_vol_ml
        # calculate how often to we have to do bursts
        self._bact_burst_interval = h(1) // bact_bursts_per_hour
        self._bact_burst_duration = hardware_config.pump_incubator_to_lagoon_burst_duration_s
        self._waste_burst_duration = hardware_config.pump_lagoon_to_waste_burst_duration_s
        logger.info('LagoonFlowController: bacteria pump burst every ', self._bact_burst_interval // 1000, 's')
        if self._bact_burst_interval < self._bact_burst_duration:
            raise ValueError('Bacteria pump burst interval too short, smaller than burst duration')
        
        ara_flow_ml_per_hour = self._flow_rate * self._lagoon_volume * self._ara_conc
        ara_steps_per_hour = ara_flow_ml_per_hour / hardware_config.induction_ml_per_step
        self._ara_step_interval = h(1) // ara_steps_per_hour 
        logger.info('LagoonFlowController: ara step every', self._ara_step_interval // 1000, 's')

    def start(self, task_queue, priority):
        task_queue.repeat(self._bact_burst_interval, 
                          self._maintain_bact_flow, task_queue, priority, priority=priority)
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


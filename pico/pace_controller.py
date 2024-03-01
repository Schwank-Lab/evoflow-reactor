def log(*args):
    print(*args)

def s(seconds):
    return int(seconds * 1000)


def ms(milliseconds):
    return int(milliseconds)

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
        log(f"TaskQueue#cycle {t_next/1000:.3f}")
        task.run()
        if task.repeat:
            self._put_task(t_next+task.interval, priority, task)

    def empty(self):
        return self._task_queue.empty()
    
    def clear(self):
        self._task_queue = PriorityQueue()
    

class PaceController():

    state_log = 'pace_state.csv'
    exp_file = 'pace_exp.json'

    def __init__(self, hardware, config, clock, thread):
        self._thread = thread
        self._inc_temp_ctl = TempController(hardware.temp_sensor_inc, 
                hardware.heater_inc, target_temp=37)
        self._inc_stirrer_ctl = StirrerController(hardware.stirrer_inc)
        self._inc_od_ctl = ODController(hardware, config)
        
        self._lagoon_temp_ctl = TempController(hardware.temp_sensor_lagoon,
                hardware.heater_lagoon, target_temp=37)
        self._lagoon_stirrer_ctl = StirrerController(hardware.stirrer_lagoon)
        self._lagoon_flow_ctl = LagoonFlowController(hardware, config) 
        
        self._task_queue = TaskQueue(clock)
        
        self._is_running = False
        self._experiment_loaded = False
        self._state_time = None
        self._clock = clock
        self._current_state = None
        self._store_state_interval_ms = config['store_state_interval_ms']
        self._record_state_interval_ms = config['record_state_interval_ms']
        
    def new_experiment(self): 
        assert not self._is_running
        with open(self.state_log, 'w') as f:
            f.write('timestamp,inc_od,inc_temp,lagoon_temp,lagoon_flow_rate\n')
        with open(self.exp_file, 'w') as f:
            self._start_time = self._clock.time_since_epoch()
            self._clock.set_start_time(self._start_time)
            f.write(f"start_time: {self._start_time}\n")
        self._experiment_loaded = True

    def load_experiment(self):
        try:
            with open(self.exp_file, 'r') as f:
                start_time = float(f.readline().split(':')[1])
                self._clock.set_start_time(start_time)
                self._experiment_loaded = True
                return True
        except OSError:
            return False 
        
    def experiment_info(self): 
        return {
            'start_time': self._start_time,
            'is_running': self._is_running
        }

    def start(self):
        assert not self._is_running
        assert self._experiment_loaded
        self._is_running = True 
        self._inc_temp_ctl.start(self._task_queue, priority=10)
        self._inc_stirrer_ctl.start(self._task_queue, priority=9)
        self._inc_od_ctl.start(self._task_queue, priority=8)
        self._lagoon_temp_ctl.start(self._task_queue, priority=7)
        self._lagoon_stirrer_ctl.start(self._task_queue, priority=6)
        self._lagoon_flow_ctl.start(self._task_queue, priority=5)
        self._task_queue.repeat(self._record_state_interval_ms, self._record_state, priority=1)
        self._task_queue.repeat(self._store_state_interval_ms, self._store_state, priority=2)
        self._thread(self._run)

    def stop(self):
        assert self._is_running
        self._is_running = False
    
    def _run(self):
        while not self._task_queue.empty() and self._is_running:
            self._task_queue.cycle()
        # Note: it's ungraceful and we might end up in a broken state, e.g. with LED turned on 
        self._task_queue.clear()

    def _record_state(self):
        log('PaceController#record_state')
        state = {
            'timestamp': self._clock.time_ms() // 1000,
            'inc_od': self._inc_od_ctl.current_od(), 
            'inc_temp': self._inc_temp_ctl.current_temp(),
            'lagoon_temp': self._lagoon_temp_ctl.current_temp(),
            'lagoon_flow_rate': self._lagoon_flow_ctl.flow_rate(),

        }
        self._current_state = state
        
    def _store_state(self):
        log('Calling PaceController#store_state')
        state = self._current_state
        with open(self.state_log, 'a') as f:
            f.write(f"{state['timestamp']},{state['inc_od']},{state['inc_temp']},"
                    "{state['lagoon_temp']},{state['lagoon_flow_rate']}\n")

    def current_state(self):
        return self._current_state
    
    def load_state_history(self): 
        with open(self.state_log, 'r') as f:
            for l in f:
                yield l
    

class ODController():
    
    OD_UPDATE_INTERVAL = s(3)
    TIME_LED_ON = ms(100)
    TIME_MEDIUM_PUMP_ON = s(2)
    TIME_WASTE_PUMP_ON = s(2.2)

    def __init__(self, hardware, config):
        self._led = hardware.inc_led
        self._od_sensor = hardware.inc_od_sensor
        self._medium_pump = hardware.pump_medium_to_incubator
        self._waste_pump = hardware.pump_incubator_to_waste
        self.load_config(config)
        self._current_od = None 

    def start(self, task_queue: TaskQueue, priority):
        task_queue.repeat(ODController.OD_UPDATE_INTERVAL, self.maintain_od, task_queue, priority, priority=priority)

    def maintain_od(self, task_queue: TaskQueue, priority):
        log('ODController#maintain_od')
        self._led.on()
        task_queue.put(ODController.TIME_LED_ON, self._read_od, priority=priority)
        task_queue.put(ODController.TIME_MEDIUM_PUMP_ON, self._medium_pump.off, priority=priority)
        task_queue.put(ODController.TIME_WASTE_PUMP_ON, self._waste_pump.off, priority=priority)
        

    def _read_od(self):
        self._led.off()
        od = self._od_sensor.read()
        self._current_od = od
        log('ODController: measured od', od)
        if od > self._target_od:
            log('ODController pumps on')
            self._medium_pump.on()
            self._waste_pump.on()

    def load_config(self, config):
        self._target_od = config['target_od']

    def current_od(self):
        """ Current incubator OD, refreshed periocially. """ 
        return self._current_od
    
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
        log('TempController: measured temp', temp)
        if temp < self._target_temp:
            self._heater.on()
        else:
            self._heater.off()

    def current_temp(self):
        """ Current temp (in C), refreshed periocially. """ 
        return self._current_temp


class StirrerController:

    def __init__(self, stirrer):
        self._stirrer = stirrer

    def start(self, task_queue, priority):
        self._stirrer.on()
        # TODO: turn off every 5 min.


class LagoonFlowController():
    
    LAGOON_UPDATE_INTERVAL = s(20)
    MAX_FLOW_RATE = 60 # v/h

    def __init__(self, hardware, config): 
        self._bacteria_pump = hardware.pump_incubator_to_lagoon
        self._waste_pump = hardware.pump_lagoon_to_waste
        self._flow_rate = config['lagoon_flow_rate']
        self._duration_bacteria_pump_on = \
            self._convert_flow_rate_to_on_frac(self._flow_rate) * LagoonFlowController.LAGOON_UPDATE_INTERVAL
        self._duration_waste_pump_on = self._duration_bacteria_pump_on + ms(200)  

    def start(self, task_queue, priority):
        task_queue.repeat(LagoonFlowController.LAGOON_UPDATE_INTERVAL, 
                          self._maintain_lagoon, task_queue, priority, priority=priority)

    def _maintain_lagoon(self, task_queue: TaskQueue, priority): 
        self._bacteria_pump.on()
        self._waste_pump.on()
        task_queue.put(self._duration_bacteria_pump_on, self._bacteria_pump.off, priority=priority)
        task_queue.put(self._duration_waste_pump_on, self._waste_pump.off, priority=priority)
        # TODO: add arabinose. 

    def flow_rate(self): 
        return self._flow_rate

    def _convert_flow_rate_to_on_frac(self, flow_rate): 
        return flow_rate / LagoonFlowController.MAX_FLOW_RATE


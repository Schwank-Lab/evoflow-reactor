from queue import PriorityQueue

log = print

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

class TaskQueue:
    
    def __init__(self, clock):
        self._clock = clock
        self._task_queue = PriorityQueue() 

    def put_task(self, t, task):
        self._task_queue.put((t, task))
    
    def put(self, delay, task, *args):
        self.put_task(self._clock.time_ms()+delay, Task(task, args))

    def repeat(self, interval, task, *args, delay=0):
        repeat_task = Task(task, args, interval=interval)
        self.put_task(self._clock.time_ms()+delay, repeat_task)

    def cycle(self):
        t = self._clock.time_ms()
        t_next, task = self._task_queue.get()
        if t_next > t: 
            self._clock.sleep_ms(t_next - t)
        log(f"TaskQueue#cycle {t_next/1000:.3f}")
        task.run()
        if task.repeat:
            self.put_task(t_next+task.interval, task)

    def empty(self):
        return self._task_queue.empty()

class PaceController():

    def __init__(self, hardware, config, clock):
        self._od_ctl = ODController(hardware, config)
        self._inc_temp_ctl = TempController(hardware.inc_temp_sensor, 
                hardware.inc_heater, target_temp=37)
        self._task_queue = TaskQueue(clock)
        self._current_state = None
        self._store_state_interval = config['store_state_interval']
        self._record_state_interval = 1 # seconds 


    def start(self, n_cycles=None): 
        self._od_ctl.start(self._task_queue)
        self._inc_temp_ctl.start(self._task_queue, delay=ms(10))
        self._task_queue.repeat(s(1), self._record_state, delay=ms(20))
        while not self._task_queue.empty():
            self._task_queue.cycle()
            if n_cycles is not None:
                n_cycles -= 1
                if n_cycles == 0:
                    break

    def _record_state(self):
        log('PaceController#record_state')
        store_every = self._store_state_interval // self._record_state_interval
        state = {
            'od': self._od_ctl.current_od(), 
            'inc_temp': self._inc_temp_ctl.current_temp(),
        }
        self._current_state = state
    
    def current_state(self):
        return self._current_state
    

class ODController():
    
    def __init__(self, hardware, config):
        self._led = hardware.inc_led
        self._od_sensor = hardware.inc_od_sensor
        self._medium_pump = hardware.inc_medium_pump
        self._waste_pump = hardware.inc_waste_pump
        self.load_config(config)
        self._current_od = None 

    def start(self, task_queue: TaskQueue):
        task_queue.repeat(s(3), self.maintain_od, task_queue)

    def maintain_od(self, task_queue):
        log('ODController#maintain_od')
        self._led.on()
        task_queue.put(ms(100), self._read_od)
        task_queue.put(s(2), self._medium_pump.off)
        task_queue.put(s(2.2), self._waste_pump.off)
        

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
    
    def __init__(self, temp_sensor, heater, target_temp):
        self._temp_sensor = temp_sensor
        self._heater = heater
        self._target_temp = target_temp
        self._current_temp = None 

    def start(self, task_queue, delay):
        task_queue.repeat(s(1), self.maintain_temp, delay=delay)

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

class LagoonController():
    pass 
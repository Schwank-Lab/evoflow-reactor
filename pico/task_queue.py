class Task:

    def __init__(self, fn, args: list, interval_ms=-1, n_repeats=-1):
        """
        Params:
            interval_ms: if specified, task will be executed repeatedly at the given interval.
            n_repeats: number of times the task should be repeated.
                If -1, and interval_ms >= 0 the task will be repeated indefinitely.
                if -1 and interval_ms is -1, task will be executed only once.
        """
        self.fn = fn
        self.args = args
        self.interval = interval_ms
        self.n_repeats = n_repeats
        assert n_repeats == -1 or interval_ms >= 0

    def run(self):
        self.fn(*self.args)
        if self.n_repeats > 0:
            self.n_repeats -= 1

    def repeat(self):
        return self.n_repeats > 0 or (self.n_repeats == -1 and self.interval >= 0)


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
        self._priorities = set()

    def _put_task(self, t_ms, task, priority):
        """Adds task to the queue.

        Params:
            t_ms (int): time at which the task has to be executed. """
        if not priority: 
            priority = max(self._priorities) + 1 if self._priorities else 0
        if not priority in self._priorities:
            self._priorities.add(priority)
        self._task_queue.put((t_ms, priority, task))

    def put(self, delay_ms, task, *args,  priority=None):
        """ Schedule a task to be executed at after a given delay.

        Args:
            dalay: time in milliseconds after which the task should be executed (from the current timepoint)
            priority: if two tasks are scheduled to be executed at the same timepoint, order is determined by priority.
        """
        self._put_task(self._clock.ticks_ms()+delay_ms, Task(task, args), priority)

    def repeat(self, interval, task, *args, priority=None):
        """ Schedule a task to be executed at a given interval.

        Args:
            priority: if two tasks are scheduled to be executed at the same timepoint, order is determined by priority.
        """
        repeat_task = Task(task, args, interval_ms=interval)
        self._put_task(self._clock.ticks_ms(), repeat_task, priority)

    def repeat_n(self, interval, n_repeats, task, *args, priority=None):
        """ Schedule a task to be executed at a given interval for a given number of times.

        Args:
            priority: if two tasks are scheduled to be executed at the same timepoint, order is determined by priority.
        """
        repeat_task = Task(task, args, interval_ms=interval, n_repeats=n_repeats)
        self._put_task(self._clock.ticks_ms(), repeat_task, priority)

    def cycle(self):
        """ Retrieve next task from the priority queue and execute it. """
        t = self._clock.ticks_ms()
        t_next_ms, priority, task = self._task_queue.get()
        if t_next_ms > t:
            self._clock.sleep_ms(t_next_ms - t)
        task.run()
        if task.repeat():
            t = self._clock.ticks_ms()
            self._put_task(t+task.interval, task, priority)

    def empty(self):
        return self._task_queue.empty()

    def clear(self):
        self._task_queue = PriorityQueue()


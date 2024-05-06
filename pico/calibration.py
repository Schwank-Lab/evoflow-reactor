from hardware import Hardware, Clock
import hardware_config
import pace_controller
from logger import Logger


hw_config = hardware_config.default_config()
hw = Hardware(hw_config)
clk = Clock()
pace_controller.logger = Logger.create_instance(clk)

def stop_all(): 
    hw.stirrer_inc.off()
    hw.stirrer_lagoon.off()

def calibrate_inc_stirrer():
    top_speed_frac = hw_config.incubator_stirrer_top_speed_frac
    print(f'Restarting incubator stirrer at top speed fraction {top_speed_frac:.2f}')
    q = pace_controller.TaskQueue(clk)
    ctl = pace_controller.StirrerController(hw.stirrer_inc, top_speed_frac)
    ctl.restart_motor(q, priority=1)
    while not q.empty():
        q.cycle()

def calibrate_lagoon_stirrer(): 
    top_speed_frac = hw_config.lagoon_stirrer_top_speed_frac
    print(f'Restarting lagoon stirrer at top speed fraction {top_speed_frac:.2f}')
    q = pace_controller.TaskQueue(clk)
    ctl = pace_controller.StirrerController(hw.stirrer_lagoon, top_speed_frac)
    ctl.restart_motor(q, priority=1)
    while not q.empty():
        q.cycle()

stop_all()
# calibrate_lagoon_stirrer()
from hardware import Hardware, Clock
import pace_controller
from pace_controller import PaceController
from logger import Logger



config = {
            'target_od': 0.5, 
            'lagoon_flow_rate': 1, # v/h
            'lagoon_volume': 7, # ml
            'record_state_interval_ms': 2*60*1000,
            'store_state_interval_ms': 2*60*1000,
            'arabinose_stock_concentration': 2000, # mM
            'arabinose_target_concentration': 40, # mM
            }
hardware = Hardware()
hardware.stirrer_lagoon.off()
thread = lambda fn, *args: fn(*args)

pace_controller.logger = Logger.create_instance(Clock())
controller = PaceController(hardware, config, Clock(), thread)
controller.start()

def test_lagoon_motors(hardware, speed_frac, interval_on, interval_off, num_reps):
        import time 
        hardware.pump_incubator_to_lagoon.set_speed(0.0)
        for i in range(num_reps):
                hardware.pump_incubator_to_lagoon.set_speed(speed_frac)
                time.sleep_ms(interval_on)
                hardware.pump_incubator_to_lagoon.off()
                time.sleep_ms(interval_off)
                print('step: ', i, ' out of ', num_reps)
        

# test_lagoon_motors(hardware, speed_frac = 0.4, interval_on = 500, interval_off = 1000, num_reps=20)


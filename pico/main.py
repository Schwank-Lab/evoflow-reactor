from hardware import Hardware, Clock
from pace_controller import PaceController



config = {
        'target_od': 5, 
        'lagoon_flow_rate': 3, # v/h
        'record_state_interval_ms': 1000,
        'store_state_interval_ms': 3000
}
hardware = Hardware()
hardware.stirrer_lagoon.off()
thread = lambda fn, *args: fn(*args)
controller = PaceController(hardware, config, Clock(), thread)
controller.new_experiment()
controller.start()
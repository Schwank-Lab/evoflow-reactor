import hardware_config
from hardware import Hardware, Clock

reactor_config = hardware_config.load_hardware_config('configs/reactor_config.json')
hw = Hardware(reactor_config)

try: 
    while True: 
        hw.stepper_arabinose_to_lagoon.step_forward()
except KeyboardInterrupt:
    print('Interrupting the stepper...')
import hardware_config
from hardware import Hardware, Clock
from pace_controller import PaceController
from logger import  SerialLogger
import logger
from state_recorder import SerialStateRecorder
from task_queue import TaskQueue
from serial_comm import SerialComm
from commands import CommandsDispatcher
import utils
import monitor

import time 
import _thread
import json
import sys
import machine
import gc 

WATCHDOG_TIMEOUT_MS = 8 * 1000
RUN_CYCLE_SLEEP_S = 3
LOG_CLEANUP_EVERY_MS = 5 * 60 * 1000
SERIAL_RECEIVE_MESSAGE_INTERVAL_MS = 1 * 1000
RECORD_STATE_INTERVAL_MS = 1 * 1000

def init_hardware():
    global hardware, reactor_config, network_config
    reactor_config = hardware_config.load_hardware_config('configs/reactor_config.json')
    hardware = Hardware(reactor_config)
    network_config = utils.load_json('configs/network_config.json')    

def init_logger(comms: SerialComm): 
    global clock, main_logger
    main_logger = SerialLogger(clock, comms, level=logger.L_INFO)
    
def record_experiment_state(): 
    global exp_state_recorder, controller
    state = controller.current_state()
    exp_state_recorder.record(state)

def record_reactor_state():
    global reactor_state_recorder, hardware
    state = monitor.current_state()
    state['status'] = get_controller_state()
    reactor_state_recorder.record(state)

def init_state_recorder(task_queue):
    global exp_state_recorder, reactor_state_recorder, reactor_config, controller
    exp_state_recorder = SerialStateRecorder(network_config['reactor_id'], comms, controller, SerialStateRecorder.EXP_TOPIC_STATE)
    task_queue.repeat(RECORD_STATE_INTERVAL_MS, record_experiment_state)
    reactor_state_recorder = SerialStateRecorder(network_config['reactor_id'], comms, controller, SerialStateRecorder.REACTOR_TOPIC_STATE)
    task_queue.repeat(RECORD_STATE_INTERVAL_MS, record_reactor_state)


def init_command_receiver(task_queue: TaskQueue):
    global command_dispatcher 
    command_dispatcher = CommandsDispatcher(network_config['reactor_id'], controller, main_logger)
    comms.add_listener('commands', command_dispatcher.process_command)
    task_queue.repeat(SERIAL_RECEIVE_MESSAGE_INTERVAL_MS, comms.receive_messages)


def init_controller(task_queue):
    global controller, main_logger
    controller = PaceController(clock, task_queue, logger=main_logger)

    experiment_config = utils.load_json('configs/experiment_config.json')
    controller.init(hardware, reactor_config, experiment_config)
    reactor_state = utils.load_json('state/reactor_state.json')
    main_logger.info('[MAIN] Reactor state:', reactor_state['status'])
    if reactor_state['status'] == 'running':
        controller.start()

def get_controller_state(): 
    if controller.is_running():
        return 'running'
    elif controller.is_resetting_stepper():
        return 'resetting_stepper'
    else:
        return 'idle'



def run(task_queue):
    
    while True:
        if task_queue.empty():
            main_logger.critical('[MAIN]#run: task queue is empty')
            break
        try:
            task_queue.cycle()
        except Exception as ex:
            main_logger.exception('PaceController: Error in task queue cycle', ex)
            return 

# the next three commands should never fail, good luck.
clock = Clock()
comms = SerialComm()
init_logger(comms)

try: 
    init_hardware()
    main_logger.info('[MAIN] Hardware initialized.')
except Exception as e:
    main_logger.info('[MAIN] Error initializing hardware') 
    machine.reset()


if hardware.button_left.value() == 0 and hardware.button_right.value() == 0:
    main_logger.info('[MAIN] Detected button press on re-boot, entering dev mode, stopping the run...')
else:
    # TODO: receive a ping from the bridge to check if the connection is still alive.
    task_queue = TaskQueue(clock)
    init_controller(task_queue)
    init_state_recorder(task_queue)
    init_command_receiver(task_queue)
    try:
        run(task_queue)
        main_logger.info('[MAIN] Run aborted, restarting...')
        restart = True
    except KeyboardInterrupt:
        main_logger.info('Aborting the run...')
        restart = False
    except Exception as e:
        main_logger.exception('Error in main loop', e)
        restart = True
    finally: 
        controller.stop(update_status=False) 
        
    if restart:
        machine.reset()



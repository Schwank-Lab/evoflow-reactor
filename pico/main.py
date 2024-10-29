import hardware_config
from hardware import Hardware, Clock
from pace_controller import PaceController
from logger import FileLogger, ConsoleLogger, MqttLogger, CompositeLogger
import logger
from network_client import WiFiClient, MqttClient, sync_time
from state_recorder import MqttStateRecorder, FileExpStateRecorder, FileReactorStateRecorder
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
NETWORK_RECONNECT_EVERY_MS = 5 * 60 * 1000


def init_hardware():
    global hardware, reactor_config
    reactor_config = hardware_config.load_hardware_config('configs/reactor_config.json')
    hardware = Hardware(reactor_config)
    
def init_logger():
    global clock, main_logger, console_logger, pace_logger, system_state_logger
    clock = Clock()
    console_logger = ConsoleLogger(clock, level=logger.L_INFO)
    # TODO: fix mqtt logger before re-enabling it.
    # mqtt_logger = MqttLogger(reactor_id, mqtt_client, clock, level=logger.L_INFO) 
    main_logger = FileLogger(clock, prefix='main')
    pace_logger = FileLogger(clock, prefix='pace')
    main_logger = CompositeLogger([console_logger, main_logger])
    pace_logger = CompositeLogger([console_logger, pace_logger])
    system_state_logger = FileReactorStateRecorder(clock)



def init_controller():
    global controller, file_state_recorder
    thread = lambda fn, *args: _thread.start_new_thread(fn, args)
    controller = PaceController(clock, thread, bg_logger=pace_logger, main_logger=main_logger)

    experiment_config = utils.load_json('configs/experiment_config.json')
    controller.init(hardware, reactor_config, experiment_config)
    
    reactor_state = utils.load_json('state/reactor_state.json')
    main_logger.info('[MAIN] Reactor state:', reactor_state['status'])
    if reactor_state['status'] == 'running':
        controller.start()
    
    file_state_recorder = FileExpStateRecorder(clock, experiment_config['experiment_id'], record_every_s = 5*60)
    
        
def connect_to_network():
    global mqtt_client, mqtt_exp_state_recorder, mqtt_reactor_state_recorder, commads_dispatcher

    network_config = utils.load_json('configs/network_config.json')

    wifi_client = WiFiClient(network_config)
    wifi_client.request_wifi_connection()
    sync_time(clock, network_config, main_logger)

    mqtt_client = MqttClient(wifi_client, network_config, main_logger)
    mqtt_client.request_mqtt_connection(force_topic_resubscribe=True)

    reactor_id = network_config['reactor_id']
    mqtt_exp_state_recorder = MqttStateRecorder(reactor_id, mqtt_client, main_logger, MqttStateRecorder.EXP_TOPIC_STATE)
    mqtt_reactor_state_recorder = MqttStateRecorder(reactor_id, mqtt_client, main_logger, MqttStateRecorder.REACTOR_TOPIC_STATE)
    commads_dispatcher = CommandsDispatcher(reactor_id, controller, main_logger)
    mqtt_client.add_subscriber('commands', commads_dispatcher._process_commands) # TODO: refactor
    

def receive_mqtt_commands(): 
    try: 
         mqtt_client.receive()
    except OSError as ex: 
        main_logger.exception('Mqtt Client: Error receiving message', ex)
        mqtt_client.restore_connection()

def get_controller_state(): 
    if controller.is_running():
        return 'running'
    elif controller.is_resetting_stepper():
        return 'resetting_stepper'
    else:
        return 'idle'

def run():
     last_log_cleanup = clock.ticks_ms()
     last_network_connected = clock.ticks_ms()
     while True:
        system_state = monitor.current_state()
        system_state['reactor_state'] = get_controller_state()
        console_logger.info(json.dumps(system_state))
        if network_connected: 
            mqtt_reactor_state_recorder.record(system_state)    
            last_network_connected = clock.ticks_ms()
        elif clock.ticks_ms() - last_network_connected > NETWORK_RECONNECT_EVERY_MS:
            main_logger.critical('[MAIN] Network disconnected for too long, re-starting pico.')
            return
        if controller.is_running():
            exp_state = controller.current_state()
            file_state_recorder.record(exp_state)
            console_logger.info(json.dumps(exp_state))
            if network_connected: 
                mqtt_exp_state_recorder.record(exp_state)    
            if not controller.is_alive:
                main_logger.critical('[MAIN] Controller thread has died, aborting the run')
                return
            else:
                controller.is_alive = False # set alive flag to false and let controller reset it.
        if controller.run_error:
            main_logger.critical('[MAIN] Detected controller error, aborting the run')
            return  
        if network_connected:
            receive_mqtt_commands()

        if clock.ticks_ms() - last_log_cleanup > LOG_CLEANUP_EVERY_MS:
            # disable for now, I feel like log cleaning might mess things up.
            #logger.FileLogger.clear_old_logs(clock, days=2)
            #last_log_cleanup = clock.ticks_ms()
            pass 
        
        gc.collect()
        time.sleep(RUN_CYCLE_SLEEP_S)


try: 
    init_hardware()
    print('[MAIN] Hardware initialized.')
except Exception as e:
    print('[MAIN] Error initializing hardware') 
    machine.reset()


if hardware.button_left.value() == 0 and hardware.button_right.value() == 0:
    print('[MAIN] Detected button press on re-boot, entering dev mode, stopping the run...')
else:
    init_logger() # should never fail.

    try: 
        init_controller()
        main_logger.info('[MAIN] controller initialized.')
    except Exception as e:
        main_logger.exception('[MAIN] Error initializing controller', e)
        machine.reset()

    try:
        network_connected = False 
        connect_to_network()
        network_connected = True
        main_logger.info('[MAIN] Network connected')
    except Exception as e:
        main_logger.exception('[MAIN] Error connecting to network', e)

    try:
        run()
        restart = True # run aborted, means that controller has crashed in the background.
        main_logger.critical('[MAIN] Problem with controller detected, restarting pico W...')
    except KeyboardInterrupt:
        print('Aborting the run...')
        restart = False
    except Exception as e:
        main_logger.exception('[MAIN] unhandled exception', e)
        restart = True
    finally: 
        controller.stop(save_status=not restart) 
        if network_connected:
            mqtt_client.disconnect() # TODO: refactor.
        
    if restart:
        machine.reset()



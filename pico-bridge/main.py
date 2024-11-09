import threading
import serial.tools.list_ports

from serial_comm import SerialComm
from network_client import MqttClient
from bridge import EvoBridge
import config 
import logging
from pathlib import Path


def find_pico_port():
    """ Automatically detects usb port to which pico is attached."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Pico" in port.description or "Board" in port.description:
            return port.device
    return None

def configure_logging():
      # Configure logging
    logger = logging.getLogger('pico-bridge')
    logger.setLevel(logging.DEBUG)

    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    Path('logs').mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler('logs/pico_bridge.log')
    file_handler.setLevel(logging.INFO)

    # Create formatters and add them to handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def main(): 
    logger = configure_logging()    
    pico_port = find_pico_port() 
    logger.info(f"Detected Pico port: {pico_port}")
    serial = SerialComm(pico_port, logger)
  
    mqtt = MqttClient(
        client_id=f"pico-bridge",
        broker=config.MQTT_HOST,
        port=config.MQTT_PORT,
        logger = logger
    )

    bridge = EvoBridge(serial, mqtt, logger)
    
    serial.add_listener(EvoBridge.EXPERIMENT_STATUS_TOPIC, bridge.forward_experiment_state)
    serial.add_listener(EvoBridge.REACTOR_STATUS_TOPIC, bridge.forward_reactor_state)
    serial.add_listener('log', logger.info)
    mqtt.add_handler('commands', bridge.forward_command)
    mqtt.connect()
    serial.connect()
    serial.start_listening()



if __name__ == '__main__': 
    main()

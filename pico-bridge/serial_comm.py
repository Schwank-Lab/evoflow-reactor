import serial
import json
import threading
import time
import serial.tools.list_ports



def find_pico_port():
    """ Automatically detects usb port to which pico is attached."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Pico" in port.description or "Board" in port.description:
            return port.device
    return None

class SerialComm:
    def __init__(self, logger, baudrate=115200):
        self._baudrate = baudrate
        self._logger = logger
        self.ser = None
        self.listeners = {}
        self._stop_event = threading.Event()
        self._lock = threading.Lock()  # Add a lock for thread safety

    def connect(self):
        if self.ser: 
            self.ser.close()
        port = find_pico_port()
        if port is None: 
            self._logger.warning('SerialComm: Pico port not found.')
            return 
        self._logger.info(f"SerialComm: Connecting to {port}")
        self.ser = serial.Serial(port, self._baudrate, timeout=1)

    def is_connected(self):
        with self._lock:
            return self.ser is not None and self.ser.is_open

    def add_listener(self, topic, callback):
        self.listeners[topic] = callback

    def send_message(self, topic, data):
        with self._lock:
            if not self.ser:
                raise ValueError("Serial connection is not established")
            msg = json.dumps({"topic": topic, "data": data})
            self.ser.write(msg.encode() + b'\n')


    def stop_listening(self):
        self._stop_event.set()

    def start_listening(self):
        while not self._stop_event.is_set():
            if not self.is_connected():
                self._logger.info("Serial connection is dropped. Trying to reconnect")
                self.connect()
                time.sleep(2)
                continue
            with self._lock:
                if not self.ser:
                    raise ValueError("Serial connection is not established")
                try: 
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode().strip()
                        try:
                            msg = json.loads(line)
                            self._logger.debug(msg)
                            topic = msg.get("topic")
                            data = msg.get("data")
                            if topic in self.listeners:
                                self.listeners[topic](data)
                        except json.JSONDecodeError:
                            print("Received malformed message")
                    else: 
                        self._logger.debug('No data available')
                except OSError as e: 
                    self._logger.error(f"Serial connection error: {e}")
                    self.ser.close()
                    self.ser = None 
            time.sleep(1)
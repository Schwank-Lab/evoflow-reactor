import ujson
import usb_cdc
import utime

class SerialComm:
    def __init__(self):
        """
        Initialize the USB serial communication.
        """
        # Use the data channel for communication to keep REPL separate
        self.serial = usb_cdc.data
        self.listeners = {}

    def add_listener(self, topic, callback):
        """
        Register a callback for a specific topic.
        
        Args:
            topic (str): The topic to listen for.
            callback (function): The function to call when a message with the given topic is received.
        """
        self.listeners[topic] = callback

    def send_message(self, topic, data):
        """
        Send a JSON message with the given topic and data.
        
        Args:
            topic (str): The topic of the message.
            data (dict): The data payload of the message.
        """
        msg = ujson.dumps({"topic": topic, "data": data})
        # TODO: catch exceptions.
        self.serial.write((msg + '\n').encode())
        

    def receive_messages(self):
        """
        Receive all messages currently available on the serial buffer.
        """
        while self.serial.any():
            try:
                line = self.serial.readline()
                if line:
                    line = line.decode().strip()
                    msg_data = ujson.loads(line)
                    topic = msg_data.get("topic")
                    data = msg_data.get("data")
                    if topic in self.listeners:
                        # TODO: catch exceptions.
                        self.listeners[topic](data)
            except ValueError:
                print("Received malformed message")
            except Exception as e:
                print("Error:", e)
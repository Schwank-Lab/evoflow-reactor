import ujson
import utime
import select
import sys

class SerialComm:
    def __init__(self):
        """
        Initialize the USB serial communication.
        """
        # Use the data channel for communication to keep REPL separate
        self.listeners = {}
        self._buffer = ""

    def add_listener(self, topic, callback):
        """
        Register a callback for a specific topic.
        
        Args:
            topic (str): The topic to listen for.
            callback (function): The function to call when a message with the given topic is received.
        """
        self.listeners[topic] = callback

    def _send_error(self, *args):
        """
        Send an error message with the given error string.
        
        Args:
            error (str): The error message to send.
        """
        try: 
            args = ["SerialComm: "] + list(args)
            msg = " ".join(map(str, args))
            msg = ujson.dumps({"topic": "log", "message": msg})
            print(msg)
        except Exception as e: 
            print("{topic: 'log', message: 'Error sending message: " + str(e) + "'}")

    def send_message(self, topic, data):
        """
        Send a JSON message with the given topic and data.
        
        Args:
            topic (str): The topic of the message.
            data (dict): The data payload of the message.
        """
        try: 
            msg = ujson.dumps({"topic": topic, "data": data})
            msg = msg.replace('\n', '<newline>')
            print(msg)
        except Exception as e:
            self._send_error("Error sending message:", e)
        
    def is_data_available(self, timeout=0):
        """Check if there is data available on stdin."""
        return select.select([sys.stdin], [], [], timeout)[0]
    
    def receive_messages(self):
        """
        Receive all messages currently available on the serial buffer.
        Messages are delimited by newline characters ('\n').
        """
        try:
            while self.is_data_available(timeout=0):
                # Read all available data from stdin
                line = sys.stdin.readline()
                self.send_message("log", f"SerialComm: Received message")
                # Decode bytes to string and append to buffer
                try:
                    msg_data = ujson.loads(line)
                    topic = msg_data.get("topic")
                    data = msg_data.get("data")
                    if topic in self.listeners:
                        try:
                            self.listeners[topic](data)
                        except Exception as listener_error:
                            self._send_error(f"Listener error for topic '{topic}':", listener_error)
                except Exception as e:
                    self._send_error("Error processing message:", e)
        except Exception as e:
            self._send_error("Error reading from stdin:", e)



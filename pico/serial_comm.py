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
        if '\n' in msg: 
            raise ValueError("Message contains newline character")
        print(msg)
        
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
                data = sys.stdin.read()
                # Decode bytes to string and append to buffer
                self._buffer += data
                messages = self._buffer.split('\n')

                # Keep the last part in the buffer (it may be incomplete)
                self._buffer = messages.pop()  # Last element

                for line in messages:
                    line = line.strip()
                    if line:
                        try:
                            msg_data = ujson.loads(line)
                            topic = msg_data.get("topic")
                            data = msg_data.get("data")
                            if topic in self.listeners:
                                try:
                                    self.listeners[topic](data)
                                except Exception as listener_error:
                                    print(f"Listener error for topic '{topic}':", listener_error)
                        except ujson.JSONDecodeError:
                            print("Received malformed JSON message:", line)
                        except Exception as e:
                            print("Error processing message:", e)
        except Exception as e:
            print("Error reading from stdin:", e)

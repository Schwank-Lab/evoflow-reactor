import paho.mqtt.client as mqtt
from typing import Callable
import logging 
import json 

class MqttClient:
    def __init__(
        self,
        client_id: str,
        broker: str,
        port: int,
        topics_handlers: dict[str, Callable] = {},
        logger = logging.getLogger(__name__),
    ):
        self.logger = logger
        self.broker = broker
        self.port = port
        self.topics_handlers = {}
        for topic, handler in topics_handlers.items():
            self.add_handler(topic, handler)

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id,
            clean_session=True,
         )
        self.client.enable_logger(logger)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

        self.client.retry_first_connection = True

    
    def add_handler(self, topic: str, handler: Callable):
        if topic in self.topics_handlers:
            self.topics_handlers[topic].append(handler)
        else:
            self.topics_handlers[topic] = [handler]

    def connect(self):
        """ Asyncronously connects to the MQTT broker. """
        self.client.reconnect_delay_set(min_delay=30, max_delay=30)
        self.client.connect_async(self.broker, self.port, 60) 
        self.client.loop_start()
        
    def on_connect(self, client, userdata, flags, rc, properties=None):
        self.logger.info("MqttListner#on_connect: Connected with result code " + str(rc))
        self._is_connected = True
        topics = self.topics_handlers.keys()
        if len(topics) > 0:
            self.logger.info(f"Subscribing to topics {topics}")
            client.subscribe([(t, 1) for t in topics])
    
    def on_disconnect(self, client, userdata, dicsonnect_flags, rc, properties):
        self.logger.info("MqttListner#on_disconnect")
        self.logger.debug("client= "  + str(client._client_id))
        self.logger.debug("userdata= " + str(userdata))
        self.logger.debug("dicsonnect_flags= " + str(dicsonnect_flags))
        self.logger.debug("rc= " + str(rc))
        self.logger.debug("properties= " + str(properties))
        self._is_connected = False

    def on_message(self, client, userdata, msg):
        try: 
            self.logger.info(f"Received message on topic {msg.topic} with payload {msg.payload}")
            topic = msg.topic
            data = json.loads(msg.payload.decode("utf-8"))
        except Exception as e:
            self.logger.error(f"Error occurred while parsing message\n{msg}")
            self.logger.error(e, exc_info=True)
            return
        
        self.logger.debug(f"Message on topic {topic} with data {data}")
        for handler in self.topics_handlers.get(msg.topic, []):
            try: 
                handler(data)
            except Exception as e:
                self.logger.error(f"An error occurred while handling topic {topic}:  {e}", exc_info=True)

    def send_msg(self, topic: str, msg: str|dict):
        if isinstance(msg, dict):
            msg = json.dumps(msg)
        self.client.publish(topic, msg)
            
    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
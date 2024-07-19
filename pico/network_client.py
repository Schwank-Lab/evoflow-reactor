import network
from libs.umqtt.simple import MQTTClient
from time import sleep
import ntptime


STATE_UNKNOWN = 0
STATE_WIFI_NOT_CONNECTED = 1
STATE_WIFI_CONNECTING = 2
STATE_WIFI_CONNECTED = 3


def sync_time(clock, network_config, logger):
    ntptime.host = network_config['mqtt_host']
    logger.info('sync_time: Requesting NTP time... Time before request:', clock.localtime())

    try:
        ntptime.settime()
        logger.info('sync_time: Time after request:', clock.localtime())
    except Exception as ex:
        logger.exception('Could not synchronize time', ex)


class WiFiClient:
    def __init__(self, config):
        self._state = STATE_WIFI_NOT_CONNECTED
        self._config = config

    def request_wifi_connection(self):
        print("WiFi Client: Connecting ...")
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)
        self._wlan.connect(self._config['wifi_ssid'], self._config['wifi_pwd'])
        self._state = STATE_WIFI_CONNECTING
        while self._wlan.isconnected() == False:
            self._state = STATE_WIFI_CONNECTING
            print("WiFi Client: Waiting for connection")
            sleep(1)

        print("WiFi Client: Connection Established")
        self._gateway_ip = self._wlan.ifconfig()[2]
        print(self._wlan.ifconfig())
        self._state = STATE_WIFI_CONNECTED

    def check_wifi_connection(self):
        if self._wlan.isconnected() == False: 
            self._state = STATE_WIFI_NOT_CONNECTED
            print("WiFi Connection Dropped, restoring ...")
            self.request_wifi_connection()
            

class MqttClient:
    
    def __init__(self, wifi_client: WiFiClient, config: dict, logger):
        self._wifi = wifi_client
        self._config = config
        self._mqtt_client = MQTTClient(
            client_id=str(self._config['reactor_id']),
            server=self._config['mqtt_host'],
            user=self._config['mqtt_uname'],
            password=self._config['mqtt_pwd'],
        )
        self._mqtt_client.set_callback(self._process_message)
        self._mqtt_connected = False
        self._subscribers = {}
        self._logger = logger

    def add_subscriber(self, topic, callback): 
        if topic not in self._subscribers.keys():
            self._subscribers[topic] = []
            if self._mqtt_connected:
                self._mqtt_client.subscribe(topic, qos=2)

        self._subscribers[topic].append(callback)

    def _process_message(self, topic, msg):
        topic = topic.decode('utf-8')
        msg = msg.decode('utf-8')
        self._logger.info('Mqtt Client: received message', topic, msg)
        if topic in self._subscribers.keys():
            for callback in self._subscribers[topic]:
                callback(msg)

    def request_mqtt_connection(self, force_topic_resubscribe=False) -> bool:
        if self._wifi._state != STATE_WIFI_CONNECTED:
            self._logger.critical("Mqtt Client: cannot connect to MQTT broker. WiFi not ready ...")
            return False
        self._logger.info("Mqtt Client: Connecting to broker ...")
        # We connect to the broker with a persistent session, 
        # to make sure messages lost during wifi disconnection are re-sent
        try :
            is_restored_session = self._mqtt_client.connect(clean_session=False)
        except OSError as e:
            self._logger.exception("Mqtt Client: Error connecting to broker", e)
            return False
        self._mqtt_connected = True
        self._logger.info("Mqtt Client: Connecting to broker ... Done")
        
        if not force_topic_resubscribe and is_restored_session:
            self._logger.info('Skipping topic resubscription.')
            return True
        
        self._logger.info('Mqtt Client: Subscribing to topics ...')
        for topic in self._subscribers.keys():
            self._mqtt_client.subscribe(topic)
        self._logger.info('Mqtt Client: Subscribing to topics ... Done')
        return True
        
    def restore_connection(self) -> bool: 
        self._mqtt_connected = False
        self._wifi.check_wifi_connection()
        return self.request_mqtt_connection()

    def publish(self, topic, msg, qos=0):
        if self._mqtt_connected == False: 
            self._logger.critical('Mqtt Client: cannot publish the message, MQTT not connected.')
        self._mqtt_client.publish(topic, msg, qos=qos)
        return True
         
    def receive(self) -> bool: 
        if not self._mqtt_connected:
            self._logger.critical('Mqtt Client: cannot receive messages, MQTT not connected.')
        self._mqtt_client.check_msg()
        return True
    
    def disconnect(self):
        if not self._mqtt_connected:
            pass 
        try: 
            self._mqtt_client.disconnect()
        except OSError as e:
            self._logger.exception('Mqtt Client: Error disconnecting from broker', e)

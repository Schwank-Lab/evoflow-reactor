import network
from umqtt.simple import MQTTClient
from time import sleep
import _thread
from math import sin
import uasyncio as asyncio

STATE_UNKNOWN = 0
STATE_WIFI_NOT_CONNECTED = 1
STATE_WIFI_CONNECTING = 2
STATE_WIFI_CONNECTED = 3


class MqttClient:
    def __init__(self, wifi_client, config):
        self._wifi = wifi_client
        self._config = config
        self._mqtt_client = MQTTClient(
            client_id=self._config['mqtt_client_id'],
            server=self._config['mqtt_host'],
            user=self._config['mqtt_uname'],
            password=self._config['mqtt_pwd'],
        )
        self._mqtt_client.set_callback(self._process_message)
        self._mqtt_connected = False
        self._subscribers = {}

    def _check_connection(self):
        self._wifi.check_wifi_connection()
        # check we are connected to mqtt server
        # ...

    def add_subscriber(self, topic, callback): 
        if topic not in self._subscribers.keys():
            self._subscribers[topic] = []

        self._subscribers[topic].append(callback)

    def _process_message(self, topic, msg):
        if topic in self._subscribers.keys():
            for callback in self._subscribers[topic]:
                callback(msg)


    def request_mqtt_connection(self):
        if self._wifi._state == STATE_WIFI_CONNECTED:
            print("Mqtt Client: Connecting to broker ...")
            self._mqtt_client.connect()
            self._mqtt_connected = True
            print("Mqtt Client: Connecting to broker ... Done")

        else:
            print("Mqtt Client: cannot connect to MQTT broker. WiFi not ready ...")

    def publish(self, topic, msg):
        if self._wifi._state != STATE_WIFI_CONNECTED:
            # TODO: try to re-connect
            print('Mqtt Client: cannot publish the message, WiFi not connected.')
        elif self._mqtt_connected == False: 
            print('Mqtt Client: cannot publish the message, MQTT not connected.')
        else:
            self._mqtt_client.publish(topic, msg)
         
    def receive(self): 
        self._mqtt_client.check_msg()

           


class WiFiClient:
    def __init__(self, config):
        self._state = STATE_WIFI_NOT_CONNECTED
        self._config = config

    def request_wifi_connection(self):
        print("WiFi Client: Connecting ...")
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)
        self._wlan.connect(self._config['wifi_ssid'], self._config['wifi_pwd'])
        while self._wlan.isconnected() == False:
            self._state = STATE_WIFI_CONNECTING
            print("WiFi Client: Waiting for connection")
            sleep(1)

        self.check_wifi_connection()

    def check_wifi_connection(self):
        if self._wlan.isconnected() == True:
            print("WiFi Client: Connection Established")
            self._gateway_ip = self._wlan.ifconfig()[2]
            print(self._wlan.ifconfig())
            self._state = STATE_WIFI_CONNECTED
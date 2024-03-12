import network
import usocket

from time import sleep

from config import PORT 

ssid = 'radyga'
password = 'undertherainbow'

STATE_UNKNOWN = 0
STATE_WIFI_NOT_CONNECTED = 1
STATE_WIFI_CONNECTING = 2
STATE_SERVER_NOT_CONNECTED = 3
STATE_SERVER_CONNECTING = 4
STATE_SERVER_CONNECTED = 5

class Client:
    
    def __init__(self, callback):
        self._state = STATE_WIFI_NOT_CONNECTED
        self._callback = callback
        
    def cycle(self):
        if self._state == STATE_WIFI_NOT_CONNECTED:
            self.request_wifi_connection()
        elif self._state == STATE_WIFI_CONNECTING:
            self.check_wifi_connection()
        elif self._state == STATE_SERVER_NOT_CONNECTED:
            self.request_server_connection()
        elif self._state == STATE_SERVER_CONNECTING:
            self.check_server_connection()
        elif self._state == STATE_SERVER_CONNECTED:
            self.receive_commands()
        else:
            print('unknown client state')
    
    def request_wifi_connection(self):
        self._wlan = network.WLAN(network.STA_IF)
        self._wlan.active(True)
        self._wlan.connect(ssid, password)
        self._state = STATE_WIFI_CONNECTING
    
    def check_wifi_connection(self):
        if self._wlan.isconnected() == True:
            print('Wifi Connection Established')
            self._gateway_ip = wlan.ifconfig()[2]
            print(wlan.ifconfig())
            self._state = STATE_SERVER_NOT_CONNECTED
        else:
            print('Waiting for WiFi connection')
            
    def request_server_connect(self):
        self._sock = usocket.socket()
        self._sock.setblocking(False)
        self._state = STATE_SERVER_CONNECTING
    
    def check_server_connection(self):
        is_connected = (self._sock.connect_ex((self._gateaway_ip, PORT)) == 0)
        if is_connected == True:
            print('Server connected')
            self._state = STATE_SERVER_CONNECTED
    
    def receive_commands(self):
        """ Returns False if connection is lost."""
        try:
            msg = self._sock.recv(1024)
            if len(msg) == 0: 
                return True
            try:  
                self._callback(msg)
            except Exception as ex:
                print('Error while executing callback', ex)
            finally:
                return True
        except ex:
            print('Error while receiving command from server', ex)
            self.server_disconnect()
            
    def server_disconnect(self):
        self._sock.close()
        self._state = STATE_SERVER_NOT_CONNECTED



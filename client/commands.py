import paho.mqtt.client as mqtt
import json
import sys

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully.")
    else:
        print(f"Connection failed with code {rc}")

# Extract command line arguments
reactor_id = sys.argv[1]
command = sys.argv[2]

# Create the MQTT client
client = mqtt.Client()

# Set the on_connect event handler
client.on_connect = on_connect

# Connect to the MQTT broker
broker_address = "192.168.31.10"  # Replace with your MQTT broker address
port = 1883  # Default MQTT port
client.connect(broker_address, port, 60)

# Start the loop
client.loop_start()

# Prepare the payload
payload = json.dumps({"reactor_id": int(reactor_id), "command": command})

# Publish the message
client.publish("commands", payload)

# Stop the loop
client.loop_stop()

# Disconnect the client
client.disconnect()

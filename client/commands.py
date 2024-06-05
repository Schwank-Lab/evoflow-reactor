import paho.mqtt.client as mqtt
import json
import sys
import argparse
import os

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully.")
    else:
        print(f"Connection failed with code {rc}")

def load_config(config_path):
    with open(config_path, 'r') as file:
        return json.load(file)

def create_payload(args):
    payload = {
        "reactor_id": args.reactor_id,
        "command": args.command
    }
    if args.experiment_id:
        payload["experiment_id"] = args.experiment_id
    if args.config and args.command in ['new_experiment', 'update_experiment']:
        payload["experiment_config"] = load_config(args.config)
    if args.config and args.command == 'update_reactor_config':
        payload['reactor_config'] = load_config(args.config)
    if args.stepper_vol:
        payload["stepper_vol"] = args.stepper_vol
    return payload

# Set up argument parser
parser = argparse.ArgumentParser(description='Send commands to the experiments via MQTT.')
parser.add_argument('reactor_id', type=str, help='ID of the reactor')
parser.add_argument('command', type=str, choices=['start', 'stop', 'pause', 'new_experiment', 'update_experiment', 
                                                  'stepper_forward', 'stepper_reverse', 'stepper_stop',
                                                  'update_reactor_config'],
                    help='Command to send to the reactor')
parser.add_argument('--experiment_id', type=str, help='ID of the experiment (required for new_experiment and update_experiment_config)')
parser.add_argument('--config', type=str, help='Path to the experiment configuration file (required for new_experiment and update_experiment_config)')
parser.add_argument('--stepper_vol', type=int, help='Volume of the stepper motor to move (required for stepper_forward and stepper_reverse)')

# Parse arguments
args = parser.parse_args()

# Validate arguments for specific commands
if args.command in ['new_experiment', 'update_experiment']:
    if not args.experiment_id or not args.config:
        parser.error("experiment_id and config are required for new_experiment and update_experiment_config commands")
    if not args.config: 
        parser.error("config is required for new_experiment and update_experiment_config commands")

if args.command in ['stepper_forward', 'stepper_reverse']:
    if not args.stepper_vol:
        parser.error("stepper_vol is required for stepper_forward and stepper_reverse commands")

if args.command == 'update_reactor_config':
    if not args.config:
        parser.error("config is required for update_reactor_config command")

# Create the MQTT client
client = mqtt.Client()

# Set the on_connect event handler
client.on_connect = on_connect

# Connect to the MQTT broker
broker_address = "10.66.4.7"  # Replace with your MQTT broker address
port = 1883  # Default MQTT port
client.connect(broker_address, port, 60)

# Start the loop
client.loop_start()

# Prepare the payload
payload = create_payload(args)
payload_json = json.dumps(payload)

# Publish the message
client.publish("commands", payload_json)

# Stop the loop
client.loop_stop()

# Disconnect the client
client.disconnect()

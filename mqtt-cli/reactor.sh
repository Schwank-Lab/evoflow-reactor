#!/bin/bash

mosquitto_sub -h 192.168.4.1 -p 1883 -t status/reactor

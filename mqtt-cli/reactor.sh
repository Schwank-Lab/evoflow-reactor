#!/bin/bash

mosquitto_sub -h 10.66.4.7 -p 1883 -t status/reactor

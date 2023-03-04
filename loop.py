#!/usr/bin/env python

# A simple control loop for turning on heater to keep within a measured range of temperatures

# TODO
#  - Synchronize initial state of heater, rather than forcing it to be set off

import time
import re 
import pywemo
import paho.mqtt.client as mqtt

LOWER_TEMPERATURE = 65.0
UPPER_TEMPERATURE = 74.0

global SM_STATE
SM_STATE__OFF = 0
SM_STATE__ON =  1
SM_INITIAL_STATE = SM_STATE__OFF
SM_STATE = SM_INITIAL_STATE


mqtt_broker_addr = "192.168.50.6"
topic_base = "picow0"
topic_temperature = topic_base + "/probe_temperature"

wemo_name_to_topic_mapping = {
    'Bedroom 2 Plant Heater':
        {'topic' : topic_temperature}
    }

devices_of_interest = tuple(wemo_name_to_topic_mapping.keys())

print(devices_of_interest)

# Wemo discovery
devices = pywemo.discover_devices()
device_name_to_url = {}

for device in devices:
    name = device.name
    if name in devices_of_interest:
        ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', device.deviceinfo.controlURL )[0]
        url = pywemo.setup_url_for_address(ip)        
        device_name_to_url [name] = url 

device_url = device_name_to_url[devices_of_interest[0]]
device = pywemo.discovery.device_from_description(device_url)

def on_connect(client, userdata, flags, rc):
    connect_report = "Wemo %s: %s" % (device.device_type, device.name)
    print(connect_report)
    client.subscribe(topic_temperature)

def on_message(client, userdata, msg):
    try:
        temperature = msg.payload.decode()
    except:
        return

    #print(temperature)
    update_temperature(device, temperature)

def set_device_state(device, to_state):
    print(' setting device {} state to {}'.format(device.name, to_state))
    if to_state == SM_STATE__ON:
        print ("Turning device ON")
        device.on()
        time.sleep(2)
    if to_state == SM_STATE__OFF:
        print ("Turning device OFF")
        device.off()
        time.sleep(2)

# main state machine
def update_state(device, temperature):
    global SM_STATE 
    print ('current state: {}, temperature {}'.format(SM_STATE, temperature))

    if SM_STATE == SM_STATE__OFF:
        if temperature < LOWER_TEMPERATURE:
            set_device_state(device, SM_STATE__ON)
            SM_STATE = SM_STATE__ON
        else:
            # we are off and above the LOWER_TEMPERATURE
            pass 
    elif SM_STATE == SM_STATE__ON:
        if temperature > UPPER_TEMPERATURE:
            set_device_state(device, SM_STATE__OFF)
            SM_STATE = SM_STATE__OFF
        else:
            # we are on and below the UPPER_TEMPERATURE
            pass        
    else: # unknown state / condition!
        pass


def update_temperature(device, temperature_F_string):
    temperature_float = parse_temperature(temperature_F_string)
    update_state(device, temperature_float)

temperature_F_regex = re.compile(r"(\d+\.?\d*)")
def parse_temperature(temperature_F_string):
    m = temperature_F_regex.match(temperature_F_string)
    print ("{} ".format(m.group(0)), end="")
    value = float(m.group(0))
    return value

# Setup MQTT Client
client = mqtt.Client()
client.connect(mqtt_broker_addr,1883,60)
client.on_connect = on_connect
client.on_message = on_message
# Start the MQTT thread that handles this client
client.loop_start()

# set initial state
set_device_state(device, SM_INITIAL_STATE)
print ("Starting Control LOOP")

while True:
    print("D{} SM{} ".format(device.get_state(), SM_STATE), end="")
    time.sleep(60)
#!/usr/bin/env python

import time
import re 
import pywemo
import paho.mqtt.client as mqtt

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

    print(temperature)
    update_temperature(temperature)

def update_temperature(temperature_F_string):
    temperature_float = parse_temperature(temperature_F_string)
    print("Do something here.  temperature is {}".format(temperature_float))
    pass

temperature_F_regex = re.compile(r"(\d+\.?\d*)")
def parse_temperature(temperature_F_string):
    m = temperature_F_regex.match(temperature_F_string)
    print (m.group(0))
    value = float(m.group(0))
    return value

# Setup MQTT Client
client = mqtt.Client()
client.connect(mqtt_broker_addr,1883,60)
client.on_connect = on_connect
client.on_message = on_message
# Start the MQTT thread that handles this client
client.loop_start()

while True:
    print ('.', end="")
    time.sleep(10)
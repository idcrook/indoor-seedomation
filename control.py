#!/usr/bin/env python

import time
import re 
import pywemo

wemo_name_to_topic_mapping = {
    'Bedroom 2 Plant Heater':
        {'topic' : ''}
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

print(device.name, device.get_state())
device.toggle()
time.sleep(2)
print(device.name, device.get_state())
device.toggle()
time.sleep(2)
print(device.name, device.get_state())

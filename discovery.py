#!/usr/bin/env python

import pywemo
import re

devices_of_interest = ('Bedroom 2 Plant Light 2', 
    'Bedroom 2 Plant Heater')

devices = pywemo.discover_devices()
for device in devices:
    print ("  {}".format(device.name))

device_mapping = {}

for device in devices:
    name = device.name
    #print(name)
    #print('state = ', device.get_state())
    metainfo = str(device.metainfo.GetMetaInfo())
    deviceinfo = str(device.deviceinfo.GetDeviceInformation())
    if hasattr(device, "GetSmartDevInfo"):
        print(device.basicevent.GetSmartDevInfo())
    #print(device.deviceinfo.controlURL)
    ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', device.deviceinfo.controlURL )[0]
    url = pywemo.setup_url_for_address(ip)
    if name in devices_of_interest:
        device_mapping [name] = url 
        #print(name, metainfo, deviceinfo)

print(device_mapping)

for name, url in device_mapping.items(): 
    #print (name, url)
    device = pywemo.discovery.device_from_description(url)
    print(device.name)
#!/usr/bin/env python

import asyncio
import json

from kasa import Discover, Credentials

global SM_STATES
SM_STATE__OFF = 0
SM_STATE__ON =  1
SM_INITIAL_STATE = SM_STATE__OFF
SM_STATES = {}
TEMPERATURES_LAST_READ = {}

CONFIG_FILE = 'config.example.json'
CONFIG_FILE = 'config.secrets.json'

DEFAULT_MQTT_BROKER_ADDR = "192.168.50.6"
DEFAULT_MQTT_PORT = 1883
DEFAULT_TOPIC_BASE = "picow0"
DEFAULT_TEMPERATURE_KEY = "temperature"
DEFAULT_HOST_ADDRESS = '192.168.50.6'

CONFIG = {}
DEVICE_MAPPING = {'probes':{},
                  'heaters':{},
                  'topics':{}
                  }
PROBE_MAPPING = DEVICE_MAPPING['probes']
TOPIC_MAPPING = DEVICE_MAPPING['topics']
HEATER_MAPPING = DEVICE_MAPPING['heaters']

try:
    with open(CONFIG_FILE, 'r') as jsonfile:
        CONFIG = json.loads(jsonfile.read())
        print(CONFIG)
except OSError as ose:
    if ose.errno not in (errno.ENOENT,):
        # this re-raises the same error object.
        raise


# subtrees of the config file
MQTT_CONF = CONFIG.get("mqtt", {})
SENSORS_CONF = CONFIG.get("sensors", {})
CONTROLS_CONF = CONFIG.get("controls", {})
GLOBAL_CONF = CONFIG.get("global", {})

# Hosts
HOSTS_CONF = CONTROLS_CONF.get('hosts', {})
print (HOSTS_CONF)
host_address = HOSTS_CONF[0].get('address', DEFAULT_HOST_ADDRESS)
print(host_address);

# Heaters
HEATERS = HOSTS_CONF[0].get('heaters', [])
print (HEATERS)
for heater in HEATERS:
    print(heater.get('plug_alias'))


async def main():
    dev = await Discover.discover_single(host_address)
    print(dev.model)
    await dev.update()

if __name__ == "__main__":
    asyncio.run(main())

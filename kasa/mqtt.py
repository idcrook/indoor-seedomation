#!/usr/bin/env python

import asyncio
import json
import aiomqtt

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
HEATER_DISABLED_SENTINEL_VALUE = 'DISABLED'

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

# MQTT config
#print(MQTT_CONF)
MQTT_BROKER = bytes(MQTT_CONF.get('broker', DEFAULT_MQTT_BROKER_ADDR), 'utf-8')
MQTT_PORT = MQTT_CONF.get('port', DEFAULT_MQTT_PORT)
print ("Using MQTT ", MQTT_BROKER, MQTT_PORT)

# Sensors
PROBES = SENSORS_CONF.get('probes', {})

for probe in PROBES:
    for probe_name in probe:
        topic = probe[probe_name]['topic']
        #print (probe_name, topic)
        PROBE_MAPPING[probe_name] = {}
        PROBE_MAPPING[probe_name]['topic'] = topic
        TOPIC_MAPPING[topic] = {}
        TOPIC_MAPPING[topic]['probe'] = probe_name

#print(DEVICE_MAPPING)

# Hosts
HOSTS_CONF = CONTROLS_CONF.get('hosts', {})
for host in HOSTS_CONF:
    host_address = host.get('address', DEFAULT_HOST_ADDRESS)
    print("kasa host", host_address);
    this_host_heaters = host.get('heaters', [])
    #print (this_host_heaters)
    for heater_info in this_host_heaters:
        heater_name = heater_info.get('plug_alias')
        probe_name = heater_info['probe']
        upper_temp = heater_info['upper_temperature']
        lower_temp = heater_info['lower_temperature']
        topic = PROBE_MAPPING[probe_name]['topic']
        #print (host_address, heater_name, topic)
        HEATER_MAPPING[heater_name] = {}
        HEATER_MAPPING[heater_name]['host'] = host_address
        HEATER_MAPPING[heater_name]['plug_alias'] = heater_name
        HEATER_MAPPING[heater_name]['topic'] = topic
        HEATER_MAPPING[heater_name]['probe'] = probe_name
        HEATER_MAPPING[heater_name]['upper_T'] = upper_temp
        HEATER_MAPPING[heater_name]['lower_T'] = lower_temp
        TOPIC_MAPPING[topic]['heater'] = HEATER_MAPPING[heater_name]

        if heater_info.get('enabled', False):
            PROBE_MAPPING[probe_name]['heater'] = heater_name
        else:
            print("Heater", heater_name, "is not enabled.")
            PROBE_MAPPING[probe_name]['heater'] = HEATER_DISABLED_SENTINEL_VALUE

#print(DEVICE_MAPPING)

async def subscribe_device(client, heater_name, topic):
    print("subscribing", topic, heater_name)
    await client.subscribe(topic)

# FIXME: turn off or on based on temperature reading
async def handle_temperature_update(topic, payload):
    heater = TOPIC_MAPPING[topic]['heater']
    print (topic, payload, heater['plug_alias'])

async def main():
    async with aiomqtt.Client(MQTT_BROKER) as client:
        # Subscribe to MQTT
        for probe_name in PROBE_MAPPING:
            heater_name = PROBE_MAPPING[probe_name].get(
                'heater', HEATER_DISABLED_SENTINEL_VALUE)
            if heater_name != HEATER_DISABLED_SENTINEL_VALUE:
                topic = PROBE_MAPPING[probe_name]['topic']
                await subscribe_device(client, heater_name, topic)
        # Handle MQTT updates
        async for message in client.messages:
            await handle_temperature_update(message.topic.value, message.payload)


        # TODO: add concurrent processing
        # https://aiomqtt.bo3hm.com/subscribing-to-a-topic.html#processing-concurrently

if __name__ == "__main__":
    asyncio.run(main())

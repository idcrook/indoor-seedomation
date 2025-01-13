#!/usr/bin/env python

# simple control loop for turning on heater to keep within a measured range of temperatures

# FIXME
#
#  - Turn off heaters for KeyboardInterrupt / Exit
#
#
# TODO
#
#  - Add environment variable support for configuration
#  - Add tests, modularity
#  - Synchronize initial state of heater, rather than forcing it to be set off
#  - Implement a PID controller?
#  - Do proper logging
#  - Add watchdog timeout for new messages not received (temperature updates)
#    - could be sign that probe or network is down?
#    - may want to attempt to turn off switch in that case and go to a new panic state

import asyncio
import datetime
import json
import functools
import re

import aiomqtt
from kasa import Device, Discover, Credentials

DEFAULT_DISPLAY_LOOP_SLEEP_TIME = 600

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

# Globals
DISPLAY_LOOP_SLEEP_TIME = GLOBAL_CONF.get('loop_sleep_time', DEFAULT_DISPLAY_LOOP_SLEEP_TIME)
print("Status display time in seconds:", DISPLAY_LOOP_SLEEP_TIME)

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

# mapping of kasa device friendly name to heater object
DEVICE_LIST = {}

async def register_device(heater_info):
    "Initialize plugs and their data structures."
    # print (heater_info)
    heater_name = heater_info['plug_alias']
    host_address = heater_info['host']
    device = await Discover.discover_single(host_address)
    config_dict = device.config.to_dict()
    dev = await Device.connect(config=Device.Config.from_dict(config_dict))
    # print(dev)
    _socket = None
    index = _index = 0
    for plug in dev.children:
        if plug.alias == heater_name:
            _index = index
            _socket = plug
            print ("heater found at index", _index, _socket)
        index += 1
    if _socket != None:
        device_info = {}
        device_info['connect_config'] = config_dict
        device_info['_device'] = dev
        device_info['_child_index'] = _index
        device_info['_plug'] = _socket
        DEVICE_LIST[heater_name] = device_info
        # turn off if it is on
        if _socket.is_off != True:
            await _socket.turn_off()

        # initialize state machine
        SM_STATES[heater_name] = SM_INITIAL_STATE
        TEMPERATURES_LAST_READ[heater_name] = 0.0
    else :
        print('ERROR: Did not find heater control')

def get_device_info_from_heater_name(heater_name):
    device_info = DEVICE_LIST.get(heater_name);
    # print(heater_name, device_info)
    return device_info

async def subscribe_device(client, heater_name, topic):
    print("subscribing", topic, heater_name)
    await client.subscribe(topic)

def get_heater_lower_temperature(heater_name):
    return HEATER_MAPPING[heater_name]['lower_T']

def get_heater_upper_temperature(heater_name):
    return HEATER_MAPPING[heater_name]['upper_T']


def get_heater_sm_state(heater_name):
    # global SM_STATES
    return SM_STATES[heater_name]

def set_heater_sm_state(heater_name, state):
    global SM_STATES
    SM_STATES[heater_name] = state

async def set_kasa_outlet_state(heater_name, to_state):
    "controls actual Kasa outlet where heater is plugged in."

    print(' setting device {} state to {}'.format(heater_name, to_state))
    heater_device_info = get_device_info_from_heater_name(heater_name)
    # config_dict = device.config.to_dict()
    # dev = await Device.connect(config=Device.Config.from_dict(config_dict))

    plug = heater_device_info ['_plug']

    if to_state == SM_STATE__ON:
        print ("Turning ON device {}".format(heater_name))
        # device.on()
        await plug.turn_on()
        await plug.update()
    if to_state == SM_STATE__OFF:
        print ("Turning OFF device {}".format(heater_name))
        # device.off()
        await plug.turn_off()
        await plug.update()



# main update of state machine
async def update_state(heater_name, temperature):
    current_SM_STATE = get_heater_sm_state(heater_name)

    print ('"{}" SM: {}, T: {}'.format(
        heater_name[-8:], current_SM_STATE, temperature))

    # print ('current SM:', current_SM_STATE)
    if current_SM_STATE == SM_STATE__OFF:
        if temperature < get_heater_lower_temperature(heater_name):
            await set_kasa_outlet_state(heater_name, SM_STATE__ON)
            set_heater_sm_state(heater_name, SM_STATE__ON)
        else:
            # we are off and above the LOWER_TEMPERATURE
            pass
    elif current_SM_STATE == SM_STATE__ON:
        if temperature > get_heater_upper_temperature(heater_name):
            await set_kasa_outlet_state(heater_name, SM_STATE__OFF)
            set_heater_sm_state(heater_name, SM_STATE__OFF)
        else:
            # we are on and below the UPPER_TEMPERATURE
            pass
    else: # unknown state / condition!
        pass

    # FIXME?: assert that SM matches device state



async def update_temperature(heater_name, temperature_in_F_string):
    global TEMPERATURES_LAST_READ
    temperature_float = parse_temperature(temperature_in_F_string)
    TEMPERATURES_LAST_READ[heater_name] = temperature_float
    # this is where control of heater is handled too
    await update_state(heater_name, temperature_float)

temperature_in_F_regex = re.compile(r"(\d+\.?\d*)")
@functools.cache
def parse_temperature(temperature_in_F_string):
    m = temperature_in_F_regex.match(temperature_in_F_string)
    #print ("{} ".format(m.group(0)), end="")
    value = float(m.group(0))
    return value

async def handle_temperature_update(topic, payload):
    """
    Process mqtt-sourced temperature updates.

     payload will be JSON like: b'{"temperature": "54.0F"}'
    """
    heater = TOPIC_MAPPING[topic]['heater']
    heater_name = heater['plug_alias']
    print (topic, payload, heater_name)
    status=str(payload.decode("utf-8","ignore"))
    # decode JSON
    s=json.loads(status)
    # print(s)
    temperature = s[DEFAULT_TEMPERATURE_KEY]
    # print(temperature)
    await update_temperature(heater_name, temperature)

async def handle_mqtt_messages(client):
    "Handle MQTT updates"
    async for message in client.messages:
        await handle_temperature_update(message.topic.value, message.payload)


async def print_current_status():
    while True:
        for heater_name in SM_STATES:
            print(datetime.datetime.now(), end=" ")
            print(heater_name, SM_STATES[heater_name], TEMPERATURES_LAST_READ[heater_name],  end=" ")
            heater_device_info = get_device_info_from_heater_name(heater_name)
            #config_dict = heater_device_info['connect_config']
            child_index = heater_device_info.get('_child_index')
            dev = heater_device_info['_device']
            await dev.update()

            print ("is on?", dev.children[child_index].is_on)
        await asyncio.sleep(DISPLAY_LOOP_SLEEP_TIME)

# main asyncio loop
async def main():
    async with aiomqtt.Client(MQTT_BROKER) as client:

        # Initialize based on configuration
        for probe_name in PROBE_MAPPING:
            heater_name = PROBE_MAPPING[probe_name].get(
                'heater', HEATER_DISABLED_SENTINEL_VALUE)
            topic = PROBE_MAPPING[probe_name]['topic']
            if heater_name != HEATER_DISABLED_SENTINEL_VALUE:
                heater_info = TOPIC_MAPPING[topic]['heater']

                # set/sync initial state
                await register_device(heater_info)

                # Subscribe to MQTT
                await subscribe_device(client, heater_name, topic)

        print(DEVICE_LIST)

        await asyncio.gather(print_current_status(),
                             handle_mqtt_messages(client))


        # TODO: add concurrent processing
        # https://aiomqtt.bo3hm.com/subscribing-to-a-topic.html#processing-concurrently

if __name__ == "__main__":
    asyncio.run(main())

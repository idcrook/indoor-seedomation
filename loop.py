#!/usr/bin/env python

# A simple control loop for turning on heater to keep within a measured range of temperatures

# FIXME
#
#  - Turn off heaters for KeyboardInterrupt / Exit
#
#
# TODO
#
#  - Add environment variable support for configuration
#  - Add configuration file support (broker, topic, device names, etc.)
#  - Add tests, modularity
#  - Synchronize initial state of heater, rather than forcing it to be set off
#  - Implement a PID controller?
#  - Ddd proper logging
#  - Add watchdog timeout for new messages not received (temperature updates)
#    - could be sign that probe or network is down?
#    - may want to attempt to turn off switch in that case and go to a new panic state

import json
import re
import time
import traceback
import pywemo
import paho.mqtt.client as mqtt

DEFAULT_DISPLAY_LOOP_SLEEP_TIME = 600

global SM_STATES
SM_STATE__OFF = 0
SM_STATE__ON =  1
SM_INITIAL_STATE = SM_STATE__OFF
SM_STATES = {}
TEMPERATURES_LAST_READ = {}

CONFIG_FILE = 'config.secrets.json'

DEFAULT_MQTT_BROKER_ADDR = "192.168.50.6"
DEFAULT_MQTT_PORT = 1883
DEFAULT_TOPIC_BASE = "picow0"
DEFAULT_TEMPERATURE_KEY = "temperature"

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
        #print(CONFIG)
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

# MQTT config
MQTT_BROKER = bytes(MQTT_CONF.get('broker', DEFAULT_MQTT_BROKER_ADDR), 'utf-8')
MQTT_PORT = MQTT_CONF.get('port', DEFAULT_MQTT_PORT)

# Sensors
PROBES = SENSORS_CONF.get('probes', {})

for probe in PROBES:
    for probe_name in probe:
        topic = probe[probe_name]['topic']
        # print (probe_name, topic)
        PROBE_MAPPING[probe_name] = {}
        PROBE_MAPPING[probe_name]['topic'] = topic
        TOPIC_MAPPING[topic] = {}
        TOPIC_MAPPING[topic]['probe'] = probe_name

# print(DEVICE_MAPPING)

# Heaters
HEATERS = CONTROLS_CONF.get('heaters', {})

for heater in HEATERS:
    # print(heater)
    for heater_name in heater:
        heater_info = heater[heater_name]
        probe_name = heater_info['probe']
        upper_temp = heater_info['upper_temperature']
        lower_temp = heater_info['lower_temperature']
        heater_temperature_topic = PROBE_MAPPING[probe_name]['topic']
        HEATER_MAPPING[heater_name] = {}
        HEATER_MAPPING[heater_name]['topic'] = heater_temperature_topic
        HEATER_MAPPING[heater_name]['probe'] = probe_name
        HEATER_MAPPING[heater_name]['upper_T'] = upper_temp
        HEATER_MAPPING[heater_name]['lower_T'] = lower_temp
        PROBE_MAPPING[probe_name]['heater'] = heater_name

print(DEVICE_MAPPING)

devices_of_interest = tuple(HEATER_MAPPING.keys())

print(devices_of_interest)

# mapping of wemo device friendly name to WeMo object
DEVICE_LIST = {}

# Wemo discovery
devices = pywemo.discover_devices()
device_name_to_url = {}

for device in devices:
    name = device.name
    if name in devices_of_interest:
        ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', device.deviceinfo.controlURL )[0]
        url = pywemo.setup_url_for_address(ip)
        device_name_to_url [name] = url

# Populate data structures
for device_name in devices_of_interest:
    # print (device_name)
    device_url = device_name_to_url[device_name]
    # print (device_url)
    DEVICE_LIST[device_name] = pywemo.discovery.device_from_description(device_url)
    SM_STATES[device_name] = SM_INITIAL_STATE
    TEMPERATURES_LAST_READ[device_name] = 0.0

def on_connect(client, userdata, flags, reason_code, properties):
    if flags.session_present:
        # ...
        pass

    if reason_code == 0:
        # success connect
        for device in DEVICE_LIST:
            wemo_device = DEVICE_LIST[device]
            # FIXME: exception handling
            topic = HEATER_MAPPING[device]['topic']
            connect_report = "Starting Wemo %s: %s   %s" % (wemo_device.device_type,
                                                            wemo_device.name, topic)
            print(connect_report, topic)
            client.subscribe(topic)

    if reason_code > 0:
        # error processing
        pass

# def on_connect(client, userdata, flags, rc):
#     for device in DEVICE_LIST:
#         wemo_device = DEVICE_LIST[device]
#         # FIXME: exception handling
#         topic = HEATER_MAPPING[device]['topic']
#         connect_report = "Starting Wemo %s: %s   %s" % (wemo_device.device_type,
#                                                         wemo_device.name, topic)
#         print(connect_report, topic)
#         client.subscribe(topic)

def on_message(client, userdata, msg):
    # print(msg.topic, msg.payload)
    try:
        probe_name = TOPIC_MAPPING[msg.topic]['probe']
        heater_device = PROBE_MAPPING[probe_name]['heater']
        # print(probe_name, heater_device)
        status=str(msg.payload.decode("utf-8","ignore"))
        # decode JSON
        s=json.loads(status)
        # print(s)
        temperature = s[DEFAULT_TEMPERATURE_KEY]
        # print(temperature)
        update_temperature(heater_device, temperature)
    # FIXME: add more specific error handling
    except:
        print(traceback.format_exc())
        return


def get_device_lower_temperature(device):
    return HEATER_MAPPING[device]['lower_T']

def get_device_upper_temperature(device):
    return HEATER_MAPPING[device]['upper_T']

def get_device_sm_state(device):
    # global SM_STATES
    return SM_STATES[device]

def set_device_sm_state(device, state):
    global SM_STATES
    SM_STATES[device] = state

def set_wemo_device_state(device, to_state):
    print(' setting device {} state to {}'.format(device.name, to_state))
    if to_state == SM_STATE__ON:
        print ("Turning ON device {}".format(device.name))
        device.on()
        time.sleep(2)
    if to_state == SM_STATE__OFF:
        print ("Turning OFF device {}".format(device.name))
        device.off()
        time.sleep(2)

# main state machine
def update_state(device, temperature):
    current_SM_STATE = get_device_sm_state(device)

    print ('"{}" SM: {}, T: {}'.format(
        device[-8:], current_SM_STATE, temperature))

    wemo_device = DEVICE_LIST[device]
        # print ('current SM:', current_SM_STATE)
    if current_SM_STATE == SM_STATE__OFF:
        if temperature < get_device_lower_temperature(device):
            set_wemo_device_state(wemo_device, SM_STATE__ON)
            set_device_sm_state(device, SM_STATE__ON)
        else:
            # we are off and above the LOWER_TEMPERATURE
            pass
    elif current_SM_STATE == SM_STATE__ON:
        if temperature > get_device_upper_temperature(device):
            set_wemo_device_state(wemo_device, SM_STATE__OFF)
            set_device_sm_state(device, SM_STATE__OFF)
        else:
            # we are on and below the UPPER_TEMPERATURE
            pass
    else: # unknown state / condition!
        pass

    # FIXME?: assert that SM matches device state



def update_temperature(device, temperature_in_F_string):
    global TEMPERATURES_LAST_READ
    temperature_float = parse_temperature(temperature_in_F_string)
    TEMPERATURES_LAST_READ[device] = temperature_float
    update_state(device, temperature_float)

temperature_in_F_regex = re.compile(r"(\d+\.?\d*)")
def parse_temperature(temperature_in_F_string):
    m = temperature_in_F_regex.match(temperature_in_F_string)
    #print ("{} ".format(m.group(0)), end="")
    value = float(m.group(0))
    return value

# Setup MQTT Client
# https://eclipse.dev/paho/files/paho.mqtt.python/html/migrations.html#versioned-the-user-callbacks
#client = mqtt.Client()
# https://eclipse.dev/paho/files/paho.mqtt.python/html/client.html#paho.mqtt.client.Client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.on_connect = on_connect
client.on_message = on_message

# set initial state
for device in DEVICE_LIST:
    set_wemo_device_state(DEVICE_LIST[device], SM_INITIAL_STATE)

# Start the MQTT thread that handles this client
print ("Starting Control LOOP")

client.loop_start()

while True:
    for device in DEVICE_LIST:
        print("Main thread: '{}' D{} SM{} T{}F".format(
            device, DEVICE_LIST[device].get_state(),
            get_device_sm_state(device), TEMPERATURES_LAST_READ[device]))
    time.sleep(DISPLAY_LOOP_SLEEP_TIME)

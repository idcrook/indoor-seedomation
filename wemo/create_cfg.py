#!/usr/bin/env python3

import json

example_config = {
    "global": {
        "loop_sleep_time": 600
    },
    "controls": {
         "heaters": [
            {"Bedroom 2 Plant Heater 2": 
             {
                "probe": "bed2",
                "lower_temperature": 70.0,
                "upper_temperature": 72.9
                }
            },
            {"Bedroom 2 Plant Heater 3": {
                "probe": "bed1",
                "lower_temperature": 70.0,
                "upper_temperature": 72.9
                }},
        ]
    },
    "sensors": {
        "probes": [
            {"bed1": {"topic": "picow1/bed1/probe"}},
            {"bed2": {"topic": "picow1/bed2/probe"}},
        ]
    },
    "mqtt": {
        "broker": "192.168.50.6",
        "port": 1883,
    }
}


# write json file
output_json = 'config.example.json'
with open(output_json, 'w') as jsonfile:
    print('saving to', output_json)
    json.dump(example_config, jsonfile, indent=2)

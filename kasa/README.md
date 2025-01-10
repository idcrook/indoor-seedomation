# indoor-seedomation - kasa

 python-based indoor seedling starter monitor and control. Put into use on my home network using a Raspberry Pi and a TP-Link Kasa HS300 smart power strip.


TODO: [main script](loop.py)

 - It monitors an MQTT topic that contains temperature read from a sensor placed in soil.
 - Based on temperature it turns a heater on or off to keep temperature in a range.



```shell
# Install a python3 dev setup and other libraries
sudo apt install -y python3-pip python3-venv build-essential \
    python3-setuptools python3-wheel git

# need this one too (required by python-kasa on my bookworm)
sudo apt install libssl1.1

# place a clone of this repo in ~/projects/
mkdir -p ~/projects
cd ~/projects

git clone https://github.com/idcrook/indoor-seedomation.git
cd indoor-seedomation/kasa
```

## Install

```shell
$ cd ~/projects/indoor-seedomation/kasa
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv) $ pip install --no-cache-dir -r requirements.txt
```

Examples assume they are being run in the virtualenv that has been created:

```shell
$ cd ~/projects/indoor-seedomation/kasa
$ source  .venv/bin/activate
(.venv) $ python ...
```

### Simple python-kasa library test (kasa device discovery)

```shell
$ source  .venv/bin/activate
(.venv) $ python -m asyncio
>>> from kasa import Discover, Credentials
>>>
>>> found_devices = await Discover.discover()
>>> [dev.model for dev in found_devices.values()]
['HS300']
```

Example script `discovery.py`, which reads from a config file. Refer to [Configuration](#configuration) below.

```shell
$ source  .venv/bin/activate
(.venv) $ python discovery.py
'global':
...
[{'address': '192.168.50.10',
...
192.168.50.10
...
Heater 2
Heater 1
Heater 3
HS300
```

### Other examples

TODO: See `control.py` and `mqtt.py`

## Install `loop.py` as `systemd` service

Refer to instructions in comments at the top of [example service file][systemd service file]

[systemd service file]: etc/kasa-plant-heater-control.service


## Configuration

Update the generated example for your setup.

```shell
# create config file (edit script or output)
python3 create_cfg.py
cp config.example.json config.secrets.json

# !! UPDATE config.secrets.json

```

## Troublshooting

`ImportError` on `libssl`.

```
>>> import asyncio
>>> from kasa import Discover
...
ImportError: libssl.so.1.1: cannot open shared object file: No such file or directory
```

Install the missing package.


```shell
sudo apt install libssl1.1
``

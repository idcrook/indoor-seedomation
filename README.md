# indoor-seedomation

 python-based indoor seedling starter monitor and control. Put into use on my home network using a Raspberry Pi.

[main script](loop.py)

 - It monitors an MQTT topic that contains temperature read from a sensor placed in soil. 
 - Based on temperature it turns a heater on or off to keep temperature in a range.



```shell
# Install a python3 dev setup and other libraries
sudo apt install -y python3-pip python3-venv build-essential \
    python3-setuptools python3-wheel git

# need this one too (required by ssdp # from lxml import etree as et)
sudo apt install libxslt-dev

# place a clone of this repo in ~/projects/
mkdir -p ~/projects
cd ~/projects

git clone https://github.com/idcrook/indoor-seedomation.git
cd indoor-seedomation
```


## Install


```shell
$ cd ~/projects/indoor-seedomation
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv) $ pip install --no-cache-dir -r requirements.txt
```

Friendly names of the wemo devices are hard-coded in scripts below.

They also assume they are being run in the virtualenv that has been created:

```shell
$ cd ~/projects/indoor-seedomation
$ source  .venv/bin/activate
(.venv) $ python ...
```

### Simple pywemo library test (wemo device discovery)

Taken from the [pywemo docs](https://github.com/pywemo/pywemo)

```python
>>> import pywemo
>>> devices = pywemo.discover_devices()
>>> print(devices)
[<WeMo Insight "AC Insight">]

>>> devices[0].toggle()
```

> For advanced usage, the `device.explain()` method will print all known actions that the device reports to PyWeMo.

### Discovery script

Uses same library function as above but looks for device names and queries device info.

```shell
$ source  .venv/bin/activate
(.venv) $ python discovery.py
  Bedroom 2 Plant Heater
  Bedroom 2 Plant Light 2
  <<...>>
```

### Other examples

See `control.py` and `mqtt.py`

## Install `loop.py` as `systemd` service

Refer to instructions in comments at the top of [example service file][systemd service file]

[systemd service file]: etc/plant-heater-control.service

### Example `loop.py` output

```text
('Bedroom 2 Plant Heater',)
 setting device Bedroom 2 Plant Heater state to 0
Turning OFF device Bedroom 2 Plant Heater
Starting Control LOOP
Using temperature range of 68.0F to 74.0F
Main thread: D0 SM0
Wemo Insight: Bedroom 2 Plant Heater
current state: 0, temperature 67.2
 setting device Bedroom 2 Plant Heater state to 1
Turning ON  device Bedroom 2 Plant Heater
current state: 1, temperature 67.2
current state: 1, temperature 67.3
current state: 1, temperature 67.4
current state: 1, temperature 67.4
```

## Troublshooting

### Missing `libxslt` XML library

Encountered on armv7 Raspbian bookworm, from the pywemo / .ouimeaux module

```console
$ python discovery.py
[STACKTRACE]
   ...
 from lxml import etree as et
ImportError: libxslt.so.1: cannot open shared object file: No such file or directory
$ sudo apt install libxslt1.1
# should now work
$ python discovery.py
```

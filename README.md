# indoor-seedomation
A python-based indoor seedling starter monitor and control



```shell
# Install a python3 dev setup and other libraries
sudo apt install -y python3-pip python3-venv build-essential \
    python3-setuptools python3-wheel git

# place a clone of this repo in ~/projects/
mkdir -p ~/projects
cd ~/projects

git clone https://github.com/idcrook/indoor-seedomation.git
cd indoor-seedomation
```


### Install


```
python3 -m venv .venv
source .venv/bin/activate
pip install --no-cache-dir -r requirements.txt
```

From the [pywemo docs](https://github.com/pywemo/pywemo)

#### Simple test (device discovery)

```python
>>> import pywemo
>>> devices = pywemo.discover_devices()
>>> print(devices)
[<WeMo Insight "AC Insight">]

>>> devices[0].toggle()
```

> For advanced usage, the `device.explain()` method will print all known actions that the device reports to PyWeMo.

#### Install `systemd` service

Refer to instructions in comments at the top of [example service file][systemd service file]

[systemd service file]: etc/plant-heater-control.service
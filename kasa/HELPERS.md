# REPL examples

Launch using

```shell
$ source .venv/bin/activate
$ python -m asyncio
```

## `.connect()` with children

```python
import asyncio
from kasa import Discover, Device
device = await Discover.discover_single(
    "192.168.50.46",
)
config_dict = device.config.to_dict()
# DeviceConfig.to_dict() can be used to store for later
print(config_dict)

dev = await Device.connect(config=Device.Config.from_dict(config_dict))

print(dev.alias)
print(dev)
help(dev)

print(dev.children)
help(dev.children[0])
```

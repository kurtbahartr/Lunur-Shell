from fabric.audio import Audio
from fabric.bluetooth import BluetoothClient

from .notifications import *
from .battery import *
from .brightness import *
from .network import *

# Fabric services
audio_service = Audio()
bluetooth_service = BluetoothClient()

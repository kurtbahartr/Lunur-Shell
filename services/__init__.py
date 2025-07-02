from fabric.audio import Audio
from fabric.bluetooth import BluetoothClient

from .custom_notification import CustomNotifications
from .battery import *
from .brightness import *
from .network import *

# Fabric services
audio_service = Audio()
notification_service = CustomNotifications()
bluetooth_service = BluetoothClient()

from fabric.audio.service import Audio
from fabric.bluetooth.service import BluetoothClient

from .custom_notification import CustomNotifications

# Fabric services
audio_service = Audio()
notification_service = CustomNotifications()
bluetooth_service = BluetoothClient()

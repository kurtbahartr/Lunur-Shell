import gi
from fabric.bluetooth.service import BluetoothClient, BluetoothDevice
from fabric.utils import bulk_connect
from fabric.widgets.box import Box
from fabric.widgets.button import Button
from fabric.widgets.centerbox import CenterBox
from fabric.widgets.entry import Entry
from fabric.widgets.label import Label
from fabric.widgets.scrolledwindow import ScrolledWindow
from fabric.widgets.revealer import Revealer
from gi.repository import Gtk, GLib, Gio

from services import bluetooth_service
from services.bluetooth import BluetoothPairingAgent
from shared.buttons import HoverButton, QSChevronButton, ScanButton
from shared.list import ListBox
from shared.separator import Separator
from shared.submenu import QuickSubMenu
from utils.icons import text_icons
from utils.widget_utils import nerd_font_icon

gi.require_versions({"Gtk": "3.0"})


class BluetoothDeviceBox(Box):
    """A widget to display a Bluetooth device in a box."""

    def __init__(
        self,
        device: BluetoothDevice,
        on_prompt_opened=None,
        on_paired_changed=None,
        **kwargs,
    ):
        super().__init__(
            orientation="v",
            spacing=4,
            h_expand=True,
            name="bluetooth-device-box",
            **kwargs,
        )
        self.device: BluetoothDevice = device
        self.on_prompt_opened = on_prompt_opened
        self.on_paired_changed = on_paired_changed
        self._row_is_paired = False

        self.icon_to_text_icon = {
            "audio-headset": text_icons["ui"]["headset"],
            "phone": text_icons["ui"]["phone"],
            "audio-headphones": text_icons["ui"]["headphones"],
            "keyboard": text_icons["ui"]["keyboard"],
            "mouse": text_icons["ui"]["mouse"],
            "audio-speakers": text_icons["ui"]["speakers"],
            "camera": text_icons["ui"]["camera"],
            "printer": text_icons["ui"]["printer"],
            "tv": text_icons["ui"]["tv"],
            "watch": text_icons["ui"]["watch"],
            "bluetooth": text_icons["bluetooth"]["on"],
        }

        self.device_row = CenterBox(
            spacing=2,
            style_classes=["submenu-button"],
            h_expand=True,
        )

        self.connect_button = HoverButton(
            style_classes=["wifi-auth-button", "wifi-connect-button"]
        )
        self.connect_button.connect("clicked", self.on_action_clicked)

        self.forget_button = HoverButton(
            label="Forget",
            style_classes=["wifi-auth-button", "wifi-cancel-button"],
            visible=False,
        )
        # Prevent show_all() from forcing visibility
        self.forget_button.set_no_show_all(True)
        self.forget_button.connect("clicked", self.on_forget_clicked)

        self.action_box = Box(
            orientation="h",
            spacing=6,
            h_align="end",
            children=[self.forget_button, self.connect_button],
        )
        self._pairing = False
        self._prompt_timeout_id = None
        self._pair_proxy = None
        self._adapter_proxy = None
        self._adapter_restore = None
        self._adapter_restore_id = None

        # Store signal IDs to disconnect them later
        self._signal_ids = bulk_connect(
            self.device,
            {
                "notify::connecting": self.on_device_connecting,
                "notify::connected": self.on_device_connect,
                "notify::paired": self.on_device_paired,
            },
        )
        self.connect("destroy", self._on_destroy)

        device_name = device.name or "Unknown Device"

        self.device_row.add_start(
            nerd_font_icon(
                icon=self.icon_to_text_icon.get(
                    device.icon_name, text_icons["bluetooth"]["on"]
                ),
                props={"style_classes": ["panel-font-icon"]},
            ),
        )

        self.device_row.add_start(
            Label(
                label=device_name,
                style_classes=["submenu-item-label"],
                ellipsization="end",
            )
        )

        self.device_row.add_end(self.action_box)

        self.prompt_container = Box(
            orientation="v",
            spacing=6,
            h_expand=True,
            style_classes=["wifi-password-container"],
        )
        self.prompt_revealer = Revealer(
            transition_type="slide-down",
            transition_duration=200,
            child=self.prompt_container,
            reveal_child=False,
        )

        self.add(self.device_row)
        self.add(self.prompt_revealer)

        self.update_action_label()

    def _on_destroy(self, *_):
        """Clean up signals when widget is destroyed to prevent crashes."""
        if self._prompt_timeout_id is not None:
            try:
                GLib.source_remove(self._prompt_timeout_id)
            except Exception:
                pass
            self._prompt_timeout_id = None
        if self._adapter_restore_id is not None:
            try:
                GLib.source_remove(self._adapter_restore_id)
            except Exception:
                pass
            self._adapter_restore_id = None
        self._restore_adapter_settings()
        if self.device and self._signal_ids:
            for signal_id in self._signal_ids:
                try:
                    if self.device.handler_is_connected(signal_id):
                        self.device.disconnect(signal_id)
                except Exception:
                    pass
            self._signal_ids = ()

    def on_action_clicked(self, *_):
        if not self.device.paired:
            self.start_pairing()
            return
        self.device.set_property("connecting", not self.device.connected)

    def on_forget_clicked(self, *_):
        self._unpair_device()

    def cancel_pairing(self):
        self._pairing = False
        self.update_action_label()

    def start_pairing(self):
        self._pairing = True
        self.update_action_label()

        try:
            device_path = self.device.device.get_object_path()
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            self._pair_proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                device_path,
                "org.bluez.Device1",
                None,
            )
            self._ensure_adapter_pairable(bus)
            self._pair_proxy.call(
                "Pair",
                None,
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                self._on_pair_call_done,
            )
        except Exception:
            self._pairing = False
            self.update_action_label()

    def on_device_connecting(self, *_):
        if not self.device.paired:
            self.update_action_label()
            return
        if self.device.connecting:
            self.connect_button.set_label("Connecting...")
        elif self.device.connected is False:
            self.connect_button.set_label("Failed to connect")

    def on_device_connect(self, *_):
        self.update_action_label()

    def on_device_paired(self, *_):
        self._pairing = False
        self._ensure_trusted()
        self.update_action_label()
        self._restore_adapter_settings()
        if self.on_paired_changed:
            self.on_paired_changed(self.device)

    def update_action_label(self):
        if not self.device.paired:
            self.connect_button.set_label("Pairing..." if self._pairing else "Pair")
            self.forget_button.set_visible(False)
            return
        self.forget_button.set_visible(self._row_is_paired)

        self.connect_button.set_label(
            "Disconnect" if self.device.connected else "Connect"
        )

    def _on_pair_call_done(self, proxy: Gio.DBusProxy, result: Gio.AsyncResult):
        try:
            proxy.call_finish(result)
        except Exception:
            pass
        self._pairing = False
        self._ensure_trusted()
        self.update_action_label()
        self._restore_adapter_settings()

    def set_row_paired_state(self, is_paired: bool):
        self._row_is_paired = is_paired
        self.update_action_label()

    def _clear_prompt(self):
        for child in self.prompt_container.get_children():
            self.prompt_container.remove(child)
        self.prompt_revealer.set_reveal_child(False)

    def close_prompt(self):
        if self._prompt_timeout_id is not None:
            try:
                GLib.source_remove(self._prompt_timeout_id)
            except Exception:
                pass
            self._prompt_timeout_id = None
        self._clear_prompt()

    def _notify_prompt_opened(self):
        if self.on_prompt_opened:
            self.on_prompt_opened(self.device.address)

    def show_pin_prompt(self, title: str, placeholder: str, on_submit, on_cancel):
        self._notify_prompt_opened()
        self._clear_prompt()

        title_label = Label(label=title, h_align="start", style_classes=["panel-text"])

        entry = Entry(
            placeholder=placeholder,
            visibility=True,
            h_expand=True,
            style_classes=["wifi-password-entry"],
        )

        cancel_button = HoverButton(
            label="Cancel",
            style_classes=["wifi-auth-button", "wifi-cancel-button"],
        )
        cancel_button.connect("clicked", lambda *_: (self.close_prompt(), on_cancel()))

        submit_button = HoverButton(
            label="OK",
            style_classes=["wifi-auth-button", "wifi-connect-button"],
            sensitive=False,
        )

        def _update_state(*_):
            text = entry.get_text().strip()
            submit_button.set_sensitive(text.isdigit() and len(text) > 0)

        entry.connect("changed", _update_state)

        def _submit(*_):
            text = entry.get_text().strip()
            if text.isdigit() and len(text) > 0:
                self.close_prompt()
                on_submit(text)

        entry.connect("activate", _submit)
        submit_button.connect("clicked", _submit)

        entry_row = Box(
            orientation="h",
            spacing=4,
            h_expand=True,
            style_classes=["wifi-entry-row"],
            children=[entry],
        )

        button_row = Box(
            orientation="h",
            spacing=8,
            h_align="end",
            children=[cancel_button, submit_button],
        )

        self.prompt_container.add(title_label)
        self.prompt_container.add(entry_row)
        self.prompt_container.add(button_row)
        self.prompt_revealer.set_reveal_child(True)
        GLib.timeout_add(250, entry.grab_focus)

    def show_passkey_confirm_prompt(
        self, title: str, passkey: str, on_confirm, on_cancel
    ):
        self._notify_prompt_opened()
        self._clear_prompt()

        title_label = Label(label=title, h_align="start", style_classes=["panel-text"])
        passkey_label = Label(
            label=passkey,
            h_align="start",
            style_classes=["bluetooth-passkey"],
        )

        cancel_button = HoverButton(
            label="Cancel",
            style_classes=["wifi-auth-button", "wifi-cancel-button"],
        )
        cancel_button.connect("clicked", lambda *_: (self.close_prompt(), on_cancel()))

        confirm_button = HoverButton(
            label="Confirm",
            style_classes=["wifi-auth-button", "wifi-connect-button"],
        )
        confirm_button.connect(
            "clicked", lambda *_: (self.close_prompt(), on_confirm())
        )

        button_row = Box(
            orientation="h",
            spacing=8,
            h_align="end",
            children=[cancel_button, confirm_button],
        )

        self.prompt_container.add(title_label)
        if passkey:
            self.prompt_container.add(passkey_label)
        self.prompt_container.add(button_row)
        self.prompt_revealer.set_reveal_child(True)

    def show_passkey_display(self, title: str, passkey: str, timeout_seconds: int = 10):
        self._notify_prompt_opened()
        self._clear_prompt()

        title_label = Label(label=title, h_align="start", style_classes=["panel-text"])
        passkey_label = Label(
            label=passkey,
            h_align="start",
            style_classes=["bluetooth-passkey"],
        )

        self.prompt_container.add(title_label)
        self.prompt_container.add(passkey_label)
        self.prompt_revealer.set_reveal_child(True)

        def _auto_close():
            self._prompt_timeout_id = None
            self.close_prompt()
            return False

        self._prompt_timeout_id = GLib.timeout_add_seconds(timeout_seconds, _auto_close)

    def _ensure_trusted(self):
        if not self.device.paired:
            return
        try:
            device_path = self.device.device.get_object_path()
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                device_path,
                "org.bluez.Device1",
                None,
            )
            proxy.set_cached_property("Trusted", GLib.Variant("b", True))
            proxy.call(
                "org.freedesktop.DBus.Properties.Set",
                GLib.Variant(
                    "(ssv)",
                    ("org.bluez.Device1", "Trusted", GLib.Variant("b", True)),
                ),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                None,
            )
        except Exception:
            pass

    def _unpair_device(self):
        try:
            device_path = self.device.device.get_object_path()
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            device_proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                device_path,
                "org.bluez.Device1",
                None,
            )
            adapter_prop = device_proxy.get_cached_property("Adapter")
            if adapter_prop is None:
                return
            adapter_path = adapter_prop.unpack()

            adapter_proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                adapter_path,
                "org.bluez.Adapter1",
                None,
            )
            adapter_proxy.call(
                "RemoveDevice",
                GLib.Variant("(o)", (device_path,)),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                None,
            )
        except Exception:
            pass

    def _ensure_adapter_pairable(self, bus: Gio.DBusConnection):
        if self._adapter_proxy:
            return
        if not self._pair_proxy:
            return

        adapter_path = None
        try:
            adapter_prop = self._pair_proxy.get_cached_property("Adapter")
            if adapter_prop is not None:
                adapter_path = adapter_prop.unpack()
        except Exception:
            adapter_path = None

        if not adapter_path:
            return

        try:
            self._adapter_proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                adapter_path,
                "org.bluez.Adapter1",
                None,
            )
        except Exception:
            self._adapter_proxy = None
            return

        try:
            pairable = self._adapter_proxy.get_cached_property("Pairable")
            discoverable = self._adapter_proxy.get_cached_property("Discoverable")
            discoverable_timeout = self._adapter_proxy.get_cached_property(
                "DiscoverableTimeout"
            )
            self._adapter_restore = {
                "Pairable": pairable.unpack() if pairable else None,
                "Discoverable": discoverable.unpack() if discoverable else None,
                "DiscoverableTimeout": discoverable_timeout.unpack()
                if discoverable_timeout
                else None,
            }
        except Exception:
            self._adapter_restore = None

        try:
            self._adapter_proxy.set_cached_property("Pairable", GLib.Variant("b", True))
            self._adapter_proxy.call(
                "org.freedesktop.DBus.Properties.Set",
                GLib.Variant(
                    "(ssv)",
                    ("org.bluez.Adapter1", "Pairable", GLib.Variant("b", True)),
                ),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                None,
            )

            self._adapter_proxy.set_cached_property(
                "Discoverable", GLib.Variant("b", True)
            )
            self._adapter_proxy.call(
                "org.freedesktop.DBus.Properties.Set",
                GLib.Variant(
                    "(ssv)",
                    ("org.bluez.Adapter1", "Discoverable", GLib.Variant("b", True)),
                ),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                None,
            )

            self._adapter_proxy.set_cached_property(
                "DiscoverableTimeout", GLib.Variant("u", 120)
            )
            self._adapter_proxy.call(
                "org.freedesktop.DBus.Properties.Set",
                GLib.Variant(
                    "(ssv)",
                    (
                        "org.bluez.Adapter1",
                        "DiscoverableTimeout",
                        GLib.Variant("u", 120),
                    ),
                ),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                None,
            )
        except Exception:
            pass

        def _restore_later():
            self._adapter_restore_id = None
            self._restore_adapter_settings()
            return False

        self._adapter_restore_id = GLib.timeout_add_seconds(120, _restore_later)

    def _restore_adapter_settings(self):
        if not self._adapter_proxy or not self._adapter_restore:
            return

        restore = self._adapter_restore
        try:
            if restore.get("Pairable") is not None:
                self._adapter_proxy.set_cached_property(
                    "Pairable", GLib.Variant("b", restore["Pairable"])
                )
                self._adapter_proxy.call(
                    "org.freedesktop.DBus.Properties.Set",
                    GLib.Variant(
                        "(ssv)",
                        (
                            "org.bluez.Adapter1",
                            "Pairable",
                            GLib.Variant("b", restore["Pairable"]),
                        ),
                    ),
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                    None,
                )
            if restore.get("Discoverable") is not None:
                self._adapter_proxy.set_cached_property(
                    "Discoverable", GLib.Variant("b", restore["Discoverable"])
                )
                self._adapter_proxy.call(
                    "org.freedesktop.DBus.Properties.Set",
                    GLib.Variant(
                        "(ssv)",
                        (
                            "org.bluez.Adapter1",
                            "Discoverable",
                            GLib.Variant("b", restore["Discoverable"]),
                        ),
                    ),
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                    None,
                )
            if restore.get("DiscoverableTimeout") is not None:
                self._adapter_proxy.set_cached_property(
                    "DiscoverableTimeout",
                    GLib.Variant("u", restore["DiscoverableTimeout"]),
                )
                self._adapter_proxy.call(
                    "org.freedesktop.DBus.Properties.Set",
                    GLib.Variant(
                        "(ssv)",
                        (
                            "org.bluez.Adapter1",
                            "DiscoverableTimeout",
                            GLib.Variant("u", restore["DiscoverableTimeout"]),
                        ),
                    ),
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                    None,
                )
        except Exception:
            pass

        self._adapter_restore = None
        self._adapter_proxy = None


class BluetoothPromptBox(Box):
    """Fallback prompt shown when a device row does not exist yet."""

    def __init__(self, **kwargs):
        super().__init__(
            orientation="v",
            spacing=6,
            h_expand=True,
            style_classes=["wifi-password-container"],
            **kwargs,
        )
        self._prompt_timeout_id = None

    def _clear(self):
        for child in self.get_children():
            self.remove(child)

    def _clear_timeout(self):
        if self._prompt_timeout_id is not None:
            try:
                GLib.source_remove(self._prompt_timeout_id)
            except Exception:
                pass
            self._prompt_timeout_id = None

    def close(self):
        self._clear_timeout()
        self._clear()

    def show_entry(self, title: str, placeholder: str, on_submit, on_cancel):
        self._clear_timeout()
        self._clear()

        title_label = Label(label=title, h_align="start", style_classes=["panel-text"])
        entry = Entry(
            placeholder=placeholder,
            visibility=True,
            h_expand=True,
            style_classes=["wifi-password-entry"],
        )

        cancel_button = HoverButton(
            label="Cancel",
            style_classes=["wifi-auth-button", "wifi-cancel-button"],
        )
        cancel_button.connect("clicked", lambda *_: on_cancel())

        submit_button = HoverButton(
            label="OK",
            style_classes=["wifi-auth-button", "wifi-connect-button"],
            sensitive=False,
        )

        def _update_state(*_):
            text = entry.get_text().strip()
            submit_button.set_sensitive(text.isdigit() and len(text) > 0)

        entry.connect("changed", _update_state)

        def _submit(*_):
            text = entry.get_text().strip()
            if text.isdigit() and len(text) > 0:
                on_submit(text)

        entry.connect("activate", _submit)
        submit_button.connect("clicked", _submit)

        entry_row = Box(
            orientation="h",
            spacing=4,
            h_expand=True,
            style_classes=["wifi-entry-row"],
            children=[entry],
        )
        button_row = Box(
            orientation="h",
            spacing=8,
            h_align="end",
            children=[cancel_button, submit_button],
        )

        self.add(title_label)
        self.add(entry_row)
        self.add(button_row)

        GLib.timeout_add(250, entry.grab_focus)

    def show_confirm(self, title: str, passkey: str, on_confirm, on_cancel):
        self._clear_timeout()
        self._clear()

        title_label = Label(label=title, h_align="start", style_classes=["panel-text"])
        passkey_label = Label(
            label=passkey,
            h_align="start",
            style_classes=["bluetooth-passkey"],
        )

        cancel_button = HoverButton(
            label="Cancel",
            style_classes=["wifi-auth-button", "wifi-cancel-button"],
        )
        cancel_button.connect("clicked", lambda *_: on_cancel())

        confirm_button = HoverButton(
            label="Confirm",
            style_classes=["wifi-auth-button", "wifi-connect-button"],
        )
        confirm_button.connect("clicked", lambda *_: on_confirm())

        button_row = Box(
            orientation="h",
            spacing=8,
            h_align="end",
            children=[cancel_button, confirm_button],
        )

        self.add(title_label)
        if passkey:
            self.add(passkey_label)
        self.add(button_row)

    def show_display(self, title: str, passkey: str, timeout_seconds: int = 10):
        self._clear_timeout()
        self._clear()

        title_label = Label(label=title, h_align="start", style_classes=["panel-text"])
        passkey_label = Label(
            label=passkey,
            h_align="start",
            style_classes=["bluetooth-passkey"],
        )
        self.add(title_label)
        self.add(passkey_label)

        def _auto_close():
            self._prompt_timeout_id = None
            self.close()
            return False

        self._prompt_timeout_id = GLib.timeout_add_seconds(timeout_seconds, _auto_close)


class BluetoothSubMenu(QuickSubMenu):
    """A submenu to display the Bluetooth settings."""

    def __init__(self, **kwargs):
        self.client = bluetooth_service

        self.separator = Separator(
            orientation="horizontal",
            style_classes=["app-volume-separator"],
        )
        self.paired_devices_listbox = ListBox(
            visible=True, name="paired-devices-listbox"
        )
        self.paired_devices_container = Box(
            orientation="v",
            spacing=10,
            h_expand=True,
            children=[
                Label(
                    label="Paired Devices",
                    h_align="start",
                    style_classes=["panel-text"],
                ),
                self.paired_devices_listbox,
            ],
        )

        self.available_devices_listbox = ListBox(
            visible=True, name="available-devices-listbox"
        )
        self.available_devices_container = Box(
            orientation="v",
            spacing=4,
            h_expand=True,
            children=[
                Label(
                    label="Available Devices",
                    h_align="start",
                    name="available-devices-label",
                    style_classes=["panel-text"],
                ),
                self.available_devices_listbox,
            ],
        )

        self.scan_button = ScanButton()
        self.scan_button.connect("clicked", self.on_scan_toggle)

        self.child = ScrolledWindow(
            min_content_size=(-1, 190),
            max_content_size=(-1, 190),
            propagate_width=True,
            propagate_height=True,
            child=Box(
                orientation="v",
                children=[
                    self.separator,
                    self.paired_devices_container,
                    self.available_devices_container,
                ],
                spacing=10,
            ),
        )

        super().__init__(
            title="Bluetooth",
            title_icon=text_icons["bluetooth"]["on"],
            scan_button=self.scan_button,
            child=self.child,
            **kwargs,
        )

        # Connect device-added signal
        self._added_signal_id = self.client.connect(
            "device-added", self.populate_new_device
        )
        self._removed_signal_id = self.client.connect(
            "device-removed", self.on_device_removed
        )
        self._changed_signal_id = self.client.connect("changed", self.on_client_changed)

        # Connect to self for cleanup
        self.connect("destroy", self._on_destroy)

        # Track device rows for easy update
        self.device_rows = {}
        # Track device signals separately
        self.device_signals = {}
        self._agent_registered = False
        self._fallback_prompt_row = None
        self._fallback_prompt_box = None
        self._refresh_id = None

        # Populate initial devices
        for device in self.client.devices:
            self.add_device_row(device)
            # Track this signal connection
            sig_id = device.connect("notify::paired", self.on_device_paired_changed)
            self.device_signals[device.address] = (device, sig_id)

        self.pairing_agent = BluetoothPairingAgent(
            on_request_pin=self._on_request_pin,
            on_request_passkey=self._on_request_passkey,
            on_request_confirmation=self._on_request_confirmation,
            on_display_passkey=self._on_display_passkey,
            on_request_authorization=self._on_request_authorization,
            on_authorize_service=self._on_authorize_service,
            on_cancel=self._on_agent_cancel,
        )
        self._agent_registered = self.pairing_agent.register()

    def _on_destroy(self, *_):
        """Clean up submenu signals."""
        if self._added_signal_id:
            try:
                self.client.disconnect(self._added_signal_id)
            except Exception:
                pass
        if self._removed_signal_id:
            try:
                self.client.disconnect(self._removed_signal_id)
            except Exception:
                pass
        if self._changed_signal_id:
            try:
                self.client.disconnect(self._changed_signal_id)
            except Exception:
                pass

        # Clean up device specific signals
        for device, sig_id in self.device_signals.values():
            try:
                if device.handler_is_connected(sig_id):
                    device.disconnect(sig_id)
            except Exception:
                pass
        self.device_signals.clear()

        if self._agent_registered:
            self.pairing_agent.unregister()
            self._agent_registered = False

        self._clear_fallback_prompt()
        self._removed_signal_id = None
        self._changed_signal_id = None
        if self._refresh_id is not None:
            try:
                GLib.source_remove(self._refresh_id)
            except Exception:
                pass
            self._refresh_id = None

    def on_scan_toggle(self, btn: Button):
        """Toggle Bluetooth scanning - this is the ONLY place scanning starts."""
        self.client.toggle_scan()
        if self.client.scanning:
            btn.add_style_class("active")
        else:
            btn.remove_style_class("active")
        self.scan_button.play_animation()

    def populate_new_device(self, client: BluetoothClient, address: str):
        device = client.get_device(address)
        if device is None:
            return

        # Avoid duplicate connections
        if address not in self.device_signals:
            self.schedule_refresh()

    def on_device_removed(self, _client: BluetoothClient, address: str):
        if address in self.device_signals:
            device, sig_id = self.device_signals.pop(address)
            try:
                if device.handler_is_connected(sig_id):
                    device.disconnect(sig_id)
            except Exception:
                pass
        self.schedule_refresh()

    def on_client_changed(self, *_):
        self.schedule_refresh()

    def schedule_refresh(self):
        if self._refresh_id is not None:
            return

        def _do_refresh():
            self._refresh_id = None
            self.refresh_devices()
            return False

        self._refresh_id = GLib.idle_add(_do_refresh)

    def refresh_devices(self):
        self.paired_devices_listbox.remove_all()
        self.available_devices_listbox.remove_all()
        self.device_rows.clear()

        # Disconnect old paired signals before reconnecting
        for device, sig_id in self.device_signals.values():
            try:
                if device.handler_is_connected(sig_id):
                    device.disconnect(sig_id)
            except Exception:
                pass
        self.device_signals.clear()

        for device in self.client.devices:
            self.add_device_row(device)
            sig_id = device.connect("notify::paired", self.on_device_paired_changed)
            self.device_signals[device.address] = (device, sig_id)

        self.paired_devices_listbox.queue_draw()
        self.available_devices_listbox.queue_draw()
        self.paired_devices_listbox.queue_resize()
        self.available_devices_listbox.queue_resize()

    def add_device_row(self, device: BluetoothDevice):
        # Remove existing row if present
        if device.address in self.device_rows:
            row, listbox, device_box = self.device_rows[device.address]
            listbox.remove(row)
            row.destroy()

        bt_item = Gtk.ListBoxRow(visible=True, name="bluetooth-device-row")
        device_box = BluetoothDeviceBox(
            device,
            on_prompt_opened=self._on_prompt_opened,
            on_paired_changed=self.on_device_paired_changed,
        )
        bt_item.add(device_box)
        if device.paired:
            self.paired_devices_listbox.add(bt_item)
            self.device_rows[device.address] = (
                bt_item,
                self.paired_devices_listbox,
                device_box,
            )
            device_box.set_row_paired_state(True)
        else:
            self.available_devices_listbox.add(bt_item)
            self.device_rows[device.address] = (
                bt_item,
                self.available_devices_listbox,
                device_box,
            )
            device_box.set_row_paired_state(False)

        if device.paired:
            self._set_device_trusted(device)

    def on_device_paired_changed(self, device, *_):
        # Refresh lists when paired status changes
        if device.paired:
            self._set_device_trusted(device)
        self.schedule_refresh()

    def _set_device_trusted(self, device: BluetoothDevice):
        try:
            device_path = device.device.get_object_path()
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                device_path,
                "org.bluez.Device1",
                None,
            )
            proxy.set_cached_property("Trusted", GLib.Variant("b", True))
            proxy.call(
                "org.freedesktop.DBus.Properties.Set",
                GLib.Variant(
                    "(ssv)",
                    ("org.bluez.Device1", "Trusted", GLib.Variant("b", True)),
                ),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
                None,
            )
        except Exception:
            pass

    def _on_prompt_opened(self, address: str):
        for addr, (_, _, device_box) in self.device_rows.items():
            if addr != address:
                device_box.close_prompt()
        if self._fallback_prompt_box:
            self._fallback_prompt_box.close()
            self._clear_fallback_prompt()

    def _address_from_path(self, device_path: str) -> str | None:
        if "/dev_" not in device_path:
            return None
        return device_path.split("/dev_")[-1].replace("_", ":")

    def _get_device_box(self, address: str) -> BluetoothDeviceBox | None:
        if address not in self.device_rows:
            device = self.client.get_device(address)
            if device:
                self.add_device_row(device)
        row_info = self.device_rows.get(address)
        if not row_info:
            return None
        return row_info[2]

    def _get_device_name_from_path(self, device_path: str) -> str:
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            proxy = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                device_path,
                "org.bluez.Device1",
                None,
            )
            for prop in ("Alias", "Name"):
                value = proxy.get_cached_property(prop)
                if value is not None:
                    name = value.unpack()
                    if name:
                        return name
        except Exception:
            pass
        return "Bluetooth device"

    def _handle_missing_device(self, cancel_cb):
        if cancel_cb:
            cancel_cb()

    def _ensure_fallback_prompt(self):
        if self._fallback_prompt_row and self._fallback_prompt_box:
            return
        self._fallback_prompt_box = BluetoothPromptBox()
        self._fallback_prompt_row = Gtk.ListBoxRow(
            visible=True, name="bluetooth-device-row"
        )
        self._fallback_prompt_row.add(self._fallback_prompt_box)
        self.available_devices_listbox.insert(self._fallback_prompt_row, 0)

    def _clear_fallback_prompt(self):
        if self._fallback_prompt_row:
            try:
                self.available_devices_listbox.remove(self._fallback_prompt_row)
            except Exception:
                pass
            try:
                self._fallback_prompt_row.destroy()
            except Exception:
                pass
        self._fallback_prompt_row = None
        self._fallback_prompt_box = None

    def _on_request_pin(self, device_path: str, reply_cb, cancel_cb):
        address = self._address_from_path(device_path)
        if not address:
            self._show_fallback_entry(
                device_path,
                "Enter PIN",
                "PIN code",
                reply_cb,
                cancel_cb,
            )
            return
        device_box = self._get_device_box(address)
        if not device_box:
            self._show_fallback_entry(
                device_path,
                "Enter PIN",
                "PIN code",
                reply_cb,
                cancel_cb,
            )
            return

        device = self.client.get_device(address)
        device_name = device.name if device and device.name else "Bluetooth device"
        device_box.show_pin_prompt(
            title=f"Enter PIN for {device_name}",
            placeholder="PIN code",
            on_submit=reply_cb,
            on_cancel=cancel_cb,
        )

    def _on_request_passkey(self, device_path: str, reply_cb, cancel_cb):
        address = self._address_from_path(device_path)
        if not address:
            self._show_fallback_entry(
                device_path,
                "Enter passkey",
                "Passkey (6 digits)",
                reply_cb,
                cancel_cb,
            )
            return
        device_box = self._get_device_box(address)
        if not device_box:
            self._show_fallback_entry(
                device_path,
                "Enter passkey",
                "Passkey (6 digits)",
                reply_cb,
                cancel_cb,
            )
            return

        device = self.client.get_device(address)
        device_name = device.name if device and device.name else "Bluetooth device"
        device_box.show_pin_prompt(
            title=f"Enter passkey for {device_name}",
            placeholder="Passkey (6 digits)",
            on_submit=reply_cb,
            on_cancel=cancel_cb,
        )

    def _on_request_confirmation(
        self, device_path: str, passkey: int, confirm_cb, cancel_cb
    ):
        address = self._address_from_path(device_path)
        if not address:
            self._show_fallback_confirm(
                device_path,
                "Confirm passkey",
                f"{passkey:06d}",
                confirm_cb,
                cancel_cb,
            )
            return
        device_box = self._get_device_box(address)
        if not device_box:
            self._show_fallback_confirm(
                device_path,
                "Confirm passkey",
                f"{passkey:06d}",
                confirm_cb,
                cancel_cb,
            )
            return

        device = self.client.get_device(address)
        device_name = device.name if device and device.name else "Bluetooth device"
        device_box.show_passkey_confirm_prompt(
            title=f"Confirm passkey for {device_name}",
            passkey=f"{passkey:06d}",
            on_confirm=confirm_cb,
            on_cancel=cancel_cb,
        )

    def _on_display_passkey(self, device_path: str, passkey: int, _entered: int):
        address = self._address_from_path(device_path)
        if not address:
            self._show_fallback_display(
                device_path,
                "Passkey",
                f"{passkey:06d}",
            )
            return
        device_box = self._get_device_box(address)
        if not device_box:
            self._show_fallback_display(
                device_path,
                "Passkey",
                f"{passkey:06d}",
            )
            return

        device = self.client.get_device(address)
        device_name = device.name if device and device.name else "Bluetooth device"
        device_box.show_passkey_display(
            title=f"Passkey for {device_name}",
            passkey=f"{passkey:06d}",
        )

    def _on_request_authorization(self, device_path: str, confirm_cb, cancel_cb):
        address = self._address_from_path(device_path)
        if not address:
            self._show_fallback_confirm(
                device_path,
                "Authorize device?",
                "",
                confirm_cb,
                cancel_cb,
            )
            return
        device_box = self._get_device_box(address)
        if not device_box:
            self._show_fallback_confirm(
                device_path,
                "Authorize device?",
                "",
                confirm_cb,
                cancel_cb,
            )
            return

        device = self.client.get_device(address)
        device_name = device.name if device and device.name else "Bluetooth device"
        device_box.show_passkey_confirm_prompt(
            title=f"Authorize {device_name}?",
            passkey="",
            on_confirm=confirm_cb,
            on_cancel=cancel_cb,
        )

    def _on_authorize_service(self, device_path: str, uuid: str, confirm_cb, cancel_cb):
        address = self._address_from_path(device_path)
        if not address:
            self._show_fallback_confirm(
                device_path,
                "Authorize service?",
                uuid,
                confirm_cb,
                cancel_cb,
            )
            return
        device_box = self._get_device_box(address)
        if not device_box:
            self._show_fallback_confirm(
                device_path,
                "Authorize service?",
                uuid,
                confirm_cb,
                cancel_cb,
            )
            return

        device = self.client.get_device(address)
        device_name = device.name if device and device.name else "Bluetooth device"
        device_box.show_passkey_confirm_prompt(
            title=f"Authorize {device_name} service?",
            passkey=uuid,
            on_confirm=confirm_cb,
            on_cancel=cancel_cb,
        )

    def _on_agent_cancel(self, device_path: str | None):
        if not device_path:
            for _, (_, _, device_box) in self.device_rows.items():
                device_box.close_prompt()
                device_box.cancel_pairing()
            self._clear_fallback_prompt()
            return

        address = self._address_from_path(device_path)
        if not address:
            return
        device_box = self._get_device_box(address)
        if device_box:
            device_box.close_prompt()
            device_box.cancel_pairing()
        else:
            self._clear_fallback_prompt()

    def _show_fallback_entry(
        self, device_path: str, title: str, placeholder: str, reply_cb, cancel_cb
    ):
        self._ensure_fallback_prompt()
        if not self._fallback_prompt_box:
            self._handle_missing_device(cancel_cb)
            return

        device_name = self._get_device_name_from_path(device_path)

        def _on_submit(code: str):
            self._clear_fallback_prompt()
            reply_cb(code)

        def _on_cancel():
            self._clear_fallback_prompt()
            cancel_cb()

        self._fallback_prompt_box.show_entry(
            title=f"{title} for {device_name}",
            placeholder=placeholder,
            on_submit=_on_submit,
            on_cancel=_on_cancel,
        )

    def _show_fallback_confirm(
        self, device_path: str, title: str, passkey: str, confirm_cb, cancel_cb
    ):
        self._ensure_fallback_prompt()
        if not self._fallback_prompt_box:
            self._handle_missing_device(cancel_cb)
            return

        device_name = self._get_device_name_from_path(device_path)

        def _on_confirm():
            self._clear_fallback_prompt()
            confirm_cb()

        def _on_cancel():
            self._clear_fallback_prompt()
            cancel_cb()

        self._fallback_prompt_box.show_confirm(
            title=f"{title} for {device_name}",
            passkey=passkey,
            on_confirm=_on_confirm,
            on_cancel=_on_cancel,
        )

    def _show_fallback_display(self, device_path: str, title: str, passkey: str):
        self._ensure_fallback_prompt()
        if not self._fallback_prompt_box:
            return

        device_name = self._get_device_name_from_path(device_path)
        self._fallback_prompt_box.show_display(
            title=f"{title} for {device_name}",
            passkey=passkey,
        )


class BluetoothToggle(QSChevronButton):
    """A widget to display the Bluetooth status."""

    def __init__(self, submenu: QuickSubMenu, **kwargs):
        super().__init__(
            style_classes=["quicksettings-toggler"],
            action_label="On",
            action_icon=text_icons["bluetooth"]["on"],
            submenu=submenu,
            **kwargs,
        )

        # Client Signals
        self.client = bluetooth_service
        self._device_signals = []  # Store device signal IDs

        # Track main client signals
        self._client_signals = bulk_connect(
            self.client,
            {"device-added": self.new_device, "notify::enabled": self.toggle_bluetooth},
        )
        self.connect("destroy", self._on_destroy)

        self.toggle_bluetooth(self.client)

        for device in self.client.devices:
            self.new_device(self.client, device.address)
        if self.client.connected_devices:
            self.device_connected(self.client.connected_devices[0])

        # Button Signals
        self.connect("action-clicked", lambda *_: self.client.toggle_power())

    def _on_destroy(self, *_):
        # Disconnect client signals
        for sig_id in self._client_signals:
            try:
                self.client.disconnect(sig_id)
            except Exception:
                pass

        # Disconnect individual device signals
        for device, sig_id in self._device_signals:
            try:
                if device.handler_is_connected(sig_id):
                    device.disconnect(sig_id)
            except Exception:
                pass
        self._device_signals.clear()

    def toggle_bluetooth(self, client: BluetoothClient, *_):
        if client.enabled:
            self.add_style_class("active")
            self.action_icon.set_label(text_icons["bluetooth"]["on"])
            self.action_label.set_label("On")
        else:
            self.remove_style_class("active")
            self.action_icon.set_label(text_icons["bluetooth"]["off"])
            self.action_label.set_label("Off")

    def new_device(self, client: BluetoothClient, address: str):
        device = client.get_device(address)
        if device is None:
            return

        # Track the connected signal
        sig_id = device.connect("changed", self.device_connected)
        self._device_signals.append((device, sig_id))

    def device_connected(self, device: BluetoothDevice, *_):
        # Safety check if widget is destroyed but signal fired
        try:
            if not self.action_label or self.action_label.in_destruction():
                return
        except AttributeError:
            return

        if device.connected:
            self.action_label.set_label(device.name)
        elif self.action_label.get_label() == device.name:
            self.action_label.set_label(
                self.client.connected_devices[0].name
                if self.client.connected_devices
                else "On"
            )

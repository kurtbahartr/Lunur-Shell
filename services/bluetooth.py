from __future__ import annotations

from typing import Callable, Optional
from gi.repository import Gio, GLib


AGENT_OBJECT_PATH = "/org/lunur/bluetooth/agent"

AGENT_XML = """
<node>
  <interface name="org.bluez.Agent1">
    <method name="Release" />
    <method name="RequestPinCode">
      <arg type="o" name="device" direction="in"/>
      <arg type="s" name="pincode" direction="out"/>
    </method>
    <method name="RequestPasskey">
      <arg type="o" name="device" direction="in"/>
      <arg type="u" name="passkey" direction="out"/>
    </method>
    <method name="DisplayPasskey">
      <arg type="o" name="device" direction="in"/>
      <arg type="u" name="passkey" direction="in"/>
      <arg type="q" name="entered" direction="in"/>
    </method>
    <method name="RequestConfirmation">
      <arg type="o" name="device" direction="in"/>
      <arg type="u" name="passkey" direction="in"/>
    </method>
    <method name="RequestAuthorization">
      <arg type="o" name="device" direction="in"/>
    </method>
    <method name="AuthorizeService">
      <arg type="o" name="device" direction="in"/>
      <arg type="s" name="uuid" direction="in"/>
    </method>
    <method name="Cancel" />
  </interface>
</node>
"""


ReplyCallback = Callable[[], None]
ValueReplyCallback = Callable[[str], None]


class BluetoothPairingAgent:
    def __init__(
        self,
        on_request_pin: Callable[[str, ValueReplyCallback, ReplyCallback], None],
        on_request_passkey: Callable[[str, ValueReplyCallback, ReplyCallback], None],
        on_request_confirmation: Callable[
            [str, int, ReplyCallback, ReplyCallback], None
        ],
        on_display_passkey: Callable[[str, int, int], None],
        on_request_authorization: Callable[[str, ReplyCallback, ReplyCallback], None],
        on_authorize_service: Callable[[str, str, ReplyCallback, ReplyCallback], None],
        on_cancel: Callable[[Optional[str]], None],
        on_release: Optional[Callable[[], None]] = None,
        object_path: str = AGENT_OBJECT_PATH,
    ):
        self.on_request_pin = on_request_pin
        self.on_request_passkey = on_request_passkey
        self.on_request_confirmation = on_request_confirmation
        self.on_display_passkey = on_display_passkey
        self.on_request_authorization = on_request_authorization
        self.on_authorize_service = on_authorize_service
        self.on_cancel = on_cancel
        self.on_release = on_release
        self.object_path = object_path

        self.bus: Optional[Gio.DBusConnection] = None
        self._registration_id: Optional[int] = None
        self._agent_manager: Optional[Gio.DBusProxy] = None
        self._node_info: Optional[Gio.DBusNodeInfo] = None
        self._interface_info: Optional[Gio.DBusInterfaceInfo] = None
        self._method_call_cb = None
        self._registered = False

    def register(self) -> bool:
        if self._registered:
            return True

        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            self._node_info = Gio.DBusNodeInfo.new_for_xml(AGENT_XML)
            self._interface_info = self._node_info.interfaces[0]
            self._method_call_cb = self._on_method_call

            self._registration_id = self.bus.register_object(
                self.object_path,
                self._interface_info,
                method_call_closure=self._method_call_cb,
                get_property_closure=None,
                set_property_closure=None,
            )

            self._agent_manager = Gio.DBusProxy.new_sync(
                self.bus,
                Gio.DBusProxyFlags.NONE,
                None,
                "org.bluez",
                "/org/bluez",
                "org.bluez.AgentManager1",
                None,
            )

            self._agent_manager.call_sync(
                "RegisterAgent",
                GLib.Variant("(os)", (self.object_path, "KeyboardDisplay")),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )

            self._agent_manager.call_sync(
                "RequestDefaultAgent",
                GLib.Variant("(o)", (self.object_path,)),
                Gio.DBusCallFlags.NONE,
                -1,
                None,
            )

            self._registered = True
            return True
        except Exception:
            self._registered = False
            return False

    def unregister(self):
        if not self.bus:
            return

        if self._agent_manager and self._registered:
            try:
                self._agent_manager.call_sync(
                    "UnregisterAgent",
                    GLib.Variant("(o)", (self.object_path,)),
                    Gio.DBusCallFlags.NONE,
                    -1,
                    None,
                )
            except Exception:
                pass

        if self._registration_id is not None:
            try:
                self.bus.unregister_object(self._registration_id)
            except Exception:
                pass

        self._registration_id = None
        self._interface_info = None
        self._node_info = None
        self._method_call_cb = None
        self._registered = False

    def _return_ok(self, invocation: Gio.DBusMethodInvocation):
        invocation.return_value(GLib.Variant("()", ()))

    def _return_cancelled(self, invocation: Gio.DBusMethodInvocation):
        invocation.return_dbus_error("org.bluez.Error.Canceled", "Canceled")

    def _on_method_call(
        self,
        _connection: Gio.DBusConnection,
        _sender: str,
        _object_path: str,
        _interface_name: str,
        method_name: str,
        parameters: GLib.Variant,
        invocation: Gio.DBusMethodInvocation,
        _user_data=None,
    ):
        if method_name == "Release":
            if self.on_release:
                self.on_release()
            self._return_ok(invocation)
            return

        if method_name == "Cancel":
            self.on_cancel(None)
            self._return_ok(invocation)
            return

        if method_name == "RequestPinCode":
            (device_path,) = parameters.unpack()

            def _reply(code: str):
                invocation.return_value(GLib.Variant("(s)", (code,)))

            def _cancel():
                self._return_cancelled(invocation)

            self.on_request_pin(device_path, _reply, _cancel)
            return

        if method_name == "RequestPasskey":
            (device_path,) = parameters.unpack()

            def _reply(code: str):
                try:
                    passkey = int(code)
                except ValueError:
                    passkey = 0
                invocation.return_value(GLib.Variant("(u)", (passkey,)))

            def _cancel():
                self._return_cancelled(invocation)

            self.on_request_passkey(device_path, _reply, _cancel)
            return

        if method_name == "DisplayPasskey":
            device_path, passkey, entered = parameters.unpack()
            self.on_display_passkey(device_path, int(passkey), int(entered))
            self._return_ok(invocation)
            return

        if method_name == "RequestConfirmation":
            device_path, passkey = parameters.unpack()

            def _confirm():
                self._return_ok(invocation)

            def _cancel():
                self._return_cancelled(invocation)

            self.on_request_confirmation(device_path, int(passkey), _confirm, _cancel)
            return

        if method_name == "RequestAuthorization":
            (device_path,) = parameters.unpack()

            def _confirm():
                self._return_ok(invocation)

            def _cancel():
                self._return_cancelled(invocation)

            self.on_request_authorization(device_path, _confirm, _cancel)
            return

        if method_name == "AuthorizeService":
            device_path, uuid = parameters.unpack()

            def _confirm():
                self._return_ok(invocation)

            def _cancel():
                self._return_cancelled(invocation)

            self.on_authorize_service(device_path, uuid, _confirm, _cancel)
            return

        invocation.return_dbus_error(
            "org.bluez.Error.NotSupported",
            f"Method {method_name} not supported",
        )

import os
import subprocess
import tempfile
from datetime import datetime
from typing import Optional

from fabric.core.service import Property, Service, Signal
from fabric.utils import (
    exec_shell_command,
    exec_shell_command_async,
    get_relative_path,
    logger,
)
from gi.repository import Gio, GLib

import utils.functions as helpers
from utils.constants import APPLICATION_NAME
from utils.icons import icons


class ScreenRecorderService(Service):
    """Service to handle screen recording"""

    @Signal
    def recording(self, value: bool) -> None: ...

    _instance: Optional["ScreenRecorderService"] = None
    _enabled = True

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, **kwargs):
        if getattr(self, "_initialized", False):
            return
        super().__init__(**kwargs)
        self._initialized = True
        self.home_dir = GLib.get_home_dir()
        self.shutter_sound = get_relative_path("../assets/sounds/camera-shutter.mp3")
        self._current_screencast_path = None
        self.screenrecord_path = None
        self.screenshot_path = None
        self._widget_config: dict = {}

    @classmethod
    def get_instance(cls) -> "ScreenRecorderService":
        """Get the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_widget_config(self, config: dict):
        """Set the widget configuration."""
        self._widget_config = config
        logger.info("[SCREENRECORD] Widget config updated")

    def _get_screenshot_config(self) -> dict:
        """Get screenshot config from stored widget_config."""
        return self._widget_config.get("screenshot", {})

    def _get_recorder_config(self) -> dict:
        """Get recorder config from stored widget_config."""
        return self._widget_config.get("recorder", {})

    @classmethod
    def set_enabled(cls, enabled: bool):
        """Enable or disable the screen recorder service."""
        cls._enabled = enabled
        logger.info(f"[SCREENRECORD] Service {'enabled' if enabled else 'disabled'}")

    def screenrecord_start(
        self,
        config: dict = None,
        fullscreen: bool = False,
    ):
        """Start screen recording using wf-recorder."""
        if not self._enabled:
            logger.warning("[SCREENRECORD] Service is disabled")
            return

        # Use provided config or get from stored widget_config
        if config is None:
            config = self._get_recorder_config()

        path = config.get("path", "Videos/Recordings")

        self.screenrecord_path = os.path.join(self.home_dir, path)
        os.makedirs(self.screenrecord_path, exist_ok=True)

        if self.is_recording:
            logger.warning(
                "[SCREENRECORD] Another instance of wf-recorder is already running."
            )
            self._send_simple_notification(
                "Recording Already Active",
                "Stop the current recording first.",
                icon=icons["ui"]["camera-video"],
            )
            return

        timestamp = datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = os.path.join(self.screenrecord_path, f"{timestamp}.mp4")
        self._current_screencast_path = file_path

        # Get area selection if not fullscreen
        area = ""
        if not fullscreen:
            try:
                area_selection = exec_shell_command("slurp").strip()
                if not area_selection:
                    logger.info("[SCREENRECORD] Area selection cancelled")
                    return
                area = f"-g '{area_selection}'"
            except Exception as e:
                logger.exception(f"[SCREENRECORD] Failed to get area: {e}")
                return

        audio = "--audio=@DEFAULT_MONITOR@" if config.get("audio", False) else ""
        command = (
            f"wf-recorder {audio} --file={file_path} --pixel-format yuv420p {area}"
        )

        def start_recording():
            exec_shell_command_async(command, lambda *_: None)
            self.emit("recording", True)
            self._send_simple_notification(
                "Recording Started",
                "Screen recording is now active.",
                icon=icons["ui"]["camera-video"],
            )
            return False

        if config.get("delayed", False):
            timeout = config.get("delayed_timeout", 5000)
            self._send_simple_notification(
                "Recording Starting",
                f"Recording will start in {timeout // 1000} seconds...",
                icon=icons["ui"]["camera-video"],
            )
            GLib.timeout_add(timeout, start_recording)
        else:
            start_recording()

    def _send_simple_notification(self, title: str, body: str, icon: str = None):
        """Send a simple notification without actions."""
        cmd = [
            "notify-send",
            "-t",
            "3000",
            "-a",
            f"{APPLICATION_NAME}",
        ]
        if icon:
            cmd.extend(["-i", icon])
        cmd.extend([title, body])

        try:
            Gio.Subprocess.new(cmd, Gio.SubprocessFlags.NONE)
        except Exception as e:
            logger.exception(f"[NOTIFICATION] Failed to send: {e}")

    def send_screenshot_notification(self, file_path: str = None):
        """Send screenshot notification with actions."""
        cmd = ["notify-send"]
        cmd.extend(
            [
                "-A",
                "files=Show in Files",
                "-A",
                "view=View",
                "-A",
                "edit=Edit",
                "-t",
                "5000",
                "-i",
                icons["ui"]["camera"],
                "-a",
                f"{APPLICATION_NAME} Screenshot Utility",
                "-h",
                f"STRING:image-path:{file_path}",
                "Screenshot Saved",
                f"Saved Screenshot at {file_path}",
            ]
            if file_path
            else ["Screenshot Sent to Clipboard"]
        )

        proc: Gio.Subprocess = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE)

        def _callback(process: Gio.Subprocess, task: Gio.Task):
            try:
                _, stdout, stderr = process.communicate_utf8_finish(task)
            except Exception:
                logger.exception("[SCREENSHOT] Failed read notification action")
                return

            match stdout.strip("\n"):
                case "files":
                    exec_shell_command_async(
                        f"xdg-open {self.screenshot_path}", lambda *_: None
                    )
                case "view":
                    exec_shell_command_async(f"xdg-open {file_path}", lambda *_: None)
                case "edit":
                    exec_shell_command_async(f"swappy -f {file_path}", lambda *_: None)

        proc.communicate_utf8_async(None, None, _callback)

    def screenshot(
        self,
        config: dict = None,
        fullscreen: bool = False,
        save_copy: bool = True,
    ):
        """Take a screenshot using grimblast."""
        if not self._enabled:
            logger.warning("[SCREENSHOT] Service is disabled")
            return

        # Use provided config or get from stored widget_config
        if config is None:
            config = self._get_screenshot_config()

        path = config.get("path", "Pictures/Screenshots")

        self.screenshot_path = os.path.join(self.home_dir, path)
        os.makedirs(self.screenshot_path, exist_ok=True)

        timestamp = datetime.today().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = os.path.join(self.screenshot_path, f"{timestamp}.png")

        annotate = config.get("annotate", False)
        temp_path = file_path

        if annotate:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                temp_path = temp_file.name

        command = (
            ["grimblast", "copysave", "screen", temp_path]
            if save_copy
            else ["grimblast", "copy", "screen"]
        )

        if not fullscreen:
            command[2] = "area"

        def after_screenshot(*_):
            try:
                # Check if screenshot was actually taken
                if not os.path.exists(temp_path):
                    logger.info("[SCREENSHOT] Screenshot cancelled or failed")
                    return

                if annotate:
                    result = subprocess.run(
                        [
                            "satty",
                            "--filename",
                            temp_path,
                            "--output-filename",
                            file_path,
                        ],
                        check=False,
                    )
                    if os.path.exists(temp_path) and temp_path != file_path:
                        os.unlink(temp_path)

                    if result.returncode != 0:
                        logger.warning("[SCREENSHOT] Annotation cancelled")
                        return

                self.send_screenshot_notification(file_path=file_path)

            except Exception as e:
                logger.exception(
                    f"[SCREENSHOT] Error in annotation or notification: {e}"
                )

        def take_screenshot():
            try:
                exec_shell_command_async(" ".join(command), after_screenshot)
            except Exception:
                logger.exception(f"[SCREENSHOT] Failed to run command: {command}")
            return False

        if config.get("delayed", False):
            timeout = config.get("delayed_timeout", 5000)
            self._send_simple_notification(
                "Screenshot",
                f"Taking screenshot in {timeout // 1000} seconds...",
                icon=icons["ui"]["camera"],
            )
            GLib.timeout_add(timeout, take_screenshot)
        else:
            take_screenshot()

    def send_screenrecord_notification(self, file_path: str):
        """Send screen recording notification with actions."""
        cmd = [
            "notify-send",
            "-A",
            "files=Show in Files",
            "-A",
            "view=View",
            "-t",
            "5000",
            "-i",
            icons["ui"]["camera-video"],
            "-a",
            f"{APPLICATION_NAME} Recording Utility",
            "Screenrecord Saved",
            f"Saved Screencast at {file_path}",
        ]

        proc: Gio.Subprocess = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE)

        def _callback(process: Gio.Subprocess, task: Gio.Task):
            try:
                _, stdout, stderr = process.communicate_utf8_finish(task)
            except Exception:
                logger.exception("[SCREENRECORD] Failed read notification action")
                return

            match stdout.strip("\n"):
                case "files":
                    exec_shell_command_async(
                        f"xdg-open {self.screenrecord_path}", lambda *_: None
                    )
                case "view":
                    exec_shell_command_async(f"xdg-open {file_path}", lambda *_: None)

        proc.communicate_utf8_async(None, None, _callback)

    @Property(bool, "readable", default_value=False)
    def is_recording(self):
        return helpers.is_app_running("wf-recorder")

    def screenrecord_stop(self):
        """Stop screen recording."""
        if not self._enabled:
            logger.warning("[SCREENRECORD] Service is disabled")
            return

        if not self.is_recording:
            self._send_simple_notification(
                "No Recording",
                "No active recording to stop.",
                icon=icons["ui"]["camera-video"],
            )
            return

        helpers.kill_process("wf-recorder")
        self.emit("recording", False)

        # Wait briefly for file to be written, then notify
        def send_notification():
            if self._current_screencast_path and os.path.exists(
                self._current_screencast_path
            ):
                self.send_screenrecord_notification(self._current_screencast_path)
            return False

        GLib.timeout_add(500, send_notification)


# ============================================
# Module-level convenience functions for fabric-cli
# ============================================

_recorder_instance: Optional[ScreenRecorderService] = None


def get_recorder() -> ScreenRecorderService:
    """Get the ScreenRecorderService singleton instance."""
    global _recorder_instance
    if _recorder_instance is None:
        _recorder_instance = ScreenRecorderService.get_instance()
    return _recorder_instance


def take_screenshot(fullscreen: bool = False) -> None:
    """Take a screenshot. Call from fabric-cli."""
    get_recorder().screenshot(fullscreen=fullscreen)


def record_start(fullscreen: bool = False) -> None:
    """Start screen recording. Call from fabric-cli."""
    get_recorder().screenrecord_start(fullscreen=fullscreen)


def record_stop() -> None:
    """Stop screen recording. Call from fabric-cli."""
    get_recorder().screenrecord_stop()

import time
import setproctitle
from fabric import Application
from fabric.utils import cooldown, exec_shell_command, get_relative_path, monitor_file
from loguru import logger
from gi.repository import Gtk

import utils.functions as helpers
from modules.bar import StatusBar
from modules.launcher import AppLauncher
from utils import (
    APPLICATION_NAME,
    APP_CACHE_DIRECTORY,
    ExecutableNotFoundError,
    widget_config,
)

DEBUG = widget_config.get("general", {}).get("debug")


def time_module_load(name: str, func):
    if DEBUG:
        start = time.time()
        result = func()
        end = time.time()
        elapsed_ms = (end - start) * 1000
        logger.info(f"[Timing] Module '{name}' loaded in {elapsed_ms:.1f} ms")
        return result
    else:
        return func()


def compile_scss():
    if not helpers.executable_exists("sass"):
        raise ExecutableNotFoundError("sass")

    logger.info("[Main] Compiling SCSS")

    if DEBUG:
        start = time.time()
        output = exec_shell_command(
            "sass styles/main.scss dist/main.css --no-source-map"
        )
        end = time.time()
        elapsed_ms = (end - start) * 1000
        logger.info(f"[Timing] SCSS compiled in {elapsed_ms:.1f} ms")
    else:
        output = exec_shell_command(
            "sass styles/main.scss dist/main.css --no-source-map"
        )

    if output != "":
        logger.error("[Main] Failed to compile SCSS!")


@cooldown(2)
@helpers.run_in_thread
def process_and_apply_css(app: Application):
    compile_scss()
    app.set_stylesheet_from_file(get_relative_path("dist/main.css"))
    logger.info("[Main] CSS applied")


if __name__ == "__main__":
    helpers.ensure_directory(APP_CACHE_DIRECTORY)

    # Compile SCSS first to ensure styles are ready before widgets
    compile_scss()

    launcher = time_module_load("AppLauncher", lambda: AppLauncher())
    bar = time_module_load("StatusBar", lambda: StatusBar(widget_config))
    windows = [bar, launcher]

    if widget_config.get("keybinds", {}).get("enabled"):
        from modules.keybinds import KeybindsWidget

        keybinds = time_module_load(
            "KeybindsWidget", lambda: KeybindsWidget(widget_config)
        )
        windows.append(keybinds)

    if widget_config.get("notification", {}).get("enabled"):
        from modules.notification import NotificationPopup

        notifications = time_module_load(
            "NotificationPopup", lambda: NotificationPopup(widget_config)
        )
        windows.append(notifications)

    if widget_config.get("general", {}).get("screen_corners", {}).get("enabled"):
        from modules.corners import ScreenCorners

        screen_corners = time_module_load(
            "ScreenCorners", lambda: ScreenCorners(widget_config)
        )
        windows.append(screen_corners)

    if widget_config.get("osd", {}).get("enabled"):
        from modules.osd import OSDWindow

        osd = time_module_load("OSDWindow", lambda: OSDWindow(widget_config))
        windows.append(osd)

    app = Application(APPLICATION_NAME, windows=windows)
    app.set_stylesheet_from_file(get_relative_path("dist/main.css"))

    helpers.copy_theme(widget_config["theme"]["name"])

    icon_theme = Gtk.IconTheme.get_default()
    icons_dir = get_relative_path("./assets/icons/svg/gtk")
    icon_theme.append_search_path(icons_dir)

    # File monitoring
    style_monitor = monitor_file(get_relative_path("./styles"))
    watch_matugen = monitor_file(get_relative_path("./styles/themes/matugen.scss"))
    watch_matugen.connect(
        "changed",
        lambda *args: (
            helpers.copy_theme(widget_config["theme"]["name"]),
            process_and_apply_css(app),
        ),
    )
    style_monitor.connect("changed", lambda *args: process_and_apply_css(app))

    setproctitle.setproctitle(APPLICATION_NAME)
    app.run()

import subprocess
from fabric import Application
from fabric.utils import get_relative_path
from modules.bar import StatusBar
from modules.launcher import AppLauncher
from services.notifications import create_notification_window

def apply_css(app: Application):
    result = subprocess.run(
        ["sass", "styles/main.scss", "dist/main.css", "--no-source-map"],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        app.set_stylesheet_from_file(get_relative_path("dist/main.css"))
        print("CSS applied")
    else:
        app.set_stylesheet_from_string("")
        print(f"Failed to compile sass! {result.stderr}")


if __name__ == "__main__":
    launcher = AppLauncher()
    bar = StatusBar()
    notifications = create_notification_window()
    app = Application("Lunur-Shell", bar, launcher, notifications)

    apply_css(app)

    app.run()


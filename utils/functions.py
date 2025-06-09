from functools import lru_cache
from gi.repository import GLib
from .icons import text_icons  # Ensure this dictionary has distro icons mapped
import time

def ttl_lru_cache(seconds_to_live: int, maxsize: int = 128):
    def wrapper(func):
        @lru_cache(maxsize)
        def inner(__ttl, *args, **kwargs):
            return func(*args, **kwargs)
        return lambda *args, **kwargs: inner(time.time() // seconds_to_live, *args, **kwargs)
    return wrapper

@ttl_lru_cache(600, 10)
def get_distro_icon():
    distro_id = GLib.get_os_info("ID")
    return text_icons["distro"].get(distro_id, "")  # Fallback icon


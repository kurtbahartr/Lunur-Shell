import os
import json
import time
import pytomlpp
from fabric.utils import get_relative_path
from loguru import logger

from .constants import DEFAULT_CONFIG
from .functions import (
    exclude_keys,
    merge_defaults,
    validate_widgets,
    ttl_lru_cache,
)
from .widget_settings import BarConfig


class LunurShellConfig:
    "Reads config file, merges with defaults, and exposes the result."

    instance = None

    @staticmethod
    def get_default():
        if LunurShellConfig.instance is None:
            LunurShellConfig.instance = LunurShellConfig()
        return LunurShellConfig.instance

    def __init__(self):
        self.json_config = get_relative_path("../config.json")
        self.toml_config = get_relative_path("../config.toml")
        self.default_config()

    @ttl_lru_cache(600, 10)
    def read_config_json(self) -> dict:
        logger.info(f"[Config] Reading JSON from {self.json_config}")
        with open(self.json_config, "r", encoding="utf-8") as file:
            return json.load(file)

    @ttl_lru_cache(600, 10)
    def read_config_toml(self) -> dict:
        logger.info(f"[Config] Reading TOML from {self.toml_config}")
        with open(self.toml_config, "r", encoding="utf-8") as file:
            return pytomlpp.load(file)

    def default_config(self) -> None:
        if not (os.path.exists(self.json_config) or os.path.exists(self.toml_config)):
            raise FileNotFoundError("Missing config.json or config.toml")

        use_json = os.path.exists(self.json_config)
        start_time = time.perf_counter()

        data = self.read_config_json() if use_json else self.read_config_toml()

        read_time_ms = (time.perf_counter() - start_time) * 1000

        if data.get("general", {}).get("debug", False):
            config_type = "JSON" if use_json else "TOML"
            logger.info(
                f"[Timing] Config ({config_type}) read in {read_time_ms:.1f} ms"
            )

        validate_widgets(data, DEFAULT_CONFIG)

        # Replaced explicit for-loop with dictionary comprehension update
        data.update(
            {
                key: (
                    data.get(key, DEFAULT_CONFIG[key])
                    if key == "module_groups"
                    else merge_defaults(data.get(key, {}), DEFAULT_CONFIG[key])
                )
                for key in exclude_keys(DEFAULT_CONFIG, ["$schema"])
            }
        )

        self.config = data


configuration = LunurShellConfig.get_default()
widget_config = configuration.config

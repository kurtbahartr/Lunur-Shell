import os
import json
import pytomlpp
from fabric.utils import get_relative_path, logger

from .constants import DEFAULT_CONFIG
from .functions import (
    exclude_keys,
    merge_defaults,
    validate_widgets,
    ttl_lru_cache,
    total_time,
)


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

        # 1. Read Config
        read_func = self.read_config_json if use_json else self.read_config_toml
        config_type = "JSON" if use_json else "TOML"

        data = total_time(f"Read ({config_type})", read_func, category="Config")

        # Determine user debug preference for subsequent steps
        should_debug = data.get("general", {}).get("debug", False)

        # 2. Validate Widgets
        total_time(
            "Validation",
            lambda: validate_widgets(data, DEFAULT_CONFIG),
            debug=should_debug,
            category="Config",
        )

        # 3. Merge Defaults
        def merge_process():
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

        total_time("Merge", merge_process, debug=should_debug, category="Config")

        self.config = data


configuration = LunurShellConfig.get_default()
widget_config = configuration.config

# utils/gen_keybinds.py

import json
import subprocess
from typing import Iterator

modmask_map = {
    64: "SUPER",
    8: "ALT",
    4: "CTRL",
    1: "SHIFT",
}

def modmask_to_key(modmask: int) -> str:
    res = []
    for bf, key in modmask_map.items():
        if modmask & bf == bf:
            res.append(key)
            modmask -= bf
    if modmask != 0:
        res.append(f"({modmask})")
    if len(res) > 0:
        res.append("+ ")
    return " ".join(res)

class KeybindLoader:
    def __init__(self):
        self.keybinds = []

    def load_keybinds(self):
        try:
            output = subprocess.check_output(["hyprctl", "binds", "-j"], text=True)
            binds = json.loads(output)
        except Exception as e:
            print(f"ERROR: Failed to load keybinds from hyprctl: {e}")
            self.keybinds = []
            return

        self.keybinds.clear()
        for bind in binds:
            key_combo = modmask_to_key(bind['modmask']) + bind['key']
            description = bind.get('description', '').strip()
            dispatcher = bind.get('dispatcher', '').strip()
            arg = bind.get('arg', '').strip()
            cmd = f"{dispatcher}: {arg}".strip()
            self.keybinds.append((key_combo.strip(), description, cmd))

    def filter_keybinds(self, query: str = "") -> Iterator[tuple]:
        query_cf = query.casefold()
        return (kb for kb in self.keybinds if query_cf in " ".join(kb).casefold())


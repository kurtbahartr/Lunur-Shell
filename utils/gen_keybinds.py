import json
import subprocess
from typing import Iterator, List, Tuple

modmask_map = {
    64: "SUPER",
    8: "ALT",
    4: "CTRL",
    1: "SHIFT",
}


def modmask_to_key(modmask: int) -> str:
    keys = [key for bf, key in modmask_map.items() if (modmask & bf) == bf]
    known_bits = sum(bf for bf in modmask_map.keys())
    unknown_bits = modmask & (~known_bits)
    if unknown_bits != 0:
        keys.append(f"({unknown_bits})")
    return " + ".join(keys)


class KeybindLoader:
    def __init__(self):
        self.keybinds: List[Tuple[str, str, str]] = []

    def load_keybinds(self) -> None:
        try:
            output = subprocess.check_output(["hyprctl", "binds", "-j"], text=True)
            binds = json.loads(output)
        except Exception as e:
            print(f"ERROR: Failed to load keybinds from hyprctl: {e}")
            self.keybinds = []
            return

        self.keybinds = [
            (
                (
                    f"{modmask_to_key(bind['modmask'])} + {bind['key']}:"
                    if modmask_to_key(bind["modmask"])
                    else f"{bind['key']}:"
                ).strip(),
                bind.get("description", "").strip(),
                f"{bind.get('dispatcher', '').strip()}: {bind.get('arg', '').strip()}".strip(
                    ": "
                ),
            )
            for bind in binds
        ]

    def filter_keybinds(self, query: str = "") -> Iterator[Tuple[str, str, str]]:
        query_cf = query.casefold()
        return (kb for kb in self.keybinds if query_cf in " ".join(kb).casefold())

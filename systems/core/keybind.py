"""键位系统：从 data/keybinds.json 加载，不存在则生成默认"""
import json
import curses
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
KEYBINDS_FILE = BASE_DIR / "data" / "keybinds.json"

DEFAULTS = {
    "quit": "q", "quit_upper": "Q",
    "craft": "c", "craft_upper": "C",
    "equip": "e", "build": "b",
    "chest": "o", "chest_upper": "O",
    "look": "x", "dig": "d", "repeat": ".",
    "reload": "r", "reload_upper": "R",
    "save": "S", "load": "L",
    "move_up": "KEY_UP", "move_down": "KEY_DOWN",
    "move_left": "KEY_LEFT", "move_right": "KEY_RIGHT",
    "move_up_alt": "k", "move_down_alt": "j",
    "move_left_alt": "h", "move_right_alt": "l",
    "close": "c", "close_upper": "q",
    "confirm": "KEY_ENTER",
    "switch_tab": ",", "transfer_all": "+",
    "legacy_shop": "p",
}

CURSES_NAMES = {
    "KEY_UP": curses.KEY_UP,
    "KEY_DOWN": curses.KEY_DOWN,
    "KEY_LEFT": curses.KEY_LEFT,
    "KEY_RIGHT": curses.KEY_RIGHT,
    "KEY_ENTER": curses.KEY_ENTER,
    "KEY_BACKSPACE": curses.KEY_BACKSPACE,
    "KEY_HOME": curses.KEY_HOME,
    "KEY_END": curses.KEY_END,
    "KEY_PPAGE": curses.KEY_PPAGE,
    "KEY_NPAGE": curses.KEY_NPAGE,
}

_keymap = {}
_loaded = False


def _ensure_file():
    """Ensure the keybinds JSON file exists, creating it with defaults if not."""
    if not KEYBINDS_FILE.exists():
        KEYBINDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(KEYBINDS_FILE, "w", encoding="utf-8") as f:
            json.dump(DEFAULTS, f, indent=2, ensure_ascii=False)


def _parse_key(value):
    """Parse a key configuration value into its corresponding integer code."""
    if isinstance(value, int):
        return value
    if value in CURSES_NAMES:
        return CURSES_NAMES[value]
    if len(value) == 1:
        return ord(value)
    return ord(value)


def load_keybinds():
    """Load keybinds from the configuration file and populate the keymap cache."""
    global _keymap, _loaded
    _ensure_file()
    try:
        with open(KEYBINDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = DEFAULTS
    _keymap = {k: _parse_key(v)
               for k, v in data.items() if not k.startswith("_")}
    _loaded = True
    return _keymap


def get_key(name):
    """Get the integer key code associated with a given action name."""
    if not _loaded:
        load_keybinds()
    return _keymap.get(name, ord(name[0]) if len(name) == 1 else -1)


def reload_keybinds():
    """Reset the loaded status and re-load keybinds from the file."""
    global _loaded
    _loaded = False
    return load_keybinds()

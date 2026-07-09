""" config.py 全局配置——按功能分组。所有旧常量名通过 Config 实例兼容。"""
import curses
from dataclasses import dataclass


@dataclass
class _View:
    WIDTH: int = 40
    HEIGHT: int = 18


@dataclass
class _World:
    SEED: int = 51329
    LAYERS: int = 5
    LAYER_DEPTH_OFFSET: int = 50


@dataclass
class _Player:
    INITIAL_HP: int = 100
    BASE_DAMAGE_MIN: int = 2
    BASE_DAMAGE_MAX: int = 5
    BASE_HIT_CHANCE: float = 0.85


@dataclass
class _Spawn:
    INITIAL_COUNTDOWN: int = 20
    INTERVAL_MIN: int = 20
    INTERVAL_MAX: int = 40
    MIN_DISTANCE: int = 10
    MONSTER_SLEEP_DISTANCE: int = 30
    MONSTER_SLEEP_TICKS: int = 5


@dataclass
class _Day:
    LENGTH: int = 1800
    DAWN_START: int = 0
    DAY_START: int = 300
    DUSK_START: int = 1200
    NIGHT_START: int = 1500


class Config:
    view = _View()
    world = _World()
    player = _Player()
    spawn = _Spawn()
    day = _Day()


# ═══════════════════════════════════
# 平铺兼容别名（所有旧代码无需修改）
# ═══════════════════════════════════
VIEW_WIDTH = Config.view.WIDTH
VIEW_HEIGHT = Config.view.HEIGHT
WORLD_SEED = Config.world.SEED
WORLD_LAYERS = Config.world.LAYERS
LAYER_DEPTH_OFFSET = Config.world.LAYER_DEPTH_OFFSET
PLAYER_INITIAL_HP = 500
PLAYER_BASE_DAMAGE_MIN = Config.player.BASE_DAMAGE_MIN
PLAYER_BASE_DAMAGE_MAX = Config.player.BASE_DAMAGE_MAX
PLAYER_BASE_HIT_CHANCE = Config.player.BASE_HIT_CHANCE
SPAWN_INITIAL_COUNTDOWN = Config.spawn.INITIAL_COUNTDOWN
SPAWN_INTERVAL_MIN = Config.spawn.INTERVAL_MIN
SPAWN_INTERVAL_MAX = Config.spawn.INTERVAL_MAX
SPAWN_MIN_DISTANCE = Config.spawn.MIN_DISTANCE
MONSTER_SLEEP_DISTANCE = Config.spawn.MONSTER_SLEEP_DISTANCE
MONSTER_SLEEP_TICKS = Config.spawn.MONSTER_SLEEP_TICKS
DAY_LENGTH = Config.day.LENGTH
DAWN_START = Config.day.DAWN_START
DAY_START = Config.day.DAY_START
DUSK_START = Config.day.DUSK_START
NIGHT_START = Config.day.NIGHT_START

# ── 按键（保持原样，M28 键位系统会覆盖）──
KEY_QUIT = ord('q')
KEY_QUIT_UPPER = ord('Q')
KEY_CRAFT = ord('c')
KEY_CRAFT_UPPER = ord('C')
KEY_EQUIP = ord('e')
KEY_BUILD = ord('b')
KEY_REPEAT = ord('.')
KEY_RELOAD = ord('r')
KEY_RELOAD_UPPER = ord('R')
KEY_SAVE = ord('s')
KEY_SAVE_UPPER = ord('S')
KEY_LOAD = ord('l')
KEY_LOAD_UPPER = ord('L')
KEY_LOOK = ord('x')
KEY_DIG = ord('d')
KEY_CHEST = ord('o')
KEY_CHEST_UPPER = ord('O')
KEY_NEW_GAME = ord('n')
KEY_NEW_GAME_UPPER = ord('N')
KEY_CLOSE = ord('c')
KEY_CLOSE_UPPER = ord('q')
KEY_ENTER = ord('\n')
KEY_ENTER_ALT = ord('\r')
KEY_LEFT = ord('h')
KEY_RIGHT = ord('l')
KEY_UP = ord('k')
KEY_DOWN = ord('j')

# 方向映射
DIRECTIONS = {
    curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0),
    curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1),
    KEY_LEFT: (-1, 0), KEY_RIGHT: (1, 0),
    KEY_UP: (0, -1), KEY_DOWN: (0, 1),
}

# M28: 键位系统初始化覆盖
import systems.keybind as _kb

def _init_keybinds():
    kb = _kb.load_keybinds()
    globals().update({
        "KEY_QUIT": kb.get("quit", KEY_QUIT),
        "KEY_QUIT_UPPER": kb.get("quit_upper", KEY_QUIT_UPPER),
        "KEY_CRAFT": kb.get("craft", KEY_CRAFT),
        "KEY_CRAFT_UPPER": kb.get("craft_upper", KEY_CRAFT_UPPER),
        "KEY_EQUIP": kb.get("equip", KEY_EQUIP),
        "KEY_BUILD": kb.get("build", KEY_BUILD),
        "KEY_REPEAT": kb.get("repeat", KEY_REPEAT),
        "KEY_RELOAD": kb.get("reload", KEY_RELOAD),
        "KEY_RELOAD_UPPER": kb.get("reload_upper", KEY_RELOAD_UPPER),
        "KEY_SAVE": kb.get("save", KEY_SAVE),
        "KEY_SAVE_UPPER": kb.get("save_upper", KEY_SAVE_UPPER),
        "KEY_LOAD": kb.get("load", KEY_LOAD),
        "KEY_LOAD_UPPER": kb.get("load_upper", KEY_LOAD_UPPER),
        "KEY_LOOK": kb.get("look", KEY_LOOK),
        "KEY_DIG": kb.get("dig", KEY_DIG),
        "KEY_CHEST": kb.get("chest", KEY_CHEST),
        "KEY_CHEST_UPPER": kb.get("chest_upper", KEY_CHEST_UPPER),
        "KEY_CLOSE": kb.get("close", KEY_CLOSE),
        "KEY_CLOSE_UPPER": kb.get("close_upper", KEY_CLOSE_UPPER),
        "KEY_SWITCH_TAB": kb.get("switch_tab", ord(',')),
        "KEY_TRANSFER_ALL": kb.get("transfer_all", ord('+')),
        "KEY_LEGACY_SHOP": kb.get("legacy_shop", ord('p')),
        "KEY_MOVE_UP_ALT": kb.get("move_up_alt", KEY_UP),
        "KEY_MOVE_DOWN_ALT": kb.get("move_down_alt", KEY_DOWN),
        "KEY_MOVE_LEFT_ALT": kb.get("move_left_alt", KEY_LEFT),
        "KEY_MOVE_RIGHT_ALT": kb.get("move_right_alt", KEY_RIGHT),
    })

_init_keybinds()

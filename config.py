""" config.py 全局配置常量。"""

# ── 视口 ──
VIEW_WIDTH = 40
VIEW_HEIGHT = 18

# ── 世界 ──
WORLD_SEED = 51329  # 随机种子

# ── 玩家 ──
PLAYER_INITIAL_HP = 100
PLAYER_BASE_DAMAGE_MIN = 2
PLAYER_BASE_DAMAGE_MAX = 5
PLAYER_BASE_HIT_CHANCE = 0.85

# ── 怪物 ──
SPAWN_INITIAL_COUNTDOWN = 20
SPAWN_INTERVAL_MIN = 20
SPAWN_INTERVAL_MAX = 40
SPAWN_MIN_DISTANCE = 10
MONSTER_SLEEP_DISTANCE = 30
MONSTER_SLEEP_TICKS = 5

# ── 多层世界 ──
WORLD_LAYERS = 5          # 总层数（0=地表, -1=地下1层, -2=地下2层...）
LAYER_DEPTH_OFFSET = 50   # 每层偏移量（叠加到 y 坐标计算深度）

# ── 昼夜循环 ──
DAY_LENGTH = 1800
DAWN_START = 0
DAY_START = 300
DUSK_START = 1200
NIGHT_START = 1500


# ═══════════════════════════════════════════
# 按键绑定（集中管理，M18）
# ═══════════════════════════════════════════
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
KEY_CLOSE_UPPER = ord('q')  # 兼容
KEY_ENTER = ord('\n')
KEY_ENTER_ALT = ord('\r')
KEY_LEFT = ord('h')
KEY_RIGHT = ord('l')
KEY_UP = ord('k')
KEY_DOWN = ord('j')

# M28: 从 keybinds.json 加载键位，覆盖上方默认值
import systems.keybind as _kb

def _init_keybinds():
    """用 keybinds.json 覆盖默认按键常量"""
    kb = _kb.load_keybinds()
    globals().update({
        "KEY_QUIT": kb["quit"],
        "KEY_QUIT_UPPER": kb["quit_upper"],
        "KEY_CRAFT": kb["craft"],
        "KEY_CRAFT_UPPER": kb["craft_upper"],
        "KEY_EQUIP": kb["equip"],
        "KEY_BUILD": kb["build"],
        "KEY_CHEST": kb["chest"],
        "KEY_CHEST_UPPER": kb["chest_upper"],
        "KEY_LOOK": kb["look"],
        "KEY_DIG": kb["dig"],
        "KEY_REPEAT": kb["repeat"],
        "KEY_RELOAD": kb["reload"],
        "KEY_RELOAD_UPPER": kb["reload_upper"],
        "KEY_SAVE": kb["save"],
        "KEY_LOAD": kb["load"],
        "KEY_CLOSE": kb["close"],
        "KEY_CLOSE_UPPER": kb["close_upper"],
        "KEY_SWITCH_TAB": kb["switch_tab"],
        "KEY_TRANSFER_ALL": kb["transfer_all"],
        "KEY_LEGACY_SHOP": kb["legacy_shop"],
        "KEY_MOVE_UP_ALT": kb["move_up_alt"],
        "KEY_MOVE_DOWN_ALT": kb["move_down_alt"],
        "KEY_MOVE_LEFT_ALT": kb["move_left_alt"],
        "KEY_MOVE_RIGHT_ALT": kb["move_right_alt"],
    })

_init_keybinds()

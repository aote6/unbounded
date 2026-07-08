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

"""codex.py —— 游戏显示系统唯一数据源

设计原则：
  - 大类决定符号，颜色决定子类
  - 加新东西只改数据表，不改渲染逻辑
  - 一个入口 get_display(key)，渲染器和图鉴共用

扩展指南：
  - 新大类：在 CATEGORY_SYMBOL 加一行
  - 新子类：在 CODEX 加一条，category 填对应大类名
  - 动态注册：调用 register(name, category, color, desc)
"""

# ═══════════════════════════════════════════════════
# 一、大类 → 符号映射（字符稀缺资源分配）
# ═══════════════════════════════════════════════════

from tile_props import (
    TILE_AIR, TILE_DIRT, TILE_STONE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
    TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_SAND,
    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,
    TILE_WATER, TILE_TREE, TILE_TORCH,
)
CATEGORY_SYMBOL = {
    "air": " ",
    "soft_terrain": ".",
    "loose_terrain": "░",  # ░
    "hard_terrain": "#",
    "liquid": "~",
    "plant": "▲",  # ▲
    "rough_wall": "▓",  # ▓
    "smooth_wall": "▒",  # ▒
    "solid_block": "█",  # █
    "fixture": "□",  # □
    "floor": "=",
    "door": "+",
    "light_source": "!",
    "storage": "□",  # □
    "corpse": "%",
    "drop_item": "*",
    "stairs_down": ">",
    "stairs_up": "<",
    "player": "@",
    "monster": "A-Z",
    "passive": "a-z",
}

# ═══════════════════════════════════════════════════
# 二、颜色语义表（256色）
# ═══════════════════════════════════════════════════

COLOR = {
    "earth_brown": 94, "earth_dark": 95,
    "sand_yellow": 180, "sand_light": 187,
    "stone_gray": 240, "stone_mid": 246,
    "stone_light": 252, "stone_dark": 238,
    "obsidian": 232, "coal": 234,
    "water_deep": 20, "water_shallow": 51,
    "lava": 196, "acid": 118,
    "tree_green": 28, "grass": 34,
    "wood_brown": 94, "wood_dark": 58,
    "copper": 172, "iron": 250,
    "silver": 255, "gold": 220,
    "diamond": 51, "sulfur": 226,
    "salt": 195, "clay": 95,
    "brick_red": 131, "bone_white": 255,
    "glass_cyan": 51, "silk_pink": 219,
    "fire_orange": 202, "light_warm": 229,
    "monster_red": 196, "passive_green": 76,
    "corpse_gray": 238, "player_green": 46,
    "white": 255, "black": 232,
    "unknown": 7,
}

# ═══════════════════════════════════════════════════
# 三、核心数据表
# ═══════════════════════════════════════════════════

CODEX = {
    "泥土": {"category": "soft_terrain", "color": COLOR["earth_brown"], "desc": "松软泥土，可挖掘"},
    "黏土": {"category": "soft_terrain", "color": COLOR["clay"], "desc": "湿润黏土"},
    "沙子": {"category": "loose_terrain", "color": COLOR["sand_yellow"], "desc": "松散沙地"},
    "灰烬": {"category": "loose_terrain", "color": COLOR["stone_gray"], "desc": "燃烧后的灰烬"},
    "石头": {"category": "hard_terrain", "color": COLOR["stone_gray"], "desc": "坚硬的岩石"},
    "石灰岩": {"category": "hard_terrain", "color": COLOR["stone_mid"], "desc": "层积石灰岩"},
    "大理石": {"category": "hard_terrain", "color": COLOR["stone_light"], "desc": "光滑大理石"},
    "花岗岩": {"category": "hard_terrain", "color": COLOR["stone_dark"], "desc": "坚硬花岗岩"},
    "黑曜石": {"category": "hard_terrain", "color": COLOR["obsidian"], "desc": "暗沉黑曜石"},
    "煤矿": {"category": "hard_terrain", "color": COLOR["coal"], "desc": "黑色煤矿"},
    "铜矿石": {"category": "hard_terrain", "color": COLOR["copper"], "desc": "泛铜色矿石"},
    "铁矿石": {"category": "hard_terrain", "color": COLOR["iron"], "desc": "坚硬铁矿石"},
    "银矿石": {"category": "hard_terrain", "color": COLOR["silver"], "desc": "闪耀银光"},
    "金矿石": {"category": "hard_terrain", "color": COLOR["gold"], "desc": "金光闪闪"},
    "钻石原石": {"category": "hard_terrain", "color": COLOR["diamond"], "desc": "璀璨钻石"},
    "硫磺": {"category": "hard_terrain", "color": COLOR["sulfur"], "desc": "黄色硫磺"},
    "盐矿石": {"category": "hard_terrain", "color": COLOR["salt"], "desc": "白色盐矿石"},
    "水域": {"category": "liquid", "color": COLOR["water_deep"], "desc": "无法通行"},
    "浅水": {"category": "liquid", "color": COLOR["water_shallow"], "desc": "可以涉过"},
    "熔岩": {"category": "liquid", "color": COLOR["lava"], "desc": "极度危险"},
    "树木": {"category": "plant", "color": COLOR["tree_green"], "desc": "可砍伐获取木材"},
    "灌木": {"category": "plant", "color": COLOR["grass"], "desc": "低矮灌木"},
    "石墙": {"category": "rough_wall", "color": COLOR["stone_gray"], "desc": "坚固石墙"},
    "木墙": {"category": "rough_wall", "color": COLOR["wood_brown"], "desc": "木质墙壁"},
    "砖墙": {"category": "rough_wall", "color": COLOR["brick_red"], "desc": "砖砌墙壁"},
    "骨墙": {"category": "rough_wall", "color": COLOR["bone_white"], "desc": "白骨垒墙"},
    "砂岩墙": {"category": "rough_wall", "color": COLOR["sand_yellow"], "desc": "砂岩墙壁"},
    "石灰岩墙": {"category": "rough_wall", "color": COLOR["stone_mid"], "desc": "石灰岩墙"},
    "大理石柱": {"category": "smooth_wall", "color": COLOR["stone_light"], "desc": "大理石柱"},
    "丝绸墙纸": {"category": "smooth_wall", "color": COLOR["silk_pink"], "desc": "精致墙纸"},
    "石砖墙": {"category": "smooth_wall", "color": COLOR["stone_mid"], "desc": "石砖墙面"},
    "花岗岩砖": {"category": "solid_block", "color": COLOR["stone_dark"], "desc": "花岗岩砖"},
    "玻璃窗": {"category": "fixture", "color": COLOR["glass_cyan"], "desc": "透明玻璃窗"},
    "木箱": {"category": "storage", "color": COLOR["wood_brown"], "desc": "储存物品"},
    "木地板": {"category": "floor", "color": COLOR["wood_brown"], "desc": "木质地板"},
    "木门": {"category": "door", "color": COLOR["wood_brown"], "desc": "可以开关"},
    "木桌": {"category": "fixture", "color": COLOR["wood_brown"], "desc": "木质桌子"},
    "木椅": {"category": "fixture", "color": COLOR["wood_brown"], "desc": "木质椅子"},
    "地毯": {"category": "floor", "color": COLOR["brick_red"], "desc": "柔软地毯"},
    "火把": {"category": "light_source", "color": COLOR["fire_orange"], "desc": "提供照明"},
    "火焰": {"category": "light_source", "color": COLOR["fire_orange"], "desc": "燃烧的火焰"},
    "盐灯": {"category": "light_source", "color": COLOR["light_warm"], "desc": "柔和光芒"},
    "硫磺灯": {"category": "light_source", "color": COLOR["sulfur"], "desc": "黄色光芒"},
    "向下的楼梯": {"category": "stairs_down", "color": COLOR["white"], "desc": "向下层"},
    "向上的楼梯": {"category": "stairs_up", "color": COLOR["white"], "desc": "向上层"},
    "史莱姆尸体": {"category": "corpse", "color": COLOR["corpse_gray"], "desc": "史莱姆残骸"},
    "巨型史莱姆尸体": {"category": "corpse", "color": COLOR["corpse_gray"], "desc": "巨型残骸"},
    "蝙蝠尸体": {"category": "corpse", "color": COLOR["corpse_gray"], "desc": "蝙蝠尸体"},
    "岩石傀儡残骸": {"category": "corpse", "color": COLOR["stone_gray"], "desc": "傀儡碎片"},
    "空气": {"category": "air", "color": COLOR["black"], "desc": ""},
}

# ═══════════════════════════════════════════════════
# 四、tile ID → name 映射
# ═══════════════════════════════════════════════════


TILE_ID_TO_NAME = {
    TILE_AIR: "空气",
    TILE_DIRT: "泥土",
    TILE_STONE: "石头",
    TILE_COAL: "煤矿",
    TILE_COPPER: "铜矿石",
    TILE_IRON: "铁矿石",
    TILE_SILVER: "银矿石",
    TILE_GOLD: "金矿石",
    TILE_DIAMOND: "钻石原石",
    TILE_SULFUR: "硫磺",
    TILE_SALT: "盐矿石",
    TILE_CLAY: "黏土",
    TILE_SAND: "沙子",
    TILE_LIMESTONE: "石灰岩",
    TILE_MARBLE: "大理石",
    TILE_GRANITE: "花岗岩",
    TILE_OBSIDIAN: "黑曜石",
    TILE_WATER: "水域",
    TILE_TREE: "树木",
    TILE_TORCH: "火把",
}

# ═══════════════════════════════════════════════════
# 五、API
# ═══════════════════════════════════════════════════

_DEFAULT = {
    "char": "?",
    "color": COLOR["unknown"],
    "name": "未知",
    "desc": "未定义",
    "category": None}


def get_display(key):
    """统一入口。key: int=地形ID, str=名字"""
    if isinstance(key, int):
        name = TILE_ID_TO_NAME.get(key)
        if name:
            entry = CODEX.get(name, _DEFAULT)
            result = {"name": name}
            result.update(entry)
            if "char" not in result:
                result["char"] = CATEGORY_SYMBOL.get(
                    result.get("category"), "?")
            return result
    elif isinstance(key, str):
        entry = CODEX.get(key)
        if entry:
            result = {"name": key}
            result.update(entry)
            if "char" not in result:
                result["char"] = CATEGORY_SYMBOL.get(
                    result.get("category"), "?")
            return result
    return dict(_DEFAULT)


def get_char(key):
    return get_display(key)["char"]


def get_color(key):
    return get_display(key)["color"]


def get_desc(key):
    return get_display(key)["desc"]


def get_codex_by_category(category=None):
    result = []
    for name, props in CODEX.items():
        if category is None or props.get("category") == category:
            entry = dict(props)
            entry["name"] = name
            result.append(entry)
    return result


def list_categories():
    return list(CATEGORY_SYMBOL.keys())


# ═══════════════════════════════════════════════════
# 六、动态扩展
# ═══════════════════════════════════════════════════

def register(name, category, color, desc="", char=None):
    CODEX[name] = {"category": category, "color": color, "desc": desc}
    if char:
        CODEX[name]["char"] = char


def register_category(name, symbol):
    CATEGORY_SYMBOL[name] = symbol


# ═══════════════════════════════════════════════════
# 七、兼容旧接口
# ═══════════════════════════════════════════════════

def get_color_attr(tile):
    return "white", "normal"

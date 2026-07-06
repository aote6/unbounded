#!/usr/bin/env python3
"""M9 第1步补丁 v2 - 基于实际文件内容精确匹配"""
from pathlib import Path

BASE = Path(__file__).parent

def apply_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        print(f"[跳过] {label}: 匹配 {count} 处（需1处）")
        return text
    print(f"[OK] {label}")
    return text.replace(old, new, 1)

# === 1. tile_props.py: PLACEABLE_PROPS 末尾加楼梯 ===
fp = BASE / "tile_props.py"
src = fp.read_text("utf-8")
old = '''    "岩石傀儡残骸": {
        "name": "岩石傀儡残骸", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 4.0,
        "drop": "石头", "char": "\\u2588",
    },
}'''
new = '''    "岩石傀儡残骸": {
        "name": "岩石傀儡残骸", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 4.0,
        "drop": "石头", "char": "\\u2588",
    },
    "楼梯下": {
        "name": "向下的楼梯", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 999.0, "char": ">",
    },
    "楼梯上": {
        "name": "向上的楼梯", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 999.0, "char": "<",
    },
}'''
src = apply_one(src, old, new, "1/5 tile_props 楼梯定义")
fp.write_text(src, "utf-8")

# === 2. world_gen.py: 加楼梯常量 + place_stairs + generate_world 改签名 ===
fp = BASE / "world_gen.py"
src = fp.read_text("utf-8")

old = "TILE_OBSIDIAN = 16"
new = "TILE_OBSIDIAN = 16\nTILE_STAIRS_DOWN = 17\nTILE_STAIRS_UP = 18"
src = apply_one(src, old, new, "2/5 world_gen 楼梯常量")

old = '''TILE_GRANITE: "花岗岩", TILE_OBSIDIAN: "黑曜石",
}'''
new = '''TILE_GRANITE: "花岗岩", TILE_OBSIDIAN: "黑曜石",
    TILE_STAIRS_DOWN: "楼梯下", TILE_STAIRS_UP: "楼梯上",
}'''
src = apply_one(src, old, new, "2.5/5 world_gen TILE_DROPS 楼梯")

old = '''def generate_world(seed: int = 12345):
    """兼容旧接口——返回 World 对象。"""
    return World(seed=seed)'''
new = '''def generate_world(seed: int = 12345, layer: int = 0):
    """兼容旧接口——返回 World 对象。layer 参数预留分层 支持。"""
    return World(seed=seed + layer * 10000)'''
src = apply_one(src, old, new, "3/5 world_gen generate_world 加 layer")

old = '''def find_spawn(world: World, start_x: int = 0) -> tuple:
    """寻找合适的出生点。"""
    for offset in range(200):'''
new = '''def place_stairs(world: World, layer: int = 0):
    """在 spawn 周围放置上下楼梯。"""
    import random
    rng = random.Random(world.seed + layer * 777)
    sx, sy = find_spawn(world)
    for _ in range(4):
        dx = rng.randint(-20, 20)
        dy = rng.randint(-15, 15)
        x, y = sx + dx, sy + dy
        tile = world.get_tile(x, y)["tile"]
        if tile == TILE_AIR:
            continue
        for ndx, ndy in [(1,0),(-1,0),(0,1),(0,-1)]:
            if world.get_tile(x+ndx, y+ndy)["tile"] == TILE_AIR:
                world.set_tile(x, y, TILE_STAIRS_DOWN)
                break

def find_spawn(world: World, start_x: int = 0) -> tuple:
    """寻找合适的出生点。"""
    for offset in range(200):'''
src = apply_one(src, old, new, "4/5 world_gen place_stairs 函数")

old = '''    return World(seed=seed + layer * 10000)'''
new = '''    w = World(seed=seed + layer * 10000)
    place_stairs(w, layer)
    return w'''
src = apply_one(src, old, new, "5/5 world_gen 调用 place_stairs")
fp.write_text(src, "utf-8")

# === 3. main.py: 加楼梯字符 + 导入 WORLD_LAYERS + player_z ===
fp = BASE / "main.py"
src = fp.read_text("utf-8")

old = '''    "岩石傀儡残骸": "\\u2588",
}'''
new = '''    "岩石傀儡残骸": "\\u2588",
    "楼梯下": ">",
    "楼梯上": "<",
}'''
src = apply_one(src, old, new, "6/8 main TILE_CHARS 楼梯")

old = '''from config import (
    VIEW_WIDTH, VIEW_HEIGHT, WORLD_SEED,
    PLAYER_INITIAL_HP,
    PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX, PLAYER_BASE_HIT_CHANCE,
    SPAWN_INITIAL_COUNTDOWN, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    SPAWN_MIN_DISTANCE,
    DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START,
)'''
new = '''from config import (
    VIEW_WIDTH, VIEW_HEIGHT, WORLD_SEED,
    PLAYER_INITIAL_HP,
    PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX, PLAYER_BASE_HIT_CHANCE,
    SPAWN_INITIAL_COUNTDOWN, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    SPAWN_MIN_DISTANCE,
    DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START,
    WORLD_LAYERS, LAYER_DEPTH_OFFSET,
)'''
src = apply_one(src, old, new, "7/8 main 导入 WORLD_LAYERS")

old = '''        self.player_x = self.player_y = 0
        self.cursor_x = self.cursor_y = 0'''
new = '''        self.player_x = self.player_y = 0
        self.player_z = 0
        self.cursor_x = self.cursor_y = 0'''
src = apply_one(src, old, new, "8/8 main __init__ player_z")
fp.write_text(src, "utf-8")

print("\n=== M9 第1步 v2 完成 ===")
print("已修改: tile_props.py, world_gen.py, main.py, config.py")

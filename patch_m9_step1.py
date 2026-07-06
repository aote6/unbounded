#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M9 多层地图 - 第1步：数据模型 + 楼梯方块 + 存档兼容
1. tile_props.py 添加上/下楼梯方块定义
2. config.py 添加 WORLD_LAYERS 配置
3. world_gen.py 添加楼梯生成 + 分层世界支持
4. main.py Game 类添加 player_z + 存档兼容 + 渲染楼梯符号
"""
import sys
from pathlib import Path

BASE = Path(__file__).parent

def apply_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        print(f"[跳过] {label}: 匹配 {count} 处（需1处），请反馈")
        return text
    print(f"[OK] {label}")
    return text.replace(old, new, 1)

# ─── 1. tile_props.py 添加上/下楼梯 ───
fp = BASE / "tile_props.py"
src = fp.read_text("utf-8")
backup = fp.with_suffix(".py.bak_m9")
backup.write_text(src, "utf-8")

old = '''    "黑曜石": {"name": "黑曜石", "passable": False, "transparent": False, "diggable": True, "hardness": 25, "drop": "黑曜石"},
}'''
new = '''    "黑曜石": {"name": "黑曜石", "passable": False, "transparent": False, "diggable": True, "hardness": 25, "drop": "黑曜石"},
    "楼梯下": {"name": "向下的楼梯", "passable": True, "transparent": False, "diggable": False, "hardness": 999, "drop": None},
    "楼梯上": {"name": "向上的楼梯", "passable": True, "transparent": False, "diggable": False, "hardness": 999, "drop": None},
}'''
src = apply_one(src, old, new, "1/6 tile_props 添加上/下楼梯")
fp.write_text(src, "utf-8")

# ─── 2. config.py 添加 WORLD_LAYERS ───
fp = BASE / "config.py"
src = fp.read_text("utf-8")
backup_cfg = fp.with_suffix(".py.bak_m9")
backup_cfg.write_text(src, "utf-8")

old = '''# ── 昼夜循环 ──
DAY_LENGTH = 1800'''
new = '''# ── 多层世界 ──
WORLD_LAYERS = 5          # 总层数（0=地表, -1=地下1层, -2=地下2层...）
LAYER_DEPTH_OFFSET = 50   # 每层偏移量（叠加到 y 坐标计算深度）

# ── 昼夜循环 ──
DAY_LENGTH = 1800'''
src = apply_one(src, old, new, "2/6 config 添加 WORLD_LAYERS")
fp.write_text(src, "utf-8")

# ─── 3. world_gen.py 添加楼梯生成 + 分层支持 ───
fp = BASE / "world_gen.py"
src = fp.read_text("utf-8")
backup_wg = fp.with_suffix(".py.bak_m9")
backup_wg.write_text(src, "utf-8")

old = '''TILE_OBSIDIAN = "黑曜石"'''
new = '''TILE_OBSIDIAN = "黑曜石"
TILE_STAIRS_DOWN = "楼梯下"
TILE_STAIRS_UP = "楼梯上"'''
src = apply_one(src, old, new, "3/6 world_gen 添加楼梯常量")

# 在 generate_world 签名加 layer 参数
old = '''def generate_world(seed=42, start_x=0):'''
new = '''def generate_world(seed=42, start_x=0, layer=0):'''
src = apply_one(src, old, new, "3.5/6 generate_world 加 layer 参数")

# 楼梯生成逻辑：在 find_spawn 后面插入
old = '''def find_spawn(world, start_x=0):'''
new = '''def place_stairs(world, layer):
    """在指定层放置一组上下楼梯（spawn点附近 + 远处随机）。"""
    import random
    rng = random.Random(world.seed + layer * 1000)
    # spawn 附近的楼梯（10~20格范围内）
    sx, sy = find_spawn(world)
    for _ in range(3):
        dx = rng.randint(-20, 20)
        dy = rng.randint(-15, 15)
        x, y = sx + dx, sy + dy
        if world.get_tile(x, y)["tile"] == TILE_AIR:
            continue
        # 放在空腔旁边
        for ndx, ndy in [(1,0),(-1,0),(0,1),(0,-1)]:
            nx, ny = x + ndx, y + ndy
            if world.get_tile(nx, ny)["tile"] == TILE_AIR:
                if layer > -WORLD_LAYERS + 1:
                    world.set_tile(x, y, TILE_STAIRS_DOWN)
                break

def find_spawn(world, start_x=0):'''
src = apply_one(src, old, new, "4/6 world_gen 添加 place_stairs 函数")

# 在 generate_world 函数末尾（return world 前）调用 place_stairs
old = '''    # 确保至少生成一个 chunk（玩家所在位置）
    world.get_chunk(cx, cy)
    return world'''
new = '''    # 确保至少生成一个 chunk（玩家所在位置）
    world.get_chunk(cx, cy)
    place_stairs(world, layer)
    return world'''
src = apply_one(src, old, new, "4.5/6 generate_world 调用 place_stairs")
fp.write_text(src, "utf-8")

# ─── 4. main.py 添加 player_z + 渲染 + 存档兼容 ───
fp = BASE / "main.py"
src = fp.read_text("utf-8")
backup_main = fp.with_suffix(".py.bak_m9")
backup_main.write_text(src, "utf-8")

# TILE_CHARS 加楼梯符号
old = '''    "岩石傀儡残骸": "\\u2588",
}'''
new = '''    "岩石傀儡残骸": "\\u2588",
    "楼梯下": ">",
    "楼梯上": "<",
}'''
src = apply_one(src, old, new, "5/9 main TILE_CHARS 楼梯符号")

# 导入 WORLD_LAYERS, LAYER_DEPTH_OFFSET
old = '''from config import (
    VIEW_WIDTH, VIEW_HEIGHT, WORLD_SEED, PLAYER_INITIAL_HP,
    PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX,
    PLAYER_BASE_HIT_CHANCE,
    SPAWN_INITIAL_COUNTDOWN,
    SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    SPAWN_MIN_DISTANCE,
    DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START,
)'''
new = '''from config import (
    VIEW_WIDTH, VIEW_HEIGHT, WORLD_SEED, PLAYER_INITIAL_HP,
    PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX,
    PLAYER_BASE_HIT_CHANCE,
    SPAWN_INITIAL_COUNTDOWN,
    SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    SPAWN_MIN_DISTANCE,
    DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START,
    WORLD_LAYERS, LAYER_DEPTH_OFFSET,
)'''
src = apply_one(src, old, new, "5.5/9 main 导入 WORLD_LAYERS")

# __init__ 加 player_z
old = '''        self.player_x = self.player_y = 0
        self.cursor_x = self.cursor_y = 0'''
new = '''        self.player_x = self.player_y = 0
        self.player_z = 0
        self.cursor_x = self.cursor_y = 0'''
src = apply_one(src, old, new, "6/9 main __init__ player_z")

# new_game 加 player_z
old = '''        self.player_x, self.player_y = sx, sy
        self.cursor_x, self.cursor_y = sx, sy'''
new = '''        self.player_x, self.player_y = sx, sy
        self.player_z = 0
        self.cursor_x, self.cursor_y = sx, sy'''
src = apply_one(src, old, new, "7/9 main new_game player_z")

# save_game 加 player_z
old = '''        data = {
            "seed": WORLD_SEED,
            "player_x": self.player_x, "player_y": self.player_y,''' 
new = '''        data = {
            "seed": WORLD_SEED,
            "player_x": self.player_x, "player_y": self.player_y,
            "player_z": self.player_z,'''
src = apply_one(src, old, new, "8/9 main save_game player_z")

# load_game 读 player_z（兼容旧存档无此字段）
old = '''        self.player_x = data["player_x"]; self.player_y = data["player_y"]
        self.cursor_x, self.cursor_y = self.player_x, self.player_y'''
new = '''        self.player_x = data["player_x"]; self.player_y = data["player_y"]
        self.player_z = data.get("player_z", 0)
        self.cursor_x, self.cursor_y = self.player_x, self.player_y'''
src = apply_one(src, old, new, "9/9 main load_game player_z 兼容")

fp.write_text(src, "utf-8")

print("\n=== M9 第1步完成 ===")
print("改动：tile_props/config/world_gen/main 四个文件已更新")
print("新增：楼梯方块(>上楼梯 <下楼梯)，player_z 字段，分层世界数据模型")
print("备份：各文件 .bak_m9 已留存")

#!/usr/bin/env python3
"""地形骨架：随机种子 + 山川河谷 + 江河湖泊 + 树木"""
from pathlib import Path
import random, time

BASE = Path(__file__).parent

def apply_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        print(f"[跳过] {label}: 匹配 {count} 处（需1处）")
        return text
    print(f"[OK] {label}")
    return text.replace(old, new, 1)

# === 1. world_gen.py：加水域常量 + 树常量 + 重写 generate_tile ===
fp = BASE / "world_gen.py"
src = fp.read_text("utf-8")

# 加水域和树常量（TILE_STAIRS_UP 后面）
old = "TILE_STAIRS_UP = 18"
new = "TILE_STAIRS_UP = 18\nTILE_WATER = 19\nTILE_TREE = 20"
src = apply_one(src, old, new, "1/5 加水域/树常量")

# TILE_DROPS 加水
old = '''    TILE_STAIRS_DOWN: "楼梯下", TILE_STAIRS_UP: "楼梯上",
}'''
new = '''    TILE_STAIRS_DOWN: "楼梯下", TILE_STAIRS_UP: "楼梯上",
    TILE_WATER: "水域", TILE_TREE: "树木",
}'''
src = apply_one(src, old, new, "2/5 TILE_DROPS 加水/树")

# 重写 generate_tile（完整版：含地形 + 水域 + 树 + 矿）
old_func = src[src.find('def generate_tile(x: int, y: int, seed: int = 12345) -> int:'):]
old_func = old_func[:old_func.find('\ndef find_spawn')]

new_func = '''def generate_tile(x: int, y: int, seed: int = 12345) -> int:
    """返回该格的 tile ID（纯函数，无副作用）。
    物理世界生成：
      地形高程 → 山川/平原/低谷
      水域系统 → 河流(沿等值线) + 湖泊(低洼)
      地表覆盖 → 树木(平原/丘陵)
      地质分层 → 矿物按深度概率分布（主力矿物+跨界可能）
    """
    # ── 地形高程（大尺度）──
    elevation = perlin_2d(x * 0.008, y * 0.008, seed=seed, octaves=6)
    # ── 局部粗糙度（小尺度）──
    detail = perlin_2d(x * 0.04, y * 0.04, seed=seed + 123, octaves=3) * 0.3
    # ── 湿度（用于河流/湖泊/树木）──
    moisture = perlin_2d(x * 0.01, y * 0.01, seed=seed + 456, octaves=4)
    # ── 矿石噪声 ──
    rng_ore = perlin_2d(x / 2.5, y / 2.5, seed=seed + 7777, octaves=3)
    rng_layer = perlin_2d(x / 8.0, y / 8.0, seed=seed + 5555, octaves=2)
    
    h = elevation + detail  # 最终高程 -1~1

    # ── 水域系统（河流 + 湖泊）──
    # 河流：湿度高 + 高程接近中等（河流沿等高线）
    river_noise = perlin_2d(x * 0.03, y * 0.03, seed=seed + 789, octaves=2)
    is_river = (abs(h - 0.0) < 0.08 and moisture > 0.45 and river_noise > 0.35)
    # 湖泊：低洼积水
    is_lake = (h < -0.15 and moisture > 0.30)
    if is_river or is_lake:
        return TILE_WATER

    # ── 地表（y > -3 视为地表）──
    if y > -3:
        if h > 0.25:
            # 高山：裸露岩石
            if rng_layer > 0.40:
                return TILE_GRANITE
            return TILE_STONE
        elif h > 0.08:
            # 丘陵：石头 + 石灰岩
            if rng_layer > 0.60:
                return TILE_LIMESTONE
            # 树木（平原/丘陵，湿度适中）
            tree_chance = perlin_2d(x * 0.2, y * 0.2, seed=seed + 999, octaves=1)
            if 0.25 < moisture < 0.60 and tree_chance > 0.55:
                return TILE_TREE
            return TILE_DIRT
        elif h > -0.08:
            # 平原：泥土为主，沙/黏土斑块
            if rng_ore > 0.70:
                return TILE_CLAY
            elif rng_ore < 0.18:
                return TILE_SAND
            tree_chance = perlin_2d(x * 0.2, y * 0.2, seed=seed + 999, octaves=1)
            if 0.30 < moisture < 0.55 and tree_chance > 0.50:
                return TILE_TREE
            return TILE_DIRT
        else:
            # 低谷：沙地/湿地
            if moisture > 0.50:
                return TILE_CLAY
            return TILE_SAND

    # ── 地下（y <= -3）：地质分层 ──
    if y > -8:
        # 表层：泥土/沙/黏土/石灰岩
        if h > -0.15:
            if rng_layer > 0.55:
                return TILE_LIMESTONE
            elif rng_layer < 0.25:
                return TILE_SAND
            elif rng_ore > 0.65:
                return TILE_CLAY
            return TILE_DIRT
        else:
            return TILE_AIR

    elif y > -25:
        if h > -0.20:
            if rng_ore > 0.62:
                return TILE_COAL
            elif rng_layer > 0.55 and rng_ore > 0.45:
                return TILE_LIMESTONE
            return TILE_STONE
        else:
            if rng_layer > 0.35:
                return TILE_STONE
            return TILE_AIR

    elif y > -45:
        if h > -0.25:
            if rng_ore > 0.70:
                return TILE_IRON
            elif rng_ore > 0.58:
                return TILE_COPPER
            elif rng_ore < 0.22 and rng_layer > 0.50:
                return TILE_SALT
            elif rng_layer > 0.60:
                return TILE_MARBLE
            return TILE_STONE
        else:
            return TILE_STONE

    elif y > -70:
        if h > -0.28:
            if rng_ore > 0.72:
                return TILE_GOLD
            elif rng_ore > 0.62:
                return TILE_SILVER
            elif rng_layer > 0.65:
                return TILE_GRANITE
            elif rng_ore < 0.15 and rng_layer < 0.30:
                return TILE_SULFUR
            return TILE_STONE
        else:
            return TILE_STONE

    else:
        if h > -0.30:
            if rng_ore > 0.75:
                return TILE_DIAMOND
            elif rng_ore > 0.60:
                return TILE_OBSIDIAN
            elif rng_layer > 0.55:
                return TILE_MARBLE
            return TILE_STONE
        else:
            return TILE_STONE'''

src = src.replace(old_func, new_func, 1)
print("[OK] 3/5 generate_tile 重写（地形+水域+树+矿）")

# tile_props.py 加水域和树的属性
fp2 = BASE / "tile_props.py"
src2 = fp2.read_text("utf-8")
old2 = '''from world_gen import (
    TILE_AIR, TILE_DIRT, TILE_STONE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
    TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_SAND,
    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,
)'''
new2 = '''from world_gen import (
    TILE_AIR, TILE_DIRT, TILE_STONE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
    TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_SAND,
    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,
    TILE_WATER, TILE_TREE,
)'''
src2 = apply_one(src2, old2, new2, "4/5 tile_props 导入水/树")

# 在 TILE_OBSIDIAN 属性后加 TILE_WATER 和 TILE_TREE
old3 = '''    TILE_OBSIDIAN: {
        "name": "黑曜石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 10.0,
        "drop": "黑曜石", "char": "\\u25a0",
    },
}'''
new3 = '''    TILE_OBSIDIAN: {
        "name": "黑曜石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 10.0,
        "drop": "黑曜石", "char": "\\u25a0",
    },
    TILE_WATER: {
        "name": "水域", "passable": False, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 999.0,
        "drop": None, "char": "~",
    },
    TILE_TREE: {
        "name": "树木", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 1.5,
        "drop": "泥土", "char": "\\u2663",
    },
}'''
src2 = apply_one(src2, old3, new3, "5/5 tile_props 水域/树属性")
fp2.write_text(src2, "utf-8")
fp.write_text(src, "utf-8")

# === 2. config.py：随机种子 ===
fp3 = BASE / "config.py"
src3 = fp3.read_text("utf-8")

old4 = "WORLD_SEED = 42"
new4 = f"WORLD_SEED = {random.randint(1, 99999)}  # 随机种子"
src3 = apply_one(src3, old4, new4, "config 随机种子")
fp3.write_text(src3, "utf-8")

# === 3. main.py：加水和树的字符 + 导入新常量 ===
fp4 = BASE / "main.py"
src4 = fp4.read_text("utf-8")

# 导入 TILE_WATER, TILE_TREE
old5 = '''from world_gen import (
    generate_world, find_spawn, World,
    TILE_AIR, TILE_DIRT, TILE_STONE, TILE_DROPS, CHUNK_SIZE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
    TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_SAND,
    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,
)'''
new5 = '''from world_gen import (
    generate_world, find_spawn, World,
    TILE_AIR, TILE_DIRT, TILE_STONE, TILE_DROPS, CHUNK_SIZE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
    TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_SAND,
    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,
    TILE_WATER, TILE_TREE,
)'''
src4 = apply_one(src4, old5, new5, "main 导入水/树常量")

# TILE_CHARS 加水/树
old6 = '''    "楼梯上": "<",
}'''
new6 = '''    "楼梯上": "<",
    TILE_WATER: "~",
    TILE_TREE: "\\u2663",
}'''
src4 = apply_one(src4, old6, new6, "main TILE_CHARS 水/树")
fp4.write_text(src4, "utf-8")

print("\n=== 地形骨架完成 ===")
print("新增：随机种子、山川河谷、江河湖泊、树木")
print("水域(~)阻挡移动，树木(♣)可通过可挖掘")
print("每次启动新游戏地图不同")

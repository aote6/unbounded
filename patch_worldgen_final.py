#!/usr/bin/env python3
"""恢复 world_gen.py 后一次性加上所有累积改动"""
from pathlib import Path

BASE = Path(__file__).parent
fp = BASE / "world_gen.py"
src = fp.read_text("utf-8")

def apply(text, old, new, label):
    c = text.count(old)
    if c != 1:
        print(f"[跳过] {label}: {c}处")
        return text
    print(f"[OK] {label}")
    return text.replace(old, new, 1)

# 1. 楼梯常量
src = apply(src, "TILE_OBSIDIAN = 16", "TILE_OBSIDIAN = 16\nTILE_STAIRS_DOWN = 17\nTILE_STAIRS_UP = 18", "楼梯常量")
# 2. 水域+树常量
src = apply(src, "TILE_STAIRS_UP = 18", "TILE_STAIRS_UP = 18\nTILE_WATER = 19\nTILE_TREE = 20", "水域/树常量")
# 3. TILE_DROPS
src = apply(src,
    'TILE_GRANITE: "花岗岩", TILE_OBSIDIAN: "黑曜石",\n}',
    'TILE_GRANITE: "花岗岩", TILE_OBSIDIAN: "黑曜石",\n    TILE_STAIRS_DOWN: "楼梯下", TILE_STAIRS_UP: "楼梯上",\n    TILE_WATER: "水域", TILE_TREE: "树木",\n}',
    "TILE_DROPS 补全")
# 4. generate_world 加 layer + 楼梯 + spawn
src = apply(src,
    '''def generate_world(seed: int = 12345):
    """兼容旧接口——返回 World 对象。"""
    return World(seed=seed)''',
    '''def generate_world(seed: int = 12345, layer: int = 0):
    """返回 World 对象。layer 用于分层世界。"""
    w = World(seed=seed + layer * 10000)
    sx, sy = find_spawn(w)
    place_stairs(w, layer, sx, sy)
    return w''',
    "generate_world 加 layer")
# 5. place_stairs
src = apply(src,
    '''def find_spawn(world: World, start_x: int = 0) -> tuple:
    """寻找合适的出生点。"""
    for offset in range(200):''',
    '''def place_stairs(world: World, layer: int = 0, sx: int = None, sy: int = None):
    """在 spawn 周围放置上下楼梯。"""
    import random
    rng = random.Random(world.seed + layer * 777)
    if sx is None or sy is None:
        sx, sy = find_spawn(world)
    for _ in range(3):
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
    for offset in range(40):''',
    "place_stairs + find_spawn 缩减")
# 6. find_spawn 内部 y 范围
src = apply(src,
    "            for y in range(-20, 80):",
    "            for y in range(-10, 40):",
    "find_spawn y 范围缩减")
# 7. __all__ 导出
src = apply(src,
    "'TILE_GRANITE', 'TILE_OBSIDIAN',",
    "'TILE_GRANITE', 'TILE_OBSIDIAN', 'TILE_STAIRS_DOWN', 'TILE_STAIRS_UP', 'TILE_WATER', 'TILE_TREE',",
    "__all__ 导出补全")

# 8. 替换 generate_tile 函数——完整地形版
old_func = src[src.find('def generate_tile(x: int, y: int, seed: int = 12345) -> int:'):]
old_func = old_func[:old_func.find('\n\ndef find_spawn')]

new_func = '''def generate_tile(x: int, y: int, seed: int = 12345) -> int:
    """返回该格的 tile ID（纯函数，无副作用）。
    物理世界生成：地形高程→山川/平原/低谷，水域系统→河流/湖泊，
    地表覆盖→树木，地质分层→矿物按深度概率分布。
    """
    elevation = perlin_2d(x * 0.008, y * 0.008, seed=seed, octaves=6)
    detail = perlin_2d(x * 0.04, y * 0.04, seed=seed + 123, octaves=3) * 0.3
    moisture = perlin_2d(x * 0.01, y * 0.01, seed=seed + 456, octaves=4)
    rng_ore = perlin_2d(x / 2.5, y / 2.5, seed=seed + 7777, octaves=3)
    rng_layer = perlin_2d(x / 8.0, y / 8.0, seed=seed + 5555, octaves=2)
    h = elevation + detail
    # 水域
    river_noise = perlin_2d(x * 0.03, y * 0.03, seed=seed + 789, octaves=2)
    is_river = (abs(h - 0.0) < 0.08 and moisture > 0.45 and river_noise > 0.35)
    is_lake = (h < -0.15 and moisture > 0.30)
    if is_river or is_lake:
        return TILE_WATER
    # 地表
    if y > -3:
        if h > 0.25:
            return TILE_GRANITE if rng_layer > 0.40 else TILE_STONE
        elif h > 0.08:
            if rng_layer > 0.60:
                return TILE_LIMESTONE
            tree = perlin_2d(x * 0.2, y * 0.2, seed=seed + 999, octaves=1)
            if 0.25 < moisture < 0.60 and tree > 0.55:
                return TILE_TREE
            return TILE_DIRT
        elif h > -0.08:
            if rng_ore > 0.70:
                return TILE_CLAY
            elif rng_ore < 0.18:
                return TILE_SAND
            tree = perlin_2d(x * 0.2, y * 0.2, seed=seed + 999, octaves=1)
            if 0.30 < moisture < 0.55 and tree > 0.50:
                return TILE_TREE
            return TILE_DIRT
        else:
            return TILE_CLAY if moisture > 0.50 else TILE_SAND
    # 地下
    if y > -8:
        if h > -0.15:
            if rng_layer > 0.55:
                return TILE_LIMESTONE
            elif rng_layer < 0.25:
                return TILE_SAND
            elif rng_ore > 0.65:
                return TILE_CLAY
            return TILE_DIRT
        return TILE_AIR
    elif y > -25:
        if h > -0.20:
            if rng_ore > 0.62:
                return TILE_COAL
            elif rng_layer > 0.55 and rng_ore > 0.45:
                return TILE_LIMESTONE
            return TILE_STONE
        return TILE_STONE if rng_layer > 0.35 else TILE_AIR
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
        return TILE_STONE'''

src = src.replace(old_func, new_func, 1)
print("[OK] generate_tile 替换")

fp.write_text(src, "utf-8")
print("\nworld_gen.py 完整修复完毕，可以启动了。")

#!/usr/bin/env python3
"""M9 性能修复：缩减 find_spawn 扫描 + place_stairs 复用坐标"""
from pathlib import Path

BASE = Path(__file__).parent

def apply_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        print(f"[跳过] {label}: 匹配 {count} 处（需1处）")
        return text
    print(f"[OK] {label}")
    return text.replace(old, new, 1)

fp = BASE / "world_gen.py"
src = fp.read_text("utf-8")

# 1. find_spawn 扫描范围从 200 减到 40（足够用）
old = '''    for offset in range(200):
        for x in (start_x + offset, start_x - offset):
            for y in range(-20, 80):'''
new = '''    for offset in range(40):
        for x in (start_x + offset, start_x - offset):
            for y in range(-10, 40):'''
src = apply_one(src, old, new, "1/3 find_spawn 缩减扫描")

# 2. place_stairs 复用 find_spawn 的返回值，传入 sx,sy 避免重复扫描
old = '''def place_stairs(world: World, layer: int = 0):
    """在 spawn 周围放置上下楼梯。"""
    import random
    rng = random.Random(world.seed + layer * 777)
    sx, sy = find_spawn(world)
    for _ in range(4):'''
new = '''def place_stairs(world: World, layer: int = 0, sx: int = None, sy: int = None):
    """在 spawn 周围放置上下楼梯。"""
    import random
    rng = random.Random(world.seed + layer * 777)
    if sx is None or sy is None:
        sx, sy = find_spawn(world)
    for _ in range(3):'''
src = apply_one(src, old, new, "2/3 place_stairs 复用坐标")

# 3. generate_world 先找 spawn 再传进去
old = '''    w = World(seed=seed + layer * 10000)
    place_stairs(w, layer)
    return w'''
new = '''    w = World(seed=seed + layer * 10000)
    sx, sy = find_spawn(w)
    place_stairs(w, layer, sx, sy)
    return w'''
src = apply_one(src, old, new, "3/3 generate_world 先找 spawn 再放楼梯")

fp.write_text(src, "utf-8")
print("\n=== M9 性能修复完成 ===")
print("缩减 find_spawn 扫描范围 200→40，place_stairs 复用坐标")

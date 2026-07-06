#!/usr/bin/env python3
"""地质分层重写：真实地层 + 矿物共生 + 深层不空"""
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

# 重写 generate_tile 函数
old = '''def generate_tile(x: int, y: int, seed: int = 12345) -> int:
    """返回该格的 tile ID（纯函数，无副作用）。"""
    elevation = perlin_2d(x * 0.125, y * 0.125, seed=seed, octaves=6)
    depth_factor = y * 0.03125
    adjusted = elevation - depth_factor * 0.3

    if adjusted > 0.55:
        tile = TILE_STONE
        ore_seed = seed + 7777
        ore_val = perlin_2d(x / 3.0, y / 3.0, seed=ore_seed, octaves=3)
        depth_bonus = max(0, -y / 80.0)
        if ore_val + depth_bonus > 0.72:
            tile = TILE_DIAMOND
        elif ore_val + depth_bonus > 0.65:
            tile = TILE_GOLD
        elif ore_val + depth_bonus > 0.58:
            tile = TILE_SILVER
        elif ore_val > 0.52:
            tile = TILE_IRON
        elif ore_val > 0.45:
            tile = TILE_COPPER
        elif ore_val > 0.38:
            tile = TILE_COAL
        elif ore_val < 0.20:
            spec_val = perlin_2d(x / 7.0, y / 7.0, seed=seed + 8888, octaves=2)
            if spec_val < 0.15:
                tile = TILE_SULFUR
            elif spec_val < 0.22:
                tile = TILE_SALT
        return tile
    elif adjusted > 0.30:
        tile = TILE_DIRT
        surface_val = perlin_2d(x / 5.0, y / 5.0, seed=seed + 9999, octaves=2)
        if surface_val > 0.60:
            tile = TILE_CLAY
        elif surface_val < 0.25:
            tile = TILE_SAND
        return tile
    else:
        return TILE_AIR'''

new = '''def generate_tile(x: int, y: int, seed: int = 12345) -> int:
    """返回该格的 tile ID（纯函数，无副作用）。
    地质分层（y轴向下为正，地表y≈0）：
      表层   0 ~ -8   泥土/沙/黏土/石灰岩（松散沉积物）
      浅层  -8 ~ -25  石头 + 煤矿（与石灰岩共生）
      中层 -25 ~ -45  石头 + 铜/铁/盐（热液矿脉）
      深层 -45 ~ -70  石头 + 银/金/花岗岩（岩浆侵入）
      基底 -70 以下   黑曜石/钻石/硫磺/大理石（变质基底）
    每层有自己独立的噪声阈值，不同矿物不会混杂出现。
    """
    elevation = perlin_2d(x * 0.1, y * 0.1, seed=seed, octaves=6)
    rng_ore = perlin_2d(x / 2.5, y / 2.5, seed=seed + 7777, octaves=3)
    rng_layer = perlin_2d(x / 8.0, y / 8.0, seed=seed + 5555, octaves=2)

    # 深度分层（y 越大越深）
    if y > -8:
        # ── 表层 0~-8：沉积物 ──
        if elevation > 0.32:
            if rng_layer > 0.55:
                return TILE_LIMESTONE   # 石灰岩（高地）
            elif rng_layer < 0.25:
                return TILE_SAND        # 沙子（低洼）
            elif rng_ore > 0.65:
                return TILE_CLAY        # 黏土透镜体
            return TILE_DIRT
        else:
            return TILE_AIR  # 地表空腔

    elif y > -25:
        # ── 浅层 -8~-25：沉积岩 + 煤矿 ──
        if elevation > 0.25:
            # 石头基质
            if rng_ore > 0.62:
                return TILE_COAL        # 煤矿（与石灰岩共生）
            elif rng_layer > 0.55 and rng_ore > 0.45:
                return TILE_LIMESTONE   # 石灰岩夹层
            return TILE_STONE
        else:
            # 局部空腔（溶洞）
            if rng_layer > 0.35:
                return TILE_STONE
            return TILE_AIR

    elif y > -45:
        # ── 中层 -25~-45：热液矿脉 ──
        if elevation > 0.20:
            if rng_ore > 0.70:
                return TILE_IRON        # 铁（常见）
            elif rng_ore > 0.58:
                return TILE_COPPER      # 铜（次常见）
            elif rng_ore < 0.22 and rng_layer > 0.50:
                return TILE_SALT        # 盐（蒸发岩夹层）
            elif rng_layer > 0.60:
                return TILE_MARBLE      # 大理石（变质）
            return TILE_STONE
        else:
            return TILE_STONE  # 中层不空，全是石头

    elif y > -70:
        # ── 深层 -45~-70：岩浆侵入 ──
        if elevation > 0.18:
            if rng_ore > 0.72:
                return TILE_GOLD        # 金（稀有）
            elif rng_ore > 0.62:
                return TILE_SILVER      # 银（较稀有）
            elif rng_layer > 0.65:
                return TILE_GRANITE     # 花岗岩侵入体
            elif rng_ore < 0.15 and rng_layer < 0.30:
                return TILE_SULFUR      # 硫磺（火山成因）
            return TILE_STONE
        else:
            return TILE_STONE  # 深层全是石头

    else:
        # ── 基底 -70 以下：变质基底 ──
        if elevation > 0.15:
            if rng_ore > 0.75:
                return TILE_DIAMOND     # 钻石（极稀有）
            elif rng_ore > 0.60:
                return TILE_OBSIDIAN    # 黑曜石（火山玻璃）
            elif rng_layer > 0.55:
                return TILE_MARBLE      # 大理石（区域变质）
            return TILE_STONE
        else:
            return TILE_STONE  # 基底不空'''

src = apply_one(src, old, new, "地质分层重写")
fp.write_text(src, "utf-8")

print("\n=== 地质分层重写完成 ===")
print("表层 0~-8:   泥土/沙/黏土/石灰岩")
print("浅层 -8~-25: 石头 + 煤矿 + 石灰岩夹层")
print("中层 -25~-45: 石头 + 铜/铁/盐/大理石（不空）")
print("深层 -45~-70: 石头 + 银/金/花岗岩/硫磺（不空）")
print("基底 -70以下: 石头 + 钻石/黑曜石/大理石（不空）")

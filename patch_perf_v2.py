#!/usr/bin/env python3
"""性能优化v2：generate_tile 从6次perlin砍到2次"""
from pathlib import Path

BASE = Path(__file__).parent
fp = BASE / "world_gen.py"
src = fp.read_text("utf-8")

old = src[src.find('def generate_tile(x: int, y: int, seed: int = 12345) -> int:'):src.find('\n\nclass Chunk')]
old = old[:old.rfind('return TILE_STONE') + len('return TILE_STONE')]

new = '''def generate_tile(x: int, y: int, seed: int = 12345) -> int:
    """返回该格的 tile ID。只用2次perlin：高程(octaves=6含细节)+矿脉(octaves=3)。"""
    # 高程（octaves=6 已包含大尺度地形+细节，用 seed 区分）
    h = perlin_2d(x * 0.01, y * 0.01, seed=seed, octaves=6)
    # 矿脉/湿度（合并到一个 perlin，节省调用）
    ore = perlin_2d(x * 0.05, y * 0.05, seed=seed + 7777, octaves=3)
    
    # 水域：低高程 + 矿脉值适中 = 河流/湖泊
    if (h < -0.10 and ore > 0.30) or (h < -0.20):
        return TILE_WATER
    
    # 地表
    if y > -3:
        if h > 0.30:
            return TILE_GRANITE if ore > 0.50 else TILE_STONE
        elif h > 0.12:
            if ore > 0.70: return TILE_LIMESTONE
            if 0.30 < ore < 0.65 and h > 0.18: return TILE_TREE
            return TILE_DIRT
        elif h > -0.05:
            if ore > 0.75: return TILE_CLAY
            if ore < 0.20: return TILE_SAND
            if 0.35 < ore < 0.55: return TILE_TREE
            return TILE_DIRT
        else:
            return TILE_CLAY if ore > 0.50 else TILE_SAND
    
    # 地下分层
    if y > -8:
        if h > -0.10:
            if ore > 0.65: return TILE_LIMESTONE
            if ore < 0.20: return TILE_SAND
            if ore > 0.55: return TILE_CLAY
            return TILE_DIRT
        return TILE_AIR
    elif y > -25:
        if h > -0.15:
            if ore > 0.65: return TILE_COAL
            if ore > 0.55: return TILE_LIMESTONE
            return TILE_STONE
        return TILE_STONE if ore > 0.35 else TILE_AIR
    elif y > -45:
        if h > -0.20:
            if ore > 0.72: return TILE_IRON
            if ore > 0.58: return TILE_COPPER
            if ore < 0.20: return TILE_SALT
            if ore > 0.50: return TILE_MARBLE
            return TILE_STONE
        return TILE_STONE
    elif y > -70:
        if h > -0.23:
            if ore > 0.75: return TILE_GOLD
            if ore > 0.62: return TILE_SILVER
            if ore > 0.52: return TILE_GRANITE
            if ore < 0.15: return TILE_SULFUR
            return TILE_STONE
        return TILE_STONE
    else:
        if h > -0.25:
            if ore > 0.78: return TILE_DIAMOND
            if ore > 0.60: return TILE_OBSIDIAN
            if ore > 0.50: return TILE_MARBLE
            return TILE_STONE
        return TILE_STONE'''

src = src.replace(old, new, 1)
fp.write_text(src, "utf-8")
print("OK: generate_tile 从6次perlin砍到2次")

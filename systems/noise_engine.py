"""Perlin 噪声引擎：地形生成核心算法。从 world_gen.py 提取。"""
import math
import random as _random


# ═══════════════════════════════════
# 噪声函数
# ═══════════════════════════════════

_PERLIN_CACHE: dict = {}

def _hash2d(x: int, y: int, seed: int) -> int:
    h = seed + x * 374761393 + y * 668265263
    h = (h ^ (h >> 13)) * 1274126177
    return h ^ (h >> 16)


def _hash_uniform(x: int, y: int, seed: int) -> float:
    return (_hash2d(x, y, seed) & 0x7fffffff) / 0x7fffffff


def _smooth_noise(x: int, y: int, seed: int) -> float:
    corners = (_hash_uniform(x-1, y-1, seed) + _hash_uniform(x+1, y-1, seed) +
               _hash_uniform(x-1, y+1, seed) + _hash_uniform(x+1, y+1, seed)) / 16
    sides = (_hash_uniform(x-1, y, seed) + _hash_uniform(x+1, y, seed) +
             _hash_uniform(x, y-1, seed) + _hash_uniform(x, y+1, seed)) / 8
    center = _hash_uniform(x, y, seed) / 4
    return corners + sides + center


def _interpolated_noise(x: float, y: float, seed: int) -> float:
    ix, iy = int(x), int(y)
    fx, fy = x - ix, y - iy

    def _fade(t): return t * t * t * (t * (t * 6 - 15) + 10)
    u, v = _fade(fx), _fade(fy)

    a = _smooth_noise(ix, iy, seed)
    b = _smooth_noise(ix+1, iy, seed)
    c = _smooth_noise(ix, iy+1, seed)
    d = _smooth_noise(ix+1, iy+1, seed)

    return a + u*(b-a) + v*(c-a) + u*v*(a-b-c+d)


def perlin_2d(x: float, y: float, seed: int = 0,
              octaves: int = 4, persistence: float = 0.5,
              lacunarity: float = 2.0) -> float:
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_value = 0.0
    for _ in range(octaves):
        value += amplitude * _interpolated_noise(x * frequency, y * frequency, seed)
        max_value += amplitude
        amplitude *= persistence
        frequency *= lacunarity
    return value / max_value if max_value > 0 else 0.0


# 石头/矿脉团块缓存：以大网格为单位，每个格子最多一个"矿脉中心"。
# 用缓存而不是每格都重新算随机数，避免性能问题。
_STONE_CELL_CACHE: dict = {}
_STONE_CELL_SIZE = 24


def _get_stone_deposit(cell_x: int, cell_y: int, seed: int):
    """返回该网格内的矿脉信息 (center_x, center_y, radius)，没有矿脉则返回 None。"""
    key = (cell_x, cell_y, seed)
    if key in _STONE_CELL_CACHE:
        return _STONE_CELL_CACHE[key]
    rng_seed = seed + cell_x * 92821 + cell_y * 68917
    rng = _random.Random(rng_seed)
    # 35% 的网格里有矿脉团块，其余是空地——这个比例决定"石头有多稀疏"
    if rng.random() > 0.35:
        result = None
    else:
        cx = cell_x * _STONE_CELL_SIZE + rng.randint(0, _STONE_CELL_SIZE - 1)
        cy = cell_y * _STONE_CELL_SIZE + rng.randint(0, _STONE_CELL_SIZE - 1)
        radius = rng.randint(4, 9)
        result = (cx, cy, radius)
    _STONE_CELL_CACHE[key] = result
    return result


def _find_nearby_deposit(x: int, y: int, seed: int):
    """检查 (x,y) 周围 3x3 网格内是否落在某个矿脉团块半径内。"""
    cell_x, cell_y = x // _STONE_CELL_SIZE, y // _STONE_CELL_SIZE
    for dcx in (-1, 0, 1):
        for dcy in (-1, 0, 1):
            deposit = _get_stone_deposit(cell_x + dcx, cell_y + dcy, seed)
            if deposit is None:
                continue
            cx, cy, radius = deposit
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            if dist <= radius:
                return dist, radius
    return None


def generate_tile(x: int, y: int, seed: int = 12345) -> int:
    """俯视图地形生成：默认大面积可通行（地面/草地），
    石头与矿脉只以局部团块形式聚集出现，不再区分"地下/地表"（无深度轴）。"""
    from world_gen import (TILE_AIR, TILE_DIRT, TILE_STONE, TILE_WATER, TILE_TREE, TILE_SAND,
                            TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
                            TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_OBSIDIAN)
    key = (x, y, seed)
    if key in _PERLIN_CACHE:
        return _PERLIN_CACHE[key]

    # 大尺度噪声：决定水域/沙滩，其余默认可通行地面
    h = perlin_2d(x / 25, y / 25, seed, octaves=3)
    if h < -0.35:
        tile = TILE_WATER
    elif h < -0.28:
        tile = TILE_SAND
    else:
        tile = TILE_AIR  # 可通行地面（草地/泥地），俯视图下的默认地表

    # 石头/矿脉团块：只在局部聚集区域内出现，边缘越远越稀疏
    if tile == TILE_AIR:
        found = _find_nearby_deposit(x, y, seed)
        if found is not None:
            dist, radius = found
            edge_fade = 1 - dist / radius
            if _hash_uniform(x, y, seed + 9001) < (0.3 + 0.7 * edge_fade):
                tile = TILE_STONE
                ore = perlin_2d(x / 5 + 100, y / 5 + 100, seed, octaves=3)
                if ore > 0.85: tile = TILE_DIAMOND
                elif ore > 0.80: tile = TILE_OBSIDIAN
                elif ore > 0.75: tile = TILE_GOLD
                elif ore > 0.70: tile = TILE_SILVER
                elif ore > 0.65: tile = TILE_IRON
                elif ore > 0.60: tile = TILE_COPPER
                elif ore > 0.55: tile = TILE_COAL
                elif ore > 0.50: tile = TILE_SULFUR
                elif ore > 0.45: tile = TILE_SALT
                elif ore > 0.40: tile = TILE_CLAY

    # 树木：沿用连续噪声阈值（Perlin 本身空间连续，自然形成小片树林，而非孤立点）
    if tile == TILE_AIR:
        tree_noise = perlin_2d(x / 6 + 300, y / 6 + 300, seed, octaves=3)
        if tree_noise > 0.55:
            tile = TILE_TREE

    _PERLIN_CACHE[key] = tile
    return tile


def clear_perlin_cache():
    _PERLIN_CACHE.clear()

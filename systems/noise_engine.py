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


def generate_tile(x: int, y: int, seed: int = 12345) -> int:
    from world_gen import TILE_AIR, TILE_DIRT, TILE_STONE, TILE_WATER, TILE_TREE, TILE_SAND
    key = (x, y, seed)
    if key in _PERLIN_CACHE:
        return _PERLIN_CACHE[key]

    h = perlin_2d(x/10, y/10, seed, octaves=4)
    ore = perlin_2d(x/5+100, y/5+100, seed, octaves=3)

    if y < 0:
        depth = abs(y)
        if h < -0.2: tile = TILE_WATER
        elif h < 0.1: tile = TILE_DIRT
        elif h < 0.3: tile = TILE_STONE
        else: tile = TILE_STONE
        if depth > 5 and ore > 0.4:
            from world_gen import TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND, TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN
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
    else:
        if h < -0.15: tile = TILE_WATER
        elif h < 0.0: tile = TILE_SAND
        elif h < 0.15: tile = TILE_DIRT
        elif h < 0.35:
            if ore > 0.40: tile = TILE_TREE
            else: tile = TILE_DIRT
        elif h < 0.50:
            if ore > 0.35: tile = TILE_TREE
            else: tile = TILE_DIRT
        else:
            if ore > 0.30: tile = TILE_TREE
            else: tile = TILE_DIRT

    _PERLIN_CACHE[key] = tile
    return tile


def clear_perlin_cache():
    _PERLIN_CACHE.clear()

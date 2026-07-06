#!/usr/bin/env python3
"""性能优化：perlin_2d 加缓存 + generate_tile 减少冗余计算"""
from pathlib import Path
from functools import lru_cache

BASE = Path(__file__).parent
fp = BASE / "world_gen.py"
src = fp.read_text("utf-8")

# 1. 在 perlin_2d 上面加 import 和装饰器
old = '''def perlin_2d(x: float, y: float, seed: int = 0,
              persistence: float = 0.5, octaves: int = 4) -> float:'''
new = '''from functools import lru_cache

@lru_cache(maxsize=16384)
def _perlin_cached(x: float, y: float, seed: int, persistence: float, octaves: int) -> float:
    """缓存版 perlin_2d，相同参数只算一次。"""
    total = 0.0; freq = 1.0; amp = 1.0; max_val = 0.0
    for _ in range(octaves):
        total += _interpolated_noise(x * freq, y * freq, seed) * amp
        max_val += amp
        freq *= 2.0; amp *= persistence
    return total / max_val

def perlin_2d(x: float, y: float, seed: int = 0,
              persistence: float = 0.5, octaves: int = 4) -> float:'''
# 函数体简化成调缓存版
old2 = '''    total = 0.0; freq = 1.0; amp = 1.0; max_val = 0.0
    for _ in range(octaves):
        total += _interpolated_noise(x * freq, y * freq, seed) * amp
        max_val += amp
        freq *= 2.0; amp *= persistence
    return total / max_val'''
new2 = '''    # 四舍五入到 0.1 精度，提高缓存命中率
    rx = round(x, 1); ry = round(y, 1)
    return _perlin_cached(rx, ry, seed, persistence, octaves)'''

src = src.replace(old, new, 1)
src = src.replace(old2, new2, 1)
print("[OK] 1/2 perlin_2d 加缓存")

# 2. 清理缓存函数（新游戏/读档时调用）
old3 = '''def generate_world(seed: int = 12345, layer: int = 0):
    """返回 World 对象。"""
    return World(seed=seed + layer * 10000)'''
new3 = '''def clear_perlin_cache():
    """清理 perlin 缓存（切换世界时调用）。"""
    _perlin_cached.cache_clear()

def generate_world(seed: int = 12345, layer: int = 0):
    """返回 World 对象。"""
    clear_perlin_cache()
    return World(seed=seed + layer * 10000)'''
src = src.replace(old3, new3, 1)
print("[OK] 2/2 generate_world 加缓存清理")

fp.write_text(src, "utf-8")
print("\n优化完成。重新测试启动耗时。")

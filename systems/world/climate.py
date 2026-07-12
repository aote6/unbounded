"""气候系统：温度/湿度噪声场 + 生物群系判定。"""
from systems.world.noise_engine import perlin_2d

_TEMP_SEED_OFFSET = 31337
_HUMID_SEED_OFFSET = 90210
_CLIMATE_SCALE = 120.0


def get_temperature(x: int, y: int, seed: int = 12345) -> float:
    """返回该坐标的气温，范围约 [-1, 1]，越大越热。"""
    return perlin_2d(x / _CLIMATE_SCALE, y / _CLIMATE_SCALE, seed + _TEMP_SEED_OFFSET, octaves=3)


def get_humidity(x: int, y: int, seed: int = 12345) -> float:
    """返回该坐标的湿度，范围约 [-1, 1]，越大越湿润。"""
    return perlin_2d(x / _CLIMATE_SCALE, y / _CLIMATE_SCALE, seed + _HUMID_SEED_OFFSET, octaves=3)


BIOME_ICE = "冰原"
BIOME_TUNDRA = "苔原"
BIOME_TAIGA = "针叶林"
BIOME_GRASSLAND = "草原"
BIOME_FOREST = "温带森林"
BIOME_DESERT = "沙漠"
BIOME_RAINFOREST = "雨林"

_BIOME_CACHE: dict = {}


def get_biome(x: int, y: int, seed: int = 12345) -> str:
    """根据温度/湿度返回该坐标所属的生物群系名称。"""
    cell = (x // 16, y // 16, seed)
    if cell in _BIOME_CACHE:
        return _BIOME_CACHE[cell]
    t = get_temperature(x, y, seed)
    h = get_humidity(x, y, seed)
    if t < 0.0:
        biome = BIOME_ICE
    elif t < 0.3:
        biome = BIOME_TUNDRA if h < 0.3 else BIOME_TAIGA
    elif t < 0.7:
        biome = BIOME_GRASSLAND if h < 0.3 else BIOME_FOREST
    else:
        biome = BIOME_DESERT if h < 0.3 else BIOME_RAINFOREST
    _BIOME_CACHE[cell] = biome
    return biome


def clear_climate_cache():
    """清除生物群系缓存。"""
    _BIOME_CACHE.clear()

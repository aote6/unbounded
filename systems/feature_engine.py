"""Feature Engine — 统一自然生成入口。

所有自然物（水、沙、石、矿、树、未来的药草、动物巢穴等）
都是 Feature。新增一种自然物只需：
1. 实现 Feature 接口
2. 注册到 FEATURE_CHAIN
不需要改 NaturalGenerator。

设计原则（公理四）：规则决定结果，数据决定内容。
"""

from world_gen import (TILE_AIR, TILE_WATER, TILE_SAND, TILE_STONE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD,
    TILE_DIAMOND, TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_OBSIDIAN,
    TILE_TREE)

from systems.noise_engine import perlin_2d, _hash_uniform, _find_nearby_deposit
from systems.climate import get_biome


def _load_biome_params(biome_name):
    """从 biomes.json 读取群系地形参数（带缓存）"""
    import json
    from pathlib import Path
    if not hasattr(_load_biome_params, '_cache'):
        _load_biome_params._cache = {}
        biome_file = Path(__file__).parent.parent / "data" / "biomes.json"
        if biome_file.exists():
            with open(biome_file, "r", encoding="utf-8") as f:
                for b in json.load(f):
                    _load_biome_params._cache[b["name"]] = b.get("terrain", {})
    return _load_biome_params._cache.get(biome_name, {})


# ═══════════════════════════════════
# Feature 接口（每个 Feature 是一个函数）
# 签名: (x, y, seed, biome, current_tile) → new_tile or None
# 返回 None 表示"我不负责这个位置"
# ═══════════════════════════════════

def water_feature(x, y, seed, biome, current_tile):
    """水域：大尺度噪声低于 water_thresh 时出现"""
    params = _load_biome_params(biome)
    h = perlin_2d(x / 25, y / 25, seed, octaves=3)
    thresh = params.get("water_thresh", -0.35)
    if h < thresh:
        return TILE_WATER
    return None


def sand_feature(x, y, seed, biome, current_tile):
    """沙滩：水域边缘过渡带"""
    if current_tile != TILE_AIR:
        return None
    params = _load_biome_params(biome)
    sand_thresh = params.get("sand_thresh")
    if sand_thresh is None:
        return None
    h = perlin_2d(x / 25, y / 25, seed, octaves=3)
    water_thresh = params.get("water_thresh", -0.35)
    if water_thresh <= h < sand_thresh:
        return TILE_SAND
    return None


def stone_deposit_feature(x, y, seed, biome, current_tile):
    """石头+矿脉团块：局部聚集，边缘渐疏。矿石分层由 minerals.json 数据驱动。"""
    if current_tile != TILE_AIR:
        return None
    found = _find_nearby_deposit(x, y, seed)
    if found is None:
        return None
    dist, radius = found
    edge_fade = 1 - dist / radius
    if _hash_uniform(x, y, seed + 9001) >= (0.3 + 0.7 * edge_fade):
        return None
    # 矿石分层：从 minerals.json 读取，按 rarity 升序匹配
    # ore_noise 越高 → 越稀有的矿石（rarity 越小）
    ore_noise = perlin_2d(x / 5 + 100, y / 5 + 100, seed, octaves=3)
    minerals = _load_minerals()
    for m in minerals:
        if ore_noise < m["rarity"]:
            return m["tile_id"]
    return TILE_STONE


def _load_minerals():
    """加载矿物数据（带缓存）"""
    import json
    from pathlib import Path as _Path
    if not hasattr(_load_minerals, "_cache"):
        mineral_file = _Path(__file__).parent.parent / "data" / "minerals.json"
        if mineral_file.exists():
            with open(mineral_file, "r", encoding="utf-8") as f:
                # 按 rarity 降序排列（稀有矿优先匹配）
                raw = json.load(f)
                _load_minerals._cache = sorted(raw, key=lambda m: m["rarity"])
        else:
            _load_minerals._cache = []
    return _load_minerals._cache


def tree_feature(x, y, seed, biome, current_tile):
    """树木：生态层决定物种，Biome 决定密度"""
    if current_tile != TILE_AIR:
        return None
    from systems.ecology import get_flora_species
    species = get_flora_species(x, y, seed, category="tree")
    if species is not None:
        return TILE_TREE
    return None


# ═══════════════════════════════════
# Feature 链：按优先级排列
# 水 > 沙 > 石 > 树（后面的只能覆盖 AIR）
# ═══════════════════════════════════






def herb_feature(x, y, seed, biome, current_tile):
    """药材：生态层决定物种，Biome 决定密度。只在森林/草原等植被区生成。"""
    if current_tile != TILE_AIR:
        return None
    from systems.ecology import get_flora_species
    from systems.ecology import _get_biome_cluster
    # 药材密度由 Biome 的 herb_density 控制
    cfg = _load_biome_params(biome)
    density = cfg.get("herb_density", 0.1)
    if density <= 0:
        return None
    # 使用坐标哈希判断（确定性概率）
    if _hash_uniform(x, y, seed + 77777) > density * 0.15:
        return None
    species = get_flora_species(x, y, seed, category="herb")
    if species is not None:
        return TILE_AIR  # 药材不改变地形，仅作为可采集物存在
    return None


def animal_spawn_feature(x, y, seed, biome, current_tile):
    """动物生成点：生态层决定物种，不改变地形。动物由 AI 系统在生成点附近实体化。"""
    if current_tile not in (TILE_AIR,):
        return None
    # 动物密度由 Biome 生态参数控制（暂用 herb_density 作为代理，未来独立配置）
    cfg = _load_biome_params(biome)
    animal_density = cfg.get("herb_density", 0.1) * 0.5
    if animal_density <= 0:
        return None
    if _hash_uniform(x, y, seed + 88888) > animal_density * 0.05:
        return None
    from systems.ecology import get_flora_species
    species = get_flora_species(x, y, seed, category="animal")
    if species is not None:
        return TILE_AIR  # 动物不改变地形，仅标记生成点
    return None


# Feature 链：按优先级排列（水 > 沙 > 石 > 树 > 药草）
FEATURE_CHAIN = [
    water_feature,
    sand_feature,
    stone_deposit_feature,
    tree_feature,
    herb_feature,
    animal_spawn_feature,
]

def natural_generator(x: int, y: int, seed: int = 12345) -> int:
    """统一自然生成入口。遍历 Feature 链，返回第一个匹配的 tile。
    任何 Feature 都不匹配时，返回 TILE_AIR（可通行地面）。"""
    biome = get_biome(x, y, seed)
    tile = TILE_AIR

    for feature in FEATURE_CHAIN:
        result = feature(x, y, seed, biome, tile)
        if result is not None:
            tile = result
            # 非 AIR 的 Feature（如水）会阻止后续 Feature
            if result != TILE_AIR and feature == water_feature:
                # 水之后只允许沙滩
                continue
            elif result != TILE_AIR:
                break

    return tile


# ═══════════════════════════════════
# 工具函数
# ═══════════════════════════════════

def register_feature(feature_func, position=None):
    """动态注册新 Feature。
    position=None 追加到末尾，否则插入到指定位置。"""
    if position is None:
        FEATURE_CHAIN.append(feature_func)
    else:
        FEATURE_CHAIN.insert(position, feature_func)


def list_features():
    """列出所有已注册的 Feature 名称"""
    return [f.__name__ for f in FEATURE_CHAIN]

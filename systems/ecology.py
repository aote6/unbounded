"""生态数据层：统一的物种查询引擎。

所有自然物（植物/药材/未来的矿物、动物）共享同一套按气候/群系过滤 + 
按网格聚簇分配的查询方式，新增物种只需要往 data/natural.json 里加数据，
不需要改这里的任何逻辑。
"""
import json
import random
import hashlib
from pathlib import Path
from systems.climate import get_biome
from systems.noise_engine import _hash_uniform

# Biome 配置（聚簇大小等环境参数由 Biome 决定，不在物种数据中）
_BIOME_CONFIG = None

def _load_biome_config():
    global _BIOME_CONFIG
    if _BIOME_CONFIG is not None:
        return _BIOME_CONFIG
    biome_file = BASE_DIR / "data" / "biomes.json"
    if biome_file.exists():
        with open(biome_file, "r", encoding="utf-8") as f:
            raw = json.load(f)
        _BIOME_CONFIG = {b["name"]: b for b in raw}
    else:
        _BIOME_CONFIG = {}
    return _BIOME_CONFIG

def _get_biome_cluster(biome_name: str, default: int = 10) -> int:
    """从 Biome 配置读取聚簇大小。环境决定分布，物种描述自己。"""
    cfg = _load_biome_config()
    biome = cfg.get(biome_name, {})
    return biome.get("ecology", {}).get("tree_cluster", default)

BASE_DIR = Path(__file__).parent.parent
NATURAL_FILE = BASE_DIR / "data" / "natural.json"

_NATURAL_CACHE = None
_SPECIES_CELL_CACHE: dict = {}
_DEFAULT_CELL_SIZE = 10  # 回退值，实际由 Biome 配置决定


def load_natural():
    global _NATURAL_CACHE
    if _NATURAL_CACHE is not None:
        return _NATURAL_CACHE
    if not NATURAL_FILE.exists():
        _NATURAL_CACHE = []
        return _NATURAL_CACHE
    try:
        with open(NATURAL_FILE, "r", encoding="utf-8") as f:
            _NATURAL_CACHE = json.load(f)
    except Exception:
        _NATURAL_CACHE = []
    return _NATURAL_CACHE


def clear_natural_cache():
    global _NATURAL_CACHE, _BIOME_CONFIG
    _NATURAL_CACHE = None
    _BIOME_CONFIG = None
    _SPECIES_CELL_CACHE.clear()


def _pick_species_for_cell(cell_x: int, cell_y: int, biome: str, seed: int, category: str = "tree"):
    """为一个网格单元确定性地选出一个"主物种"（及其伴生物种池）。
    同一网格内所有格子共用这个结果，形成成片、伴生物种一致的效果。"""
    key = (cell_x, cell_y, biome, category, seed)
    if key in _SPECIES_CELL_CACHE:
        return _SPECIES_CELL_CACHE[key]

    natural = load_natural()
    candidates = [f for f in natural if f.get("category") == category and biome in f.get("biomes", [])]
    if not candidates:
        _SPECIES_CELL_CACHE[key] = None
        return None

    rng_seed = seed + cell_x * 71317 + cell_y * 57923 + int(hashlib.md5(category.encode()).hexdigest()[:8], 16) % 100000
    rng = random.Random(rng_seed)
    weights = [c.get("rarity", 1) for c in candidates]
    primary = rng.choices(candidates, weights=weights, k=1)[0]

    # 伴生物种池：主物种 + 它的伴生物种（如果伴生物种也适合这个群系）
    pool = [primary]
    for companion_id in primary.get("companion_with", []):
        companion = next((c for c in candidates if c["id"] == companion_id), None)
        if companion and companion not in pool:
            pool.append(companion)

    _SPECIES_CELL_CACHE[key] = pool
    return list(pool)  # 返回副本，防止外部修改污染缓存


def get_flora_species(x: int, y: int, seed: int = 12345, category: str = "tree"):
    """查询 (x,y) 这个位置应该是什么物种。返回物种 dict 或 None（不适合任何物种时）。"""
    biome = get_biome(x, y, seed)
    cluster_size = _get_biome_cluster(biome, _DEFAULT_CELL_SIZE)
    if cluster_size <= 0:
        return None
    cell_x, cell_y = x // cluster_size, y // cluster_size
    pool = _pick_species_for_cell(cell_x, cell_y, biome, seed, category)
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]
    # 伴生物种池内，按格子哈希决定具体是哪一种（同一片林子里橡树和枫树交替出现）
    idx = int(_hash_uniform(x, y, seed + 5555) * len(pool))
    idx = min(idx, len(pool) - 1)
    return pool[idx]

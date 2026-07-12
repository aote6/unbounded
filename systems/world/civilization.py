"""文明系统 — 事件驱动的聚落生成与触发。"""
import json
from pathlib import Path
from systems.world.noise_engine import _hash_uniform
from systems.world.climate import get_biome

BASE_DIR = Path(__file__).parent.parent
CIV_FILE = BASE_DIR / "data" / "civilizations.json"

_CIV_CACHE = None
_GEN_CACHE: dict = {}


def _load_civs():
    """加载并缓存文明配置数据。

    Returns:
        list: 已加载的文明配置列表。
    """
    global _CIV_CACHE
    if _CIV_CACHE is not None:
        return _CIV_CACHE
    if CIV_FILE.exists():
        with open(CIV_FILE, "r", encoding="utf-8") as f:
            _CIV_CACHE = json.load(f)
    else:
        _CIV_CACHE = []
    return _CIV_CACHE


def get_settlement_at(x: int, y: int, seed: int = 12345) -> dict | None:
    """查询 (x,y) 是否有文明聚落。"""
    CELL = 200
    cx, cy = x // CELL, y // CELL
    key = (cx, cy, seed)
    if key in _GEN_CACHE:
        return _GEN_CACHE[key]
    civs = _load_civs()
    if not civs:
        _GEN_CACHE[key] = None
        return None
    r = _hash_uniform(cx, cy, seed + 99999)
    biome = get_biome(cx * CELL + CELL // 2, cy * CELL + CELL // 2, seed)
    candidates = [(c, c["rarity"]) for c in civs if biome in c.get("biomes", [])]
    if not candidates or r > sum(w for _, w in candidates) * 0.3:
        _GEN_CACHE[key] = None
        return None
    import random
    rng = random.Random(seed + cx * 31337 + cy * 6700417)
    types, weights = zip(*candidates)
    chosen = rng.choices(types, weights=weights, k=1)[0]
    sx = cx * CELL + rng.randint(CELL // 4, 3 * CELL // 4)
    sy = cy * CELL + rng.randint(CELL // 4, 3 * CELL // 4)
    result = {
        "type": chosen["id"], "name": chosen["name"],
        "x": sx, "y": sy,
        "size": rng.randint(*chosen["size"]),
        "population": rng.randint(*chosen["population"]),
        "buildings": chosen["buildings"],
        "trades": chosen["trades"],
        "events": chosen["event_triggers"],
        "discovered": False,
    }
    _GEN_CACHE[key] = result
    return result


def check_player_near_settlement(game) -> dict | None:
    """检查玩家是否接近聚落。"""
    settlement = get_settlement_at(game.player_x, game.player_y, game.world.seed)
    if settlement is None:
        return None
    dist = max(abs(game.player_x - settlement["x"]), abs(game.player_y - settlement["y"]))
    if dist <= 10 and not settlement.get("discovered"):
        settlement["discovered"] = True
        discover = settlement["events"].get("discover", {})
        game.message = discover.get("message", f"你发现了{settlement['name']}。")
        return settlement
    return None


def clear_civ_cache():
    """清除文明配置缓存及聚落生成缓存。"""
    global _CIV_CACHE
    _CIV_CACHE = None
    _GEN_CACHE.clear()

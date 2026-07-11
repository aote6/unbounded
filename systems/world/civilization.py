"""文明系统 — 事件驱动的聚落生成与触发。

设计原则：
- 生成阶段：聚落位置由 Seed 确定性生成（与植物/动物同一套生态引擎）
- 探索阶段：玩家接近时触发事件，不持续模拟
- 事件驱动：状态改变 → 触发事件 → 世界响应
"""

import json
from pathlib import Path
from systems.world.noise_engine import _hash_uniform
from systems.world.climate import get_biome

BASE_DIR = Path(__file__).parent.parent
CIV_FILE = BASE_DIR / "data" / "civilizations.json"

_CIV_CACHE = None
_GEN_CACHE: dict = {}


def _load_civs():
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
    """查询 (x,y) 是否有文明聚落。大网格确定性生成。
    返回聚落数据 dict 或 None。"""
    # 大网格：每 200x200 区域最多一个聚落
    CELL = 200
    cx, cy = x // CELL, y // CELL
    key = (cx, cy, seed)
    if key in _GEN_CACHE:
        return _GEN_CACHE[key]

    civs = _load_civs()
    if not civs:
        _GEN_CACHE[key] = None
        return None

    # 确定性：该网格是否生成聚落
    r = _hash_uniform(cx, cy, seed + 99999)
    biome = get_biome(cx * CELL + CELL // 2, cy * CELL + CELL // 2, seed)

    # 筛选适合该群系的聚落类型
    candidates = [(c, c["rarity"])
                  for c in civs if biome in c.get("biomes", [])]
    if not candidates or r > sum(w for _, w in candidates) * 0.3:
        _GEN_CACHE[key] = None
        return None

    # 选一个类型（按 rarity 权重）
    import random
    rng = random.Random(seed + cx * 31337 + cy * 6700417)
    types, weights = zip(*candidates)
    chosen = rng.choices(types, weights=weights, k=1)[0]

    # 聚落中心在该网格内的位置
    sx = cx * CELL + rng.randint(CELL // 4, 3 * CELL // 4)
    sy = cy * CELL + rng.randint(CELL // 4, 3 * CELL // 4)

    result = {
        "type": chosen["id"],
        "name": chosen["name"],
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
    """检查玩家是否接近聚落，返回聚落数据并触发事件。"""
    settlement = get_settlement_at(
        game.player_x, game.player_y, game.world.seed)
    if settlement is None:
        return None

    dist = max(abs(game.player_x -
                   settlement["x"]), abs(game.player_y -
                                         settlement["y"]))
    if dist <= 10 and not settlement.get("discovered"):
        settlement["discovered"] = True
        # 触发发现事件
        discover = settlement["events"].get("discover", {})
        game.message = discover.get("message", f"你发现了{settlement['name']}。")
        return settlement
    return None


def clear_civ_cache():
    global _CIV_CACHE
    _CIV_CACHE = None
    _GEN_CACHE.clear()

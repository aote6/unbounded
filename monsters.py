""" monsters.py 怪物与 AI 评分引擎——无限世界版。"""
from config import MONSTER_SLEEP_DISTANCE, MONSTER_SLEEP_TICKS
from item_generator import generate_loot
from pathlib import Path
import json
import random

BASE_DIR = Path(__file__).parent
MONSTERS_FILE = BASE_DIR / "data" / "monsters.json"

def load_monsters():
    if not MONSTERS_FILE.exists():
        print(f"[monsters] 文件不存在: {MONSTERS_FILE}")
        return {}
    try:
        with open(MONSTERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        import logging; logging.warning(f"monsters.json 解析失败: {e}")
        return {}

def chebyshev(x1, y1, x2, y2):
    return max(abs(x1 - x2), abs(y1 - y2))


def _pick_monster_type(monster_data, biome=None, faction=None):
    """按生物群系 + 阵营过滤后加权随机选择怪物类型。
    biome=None 时不按群系过滤；faction=None 时不按阵营过滤（向后兼容旧调用方式）。"""
    names = []
    weights = []
    for n, t in monster_data.items():
        if faction is not None and t.get("faction", "hostile") != faction:
            continue
        biomes = t.get("biomes")
        if biome is not None and biomes is not None and biome not in biomes:
            continue
        w = t.get("spawn_weight", 1)
        if w <= 0:
            continue
        names.append(n)
        weights.append(w)
    if not names:
        return None
    return random.choices(names, weights=weights, k=1)[0]

def try_spawn(world, px, py, monsters, spawn_counter, monster_data,
              interval_min=20, interval_max=40, min_dist=10):
    spawn_counter["count"] -= 1
    if spawn_counter["count"] > 0:
        return None
    spawn_counter["count"] = random.randint(interval_min, interval_max)
    monster_index = {(m["x"], m["y"]) for m in monsters}
    from tile_props import TILE_AIR
    from systems.climate import get_biome
    for _ in range(15):
        sx = px + random.randint(-20, 20)
        sy = py + random.randint(-15, 15)
        if chebyshev(sx, sy, px, py) < min_dist:
            continue
        if world.get_tile(sx, sy)["tile"] != TILE_AIR:
            continue
        if (sx, sy) in monster_index:
            continue
        if sx == px and sy == py:
            continue
        biome = get_biome(sx, sy, world.seed)
        mtype = _pick_monster_type(monster_data, biome=biome, faction="hostile")
        if mtype is None:
            continue
        return make_monster(mtype, sx, sy, monster_data)
    return None

def make_monster(name, x, y, monster_data):
    t = monster_data.get(name, {})
    return {
        "name": name, "char": t.get("char", "?"), "x": x, "y": y,
        "hp": t.get("hp", 10), "max_hp": t.get("hp", 10),
        "attack_power": tuple(t.get("attack_power", [1, 3])),
        "hit_chance": t.get("hit_chance", 0.7),
        "vision": t.get("vision", 6),
        "flee_at_hp_ratio": t.get("flee_at_hp_ratio", 0.3),
        "scores": t.get("scores", {}), "drop": t.get("drop", {}),
        "corpse_tile": t.get("corpse_tile"),
        "split_into": t.get("split_into"),
        "special_behavior": t.get("special_behavior"),
        "properties": t.get("properties", {}),
        "tags": t.get("tags", []),
        "faction": t.get("faction", "hostile"),
    }

def get_split_spawns(monster, monster_data):
    split_info = monster.get("split_into")
    if not split_info:
        return []
    child_name = split_info.get("name")
    count = split_info.get("count", 2)
    if child_name not in monster_data:
        return []
    spawns = []
    for _ in range(count):
        for __ in range(10):
            dx = random.randint(-1, 1)
            dy = random.randint(-1, 1)
            nx, ny = monster["x"] + dx, monster["y"] + dy
            spawns.append(make_monster(child_name, nx, ny, monster_data))
            break
    return spawns

def generate_loot_for(depth, monster_name=None):
    """生成掉落物。如果有怪物名，优先用怪物的drop表"""
    import random
    # 如果有怪物特定掉落表
    if monster_name:
        monster_data = load_monsters()
        monster = monster_data.get(monster_name, {})
        drop_table = monster.get("drop", {})
        if drop_table:
            # 按权重随机选掉落
            items_list = list(drop_table.items())
            # 格式可能是 {"物品名": 权重} 或 {"物品名": 数量}
            # 先检查是否全是数字权重
            if all(isinstance(v, (int, float)) for v in drop_table.values()):
                total = sum(drop_table.values())
                r = random.randint(1, total)
                cumulative = 0
                for item_name, weight in drop_table.items():
                    cumulative += weight
                    if r <= cumulative:
                        return item_name, {"name": item_name, "count": 1}
            else:
                # 旧格式
                item = generate_loot(depth)
                if item:
                    return item["name"], item
    # 回退到通用掉落
    item = generate_loot(depth)
    if item:
        return item["name"], item
    return None, None


# ═══════════════════════════════════════════════
# M22: 中立生物 AI
# ═══════════════════════════════════════════════

def _pick_neutral_type(monster_data, biome=None):
    """按生物群系选择中立生物类型（薄封装，复用统一的按群系+阵营选择逻辑）。"""
    return _pick_monster_type(monster_data, biome=biome, faction="neutral")

# ── AI 函数兼容转发（延迟导入，避免循环依赖）──
def _get_ai_func(name):
    from systems import monster_ai
    return getattr(monster_ai, name)

def _has_line_of_sight(*args, **kw): return _get_ai_func("_has_line_of_sight")(*args, **kw)
def ai_act(*args, **kw): return _get_ai_func("ai_act")(*args, **kw)
def _ai_special_behavior(*args, **kw): return _get_ai_func("_ai_special_behavior")(*args, **kw)
def _behavior_never_flee(*args, **kw): return _get_ai_func("_behavior_never_flee")(*args, **kw)
def _behavior_erratic(*args, **kw): return _get_ai_func("_behavior_erratic")(*args, **kw)
def _erratic_teleport(*args, **kw): return _get_ai_func("_erratic_teleport")(*args, **kw)
def _do_attack(*args, **kw): return _get_ai_func("_do_attack")(*args, **kw)
def _step_toward(*args, **kw): return _get_ai_func("_step_toward")(*args, **kw)
def _is_passable(*args, **kw): return _get_ai_func("_is_passable")(*args, **kw)
def _move_toward(*args, **kw): return _get_ai_func("_move_toward")(*args, **kw)
def _move_away(*args, **kw): return _get_ai_func("_move_away")(*args, **kw)
def _move_random(*args, **kw): return _get_ai_func("_move_random")(*args, **kw)
def _ai_neutral(*args, **kw): return _get_ai_func("_ai_neutral")(*args, **kw)
def _behavior_always_flee(*args, **kw): return _get_ai_func("_behavior_always_flee")(*args, **kw)
def _ai_hunt_prey(*args, **kw): return _get_ai_func("_ai_hunt_prey")(*args, **kw)

""" monsters.py 怪物与 AI 评分引擎——无限世界版。"""
import json, random
from pathlib import Path
from world_gen import TILE_AIR
from tile_props import get_tile_props
from config import MONSTER_SLEEP_DISTANCE, MONSTER_SLEEP_TICKS
from item_generator import generate_loot

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
        print(f"[monsters] JSON 解析失败: {e}")
        return {}

def chebyshev(x1, y1, x2, y2):
    return max(abs(x1 - x2), abs(y1 - y2))

def _has_line_of_sight(world, x1, y1, x2, y2):
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1
    err = dx - dy
    cx, cy = x1, y1
    while True:
        if cx == x2 and cy == y2:
            return True
        if not (cx == x1 and cy == y1):
            tile = world.get_tile(cx, cy)["tile"]
            if get_tile_props(tile)["blocks_vision"]:
                return False
        if cx == x2 and cy == y2:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy; cx += sx
        if e2 < dx:
            err += dx; cy += sy
    return True

def ai_act(monster, world, px, py, turn, monster_index):
    dist = chebyshev(monster["x"], monster["y"], px, py)
    if dist > MONSTER_SLEEP_DISTANCE:
        if turn % MONSTER_SLEEP_TICKS != 0:
            return ""
    special = _ai_special_behavior(monster, world, px, py, monster_index)
    if special is not None:
        return special
    mx, my = monster["x"], monster["y"]
    candidates = []
    if dist <= 1:
        if _has_line_of_sight(world, mx, my, px, py):
            candidates.append(("attack", monster.get("scores", {}).get("attack", 10), px, py))
    vis = monster.get("vision", 6)
    if 1 < dist <= vis:
        candidates.append(("chase", monster.get("scores", {}).get("chase", 8), px, py))
    if dist <= vis and monster["hp"] < monster["max_hp"] * monster.get("flee_at_hp_ratio", 0.3):
        candidates.append(("flee", monster.get("scores", {}).get("flee", 12), px, py))
    candidates.append(("wander", monster.get("scores", {}).get("wander", 1), None, None))
    candidates.sort(key=lambda c: c[1], reverse=True)
    action, _, tx, ty = candidates[0]
    if action == "attack":
        return _do_attack(monster, px, py)
    elif action == "chase":
        return _move_toward(monster, tx, ty, world, monster_index, px, py)
    elif action == "flee":
        return _move_away(monster, tx, ty, world, monster_index, px, py)
    elif action == "wander":
        return _move_random(monster, world, monster_index, px, py)
    return ""

def _ai_special_behavior(monster, world, px, py, monster_index):
    special = monster.get("special_behavior")
    if special is None:
        return None
    if special == "never_flee":
        return _behavior_never_flee(monster, world, px, py, monster_index)
    if special == "erratic_movement":
        return _behavior_erratic(monster, world, px, py, monster_index)
    return None

def _behavior_never_flee(monster, world, px, py, monster_index):
    mx, my = monster["x"], monster["y"]
    dist = chebyshev(mx, my, px, py)
    vis = monster.get("vision", 5)
    if dist <= 1:
        if _has_line_of_sight(world, mx, my, px, py):
            return _do_attack(monster, px, py)
    if dist <= vis:
        if random.random() < 0.5:
            return _move_toward(monster, px, py, world, monster_index, px, py)
        return "stand_firm"
    if random.random() < 0.3:
        return _move_random(monster, world, monster_index, px, py)
    return "stand_firm"

def _behavior_erratic(monster, world, px, py, monster_index):
    mx, my = monster["x"], monster["y"]
    dist = chebyshev(mx, my, px, py)
    vis = monster.get("vision", 10)
    if dist <= 1:
        if _has_line_of_sight(world, mx, my, px, py):
            result = _do_attack(monster, px, py)
            if random.random() < 0.3:
                _erratic_teleport(monster, world, mx, my, monster_index)
            return result
    if dist <= vis:
        if random.random() < 0.7:
            return _move_random(monster, world, monster_index, px, py)
        else:
            return _move_toward(monster, px, py, world, monster_index, px, py)
    if random.random() < 0.5:
        return _move_random(monster, world, monster_index, px, py)
    return "flutter"

def _erratic_teleport(monster, world, mx, my, monster_index):
    for _ in range(10):
        dx = random.randint(-4, 4)
        dy = random.randint(-4, 4)
        nx, ny = mx + dx, my + dy
        if abs(dx) + abs(dy) >= 2:
            tile = world.get_tile(nx, ny)["tile"]
            if get_tile_props(tile)["passable"] and (nx, ny) not in monster_index:
                monster["x"], monster["y"] = nx, ny
                return

def _do_attack(monster, px, py):
    atk = monster.get("attack_power", (1, 3))
    dmg = random.randint(atk[0], atk[1])
    return dmg if random.random() < monster.get("hit_chance", 0.7) else 0

def _step_toward(mx, my, tx, ty):
    dx = (tx - mx) // max(1, abs(tx - mx)) if tx != mx else 0
    dy = (ty - my) // max(1, abs(ty - my)) if ty != my else 0
    return dx, dy

def _is_passable(world, x, y, monster_index, px, py):
    """检查格子是否可通行：地形 + 无怪物 + 非玩家位置"""
    tile = world.get_tile(x, y)["tile"]
    if not get_tile_props(tile)["passable"]:
        return False
    if (x, y) in monster_index:
        return False
    if x == px and y == py:
        return False
    return True

def _move_toward(monster, tx, ty, world, monster_index, px, py):
    dx, dy = _step_toward(monster["x"], monster["y"], tx, ty)
    nx, ny = monster["x"] + dx, monster["y"] + dy
    if _is_passable(world, nx, ny, monster_index, px, py):
        monster["x"], monster["y"] = nx, ny
        return "chase"
    for adx, ady in [(dy, dx), (-dy, -dx), (dx, 0), (0, dy)]:
        ax, ay = monster["x"] + adx, monster["y"] + ady
        if _is_passable(world, ax, ay, monster_index, px, py):
            monster["x"], monster["y"] = ax, ay
            return "chase"
    return "blocked"

def _move_away(monster, tx, ty, world, monster_index, px, py):
    dx, dy = _step_toward(monster["x"], monster["y"], tx, ty)
    nx, ny = monster["x"] - dx, monster["y"] - dy
    if _is_passable(world, nx, ny, monster_index, px, py):
        monster["x"], monster["y"] = nx, ny
        return "flee"
    return "cower"

def _move_random(monster, world, monster_index, px, py):
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)]
    random.shuffle(dirs)
    for dx, dy in dirs:
        nx, ny = monster["x"] + dx, monster["y"] + dy
        if _is_passable(world, nx, ny, monster_index, px, py):
            monster["x"], monster["y"] = nx, ny
            return "wander"
    return "idle"

def _pick_monster_type(monster_data, depth=0):
    names = list(monster_data.keys())
    if not names:
        return None
    weights = []
    for n in names:
        w = monster_data[n].get("spawn_weight", 1)
        depth_range = monster_data[n].get("depth_range", None)
        if depth_range:
            d_min, d_max = depth_range
            if not (d_min <= depth <= d_max):
                w = 0
        weights.append(w)
    if sum(weights) == 0:
        return random.choice(names)
    return random.choices(names, weights=weights, k=1)[0]

def try_spawn(world, px, py, monsters, spawn_counter, monster_data,
              interval_min=20, interval_max=40, min_dist=10):
    spawn_counter["count"] -= 1
    if spawn_counter["count"] > 0:
        return None
    spawn_counter["count"] = random.randint(interval_min, interval_max)
    mtype = _pick_monster_type(monster_data, depth=py)
    if mtype is None:
        return None
    monster_index = {(m["x"], m["y"]) for m in monsters}
    for _ in range(50):
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

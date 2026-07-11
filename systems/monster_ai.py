import config
"""怪物AI系统：行为决策、移动索引、生成控制
from config import config.MONSTER_SLEEP_DISTANCE, config.MONSTER_SLEEP_TICKS

M21: tick_status_effects 改为委托 BuffManager.tick_all()，
     保留兼容包装函数供旧调用方使用。
"""
import random
import monsters as monsters_mod
from tile_props import get_tile_props
from systems.inventory_actions import add_monster, monster_moved
from systems.combat_system import kill_monster

# ── 工具函数（从 monsters.py 迁移，避免循环导入）──


def chebyshev(x1, y1, x2, y2):
    return max(abs(x1 - x2), abs(y1 - y2))


def tick_monsters(game):
    """每回合处理所有怪物AI。返回攻击消息列表。"""
    msgs = []
    for m in game.monsters:
        old_x, old_y = m["x"], m["y"]
        act = ai_act(
            m, game.world, game.player_x, game.player_y,
            game.turn, game._monster_index, game
        )
        # 更新空间索引
        if m["x"] != old_x or m["y"] != old_y:
            monster_moved(game, m, old_x, old_y)
        if isinstance(act, int):
            if act > 0:
                dmg = max(1, act - game._player_defense())
                game.player_hp -= dmg
                msgs.append(f"{m['name']} 攻击了你，造成 {dmg} 点伤害！")
                game._gain_skill("defense")
            else:
                msgs.append(f"{m['name']} 的攻击落空了。")
    # M22: 怪物攻击附近的中立生物
    _tick_monster_vs_neutral(game)

    if msgs:
        game.message = " ".join(msgs[-2:])


def try_spawn_monster(game):
    """尝试生成怪物。"""
    from config import SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX, SPAWN_MIN_DISTANCE

    m = monsters_mod.try_spawn(
        game.world, game.player_x, game.player_y,
        game.monsters, game.spawn_counter, game.monster_data,
        interval_min=SPAWN_INTERVAL_MIN, interval_max=SPAWN_INTERVAL_MAX,
        min_dist=SPAWN_MIN_DISTANCE,
    )
    if m:
        # M21: 新怪物也做旧格式迁移
        if hasattr(game, 'buff_manager'):
            game.buff_manager.migrate_legacy(m)
        add_monster(game, m)
        game.message = f"一只 {m['name']} 出现了！"

    # M22: 中立生物生成
    _try_spawn_neutral(game)


def _try_spawn_neutral(game):
    """每回合有概率在玩家远处生成中立生物。

    物种由生态层 get_flora_species(category='animal') 决定，
    替代旧的按群系随机挑选逻辑，与植物/药材共用同一套引擎。
    """
    import random as _random
    from systems.ecology import get_flora_species
    from systems.weather_system import get_weather_at

    # 天气影响生成密度
    weather_mod = get_weather_at(
        game.player_x,
        game.player_y,
        game.world.seed,
        game.turn)
    density_mult = weather_mod.get(
        "modifiers", {}).get(
        "animal_density_mult", 1.0)
    if _random.random() > 0.25 * density_mult:
        return

    for _ in range(20):
        sx = game.player_x + _random.randint(-15, 15)
        sy = game.player_y + _random.randint(-10, 10)
        if abs(sx - game.player_x) < 8 or abs(sy - game.player_y) < 8:
            continue
        if game.world.get_tile(sx, sy)["tile"] != 0:  # TILE_AIR
            continue
        if (sx, sy) in game._monster_index:
            continue

        # 生态层决定该位置是否有动物、什么物种
        animal_sp = get_flora_species(
            sx, sy, game.world.seed, category="animal")
        if animal_sp is None:
            continue

        animal_name = animal_sp["name"]
        # 如果 monsters.json 里有对应条目，用它；否则用通用模板
        if animal_name in game.monster_data:
            nm = monsters_mod.make_monster(
                animal_name, sx, sy, game.monster_data)
        else:
            # 生态层有定义但 monsters.json 没有 —— 用通用中立生物模板
            nm = {
                "name": animal_name, "char": animal_sp.get("char", "a"),
                "x": sx, "y": sy, "hp": 5, "max_hp": 5,
                "attack_power": (1, 2), "hit_chance": 0.5,
                "vision": 6, "flee_at_hp_ratio": 0.5,
                "scores": {}, "drop": {}, "corpse_tile": None,
                "split_into": None, "special_behavior": None,
                "properties": {}, "tags": animal_sp.get("tags", []),
                "faction": "neutral",
            }
        if hasattr(game, 'buff_manager'):
            game.buff_manager.migrate_legacy(nm)
        add_monster(game, nm)
        break


def tick_corpses(game):
    """每回合处理尸体腐烂。"""
    from world_gen import TILE_AIR
    decayed = []
    for (cx, cy), remaining in game.corpses.items():
        remaining -= 1
        if remaining <= 0:
            if game.world.get_tile(cx, cy)["tile"] != TILE_AIR:
                game.world.set_tile(cx, cy, TILE_AIR)
                game.modified_tiles[(cx, cy)] = TILE_AIR
            decayed.append((cx, cy))
        else:
            game.corpses[(cx, cy)] = remaining
    for pos in decayed:
        del game.corpses[pos]


def _tick_monster_vs_neutral(game):
    """每回合: 敌对怪物攻击相邻的中立生物"""
    for m in game.monsters:
        if m.get("faction") != "hostile":
            continue
        mx, my = m["x"], m["y"]
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                       (0, 1), (1, -1), (1, 0), (1, 1)]:
            nx, ny = mx + dx, my + dy
            target = game._monster_index.get((nx, ny))
            if target and target.get("faction") == "neutral":
                ap = m.get("attack_power", [1, 3])
                dmg = random.randint(ap[0], ap[1])
                target["hp"] -= dmg
                if target["hp"] <= 0:
                    kill_monster(game, target, cause="predator")
                break


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
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy
    return True


def ai_act(monster, world, px, py, turn, monster_index, game=None):
    dist = chebyshev(monster["x"], monster["y"], px, py)
    if dist > config.MONSTER_SLEEP_DISTANCE:
        if turn % config.MONSTER_SLEEP_TICKS != 0:
            return ""
    special = _ai_special_behavior(monster, world, px, py, monster_index, game)
    if special is not None:
        return special
    mx, my = monster["x"], monster["y"]
    candidates = []
    if dist <= 1:
        if _has_line_of_sight(world, mx, my, px, py):
            candidates.append(
                ("attack", monster.get(
                    "scores", {}).get(
                    "attack", 0), px, py))
    vis = monster.get("vision", 6)
    if 1 < dist <= vis:
        candidates.append(
            ("chase", monster.get(
                "scores", {}).get(
                "chase", 0), px, py))
    if dist <= vis and monster["hp"] < monster["max_hp"] * \
            monster.get("flee_at_hp_ratio", 0.3):
        candidates.append(
            ("flee", monster.get(
                "scores", {}).get(
                "flee", 12), px, py))
    candidates.append(
        ("wander",
         monster.get(
             "scores",
             {}).get(
             "wander",
             1),
            None,
            None))
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


def _ai_special_behavior(monster, world, px, py, monster_index, game=None):
    special = monster.get("special_behavior")
    if special is None:
        return None
    if special == "never_flee":
        return _behavior_never_flee(monster, world, px, py, monster_index)
    if special == "erratic_movement":
        return _behavior_erratic(monster, world, px, py, monster_index)
    if special == "always_flee":
        return _behavior_always_flee(monster, world, px, py, monster_index)
    if special == "hunt_prey":
        return _ai_hunt_prey(monster, world, px, py, monster_index, game)
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
            if get_tile_props(tile)["passable"] and (
                    nx, ny) not in monster_index:
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
    # 优先使用气味地图寻路（解决卡墙角问题）
    try:
        from systems.scent_map import scent_best_direction
        dx, dy = scent_best_direction(monster["x"], monster["y"])
        if (dx, dy) != (0, 0):
            nx, ny = monster["x"] + dx, monster["y"] + dy
            if _is_passable(world, nx, ny, monster_index, px, py):
                monster["x"], monster["y"] = nx, ny
                return "chase"
    except ImportError:
        pass

    # 回退到贪心算法
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
    dirs = [(0, -1), (0, 1), (-1, 0), (1, 0),
            (-1, -1), (1, -1), (-1, 1), (1, 1)]
    random.shuffle(dirs)
    for dx, dy in dirs:
        nx, ny = monster["x"] + dx, monster["y"] + dy
        if _is_passable(world, nx, ny, monster_index, px, py):
            monster["x"], monster["y"] = nx, ny
            return "wander"
    return "idle"


def _ai_neutral(monster, world, px, py, turn, monster_index):
    """中立生物 AI: 逃跑或随机移动, 不攻击玩家"""
    mx, my = monster["x"], monster["y"]
    dist = chebyshev(mx, my, px, py)
    vis = monster.get("vision", 6)

    if dist <= 3:
        return _move_away(monster, px, py, world, monster_index, px, py)

    if dist <= vis and monster["hp"] < monster["max_hp"] * \
            monster.get("flee_at_hp_ratio", 0.5):
        return _move_away(monster, px, py, world, monster_index, px, py)

    if turn % 3 == 0:
        return _move_random(monster, world, monster_index, px, py)

    return ""


def _behavior_always_flee(monster, world, px, py, monster_index):
    """中立生物: 始终与玩家保持距离"""
    mx, my = monster["x"], monster["y"]
    dist = chebyshev(mx, my, px, py)
    vis = monster.get("vision", 8)
    if dist <= vis:
        return _move_away(monster, px, py, world, monster_index, px, py)
    return _move_random(monster, world, monster_index, px, py)


def _ai_hunt_prey(monster, world, px, py, monster_index, game=None):
    """捕食者 AI: 主动搜寻视野内带 'prey' 标签的猎物，追踪并猎杀；
    没有猎物时才会躲避玩家或随机游荡，不主动招惹玩家。"""
    mx, my = monster["x"], monster["y"]
    vis = monster.get("vision", 8)

    target = None
    target_dist = None
    for (ox, oy), other in monster_index.items():
        if other is monster:
            continue
        if "prey" not in other.get("tags", []):
            continue
        d = chebyshev(mx, my, ox, oy)
        if d <= vis and (target_dist is None or d < target_dist):
            target, target_dist = other, d

    if target is not None:
        if target_dist <= 1 and _has_line_of_sight(
                world, mx, my, target["x"], target["y"]):
            _attack_other_monster(monster, target, game)
            return "hunt_attack"
        return _move_toward(
            monster,
            target["x"],
            target["y"],
            world,
            monster_index,
            px,
            py)

    dist_to_player = chebyshev(mx, my, px, py)
    if dist_to_player <= 4:
        return _move_away(monster, px, py, world, monster_index, px, py)
    return _move_random(monster, world, monster_index, px, py)


def _attack_other_monster(attacker, target, game=None):
    """捕食者攻击另一只怪物（而非玩家），直接扣血并在死亡时正确清理。"""
    ap = attacker.get("attack_power", (1, 3))
    dmg = random.randint(ap[0], ap[1])
    if random.random() > attacker.get("hit_chance", 0.6):
        return
    target["hp"] -= dmg
    if target["hp"] <= 0 and game is not None:
        kill_monster(game, target, cause="predator")

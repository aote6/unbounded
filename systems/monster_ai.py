"""怪物AI系统：行为决策、移动索引、生成控制"""

import monsters as monsters_mod


def tick_monsters(game):
    """每回合处理所有怪物AI。返回攻击消息列表。"""
    msgs = []
    for m in game.monsters:
        old_x, old_y = m["x"], m["y"]
        act = monsters_mod.ai_act(
            m, game.world, game.player_x, game.player_y,
            game.turn, game._monster_index
        )
        # 更新空间索引
        if m["x"] != old_x or m["y"] != old_y:
            game._monster_moved(m, old_x, old_y)
        if isinstance(act, int):
            if act > 0:
                dmg = max(1, act - game._player_defense())
                game.player_hp -= dmg
                msgs.append(f"{m['name']} 攻击了你，造成 {dmg} 点伤害！")
                game._gain_skill("defense")
            else:
                msgs.append(f"{m['name']} 的攻击落空了。")
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
        game._add_monster(m)
        game.message = f"一只 {m['name']} 出现了！"



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


def tick_status_effects(game):
    """每回合处理怪物身上的状态效果。"""
    for m in list(game.monsters):
        # 旧版 on_fire
        if m.get("on_fire", 0) > 0:
            m["hp"] -= 2
            m["on_fire"] -= 1
            if m["hp"] <= 0:
                game._kill_monster(m, cause="burn")
                continue
        # 新版 burning（标签系统触发）
        burn = m.get("burning")
        if burn and burn.get("duration", 0) > 0:
            m["hp"] -= burn.get("damage_per_turn", 2)
            burn["duration"] -= 1
            if burn["duration"] <= 0:
                del m["burning"]
            if m["hp"] <= 0:
                game._kill_monster(m, cause="burn")
                continue
        if m.get("poisoned", 0) > 0:
            m["hp"] -= 1
            m["poisoned"] -= 1
            if m["hp"] <= 0:
                game._kill_monster(m, cause="poison")

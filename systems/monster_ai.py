"""怪物AI系统：行为决策、移动索引、生成控制

M21: tick_status_effects 改为委托 BuffManager.tick_all()，
     保留兼容包装函数供旧调用方使用。
"""

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
        # M21: 新怪物也做旧格式迁移
        if hasattr(game, 'buff_manager'):
            game.buff_manager.migrate_legacy(m)
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
    """每回合处理怪物身上的状态效果。
    
    M21: 委托给 BuffManager.tick_all()，保留此函数供旧调用方兼容。
    新代码应直接在 advance_turn 中调用 game.buff_manager.tick_all(game)。
    """
    if hasattr(game, 'buff_manager'):
        game.buff_manager.tick_all(game)
    else:
        # 极端回退：如果 buff_manager 不存在（不应发生），
        # 不做任何处理，避免重复扣血逻辑。
        pass

"""回合推进系统：接管原 Game.advance_turn 的所有逻辑"""
from systems.world.scent_map import rebuild_scent_map
from systems.combat.monster_ai import tick_monsters, try_spawn_monster, tick_corpses
from systems.gameplay.tile_interaction import tick_tile_interactions, tick_burning_tiles
from systems.gameplay.legacy_system import check_death, show_death_screen
from systems.core.save_manager import new_game
from systems.gameplay.goal_system import check_goals
from systems.world.civilization import check_player_near_settlement


def advance_turn(game):
    """每回合推进：气味→Buff→尸体→怪物→区块→目标→死亡检查"""
    game.turn += 1

    # 只在附近有怪物时才重建气味场，避免无怪物区域每步全量计算
    if any(abs(m["x"] - game.player_x) <= 20 and abs(m["y"] -
           game.player_y) <= 20 for m in game.monsters):
        rebuild_scent_map(game)
    game.buff_manager.tick_all(game)
    tick_corpses(game)
    tick_monsters(game)
    try_spawn_monster(game)
    tick_tile_interactions(game)
    tick_burning_tiles(game)

    if game.world:
        game.world.keep_radius(game.player_x, game.player_y, 3)

    if game.turn % 10 == 0:
        check_goals(game)

    # 聚落发现：轻量的距离判断+缓存查询，每回合检查，玩家走近应立即触发
    check_player_near_settlement(game)

    if check_death(game):
        show_death_screen(game)
        new_game(game, inherit_world=True)

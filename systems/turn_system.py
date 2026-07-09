"""回合推进系统：接管原 Game.advance_turn 的所有逻辑"""
from systems.scent_map import rebuild_scent_map
from systems.monster_ai import tick_monsters, try_spawn_monster, tick_corpses
from systems.legacy_system import check_death, show_death_screen
from systems.save_manager import new_game


def advance_turn(game):
    """每回合推进：气味→Buff→尸体→怪物→区块→目标→死亡检查"""
    game.turn += 1

    # 1. 刷新气味地图
    rebuild_scent_map(game)

    # 2. Buff 结算
    game.buff_manager.tick_all(game)

    # 3. 尸体 decay
    tick_corpses(game)

    # 4. 怪物 AI
    tick_monsters(game)

    # 5. 尝试生成新怪物
    try_spawn_monster(game)

    # 6. 世界区块维护
    if game.world:
        game.world.keep_radius(game.player_x, game.player_y, 3)

    # 7. 目标检查（每10回合）
    if game.turn % 10 == 0:
        _check_goals(game)

    # 8. 死亡检查
    if check_death(game):
        show_death_screen(game)
        new_game(game, inherit_world=True)


def _check_goals(game):
    """根据玩家进度推进目标"""
    if game.goal == "build_first_room" and game._count_rooms_nearby() >= 1:
        game.goal = "explore_cave"
        game.message = "【目标】家已建成！深入地下探索吧。"
    elif game.goal == "explore_cave" and game.player_y < -20:
        game.goal = "kill_spiders"
        game.message = "【目标】深入地下！狩猎蜘蛛。"

"""回合推进系统：接管原 Game.advance_turn 的所有逻辑"""
from systems.scent_map import rebuild_scent_map
from systems.monster_ai import tick_monsters, try_spawn_monster, tick_corpses
from systems.legacy_system import check_death, show_death_screen
from systems.save_manager import new_game
from systems.goal_system import check_goals


def advance_turn(game):
    """每回合推进：气味→Buff→尸体→怪物→区块→目标→死亡检查"""
    game.turn += 1

    rebuild_scent_map(game)
    game.buff_manager.tick_all(game)
    tick_corpses(game)
    tick_monsters(game)
    try_spawn_monster(game)

    if game.world:
        game.world.keep_radius(game.player_x, game.player_y, 3)

    if game.turn % 10 == 0:
        check_goals(game)

    if check_death(game):
        show_death_screen(game)
        new_game(game, inherit_world=True)

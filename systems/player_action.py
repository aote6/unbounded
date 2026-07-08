"""玩家动作系统：挖掘、放置——从 Game 类提取。"""
from world_gen import TILE_AIR
from tile_props import get_tile_props
from systems.event_bus import EventBus, EventType, GameEvent
import items as items_mod


def dig_adjacent(game, dx, dy):
    """挖掘玩家相邻方块。"""
    nx, ny = game.player_x + dx, game.player_y + dy
    if game._monster_at(nx, ny):
        game.message = "有怪物挡住了挖掘位置。"
        return

    tile = game.world.get_tile(nx, ny)["tile"]
    drop_info = items_mod.get_drop_on_mine(game.items, tile)
    if drop_info:
        game._maybe_cancel_dig(nx, ny)
        for d, c in drop_info.items():
            game._add_material(d, c)
        old_tile = game.world.get_tile(nx, ny)["tile"]
        game.world.set_tile(nx, ny, TILE_AIR)
        game.modified_tiles[(nx, ny)] = TILE_AIR
        EventBus().emit(GameEvent(EventType.TILE_CHANGED,
            {"x": nx, "y": ny, "old": old_tile, "new": TILE_AIR}), game)
        if (nx, ny) in game.corpses:
            del game.corpses[(nx, ny)]
        # 拆除箱子，回收内容
        if (nx, ny) in game.chests:
            chest = game.chests.pop((nx, ny))
            for mat, count in chest["materials"].items():
                game._add_material(mat, count)
            for inst in chest["equipment_instances"]:
                game._add_equipment_instance(inst.name, inst)
            game.message = f"拆掉了 {tile}，箱内物品已回收。"
        else:
            game.message = f"拆掉了 {tile}，回收材料。"
        game._gain_skill("digging")
    elif get_tile_props(tile)["diggable"]:
        game._dig_any_tile(nx, ny)
    else:
        game.message = "这个方块无法挖掘。"


def do_place(game):
    """在光标位置放置方块。"""
    if game.place_item_name and game.inventory.count(game.place_item_name) <= 0:
        game.message = f"背包里已经没有 {game.place_item_name} 了。"
        game.place_mode = None
        game.place_item_name = None
        return

    bx, by = game.cursor_x, game.cursor_y
    if game._monster_at(bx, by):
        game.message = "有怪物挡住了建造位置。"
        return
    if game.world.get_tile(bx, by)["tile"] != TILE_AIR:
        game.message = "这里不是空地，无法放置。"
        return

    if bx == game.player_x and by == game.player_y:
        push_order = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        pushed = False
        for pdx, pdy in push_order:
            px, py = game.player_x + pdx, game.player_y + pdy
            if (game.world.get_tile(px, py)["tile"] == TILE_AIR
                    and not game._monster_at(px, py)
                    and not game._monster_has_position(px, py)):
                game.player_x, game.player_y = px, py
                pushed = True
                break
        if not pushed:
            game.message = "玩家没有空间后退，无法在脚下放置。"
            return

    old_tile = game.world.get_tile(bx, by)["tile"]
    game.world.set_tile(bx, by, game.place_mode)
    game.modified_tiles[(bx, by)] = game.place_mode
    EventBus().emit(GameEvent(EventType.TILE_CHANGED,
        {"x": bx, "y": by, "old": old_tile, "new": game.place_mode}), game)

    game._blocks_placed_this_life += 1

    if game.place_mode == "木箱":
        game.chests[(bx, by)] = {"materials": {}, "equipment_instances": []}

    if game.place_item_name:
        game._remove_material(game.place_item_name, 1)
        if game._count_material(game.place_item_name) <= 0:
            game.message = f"放置了 {game.place_mode}（背包中已无更多，退出建造模式）"
            game.place_mode = None
            game.place_item_name = None
            return

    game.message = f"放置了 {game.place_mode}（建造模式中，c 退出）"

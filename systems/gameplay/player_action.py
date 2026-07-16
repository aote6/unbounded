
"""玩家动作系统：挖掘、放置——从 Game 类提取。"""
from systems.gameplay.goal_system import check_special_location
from tile_props import TILE_AIR, get_tile_props, get_dig_turns
from world_gen import TILE_TREE
from systems.gameplay.inventory_actions import add_equipment_instance
from systems.core.event_bus import EventBus, EventType, GameEvent
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
        _maybe_cancel_dig(game, nx, ny)
        for d, c in drop_info.items():
            game.inventory.add(d, c)
        old_tile = game.world.get_tile(nx, ny)["tile"]
        game.world.set_tile(nx, ny, TILE_AIR)
        game.modified_tiles[(nx, ny)] = TILE_AIR
        EventBus().emit(
            GameEvent(
                EventType.TILE_CHANGED, {
                    "x": nx, "y": ny, "old": old_tile, "new": TILE_AIR}), game)
        if (nx, ny) in game.corpses:
            del game.corpses[(nx, ny)]
        if (nx, ny) in game.chests:
            chest = game.chests.pop((nx, ny))
            for mat, count in chest["materials"].items():
                game.inventory.add(mat, count)
            for inst in chest["equipment_instances"]:
                add_equipment_instance(game, inst.name, inst)
            game.message = f"拆掉了 {tile}，箱内物品已回收。"
        else:
            game.message = f"拆掉了 {tile}，回收材料。"
        game._gain_skill("digging")
    elif get_tile_props(tile)["diggable"]:
        dig_any_tile(game, nx, ny)
    else:
        game.message = "这个方块无法挖掘。"

def _has_item_to_place(game):
    """检查背包里是否还有要放置的物品，没有则退出建造模式。"""
    if game.place_item_name and game.inventory.count(
            game.place_item_name) <= 0:
        game.message = f"背包里已经没有 {game.place_item_name} 了。"
        game.place_mode = None
        game.place_item_name = None
        return False
    return True


def _cursor_is_valid_for_placement(game, bx, by):
    """检查光标位置是否可以放置（无怪物、是空地）。"""
    if game._monster_at(bx, by):
        game.message = "有怪物挡住了建造位置。"
        return False
    if game.world.get_tile(bx, by)["tile"] != TILE_AIR:
        game.message = "这里不是空地，无法放置。"
        return False
    return True


def _push_player_away(game):
    """玩家要在脚下放置时，尝试把玩家推到相邻空地。"""
    push_order = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    for pdx, pdy in push_order:
        px, py = game.player_x + pdx, game.player_y + pdy
        if (game.world.get_tile(px, py)["tile"] == TILE_AIR
                and not game._monster_at(px, py)
                and not game._monster_has_position(px, py)):
            game.player_x, game.player_y = px, py
            return True
    game.message = "玩家没有空间后退，无法在脚下放置。"
    return False


def _place_tile_and_emit(game, bx, by):
    """实际写入方块、记录修改、发出 TILE_CHANGED 事件。"""
    old_tile = game.world.get_tile(bx, by)["tile"]
    game.world.set_tile(bx, by, game.place_mode)
    game.modified_tiles[(bx, by)] = game.place_mode
    EventBus().emit(
        GameEvent(
            EventType.TILE_CHANGED, {
                "x": bx, "y": by, "old": old_tile, "new": game.place_mode}), game)
    game._blocks_placed_this_life += 1


def _consume_place_item(game):
    """放置后扣减背包物品，若耗尽则退出建造模式。"""
    game.inventory.remove(game.place_item_name, 1)
    if game.inventory.count(game.place_item_name) <= 0:
        game.message = f"放置了 {game.place_mode}（背包中已无更多，退出建造模式）"
        game.place_mode = None
        game.place_item_name = None
        return False
    return True


def do_place(game):
    """在光标位置放置方块。"""
    if not _has_item_to_place(game):
        return

    bx, by = game.cursor_x, game.cursor_y
    if not _cursor_is_valid_for_placement(game, bx, by):
        return

    if bx == game.player_x and by == game.player_y:
        if not _push_player_away(game):
            return

    _place_tile_and_emit(game, bx, by)

    if game.place_mode == "木箱":
        game.chests[(bx, by)] = {"materials": {}, "equipment_instances": []}

    if game.place_item_name:
        if not _consume_place_item(game):
            return

    game.message = f"放置了 {game.place_mode}（建造模式中，c 退出）"



def dig_any_tile(game, x, y):
    """挖掘任意方块（含连续挖掘进度）。"""
    tile = game.world.get_tile(x, y)["tile"]
    props = get_tile_props(tile)
    if not props["diggable"]:
        return False

    if not (
            game.dig_progress and game.dig_progress["x"] == x and game.dig_progress["y"] == y):
        tool_power = 1 + game._best_equipped_tool_bonus("digging")
        base_turns = get_dig_turns(tile, tool_power)
        speed_bonus = game._digging_speed_bonus()
        total = max(1, base_turns - speed_bonus)
        game.dig_progress = {
            "x": x,
            "y": y,
            "remaining": total,
            "total": total}

    game.dig_progress["remaining"] -= 1
    if game.dig_progress["remaining"] <= 0:
        drop = props.get("drop")
        if drop:
            game.inventory.add(drop, 1)
            game.message = f"挖到了 {drop} x1（共 {game.inventory.count(drop)}）"
        else:
            game.message = f"挖掉了 {props['name']}。"
        old_tile = game.world.get_tile(x, y)["tile"]
        game.world.set_tile(x, y, TILE_AIR)
        game.modified_tiles[(x, y)] = TILE_AIR
        EventBus().emit(
            GameEvent(
                EventType.TILE_CHANGED, {
                    "x": x, "y": y, "old": old_tile, "new": TILE_AIR}), game)
        if (x, y) in game.corpses:
            del game.corpses[(x, y)]
        game.dig_progress = None
        game._gain_skill("digging")
    else:
        game.message = f"挖掘中...还需 {game.dig_progress['remaining']} 回合"
    return True


def _badge_position(game, nx, ny):
    """Effect badge defaults to player's right side; if that cell
    is the monster's own cell (attacking right), fall back to below
    the player instead, so the badge never sits on the monster."""
    bx, by = game.player_x + 1, game.player_y
    if (bx, by) == (nx, ny):
        bx, by = game.player_x, game.player_y + 1
    return bx, by


def try_move_or_dig(game, dx, dy):
    """尝试移动或挖掘/攻击。"""
    nx, ny = game.player_x + dx, game.player_y + dy
    tile = game.world.get_tile(nx, ny)["tile"]
    mon = game._monster_at(nx, ny)

    if game.place_mode is not None:
        game.cursor_x += dx
        game.cursor_y += dy
        game.message = f"建造光标 ({game.cursor_x},{game.cursor_y})，回车放置，c 退出。"
        return

    if mon:
        _maybe_cancel_dig(game, nx, ny)
        # 攻击交给 combat_system 处理
        from systems.combat.combat_system import kill_monster
        from config import PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX, PLAYER_BASE_HIT_CHANCE
        import random
        if random.random() < PLAYER_BASE_HIT_CHANCE:
            dmg = random.randint(
                PLAYER_BASE_DAMAGE_MIN,
                PLAYER_BASE_DAMAGE_MAX)
            dmg += game._combat_damage_bonus()
            mon["hp"] -= dmg
            game.message = f"攻击 {mon['name']}，造成 {dmg} 点伤害"
            game.effect_manager.spawn("hit_flash", nx, ny, "", duration=2)
            bx, by = _badge_position(game, nx, ny)
            game.effect_manager.spawn("slash", bx, by, "/", duration=2)
            EventBus().emit(
                GameEvent(
                    EventType.DAMAGE_DEALT, {
                        "target": mon, "damage": dmg, "attacker": "player"}), game)
            if mon["hp"] <= 0:
                kill_monster(game, mon, cause="attack")
        else:
            game.message = f"攻击 {mon['name']}，未命中！"
            bx, by = _badge_position(game, nx, ny)
            game.effect_manager.spawn("text", bx, by, "MISS", duration=2)
        return

    props = get_tile_props(tile)
    if props["passable"]:
        if tile == TILE_TREE:
            dig_any_tile(game, nx, ny)
            return
        if game._monster_has_position(nx, ny):
            return
        _maybe_cancel_dig(game, nx, ny)
        game.player_x, game.player_y = nx, ny
        check_special_location(game)
    elif props["diggable"]:
        dig_any_tile(game, nx, ny)


def _maybe_cancel_dig(game, x, y):
    """如果挖掘目标改变，取消当前进度。"""
    if game.dig_progress and (
            game.dig_progress["x"] != x or game.dig_progress["y"] != y):
        game.dig_progress = None


def sprint_move(game, dx, dy, max_steps=5):
    """连续朝一个方向移动，直到撞墙/遇怪/踏上特殊地块/达到步数上限。
    纯逻辑函数，不关心是键盘连按触发还是以后触屏点选触发。
    返回实际走的步数。
    """
    steps = 0
    while steps < max_steps:
        nx, ny = game.player_x + dx, game.player_y + dy

        if game._monster_at(nx, ny) or game._monster_has_position(nx, ny):
            break

        tile = game.world.get_tile(nx, ny)["tile"]
        props = get_tile_props(tile)
        if not props["passable"]:
            break
        if tile == TILE_TREE:
            break

        _maybe_cancel_dig(game, nx, ny)
        game.player_x, game.player_y = nx, ny
        check_special_location(game)
        steps += 1

    return steps

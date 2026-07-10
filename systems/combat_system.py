"""战斗系统：接管击杀怪物、掉落、分裂等逻辑"""
import monsters as monsters_mod
from systems.event_bus import EventBus, EventType, GameEvent
from systems.inventory_actions import add_material, add_equipment_instance, remove_monster, add_monster, get_equipment_instance
from tile_props import TILE_AIR
CORPSE_DECAY_TURNS = 100  # 尸体 decay 回合数


def kill_monster(game, monster, cause="attack"):
    """击杀怪物：掉落、尸体、分裂、消息。"""
    game._monsters_killed_this_life += 1
    mx, my = monster["x"], monster["y"]
    mname = monster["name"]

    # 发送事件
    EventBus().emit(
        GameEvent(
            EventType.MONSTER_KILLED, {
                "monster": monster, "cause": cause}), game)

    corpse_tile = monster.get("corpse_tile")
    splits = monsters_mod.get_split_spawns(monster, game.monster_data)
    drop_name, drop_obj = monsters_mod.generate_loot_for(game.player_y, mname)

    # 掉落
    if drop_name and drop_obj:
        if isinstance(drop_obj, dict) and "count" in drop_obj:
            add_material(game, drop_name, drop_obj.get("count", 1))
        else:
            add_equipment_instance(game, drop_name, drop_obj)

    # 移除怪物
    remove_monster(game, monster)

    # 放置尸体
    if corpse_tile and game.world.get_tile(mx, my)["tile"] == TILE_AIR:
        game.world.set_tile(mx, my, corpse_tile)
        game.modified_tiles[(mx, my)] = corpse_tile
        game.corpses[(mx, my)] = CORPSE_DECAY_TURNS

    # 分裂
    if splits:
        for s in splits:
            add_monster(game, s)

    # 消息
    cause_msg = {
        "attack": f"打倒了 {mname}！",
        "burn": f"{mname} 被烧死了！",
        "poison": f"{mname} 中毒身亡！",
    }.get(cause, f"{mname} 死了。")
    if splits:
        cause_msg += f"它分裂成了 {len(splits)} 只小史莱姆！"
    elif drop_name:
        cause_msg += f"掉落了 {drop_name}。"
    game.message = cause_msg


def collect_attack_effects(game):
    """收集所有装备的 on_attack 效果"""
    effects = []
    for item_name in game.equipment.values():
        inst = get_equipment_instance(game, item_name)
        if inst:
            effects.extend(inst.on_attack)
        else:
            effects.extend(game.items.get(item_name, {}).get("on_attack", []))
    return effects

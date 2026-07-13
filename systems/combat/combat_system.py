"""战斗系统：接管击杀怪物、掉落、分裂等逻辑"""
import monsters as monsters_mod
from systems.core.event_bus import EventBus, EventType, GameEvent
from systems.gameplay.inventory_actions import (
    add_material, add_equipment_instance, get_equipment_instance)
from systems.entity.monster_index import add_monster, remove_monster
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
    """收集所有已装备物品的 on_attack 效果。

    game.equipment 的槽位里存的本就是 EquipmentInstance 对象
    （或历史遗留的纯字符串，见 save_system._deserialize_equipment
    的兼容注释），不需要再反查背包。之前误把对象当字符串传给
    get_equipment_instance()，导致对象被当成 dict key 使用而崩溃。
    """
    effects = []
    for inst in game.equipment.values():
        if inst is None:
            continue
        if hasattr(inst, "on_attack"):
            effects.extend(inst.on_attack)
        elif isinstance(inst, str):
            # 兼容旧存档里可能残留的纯字符串装备记录
            effects.extend(game.items.get(inst, {}).get("on_attack", []))
    return effects

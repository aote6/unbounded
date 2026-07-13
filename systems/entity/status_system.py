"""状态系统：统一管理燃烧、中毒、吸血等状态效果。"""
from systems.core.event_bus import EventBus, EventType
from systems.entity.tag_system import check_interaction
from systems.combat.combat_system import collect_attack_effects


def _tags_of(entity):
    """获取实体的标签列表。

    Args:
        entity: The entity instance, typically a dictionary or an object.

    Returns:
        list: A list of tags associated with the entity.
    """
    if isinstance(entity, dict):
        return entity.get("tags", [])
    return []


def _player_attack_tags(game):
    """获取玩家当前主手武器的标签。

    game.equipment 槽位里存的是 EquipmentInstance 对象本身
    （或历史遗留的纯字符串），不是名字字符串，因此这里直接读取
    对象属性，不需要（也不能）再拿它当 key 去反查背包或 items。

    Args:
        game: The main game controller instance.

    Returns:
        list: A list of tags associated with the player's current weapon.
    """
    tags = []
    weapon = game.equipment.get("main_hand")
    if weapon is None:
        return tags
    if hasattr(weapon, "tags") and weapon.tags:
        tags.extend(weapon.tags)
    elif isinstance(weapon, str) and weapon in game.items:
        # 兼容旧存档里可能残留的纯字符串装备记录
        tags.extend(game.items[weapon].get("tags", []))
    return tags


def _on_damage_dealt(event, game):
    """DAMAGE_DEALT: 施加装备特效 + 标签交互。

    Args:
        event: The GameEvent instance containing damage data.
        game: The main game controller instance.
    """
    target = event.data.get("target")
    damage = event.data.get("damage", 0)
    attacker = event.data.get("attacker")
    if not target:
        return

    bm = game.buff_manager

    effects = collect_attack_effects(game)
    for effect in effects:
        if effect == "fire":
            bm.add(target, "burning", duration=3, damage_per_turn=2, source="fire")
        elif effect == "poison":
            bm.add(target, "poisoned", duration=5, damage_per_turn=1, source="poison")

    source_tags = _player_attack_tags(game) if attacker == "player" else _tags_of(attacker)
    target_tags = _tags_of(target)
    for rule in check_interaction(source_tags, target_tags):
        if rule["effect"] == "apply_burning":
            duration = rule.get("duration", 3)
            dpt = rule.get("damage_per_turn", 2)
            bm.add(target, "burning", duration=duration, damage_per_turn=dpt, source="fire")
            game.message = f"{target.get('name', '目标')} 燃烧起来了！"

    if attacker == "player" and damage > 0:
        lifesteal_total = 0
        for inst in game.equipment.values():
            if inst is None:
                continue
            lifesteal_total += getattr(inst, "lifesteal", 0)
        if lifesteal_total > 0:
            heal = min(lifesteal_total, damage)
            game.player_hp = min(game.player_max_hp, game.player_hp + heal)


def _on_turn_start(event, game):
    """TURN_START: 委托给 BuffManager 处理所有实体状态。

    Args:
        event: The GameEvent instance triggering the start of a turn.
        game: The main game controller instance.
    """
    pass


def _on_monster_killed(event, game):
    """MONSTER_KILLED: 清理死亡实体的 Buff。

    Args:
        event: The GameEvent instance containing killed monster data.
        game: The main game controller instance.
    """
    monster = event.data.get("monster")
    if monster and hasattr(game, 'buff_manager'):
        game.buff_manager.remove_entity(monster)


def register():
    """Register all status system event handlers to the global EventBus."""
    bus = EventBus()
    bus.subscribe(EventType.TURN_START, _on_turn_start)
    bus.subscribe(EventType.DAMAGE_DEALT, _on_damage_dealt)
    bus.subscribe(EventType.MONSTER_KILLED, _on_monster_killed)

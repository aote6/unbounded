"""战斗效果系统：监听事件总线，处理状态效果、吸血等。"""
from systems.event_bus import EventBus, EventType, GameEvent


def register_combat_handlers():
    """注册所有战斗相关的事件处理器。"""
    bus = EventBus()
    bus.subscribe(EventType.DAMAGE_DEALT, _handle_status_effects)
    bus.subscribe(EventType.DAMAGE_DEALT, _handle_lifesteal)
    bus.subscribe(EventType.MONSTER_KILLED, _handle_on_kill)


def _handle_status_effects(event: GameEvent, game):
    """造成伤害时，施加装备上的状态效果（燃烧/中毒）。"""
    effects = game._collect_attack_effects()
    target = event.data.get("target")
    if not target:
        return
    for effect in effects:
        if effect == "fire":
            target["on_fire"] = 3
        elif effect == "poison":
            target["poisoned"] = 5


def _handle_lifesteal(event: GameEvent, game):
    """造成伤害时，计算吸血回复。"""
    dmg = event.data.get("damage", 0)
    if dmg <= 0:
        return
    lifesteal_total = 0
    for item_name in game.equipment.values():
        lifesteal_total += game._get_item_attr(item_name, "lifesteal")
    if lifesteal_total > 0:
        heal = min(lifesteal_total, dmg)
        game.player_hp = min(game.player_max_hp, game.player_hp + heal)


def _handle_on_kill(event: GameEvent, game):
    """怪物死亡时，可以做额外处理（如触发装备特效）。"""
    pass  # 预留，等有 on_kill 效果的装备时再实现

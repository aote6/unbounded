"""状态系统：统一管理燃烧、中毒、吸血等状态效果。
监听事件总线，替代 _attack_monster 和 _tick_status_effects 中的硬编码逻辑。

M21 重构：通过 BuffManager 施加 Buff，不再直接修改实体字典。
"""
from systems.event_bus import EventBus, EventType
from systems.tag_system import check_interaction


# ═══════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════

def _tags_of(entity):
    """获取实体的标签列表。"""
    if isinstance(entity, dict):
        return entity.get("tags", [])
    return []


def _player_attack_tags(game):
    """获取玩家当前攻击的标签。优先从装备实例读，回退到 items.json。"""
    tags = []
    weapon_name = game.equipment.get("main_hand")
    if not weapon_name:
        return tags
    # 优先从装备实例读 tags（新系统）
    inst = game._get_equipment_instance(weapon_name)
    if inst and hasattr(inst, 'tags') and inst.tags:
        tags.extend(inst.tags)
    # 回退到 items.json（旧存档兼容）
    elif weapon_name in game.items:
        tags.extend(game.items[weapon_name].get("tags", []))
    return tags


# ═══════════════════════════════════════════════
# 伤害事件处理器
# ═══════════════════════════════════════════════

def _on_damage_dealt(event, game):
    """DAMAGE_DEALT: 施加装备特效 + 标签交互。"""
    target = event.data.get("target")
    damage = event.data.get("damage", 0)
    attacker = event.data.get("attacker")
    if not target:
        return

    bm = game.buff_manager

    # ── 装备特效（燃烧/中毒）──
    effects = game._collect_attack_effects()
    for effect in effects:
        if effect == "fire":
            bm.add(target, "burning", duration=3, damage_per_turn=2, source="fire")
        elif effect == "poison":
            bm.add(target, "poisoned", duration=5, damage_per_turn=1, source="poison")

    # ── 标签交互（规则矩阵）──
    source_tags = _player_attack_tags(game) if attacker == "player" else _tags_of(attacker)
    target_tags = _tags_of(target)
    for rule in check_interaction(source_tags, target_tags):
        if rule["effect"] == "apply_burning":
            duration = rule.get("duration", 3)
            dpt = rule.get("damage_per_turn", 2)
            bm.add(target, "burning", duration=duration, damage_per_turn=dpt, source="fire")
            game.message = f"{target.get('name', '目标')}  燃烧起来了！"

    # ── 吸血（仅玩家攻击时触发）──
    if attacker == "player" and damage > 0:
        lifesteal_total = 0
        for item_name in game.equipment.values():
            lifesteal_total += game._get_item_attr(item_name, "lifesteal")
        if lifesteal_total > 0:
            heal = min(lifesteal_total, damage)
            game.player_hp = min(game.player_max_hp, game.player_hp + heal)


# ═══════════════════════════════════════════════
# 回合开始事件处理器
# ═══════════════════════════════════════════════

def _on_turn_start(event, game):
    """TURN_START: 委托给 BuffManager 处理所有实体状态。
    
    M21: 不再直接遍历怪物字典，改为调用 buff_manager.tick_all()。
    该调用已整合到 advance_turn 中，此处保留为事件钩子占位。
    """
    # Buff tick 已由 advance_turn → buff_manager.tick_all() 统一处理
    pass


# ═══════════════════════════════════════════════
# 怪物死亡事件处理器
# ═══════════════════════════════════════════════

def _on_monster_killed(event, game):
    """MONSTER_KILLED: 清理死亡实体的 Buff。"""
    monster = event.data.get("monster")
    if monster and hasattr(game, 'buff_manager'):
        game.buff_manager.remove_entity(monster)


# ═══════════════════════════════════════════════
# 注册
# ═══════════════════════════════════════════════

def register():
    bus = EventBus()
    bus.subscribe(EventType.TURN_START, _on_turn_start)
    bus.subscribe(EventType.DAMAGE_DEALT, _on_damage_dealt)
    bus.subscribe(EventType.MONSTER_KILLED, _on_monster_killed)

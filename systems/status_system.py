"""状态系统：统一管理燃烧、中毒、吸血等状态效果。
监听事件总线，替代 _attack_monster 和 _tick_status_effects 中的硬编码逻辑。
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
    """获取玩家当前攻击的标签。"""
    tags = []
    weapon = game.equipment.get("main_hand")
    if weapon and weapon in game.items:
        tags.extend(game.items[weapon].get("tags", []))
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

    # ── 装备特效（燃烧/中毒）──
    effects = game._collect_attack_effects()
    for effect in effects:
        if effect == "fire":
            target["burning"] = {"duration": 3, "damage_per_turn": 2}
        elif effect == "poison":
            target["poisoned"] = 5

    # ── 标签交互（规则矩阵）──
    source_tags = _player_attack_tags(game) if attacker == "player" else _tags_of(attacker)
    target_tags = _tags_of(target)
    for rule in check_interaction(source_tags, target_tags):
        if rule["effect"] == "apply_burning":
            duration = rule.get("duration", 3)
            dpt = rule.get("damage_per_turn", 2)
            target["burning"] = {"duration": duration, "damage_per_turn": dpt}
            game.message = f"{target.get('name', '目标')} 燃烧起来了！"

    # ── 吸血 ──
    if damage > 0:
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
    """TURN_START: 处理所有实体的持续状态伤害。"""
    for m in list(game.monsters):
        # 燃烧
        burn = m.get("burning")
        if burn and burn.get("duration", 0) > 0:
            m["hp"] -= burn.get("damage_per_turn", 2)
            burn["duration"] -= 1
            if burn["duration"] <= 0:
                del m["burning"]
            if m["hp"] <= 0:
                game._kill_monster(m, cause="burn")
                continue

        # 中毒
        if m.get("poisoned", 0) > 0:
            m["hp"] -= 1
            m["poisoned"] -= 1
            if m["hp"] <= 0:
                game._kill_monster(m, cause="poison")


# ═══════════════════════════════════════════════
# 怪物死亡事件处理器
# ═══════════════════════════════════════════════

def _on_monster_killed(event, game):
    """MONSTER_KILLED: 预留，等有 on_kill 效果的装备时实现。"""
    pass


# ═══════════════════════════════════════════════
# 注册
# ═══════════════════════════════════════════════

def register():
    bus = EventBus()
    bus.subscribe(EventType.TURN_START, _on_turn_start)
    bus.subscribe(EventType.DAMAGE_DEALT, _on_damage_dealt)
    bus.subscribe(EventType.MONSTER_KILLED, _on_monster_killed)

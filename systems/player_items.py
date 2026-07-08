"""玩家物品操作：材料、装备实例、装备槽加成。"""
from equipment import EquipmentInstance
from inventory import ItemCategory


def add_equipment_instance(game, name, instance_data=None):
    """添加一个装备实例到背包。"""
    if instance_data is None:
        item_data = game.items.get(name, {})
        inst = EquipmentInstance(
            name=name,
            slot=item_data.get("slot"),
            attack_bonus=item_data.get("attack_bonus", 0),
            defense_bonus=item_data.get("defense_bonus", 0),
            tool_bonus=item_data.get("tool_bonus", 0),
            damage_min=item_data.get("damage_min", 0),
            damage_max=item_data.get("damage_max", 0),
            hit_bonus=item_data.get("hit_bonus", 0),
            affixes=item_data.get("affixes", []),
            on_attack=item_data.get("on_attack", []),
            lifesteal=item_data.get("lifesteal", 0),
            speed_bonus=item_data.get("speed_bonus", 0),
        )
    elif isinstance(instance_data, EquipmentInstance):
        inst = instance_data
    else:
        inst = EquipmentInstance.from_dict(instance_data)
    game.inventory.add(name, item_type=ItemCategory.EQUIPMENT, instance=inst)


def get_equipment_instance(game, name):
    """从背包查找装备实例。"""
    for item_id, item in game.inventory.all_items():
        if item.item_type == ItemCategory.EQUIPMENT and item.instance and item.instance.name == name:
            return item.instance
    return None


def count_equipment(game, name):
    """统计背包中某装备数量。"""
    return sum(1 for _, item in game.inventory.all_items()
               if item.item_type == ItemCategory.EQUIPMENT and item.instance and item.instance.name == name)


def get_item_attr(game, item_name, field_name):
    """获取装备属性，优先从装备槽查找。"""
    for inst in game.equipment.values():
        if inst and inst.name == item_name:
            return getattr(inst, field_name, 0)
    inst = get_equipment_instance(game, item_name)
    if inst:
        return getattr(inst, field_name, 0)
    return 0


def equipment_bonus(game, field_name):
    """从装备槽实例直接读取属性总和。"""
    total = 0
    for inst in game.equipment.values():
        if inst is None:
            continue
        if field_name == "attack_bonus":
            dmg_min = getattr(inst, "damage_min", 0)
            dmg_max = getattr(inst, "damage_max", 0)
            if dmg_max > 0:
                total += (dmg_min + dmg_max) // 2
            else:
                total += getattr(inst, "attack_bonus", 0)
        else:
            total += getattr(inst, field_name, 0)
    return total


def best_equipped_tool_bonus(game):
    """获取装备中最高工具加成。"""
    best = 0
    for item_name in game.equipment.values():
        inst = get_equipment_instance(game, item_name)
        if inst:
            best = max(best, inst.tool_bonus)
        else:
            best = max(best, game.items.get(item_name, {}).get("tool_bonus", 0))
    return best


def collect_attack_effects(game):
    """收集所有装备的攻击效果。"""
    effects = []
    for item_name in game.equipment.values():
        inst = get_equipment_instance(game, item_name)
        if inst:
            effects.extend(inst.on_attack)
        else:
            effects.extend(game.items.get(item_name, {}).get("on_attack", []))
    return effects

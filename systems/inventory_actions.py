"""物品与怪物操作函数。所有函数接收 game 作为第一参数，不依赖 Game 类。"""
from equipment import EquipmentInstance
from inventory import ItemCategory


# ═══════════════════════════════════
# 材料操作
# ═══════════════════════════════════

def count_material(game, name):
    return game.inventory.count(name)


def add_material(game, name, count):
    game.inventory.add(name, count)


def remove_material(game, name, count):
    game.inventory.remove(name, count)


# ═══════════════════════════════════
# 装备实例操作
# ═══════════════════════════════════

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
    for _, item in game.inventory.all_items():
        if item.item_type == ItemCategory.EQUIPMENT and item.instance and item.instance.name == name:
            return item.instance
    return None


def count_equipment(game, name):
    return sum(1 for _, item in game.inventory.all_items() if item.item_type ==
               ItemCategory.EQUIPMENT and item.instance and item.instance.name == name)


def get_item_attr(game, item_name, field_name):
    """获取装备实例的属性，兼容旧 items dict。"""
    inst = get_equipment_instance(game, item_name)
    if inst:
        return getattr(inst, field_name, 0)
    return game.items.get(item_name, {}).get(field_name, 0)


# ═══════════════════════════════════
# 怪物空间索引
# ═══════════════════════════════════

def build_monster_index(game):
    """全量重建空间索引（仅在读档/新游戏时调用）。"""
    game._monster_index = {(m["x"], m["y"]): m for m in game.monsters}


def monster_moved(game, monster, old_x, old_y):
    """怪物移动后更新索引。"""
    game._monster_index.pop((old_x, old_y), None)
    game._monster_index[(monster["x"], monster["y"])] = monster


def add_monster(game, monster):
    """添加怪物并更新索引。"""
    game.monsters.append(monster)
    game._monster_index[(monster["x"], monster["y"])] = monster


def remove_monster(game, monster):
    """移除怪物并更新索引。"""
    if monster in game.monsters:
        game.monsters.remove(monster)
    game._monster_index.pop((monster["x"], monster["y"]), None)

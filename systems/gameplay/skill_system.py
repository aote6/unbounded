"""技能系统：经验、升级、加成。"""

SKILL_LEVEL_THRESHOLD = 10
SKILL_NAMES_CN = {"digging": "挖掘", "combat": "战斗", "defense": "防御"}


def gain_skill(game, name, amount=1):
    """增加技能经验，达到阈值时升级并提示。"""
    game.skills[name] = game.skills.get(name, 0) + amount
    if game.skills[name] >= game.skill_levels[name] * SKILL_LEVEL_THRESHOLD:
        game.skill_levels[name] += 1


def best_equipped_tool_bonus(game, tool_type):
    """获取装备中指定类型工具的最高加成。"""
    best = 0
    for inst in game.equipment.values():
        if inst and hasattr(inst, "tool_bonus") and tool_type in getattr(inst, "tags", []):
            best = max(best, inst.tool_bonus or 0)
    return best


def digging_speed_bonus(game):
    """获取当前装备提供的挖掘速度加成。

    Args:
        game: The current game state object.

    Returns:
        The best digging tool bonus among all equipped items.
    """
    return best_equipped_tool_bonus(game, "digging")


def combat_damage_bonus(game):
    """获取当前战斗伤害加成。

    Args:
        game: The current game state object.

    Returns:
        The combined attack bonus from equipment and combat skill level.
    """
    return game.player.equipment_bonus("attack_bonus") + (game.skills.get("combat", 0) // 3)


def defense_bonus(game):
    """获取当前防御加成。

    Args:
        game: The current game state object.

    Returns:
        The combined defense bonus from equipment and defense skill level.
    """
    return game.player.equipment_bonus("defense_bonus") + (game.skills.get("defense", 0) // 3)

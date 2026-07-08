"""技能系统：经验、升级、加成。"""

SKILL_LEVEL_THRESHOLD = 10

SKILL_NAMES_CN = {"digging": "挖掘", "combat": "战斗", "defense": "防御"}


def gain_skill(game, skill_name):
    """增加技能经验，检查升级。"""
    game.skills[skill_name] += 1
    if game.skills[skill_name] >= game.skill_levels[skill_name] * SKILL_LEVEL_THRESHOLD:
        game.skill_levels[skill_name] += 1
        game.message = f"【{SKILL_NAMES_CN[skill_name]}】升到了 {game.skill_levels[skill_name]} 级！"


def digging_speed_bonus(skill_levels):
    return (skill_levels["digging"] - 1) // 10


def combat_damage_bonus(skill_levels):
    return (skill_levels["combat"] - 1) // 10


def defense_reduction(skill_levels):
    return (skill_levels["defense"] - 1) // 10

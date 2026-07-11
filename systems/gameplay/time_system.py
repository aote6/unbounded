"""时间与地质系统。"""
from config import DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START


def get_time_of_day(turn):
    """根据回合数返回 (时段名, 环境光等级)。"""
    t = turn % DAY_LENGTH
    if DAWN_START <= t < DAY_START:
        return "黎明", 4
    elif DAY_START <= t < DUSK_START:
        return "白天", 9
    elif DUSK_START <= t < NIGHT_START:
        return "黄昏", 4
    else:
        return "夜晚", 1


def get_geology_zone(y):
    """根据 y 坐标返回地质层名称。"""
    if y > -8:
        return "地表沉积层"
    elif y > -25:
        return "浅层沉积岩"
    elif y > -45:
        return "热液矿脉带"
    elif y > -70:
        return "岩浆侵入带"
    else:
        return "深部变质基底"

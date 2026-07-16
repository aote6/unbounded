"""目标系统 — Goal → Behavior → Action 架构。

Goal:     玩家当前追求的目标（数据驱动，不硬编码条件）
Behavior: Goal 分解为可执行的行为序列
Action:   Behavior 产出的具体操作

不再使用 if-elif-elif 线性推进，改为：
1. 检查当前 Goal 的完成条件
2. 完成 → 查找下一个 Goal
3. 未完成 → 当前 Goal 的 Behavior 提供指引
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
GOAL_FILE = BASE_DIR / "data" / "goals.json"

_GOALS_CACHE = None


def _load_goals():
    global _GOALS_CACHE
    if _GOALS_CACHE is not None:
        return _GOALS_CACHE
    if GOAL_FILE.exists():
        with open(GOAL_FILE, "r", encoding="utf-8") as f:
            _GOALS_CACHE = json.load(f)
    else:
        _GOALS_CACHE = []
    return _GOALS_CACHE


def check_goals(game):
    """每回合检查：当前目标是否完成，推进到下一目标。"""
    goals = _load_goals()
    if not goals:
        return

    current = _find_goal(goals, game.goal)
    if current is None:
        return

    # 检查完成条件
    if _evaluate_condition(current.get("complete_if", {}), game):
        # 推进到下一个目标
        next_id = current.get("next")
        if next_id:
            next_goal = _find_goal(goals, next_id)
            if next_goal:
                game.goal = next_id
                game.narration = f"【目标】{next_goal.get('complete_msg', '新目标！')}"
                game.goal_message_shown = False


def _find_goal(goals, goal_id):
    for g in goals:
        if g["id"] == goal_id:
            return g
    return None


def _evaluate_condition(condition, game):
    """评估完成条件。支持的检查类型：
    - player_y_below: int  → 玩家 Y 坐标低于此值
    - turns_played: int    → 游戏回合数超过此值
    - monsters_killed: int → 击杀数
    - has_item: str        → 背包中有此物品
    - room_built: bool     → 建造了房间
    """
    if not condition:
        return False

    for key, value in condition.items():
        if key == "player_y_below":
            if game.player_y >= value:
                return False
        elif key == "turns_played":
            if game.turn < value:
                return False
        elif key == "monsters_killed":
            if game.life_stats.monsters_killed < value:
                return False
        elif key == "has_item":
            if game.inventory.count(value) == 0:
                return False
        elif key == "room_built":
            if not _simple_room_check(game):
                return False
        else:
            # 未知条件类型，默认不满足
            return False
    return True


def check_special_location(game):
    """检测玩家是否进入特殊地貌（Feature 系统将来会接管此功能）。"""
    if not hasattr(game.world, 'special_locations'):
        return
    for x, y, name in game.world.special_locations:
        if abs(game.player_x - x) <= 6 and abs(game.player_y - y) <= 6:
            if not hasattr(game, '_found_specials'):
                game._found_specials = set()
            if (x, y) not in game._found_specials:
                game._found_specials.add((x, y))
                game.narration = f"🔍 你发现了【{name}】！这里似乎有稀有资源..."
                loot_tables = {
                    "废弃矿洞": {"铁矿石": 10, "石头": 20},
                    "蜘蛛巢穴": {"蜘蛛丝": 15},
                    "水晶洞穴": {"钻石原石": 3, "玻璃": 8},
                    "地下湖": {"沙子": 15},
                    "远古遗迹": {"金矿石": 5, "大理石": 10},
                    "蘑菇洞": {"黏土": 20},
                    "硫磺温泉": {"硫磺": 10},
                }
                loot = loot_tables.get(name, {})
                for item, count in loot.items():
                    game.inventory.add(item, count)
                game.narration += f" 获得: {
                    ', '.join(
                        f'{c}x{k}' for k,
                        c in loot.items())}"
            break


def _simple_room_check(game):
    """简化版房间检测：周围10格内非空气方块>=5"""
    count = 0
    for dx in range(-10, 11, 2):
        for dy in range(-10, 11, 2):
            tile = game.world.get_tile(game.player_x + dx, game.player_y + dy)
            if tile and tile.get("tile", 0) != 0:
                count += 1
    return count >= 5

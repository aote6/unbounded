"""目标系统：进度推进 + 特殊地点检测。"""


def check_goals(game):
    """根据玩家进度推进目标。"""
    if game.goal == "build_first_room" and _simple_room_check(game):
        game.goal = "explore_cave"
        game.message = "【目标】家已建成！深入地下探索吧。"
    elif game.goal == "explore_cave" and game.player_y < -20:
        game.goal = "kill_spiders"
        game.message = "【目标】你进入了深层地下！狩猎怪物收集稀有材料。"
    elif game.goal == "kill_spiders" and game.turn > 500:
        game.goal = "build_luxury"
        game.message = "【目标】收集了足够的材料，建造豪华基地吧！"


def check_special_location(game):
    """检测玩家是否进入特殊地貌。"""
    if not hasattr(game.world, 'special_locations'):
        return
    for x, y, name in game.world.special_locations:
        if abs(game.player_x - x) <= 6 and abs(game.player_y - y) <= 6:
            if not hasattr(game, '_found_specials'):
                game._found_specials = set()
            if (x, y) not in game._found_specials:
                game._found_specials.add((x, y))
                game.message = f"🔍 你发现了【{name}】！这里似乎有稀有资源..."
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
                game.message += f" 获得: {', '.join(f'{c}x{k}' for k,c in loot.items())}"
            break


def _simple_room_check(game):
    """简化版房间检测：周围10格内墙壁数量>=5视为有房间"""
    count = 0
    for dx in range(-10, 11, 2):
        for dy in range(-10, 11, 2):
            tile = game.world.get_tile(game.player_x + dx, game.player_y + dy)
            if tile and tile.get("tile", 0) != 0:  # 非空气
                count += 1
    return count >= 5

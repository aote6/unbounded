"""交互系统：统一处理"站旁边按按键"类操作。当前支持箱子存取，后续扩展门/开关/NPC对话。"""
import curses


def get_nearby_chest(game):
    """检查玩家四周是否有箱子，返回坐标或 None"""
    for dx, dy in [(0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,-1),(-1,1),(1,1)]:
        cx, cy = game.player_x + dx, game.player_y + dy
        if (cx, cy) in game.chests:
            return (cx, cy)
    return None



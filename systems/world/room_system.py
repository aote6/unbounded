
"""房间检测系统：从 Game 类提取。"""
from world_gen import TILE_AIR
from tile_props import get_tile_props

def _flood_fill_room(game, start_x, start_y):
    """从起点做 flood fill，返回 (tiles, is_enclosed)；超出步数上限返回 None。"""
    visited = set()
    stack = [(start_x, start_y)]
    tiles = []
    is_enclosed = True
    max_steps = 500
    steps = 0

    while stack and steps < max_steps:
        x, y = stack.pop()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        steps += 1

        tile = game.world.get_tile(x, y)["tile"]
        props = get_tile_props(tile)
        if tile == TILE_AIR:
            tiles.append((x, y))
        elif props.get("passable", False):
            tiles.append((x, y))
        else:
            continue

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1),
                       (-1, -1), (1, -1), (-1, 1), (1, 1)]:
            nx, ny = x + dx, y + dy
            if (nx, ny) not in visited:
                if abs(nx - start_x) > 25 or abs(ny - start_y) > 25:
                    is_enclosed = False
                stack.append((nx, ny))

    if steps >= max_steps:
        return None

    return tiles, is_enclosed

def _scan_room_boundary(game, tiles):
    """扫描房间格子的四邻，判断是否存在门/墙。"""
    has_door = False
    has_wall = False
    for x, y in tiles:
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            adj = game.world.get_tile(x + dx, y + dy)["tile"]
            adj_props = get_tile_props(adj)
            if "door" in adj_props.get("tags", []):
                has_door = True
            if "wall" in adj_props.get("tags", []):
                has_wall = True
    return has_door, has_wall


def detect_room(game, start_x, start_y):
    """Flood fill 检测封闭房间。"""
    if game.world.get_tile(start_x, start_y)["tile"] != TILE_AIR:
        return None

    fill_result = _flood_fill_room(game, start_x, start_y)
    if fill_result is None:
        return None
    tiles, is_enclosed = fill_result

    if not is_enclosed or len(tiles) < 4:
        return None

    has_door, has_wall = _scan_room_boundary(game, tiles)

    return {
        "tiles": tiles,
        "size": len(tiles),
        "is_enclosed": is_enclosed,
        "has_door": has_door,
        "has_wall": has_wall,
    }



def check_room_formation(game):
    """检测玩家周围是否形成封闭房间。"""
    room = detect_room(game, game.player_x, game.player_y)
    if room:
        size = room["size"]
        if room["has_door"] and room["has_wall"] and size >= 6:
            game.message = f"检测到完整房间！面积 {size} 格。"
        elif size >= 4:
            game.message = f"检测到封闭空间，面积 {size} 格。"


def count_rooms_nearby(game):
    """统计附近的房间数量。"""
    count = 0
    for dx in range(-20, 21, 5):
        for dy in range(-20, 21, 5):
            room = detect_room(game, game.player_x + dx, game.player_y + dy)
            if room and room.get("has_door"):
                count += 1
    return count

"""气味地图系统 - Dijkstra 气味场，替代贪心寻路"""

from collections import deque
from tile_props import get_tile_props


# 8方向偏移（含对角线）
DIRS_8 = [
    (0, -1), (0, 1), (-1, 0), (1, 0),
    (-1, -1), (1, -1), (-1, 1), (1, 1),
]


class ScentMap:
    """玩家气味扩散场。每回合重建，怪物查询 O(1)。"""

    def __init__(self, max_range=15):
        self.max_range = max_range
        self._grid = {}          # {(x,y): scent_value}
        self._player_pos = None

    def build(self, world, player_x, player_y, monster_index):
        """从玩家位置 BFS 扩散气味。墙壁阻断扩散，怪物位置可通行但不产生气味。"""
        self._grid.clear()
        self._player_pos = (player_x, player_y)

        # BFS 队列：(x, y, value)
        queue = deque()
        queue.append((player_x, player_y, self.max_range))
        self._grid[(player_x, player_y)] = self.max_range
        visited = {(player_x, player_y)}

        while queue:
            x, y, val = queue.popleft()
            next_val = val - 1
            if next_val <= 0:
                continue

            for dx, dy in DIRS_8:
                nx, ny = x + dx, y + dy
                if (nx, ny) in visited:
                    continue
                if abs(
                        nx -
                        player_x) > self.max_range or abs(
                        ny -
                        player_y) > self.max_range:
                    continue

                tile = world.get_tile(nx, ny)["tile"]
                props = get_tile_props(tile)
                if not props["passable"]:
                    continue

                # 怪物位置：可通过但不继续扩散（怪物身体阻断气味传播）
                if (nx, ny) in monster_index:
                    self._grid[(nx, ny)] = next_val
                    visited.add((nx, ny))
                    continue

                visited.add((nx, ny))
                self._grid[(nx, ny)] = next_val
                queue.append((nx, ny, next_val))

    def get_scent(self, x, y):
        """获取指定坐标的气味值。越近越高。"""
        return self._grid.get((x, y), 0)

    def best_direction(self, mx, my):
        """怪物查询：周围 8 格中气味值最高的方向。返回 (dx, dy) 或 (0,0)。"""
        best_val = -1
        best_dir = (0, 0)
        for dx, dy in DIRS_8:
            nx, ny = mx + dx, my + dy
            val = self._grid.get((nx, ny), 0)
            if val > best_val:
                best_val = val
                best_dir = (dx, dy)
        return best_dir


# 全局单例
_scent_map = None


def get_scent_map():
    global _scent_map
    if _scent_map is None:
        _scent_map = ScentMap()
    return _scent_map


def rebuild_scent_map(game):
    """每回合重建气味地图。"""
    sm = get_scent_map()
    sm.build(game.world, game.player_x, game.player_y, game._monster_index)


def scent_best_direction(mx, my):
    """怪物查询最佳移动方向。"""
    return get_scent_map().best_direction(mx, my)

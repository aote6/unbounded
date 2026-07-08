"""怪物空间索引：O(1) 查找。"""


def build_monster_index(game):
    """全量重建空间索引。"""
    game._monster_index = {(m["x"], m["y"]): m for m in game.monsters}


def monster_at(game, x, y):
    """O(1) 查找指定坐标的怪物。"""
    return game._monster_index.get((x, y))


def monster_has_position(game, x, y):
    """检查坐标是否有怪物占用。"""
    return (x, y) in game._monster_index


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

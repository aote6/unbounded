"""疾走(sprint_move)回归测试，无需打开游戏，几秒出结果。"""
import sys
sys.path.insert(0, '.')
import main
from systems.gameplay.player_action import sprint_move


class FakeWorld:
    def __init__(self):
        self.seed = 1
        self.special_locations = []

    def get_tile(self, x, y):
        return {"tile": 0, "passable": True}

    def keep_radius(self, *a):
        pass


def run():
    g = main.Game()
    g.new_game()
    g.world = FakeWorld()
    g.monsters = []
    g._monster_at = lambda x, y: None
    g._monster_has_position = lambda x, y: False
    start_x, start_y = g.player_x, g.player_y
    steps = sprint_move(g, 1, 0, max_steps=5)
    end_x, end_y = g.player_x, g.player_y
    moved = end_x - start_x
    print("steps返回值:", steps)
    print("实际x位移:", moved)
    if steps == moved:
        print("PASS: steps与实际位移一致，sprint_move本身没问题")
    else:
        print("FAIL: steps=" + str(steps) + " 但实际位移=" + str(moved) + "，bug在sprint_move内部")


run()

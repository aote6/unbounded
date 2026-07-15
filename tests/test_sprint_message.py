"""疾走后HUD消息是否正确清除的回归测试。"""
import sys
sys.path.insert(0, '.')
import main
from config import DIRECTIONS, KEY_SPRINT
from ui.states.play_state import PlayState


class FakeWorld:
    def __init__(self):
        self.seed = 1
        self.special_locations = []

    def get_tile(self, x, y):
        return {"tile": 0, "passable": True}

    def keep_radius(self, *a):
        pass


class FakeEngine:
    def __init__(self):
        self._running = True

    def pop_state(self):
        pass

    def push_state(self, s):
        pass


def run():
    g = main.Game()
    g.new_game()
    g.world = FakeWorld()
    g.monsters = []
    g._monster_at = lambda x, y: None
    g._monster_has_position = lambda x, y: False
    g.engine = FakeEngine()

    state = PlayState(g)
    dir_key = next(iter(DIRECTIONS))

    state.handle_input(KEY_SPRINT)
    state.handle_input(dir_key)
    sprint_message = g.message
    print("疾走后message:", sprint_message)

    start_x, start_y = g.player_x, g.player_y
    state.handle_input(dir_key)
    end_x, end_y = g.player_x, g.player_y
    moved = abs(end_x - start_x) + abs(end_y - start_y)
    normal_message = g.message
    print("普通移动后位移:", moved)
    print("普通移动后message:", normal_message)

    if moved == 1 and normal_message == sprint_message:
        print("FAIL: 实际只走1步，但HUD仍显示上次疾走的消息，确认是显示未清除的bug")
    elif moved == 1 and normal_message != sprint_message:
        print("PASS: 消息已正确更新，不是这个bug")
    else:
        print("异常: moved=" + str(moved) + "，需要人工看一下")


run()

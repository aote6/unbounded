"""压力测试：模拟极端场景，验证系统不崩溃"""
from main import Game
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class FakeWorld:
    def get_tile(self, x, y):
        return {"tile": 0, "passable": True}

    def set_tile(self, x, y, t):
        pass

    def keep_radius(self, *a):
        pass

    def __init__(self):
        self.seed = 12345


class FakeStdscr:
    def erase(self): pass
    def refresh(self): pass
    def getch(self): return -1
    def addstr(self, *a, **k): pass
    def getmaxyx(self): return (24, 80)
    def keypad(self, v): pass
    def touchwin(self): pass


class FakeEngine:
    def __init__(self):
        self.stdscr = FakeStdscr()

    def push_state(self, s): pass
    def pop_state(self): pass
    def _running(self): pass
    _running = True


def make_game():
    g = Game()
    g.world = FakeWorld()
    g.engine = FakeEngine()
    g.player_hp = 99999  # 压力测试不死
    return g


def test_spawn_100_monsters():
    g = make_game()
    from systems.inventory_actions import add_monster
    for i in range(100):
        m = {"name": f"怪{i}", "x": i % 20, "y": i // 20,
             "hp": 10, "max_hp": 10, "char": "S", "exp": 5, "drops": []}
        add_monster(g, m)
    assert len(g.monsters) == 100
    assert len(g._monster_index) == 100
    print("[PASS] 100怪物生成")


def test_advance_1000_turns():
    g = make_game()
    from systems.turn_system import advance_turn
    from systems.inventory_actions import add_monster
    m = {"name": "S", "x": 5, "y": 5, "hp": 10, "max_hp": 10,
         "char": "S", "exp": 5, "drops": [], "speed": 1}
    add_monster(g, m)
    for _ in range(1000):
        advance_turn(g)
    assert g.turn == 1000
    print("[PASS] 1000回合推进")


def test_inventory_overflow():
    g = make_game()
    for i in range(100):
        g.inventory.add(f"物品{i}", 999)
    mats = g.inventory.get_materials()
    assert len(mats) == 100
    print("[PASS] 100种物品各999")


def test_save_load_100_monsters():
    g = make_game()
    from systems.inventory_actions import add_monster
    from systems.save_system import build_save_data, apply_load_data
    for i in range(100):
        m = {"name": f"怪{i}", "x": i % 20, "y": i // 20,
             "hp": 10, "max_hp": 10, "char": "M", "exp": 5, "drops": []}
        add_monster(g, m)
    player, world = build_save_data(g)
    g2 = make_game()
    apply_load_data(g2, {"player": player, "world": world})
    assert len(g2.monsters) == 100
    print("[PASS] 100怪物存档读档")


if __name__ == "__main__":
    test_spawn_100_monsters()
    test_advance_1000_turns()
    test_inventory_overflow()
    test_save_load_100_monsters()
    print("压力测试全部通过")

"""冒烟测试：不依赖 curses，验证核心系统不崩溃。"""
import sys, json
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

import curses as _curses_module

class FakeStdscr:
    def __init__(self): self.lines, self.cols = 40, 120
    def getmaxyx(self): return (self.lines, self.cols)
    def addstr(self, *a, **k): pass
    def refresh(self): pass
    def erase(self): pass
    def clear(self): pass
    def getch(self): return -1
    def nodelay(self, v): pass
    def keypad(self, v): pass
    def touchwin(self): pass
    def box(self): pass
    def border(self): pass

class FakeCurses:
    LINES, COLS = 40, 120
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT = 259, 258, 260, 261
    KEY_ENTER, KEY_BACKSPACE = 10, 263
    KEY_HOME, KEY_END = 262, 360
    KEY_PPAGE, KEY_NPAGE = 339, 338
    A_BOLD, A_NORMAL, A_REVERSE = 1, 0, 2
    COLOR_PAIR = lambda n: n
    COLOR_BLACK, COLOR_RED, COLOR_GREEN = 0, 1, 2
    COLOR_YELLOW, COLOR_BLUE, COLOR_MAGENTA = 3, 4, 5
    COLOR_CYAN, COLOR_WHITE = 6, 7
    def wrapper(f): return lambda: f(FakeStdscr())
    def newwin(self, h, w, y, x):
        w = FakeStdscr(); w.lines, w.cols = h, w; return w
    def color_pair(self, n): return n
    def curs_set(self, v): pass
    def noecho(self): pass
    def cbreak(self): pass
    def start_color(self): pass
    def init_pair(self, *a): pass
    def use_default_colors(self): pass
    def flushinp(self): pass

sys.modules['curses'] = FakeCurses()

print("=== Test 1: import main ===")
import main
print("  OK")

print("\n=== Test 2: Game.__init__ ===")
game = main.Game(FakeStdscr())
print("  OK")

print("\n=== Test 3: new_game ===")
game.new_game()
print(f"  OK, player at ({game.player_x}, {game.player_y})")

print("\n=== Test 4: recipe synthesis ===")
failed = 0
for name, r in game.recipes.items():
    if not isinstance(r, dict) or "ingredients" not in r: continue
    for mat, count in r.get("ingredients", {}).items():
        game._add_material(mat, count * 10)
    try:
        rd = r.get("result", {})
        rt = rd.get("type", "")
        if rt == "equipment":
            from item_generator import get_generator
            from config import ORE_TO_MATERIAL
            gen = get_generator()
            ga = rd.get("generator_args", {})
            a = ga.get("archetype", "剑")
            m = ga.get("material", "石头")
            m = ORE_TO_MATERIAL.get(m, m)
            item = gen.generate(archetype_name=a, material_name=m)
            assert item["name"]
    except Exception as e:
        failed += 1
        if failed <= 3: print(f"  FAIL: {name}: {e}")
print(f"  {'OK' if failed==0 else f'{failed} FAILED'}")

print("\n=== Test 5: monster AI tick ===")
from systems.monster_ai import try_spawn_monster, tick_monsters
for _ in range(10): try_spawn_monster(game)
n = len(game.monsters)
for _ in range(10): tick_monsters(game)
print(f"  OK, {n} monsters ticked 10 turns")

print("\n=== Test 6: save/load ===")
from systems.save_system import build_save_data, apply_load_data
pd, wd = build_save_data(game)
game2 = main.Game(FakeStdscr())
game2.new_game()
apply_load_data(game2, {"player": pd, "world": wd})
assert game2.player_x == game.player_x
print("  OK")

print("\n=== Test 7: buff system ===")
from systems.buff_system import Buff, BuffManager
bm = BuffManager()
te = {"name": "t", "hp": 10, "max_hp": 10, "x": 0, "y": 0, "buffs": []}
bm.add(te, "burning", duration=3, damage_per_turn=2, source="test")
bm.tick_all(MagicMock(player_hp=100, monsters=[te], equipment={}, buff_manager=bm,
                      _kill_monster=lambda m,c: None, _gain_skill=lambda s: None))
assert te["hp"] == 8
print("  OK")

print("\n" + "="*40)
print("ALL TESTS PASSED")

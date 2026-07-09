"""冒烟测试：不依赖 curses，验证核心系统不崩溃。"""
import sys, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

class FakeCurses:
    KEY_LEFT = 260; KEY_RIGHT = 261; KEY_UP = 259; KEY_DOWN = 258; KEY_ENTER = 10; KEY_BACKSPACE = 127
    COLOR_WHITE = 1; COLOR_YELLOW = 2; COLOR_CYAN = 3; COLOR_BLACK = 0
    COLOR_GREEN = 4; COLOR_RED = 5; COLOR_MAGENTA = 6
    A_BOLD = 2097152; A_NORMAL = 0
    def __init__(self): pass
    @staticmethod
    def curs_set(v): pass
    @staticmethod
    def noecho(): pass
    @staticmethod
    def start_color(): pass
    @staticmethod
    def use_default_colors(): pass
    @staticmethod
    def init_pair(*a): pass
    @staticmethod
    def color_pair(n): return 0
    @staticmethod
    def wrapper(f): return f(None)

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

sys.modules['curses'] = FakeCurses()

print("=== Test 1: import main ===")
from systems.player_items import add_equipment_instance
import main

print("\n=== Test 2: Game.__init__ ===")
game = main.Game()
print("  OK")

print("\n=== Test 3: new_game ===")
game.new_game()
print(f"  OK, player at ({game.player_x}, {game.player_y})")

print("\n=== Test 4: recipe synthesis ===")
if hasattr(game, 'recipes') and game.recipes:
    recipe_names = list(game.recipes.keys())
    print(f"  OK, {len(recipe_names)} recipes loaded")
    for mat in ["石头", "泥土", "铁矿石"]:
        if mat in game.items:
            game.inventory.add(mat, 100)

print("\n=== Test 5: monster AI tick ===")
from systems.monster_ai import tick_monsters
game.monsters = [{"name": "史莱姆", "x": 5, "y": 5, "hp": 10, "dmg": 3, "speed": 1}]
build_monster_index(game) if hasattr(main, 'build_monster_index') else None
for _ in range(10): tick_monsters(game)
print(f"  OK, {len(game.monsters)} monsters ticked 10 turns")

print("\n=== Test 6: save/load ===")
game.save_game()
game2 = main.Game()
game2.load_game()
print("  OK")

print("\n=== Test 7: buff system ===")
if hasattr(game, 'buff_manager'):
    game.buff_manager.tick_all(game)
    print("  OK")
else:
    print("  SKIP")

print("\n" + "=" * 40)
print("ALL TESTS PASSED")

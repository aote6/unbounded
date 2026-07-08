"""PlayState - 主游戏状态：移动/攻击/挖掘/查看"""

import curses
from core.state_machine import State
from config import (
    KEY_QUIT, KEY_QUIT_UPPER, KEY_CHEST, KEY_CHEST_UPPER,
    KEY_CRAFT, KEY_CRAFT_UPPER, KEY_EQUIP, KEY_BUILD,
    KEY_REPEAT, KEY_RELOAD, KEY_RELOAD_UPPER,
    KEY_SAVE, KEY_SAVE_UPPER, KEY_LOAD, KEY_LOAD_UPPER,
    KEY_LOOK, KEY_DIG,
    KEY_MOVE_UP_ALT, KEY_MOVE_DOWN_ALT, KEY_MOVE_LEFT_ALT, KEY_MOVE_RIGHT_ALT,
)
from ui.game_renderer import draw
from ui.states.crafting_state import CraftingState
from ui.states.equipment_state import EquipmentState
from ui.states.build_state import BuildState
from ui.states.chest_state import ChestState


DIRECTIONS = {
    curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0),
    curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1),
    KEY_MOVE_LEFT_ALT: (-1, 0), KEY_MOVE_RIGHT_ALT: (1, 0),
    KEY_MOVE_UP_ALT: (0, -1), KEY_MOVE_DOWN_ALT: (0, 1),
}


class PlayState(State):
    """主游戏状态。持有 Game 引用，委托游戏逻辑。"""

    def __init__(self, game):
        self.game = game

    def handle_input(self, key):
        game = self.game

        if key in (KEY_QUIT, KEY_QUIT_UPPER):
            game.engine._running = False
            return None
        elif key == ord("?"):
            from systems.keybind import reload_keybinds
            from config import _init_keybinds
            reload_keybinds()
            _init_keybinds()
            game.message = "键位已重新加载。"

        acted = False

        if key in (KEY_CHEST, KEY_CHEST_UPPER):
            return ChestState(game)
        elif key in (KEY_CRAFT, KEY_CRAFT_UPPER):
            return CraftingState(game)
        elif key == KEY_EQUIP:
            return EquipmentState(game)
        elif key == KEY_BUILD:
            return BuildState(game)
        elif key in (KEY_RELOAD, KEY_RELOAD_UPPER):
            game._handle_reload()
        elif key in (KEY_SAVE, KEY_SAVE_UPPER):
            game._handle_save()
        elif key in (KEY_LOAD, KEY_LOAD_UPPER):
            game._handle_load()
        elif key == KEY_LOOK:
            game._handle_look_mode()
        elif key == KEY_DIG:
            acted = game._handle_dig_mode()
        elif key in DIRECTIONS:
            dx, dy = DIRECTIONS[key]
            game.try_move_or_dig(dx, dy)
            acted = True

        if acted:
            game.advance_turn()

        return None

    def update(self):
        pass

    def render(self, stdscr):
        draw(self.game)

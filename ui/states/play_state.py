"""PlayState - 主游戏状态：移动/攻击/挖掘/查看"""

import curses
from core.state_machine import State
from config import (
    DIRECTIONS,
    KEY_QUIT, KEY_QUIT_UPPER, KEY_CHEST, KEY_CHEST_UPPER,
    KEY_CRAFT, KEY_CRAFT_UPPER, KEY_EQUIP, KEY_BUILD,
    KEY_REPEAT, KEY_RELOAD, KEY_RELOAD_UPPER,
    KEY_SAVE, KEY_SAVE_UPPER, KEY_LOAD, KEY_LOAD_UPPER,
    KEY_LOOK, KEY_DIG,
    KEY_MOVE_UP_ALT, KEY_MOVE_DOWN_ALT, KEY_MOVE_LEFT_ALT, KEY_MOVE_RIGHT_ALT,
)
from ui.game_renderer import draw
from systems.turn_system import advance_turn
from systems.player_action import try_move_or_dig
from systems.save_manager import save_game, load_game
from ui.states.crafting_state import CraftingState
from ui.states.equipment_state import EquipmentState
from ui.states.build_state import BuildState
from ui.states.chest_state import ChestState




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
            game._load_static_data(); game.message = '数据已重载'
        elif key in (KEY_SAVE, KEY_SAVE_UPPER):
            save_game(game)
        elif key in (KEY_LOAD, KEY_LOAD_UPPER):
            load_game(game)
        elif key == KEY_LOOK:
            from ui.states.look_state import LookState
            return LookState(game)
        elif key == KEY_DIG:
            from ui.states.dig_state import DigState
            return DigState(game)
        elif key in DIRECTIONS:
            dx, dy = DIRECTIONS[key]
            try_move_or_dig(game, dx, dy)
            acted = True

        if acted:
            advance_turn(game)

        return None

    def update(self):
        pass

    def render(self, stdscr):
        draw(self.game)

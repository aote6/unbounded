"""PlayState - 主游戏状态：移动/攻击/挖掘/查看"""

from core.state_machine import State
from config import (
    DIRECTIONS,
    KEY_QUIT, KEY_QUIT_UPPER, KEY_CHEST, KEY_CHEST_UPPER,
    KEY_CRAFT, KEY_CRAFT_UPPER, KEY_EQUIP, KEY_BUILD, KEY_INVENTORY, KEY_SPRINT,
    KEY_RELOAD, KEY_RELOAD_UPPER, KEY_SAVE,
    KEY_SAVE_UPPER, KEY_LOAD, KEY_LOAD_UPPER, KEY_LOOK,
    KEY_DIG,
)
from ui.game_renderer import draw
from systems.gameplay.turn_system import advance_turn
from systems.gameplay.player_action import try_move_or_dig, sprint_move
from systems.core.save_manager import save_game, load_game
from ui.states.crafting_state import CraftingState
from ui.states.equipment_state import EquipmentState
from ui.states.inventory_state import InventoryState
from ui.states.build_state import BuildState
from ui.states.chest_state import ChestState
from config import _init_keybinds
from systems.core.keybind import reload_keybinds
# from systems.core.save_manager import save_game, load_game
from ui.states.dig_state import DigState
from ui.states.look_state import LookState
from ui.states.menu_state import MenuState


class PlayState(State):
    """主游戏状态。持有 Game 引用，委托游戏逻辑。"""

    def __init__(self, game):
        self.game = game
        self._main_menu_def = {"title": "主菜单", "hint": "↑↓选择 Enter确认 q返回", "items": [{"name": "合成", "state": "craft"}, {"name": "装备", "state": "equip"}, {"name": "背包", "state": "inventory"}, {"name": "建造", "state": "build"}, {"name": "挖掘", "state": "dig"}, {"name": "查看", "state": "look"}, {"name": "存档", "action": "save"}, {"name": "读档", "action": "load"}, {"name": "退出游戏", "action": "quit"}]}

    def handle_input(self, key):
        game = self.game

        if key in (KEY_QUIT, KEY_QUIT_UPPER):
            game.engine._running = False
            return None
        elif key == ord("?"):
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
        elif key == KEY_INVENTORY:
            return InventoryState(game)
        elif key == KEY_BUILD:
            return BuildState(game)
        elif key in (KEY_RELOAD, KEY_RELOAD_UPPER):
            game._load_static_data()
            game.message = '数据已重载'
        elif key in (KEY_SAVE, KEY_SAVE_UPPER):
            save_game(game)
        elif key in (KEY_LOAD, KEY_LOAD_UPPER):
            load_game(game)
        elif key == KEY_LOOK:
            return LookState(game)
        elif key == ord("m"):
            return MenuState(game, self._main_menu_def, self._menu_actions)
        elif key == KEY_DIG:
            return DigState(game)
        elif key == KEY_SPRINT:
            self._sprint_mode = not getattr(self, "_sprint_mode", False)
            if self._sprint_mode:
                game.message = "疾走模式：开启，方向键连续冲刺，再按 f 关闭。"
            else:
                game.message = "疾走模式：已关闭。"
            return None
        elif key in DIRECTIONS:
            dx, dy = DIRECTIONS[key]
            if getattr(self, "_sprint_mode", False):
                steps = sprint_move(game, dx, dy)
                if steps > 0:
                    game.message = f"疾走了 {steps} 步。"
                    for _ in range(steps):
                        advance_turn(game)
                return None
            else:
                game.message = ""
                try_move_or_dig(game, dx, dy)
            acted = True

        if acted:
            advance_turn(game)

        return None

    @property
    def _menu_actions(self):
        return {"save": lambda g: (save_game(g), None)[1], "load": lambda g: (load_game(g), None)[1], "quit": lambda g: setattr(g.engine, "_running", False)}
    def update(self):
        pass

    def render(self, stdscr):
        draw(self.game)

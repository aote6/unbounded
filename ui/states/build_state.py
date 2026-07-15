"""BuildState - 建造模式状态（选择物品 + 放置光标）"""

import curses
from core.state_machine import State
from ui.states.window_mixin import CenteredWindowMixin
from config import (
    DIRECTIONS,
    KEY_REPEAT,
    KEY_BUILD, KEY_QUIT, KEY_QUIT_UPPER,
)
from systems.gameplay.player_action import do_place
import items as items_mod


class BuildState(State, CenteredWindowMixin):
    """建造模式：先选物品，再移动光标放置。c/q 退出。"""

    def __init__(self, game):
        self.game = game
        self.win = None
        self._selecting = True  # True=选择物品, False=放置模式
        self._candidates = []
        self._selected = 0

    def enter(self):
        self._setup_candidates()
        if not self._candidates:
            self.game.message = "背包里没有可放置的物品。"
            self.game.engine.pop_state()
            return
        self._selecting = True
        self._open_win()

    def _setup_candidates(self):
        game = self.game
        self._candidates = [
            name for name, count in game.inventory.get_materials().items()
            if count > 0 and items_mod.is_placeable(game.items, name)
        ]

    def _open_win(self):
        h = len(self._candidates) + 6
        w = 45
        self._open_centered_win(h, w)

    def exit(self):
        self._close_win()

    def handle_input(self, key):
        if self._selecting:
            return self._handle_select(key)
        else:
            return self._handle_place(key)

    def _handle_select(self, key):
        if key in (KEY_BUILD, KEY_QUIT, KEY_QUIT_UPPER):
            self.game.engine.pop_state()
            return None
        elif key == curses.KEY_UP:
            self._selected = (self._selected - 1) % len(self._candidates)
        elif key == curses.KEY_DOWN:
            self._selected = (self._selected + 1) % len(self._candidates)
        elif key in (curses.KEY_ENTER, 10, 13):
            self._start_placing()
        return None

    def _start_placing(self):
        game = self.game
        name = self._candidates[self._selected]
        game.place_mode = items_mod.get_place_tile(game.items, name)
        game.place_item_name = name
        game.last_place = game.place_mode
        game.last_place_item_name = name
        game.cursor_x, game.cursor_y = game.player_x, game.player_y
        game.message = f"建造模式：放置 {name}，方向键移动光标，回车放置，b/q 退出。"
        self._selecting = False
        if self.win:
            del self.win
            self.win = None

    def _handle_place(self, key):
        game = self.game

        if key in (KEY_BUILD, KEY_QUIT, KEY_QUIT_UPPER):
            game.place_mode = None
            game.place_item_name = None
            game.message = "退出了建造模式。"
            self.game.engine.pop_state()
            return None

        if key in DIRECTIONS:
            dx, dy = DIRECTIONS[key]
            game.cursor_x += dx
            game.cursor_y += dy
            return None

        if key in (curses.KEY_ENTER, 10, 13):
            do_place(game)
            if game.place_mode is None:
                self.game.engine.pop_state()
            return None

        if key == KEY_REPEAT:
            if game.last_place:
                game.place_mode = game.last_place
                game.place_item_name = game.last_place_item_name
                game.cursor_x, game.cursor_y = game.player_x, game.player_y
                game.message = f"建造模式：放置 {game.last_place}，方向键移动光标，回车放置，b/q 取消。"
            else:
                game.message = "还没有建造过任何东西。合成一个石墙，或按 b 放置背包里的木箱。"

        return None

    def update(self):
        pass

    def render(self, stdscr):
        if self._selecting and self.win:
            self._draw_frame(" 放置物品 ", "↑↓ 选择 Enter 进入建造 b/q 关闭")
            h, w = self.win.getmaxyx()
            for i, name in enumerate(self._candidates):
                line = f" {name} x{self.game.inventory.count(name)}"
                attr = curses.A_REVERSE if i == self._selected else curses.A_NORMAL
                self.win.addstr(3 + i, 2, line[:w - 4], attr)
            self.win.refresh()
        else:
            # 建造模式：渲染地图，显示光标
            from ui.game_renderer import draw
            draw(self.game)

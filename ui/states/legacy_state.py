"""遗产商店状态：死后选择增益"""
from config import (
    KEY_LEGACY_SHOP, KEY_LEGACY_SHOP_UPPER,
    KEY_QUIT, KEY_QUIT_UPPER,
)
import curses
from core.state_machine import State
from ui.states.window_mixin import CenteredWindowMixin
from systems.gameplay.legacy_system import get_perks_shop, purchase_perk, get_legacy_points


class LegacyState(State, CenteredWindowMixin):
    def __init__(self, game):
        self.game = game
        self.win = None
        self.perks = []
        self.selected = 0
        self.status_msg = ""

    def enter(self):
        self.perks = get_perks_shop()
        h = max(len(self.perks) + 8, 15)
        w = 55
        self._open_centered_win(h, w)
        points = get_legacy_points()
        self.status_msg = f"遗产点数: {points}"

    def exit(self):
        self._close_win()

    def handle_input(self, key):
        if key in (KEY_LEGACY_SHOP, KEY_LEGACY_SHOP_UPPER, KEY_QUIT, KEY_QUIT_UPPER):
            self.game.engine.pop_state()
            return None
        elif key == curses.KEY_UP:
            self.selected = max(0, self.selected - 1)
        elif key == curses.KEY_DOWN:
            self.selected = min(len(self.perks) - 1, self.selected + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if self.perks:
                perk = self.perks[self.selected]
                success, msg = purchase_perk(perk["id"])
                self.status_msg = msg
                if success:
                    self.perks = get_perks_shop()
        return None

    def update(self):
        pass

    def render(self, stdscr):
        if not self.win:
            return
        self._draw_frame(" 遗产商店 ", "↑↓选择 Enter购买 p/q 关闭")

        h, w = self.win.getmaxyx()
        for i, perk in enumerate(self.perks):
            if i >= h - 6:
                break
            mark = "✓" if perk.get("owned") else (
                "$" if perk["affordable"] else "✗")
            line = f" [{mark}] {
                perk['name']} ({
                perk['cost']}点) - {
                perk['desc']}"
            attr = curses.A_REVERSE if i == self.selected else curses.A_NORMAL
            self.win.addstr(3 + i, 2, line[:w - 4], attr)

        if self.status_msg:
            self.win.addstr(h - 2, 2, self.status_msg[:w - 4], curses.A_BOLD)
        self.win.refresh()

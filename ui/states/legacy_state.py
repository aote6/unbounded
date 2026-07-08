"""遗产商店状态：死后选择增益"""
import curses
from core.state_machine import State
from systems.legacy_system import get_perks_shop, purchase_perk, get_legacy_points


class LegacyState(State):
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
        y = max(0, (curses.LINES - h) // 2)
        x = max(0, (curses.COLS - w) // 2)
        self.win = curses.newwin(h, w, y, x)
        self.win.keypad(True)
        points = get_legacy_points()
        self.status_msg = f"遗产点数: {points}"

    def exit(self):
        if self.win:
            del self.win
            self.win = None
        self.game.stdscr.touchwin()
        self.game.stdscr.refresh()

    def handle_input(self, key):
        if key in (ord('c'), ord('q')):
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
        self.win.erase()
        self.win.box()
        self.win.addstr(0, 2, " 遗产商店 ")
        self.win.addstr(1, 2, "↑↓选择 Enter购买 c继续游戏")
        
        h, w = self.win.getmaxyx()
        for i, perk in enumerate(self.perks):
            if i >= h - 6:
                break
            mark = "✓" if perk.get("owned") else ("$" if perk["affordable"] else "✗")
            line = f" [{mark}] {perk['name']} ({perk['cost']}点) - {perk['desc']}"
            attr = curses.A_REVERSE if i == self.selected else curses.A_NORMAL
            self.win.addstr(3 + i, 2, line[:w - 4], attr)
        
        if self.status_msg:
            self.win.addstr(h - 2, 2, self.status_msg[:w - 4], curses.A_BOLD)
        self.win.refresh()

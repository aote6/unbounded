"""EquipmentState - 装备状态一览：只读展示四个槽位当前穿戴情况"""

import curses
from core.state_machine import State

SLOTS = [
    ("main_hand", "主手"),
    ("off_hand", "副手"),
    ("body", "身体"),
    ("accessory", "饰品"),
]


class EquipmentState(State):
    """装备状态一览。任意键关闭。装备/卸下请在背包(i)中操作。"""

    def __init__(self, game):
        self.game = game
        self.win = None

    def enter(self):
        h, w = len(SLOTS) + 6, 50
        y = max(0, (curses.LINES - h) // 2)
        x = max(0, (curses.COLS - w) // 2)
        self.win = curses.newwin(h, w, y, x)
        self.win.keypad(True)

    def exit(self):
        if self.win:
            del self.win
            self.win = None
        self.game.engine.stdscr.clear()
        self.game.engine.stdscr.refresh()

    def handle_input(self, key):
        self.game.engine.pop_state()
        return None

    def update(self):
        pass

    def render(self, stdscr):
        if not self.win:
            return
        self.win.erase()
        self.win.box()
        self.win.addstr(0, 2, " 装备状态 ")
        self.win.addstr(1, 2, "装备/卸下请在背包(i)中操作，按任意键关闭")

        h, w = self.win.getmaxyx()
        for i, (slot_id, slot_name) in enumerate(SLOTS):
            inst = self.game.equipment.get(slot_id)
            if inst and hasattr(inst, 'name'):
                line = f" {slot_name}: {inst.name}"
                if getattr(inst, 'affixes', None):
                    line += " [" + "|".join(inst.affixes) + "]"
            else:
                line = f" {slot_name}: （空）"
            self.win.addstr(3 + i, 2, line[:w - 4])

        self.win.noutrefresh()

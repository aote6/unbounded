"""EquipmentState - 装备状态一览：只读展示四个槽位当前穿戴情况"""

import curses
from core.state_machine import State
from config import KEY_EQUIP, KEY_QUIT, KEY_QUIT_UPPER
from ui.states.window_mixin import CenteredWindowMixin
from ui.text_width import truncate_to_width

SLOTS = [
    ("main_hand", "主手"),
    ("off_hand", "副手"),
    ("body", "身体"),
    ("accessory", "饰品"),
]


class EquipmentState(State, CenteredWindowMixin):
    """装备状态一览。按 e 或 q 关闭。装备/卸下请在背包(i)中操作。"""

    def __init__(self, game):
        self.game = game
        self.win = None

    def enter(self):
        h, w = len(SLOTS) + 6, 50
        self._open_centered_win(h, w)

    def exit(self):
        self._close_win()

    def handle_input(self, key):
        if key in (KEY_EQUIP, KEY_QUIT, KEY_QUIT_UPPER):
            self.game.engine.pop_state()
        return None

    def update(self):
        pass

    def render(self, stdscr):
        if not self.win:
            return
        self._draw_frame(" 装备状态 ", "装备/卸下请在背包(i)中操作，按 e/q 关闭")

        h, w = self.win.getmaxyx()
        for i, (slot_id, slot_name) in enumerate(SLOTS):
            inst = self.game.equipment.get(slot_id)
            if inst and hasattr(inst, 'name'):
                line = f" {slot_name}: {inst.name}"
                if getattr(inst, 'affixes', None):
                    line += " [" + "|".join(inst.affixes) + "]"
            else:
                line = f" {slot_name}: （空）"
            self.win.addstr(3 + i, 2, truncate_to_width(line, w - 4))

        self.win.noutrefresh()

"""EquipmentState - 装备界面状态"""

import curses
from core.state_machine import State


SLOTS = [
    ("main_hand", "主手"),
    ("off_hand", "副手"),
    ("body", "身体"),
    ("accessory", "饰品"),
]


class EquipmentState(State):
    """装备菜单状态。c/q 退出回到 PlayState。"""

    def __init__(self, game):
        self.game = game
        self.win = None
        self.sub_win = None
        self.sel_slot = 0
        self.status_msg = ""
        self._choosing = False
        self._candidates = []
        self._sub_sel = 0
        self._slot_id = ""
        self._slot_name = ""

    def enter(self):
        h, w = len(SLOTS) + 6, 50
        y = max(0, (curses.LINES - h) // 2)
        x = max(0, (curses.COLS - w) // 2)
        self.win = curses.newwin(h, w, y, x)
        self.win.keypad(True)

    def exit(self):
        if self.sub_win:
            del self.sub_win
            self.sub_win = None
        if self.win:
            del self.win
            self.win = None
        self.game.stdscr.touchwin()
        self.game.stdscr.refresh()

    def handle_input(self, key):
        if self._choosing:
            return self._handle_sub_input(key)

        if key in (ord('c'), ord('q')):
            self.game.engine.pop_state()
            return None
        elif key == curses.KEY_UP:
            self.sel_slot = (self.sel_slot - 1) % len(SLOTS)
            self.status_msg = ""
        elif key == curses.KEY_DOWN:
            self.sel_slot = (self.sel_slot + 1) % len(SLOTS)
            self.status_msg = ""
        elif key in (curses.KEY_ENTER, 10, 13):
            self._open_slot_selection()
        return None

    def _open_slot_selection(self):
        game = self.game
        slot_id, slot_name = SLOTS[self.sel_slot]
        self._slot_id = slot_id
        self._slot_name = slot_name

        candidates = []
        for inst in game.inventory.get_equipment():
            if inst and inst.slot == slot_id:
                candidates.append(inst.name)
        if game.equipment.get(slot_id):
            candidates.insert(0, "__unequip__")

        if not candidates:
            self.status_msg = f"背包里没有能装备到{slot_name}的物品。"
            return

        self._candidates = candidates
        self._sub_sel = 0
        self._choosing = True

        sub_h = len(candidates) + 4
        sub_w = 40
        sub_y = max(0, (curses.LINES - sub_h) // 2)
        sub_x = max(0, (curses.COLS - sub_w) // 2)
        self.sub_win = curses.newwin(sub_h, sub_w, sub_y, sub_x)
        self.sub_win.keypad(True)

    def _handle_sub_input(self, key):
        if key in (ord('c'), ord('q')):
            self._choosing = False
            del self.sub_win
            self.sub_win = None
            return None
        elif key == curses.KEY_UP:
            self._sub_sel = (self._sub_sel - 1) % len(self._candidates)
        elif key == curses.KEY_DOWN:
            self._sub_sel = (self._sub_sel + 1) % len(self._candidates)
        elif key in (curses.KEY_ENTER, 10, 13):
            game = self.game
            chosen = self._candidates[self._sub_sel]
            old = game.equipment.get(self._slot_id)
            if chosen == "__unequip__":
                if old:
                    game.equipment[self._slot_id] = None
                old_name = old.name if hasattr(old, 'name') else str(old)
                game.message = f"卸下了 {old_name}。"
            else:
                # 从背包获取装备实例对象
                inst = game._get_equipment_instance(chosen)
                if old:
                    game.equipment[self._slot_id] = None
                game.equipment[self._slot_id] = inst if inst else chosen
                game.message = f"装备了 {chosen} 到{self._slot_name}。"
            self._choosing = False
            del self.sub_win
            self.sub_win = None
        return None

    def update(self):
        pass

    def render(self, stdscr):
        if not self.win:
            return

        self.win.erase()
        self.win.box()
        self.win.addstr(0, 2, " 装备菜单 ")
        self.win.addstr(1, 2, "↑↓ 选槽位 Enter 换装 c 关闭")

        h, w = self.win.getmaxyx()
        for i, (slot_id, slot_name) in enumerate(SLOTS):
            inst = self.game.equipment.get(slot_id)
            if inst and hasattr(inst, 'name'):
                line = f" {slot_name}: {inst.name}"
            else:
                line = f" {slot_name}: （空）"
                inst = None
            if inst:
                if inst and inst.affixes:
                    line += " [" + "|".join(inst.affixes) + "]"
            attr = curses.A_REVERSE if i == self.sel_slot else curses.A_NORMAL
            self.win.addstr(3 + i, 2, line[:w - 4], attr)

        if self.status_msg:
            self.win.addstr(h - 2, 2, self.status_msg[:w - 4], curses.A_BOLD)

        self.win.refresh()

        if self._choosing and self.sub_win:
            self.sub_win.erase()
            self.sub_win.box()
            self.sub_win.addstr(0, 2, f" 选择{self._slot_name} 装备 ")
            sw = self.sub_win.getmaxyx()[1]
            for ci, cname in enumerate(self._candidates):
                label = "（卸下）" if cname == "__unequip__" else cname
                attr = curses.A_REVERSE if ci == self._sub_sel else curses.A_NORMAL
                self.sub_win.addstr(2 + ci, 2, label[:sw - 4], attr)
            self.sub_win.refresh()

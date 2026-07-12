"""InventoryState - 背包浏览界面：按大类分类展示所有物品"""

import curses
from core.state_machine import State
from ui.text_width import display_width

CATEGORIES = [
    ("material", "材料"),
    ("equipment", "装备"),
    ("consumable", "消耗品"),
    ("placeable", "建材"),
]


class InventoryState(State):
    """背包菜单状态。左右切换分类，上下选择物品，c/q 退出。"""

    def __init__(self, game):
        self.game = game
        self.win = None
        self.tab = 0
        self.sel = 0
        self.status_msg = ""

    def enter(self):
        h, w = 20, 54
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

    def _current_entries(self):
        cat_key = CATEGORIES[self.tab][0]
        entries = []
        for item_id, item in self.game.inventory.all_items():
            if item.item_type == cat_key:
                entries.append((item_id, item))
        return entries

    def handle_input(self, key):
        if key in (ord('c'), ord('q')):
            self.game.engine.pop_state()
            return None
        elif key == curses.KEY_LEFT:
            self.tab = (self.tab - 1) % len(CATEGORIES)
            self.sel = 0
            self.status_msg = ""
        elif key == curses.KEY_RIGHT:
            self.tab = (self.tab + 1) % len(CATEGORIES)
            self.sel = 0
            self.status_msg = ""
        elif key == curses.KEY_UP:
            entries = self._current_entries()
            if entries:
                self.sel = (self.sel - 1) % len(entries)
        elif key == curses.KEY_DOWN:
            entries = self._current_entries()
            if entries:
                self.sel = (self.sel + 1) % len(entries)
        elif key in (curses.KEY_ENTER, 10, 13):
            entries = self._current_entries()
            if entries and self.sel < len(entries):
                item_id, item = entries[self.sel]
                if item.item_type == "equipment" and item.instance is not None:
                    self._toggle_equip(item.instance)
                else:
                    self.status_msg = f"{item_id} x{item.count}"
        return None

    def _toggle_equip(self, inst):
        """在背包内直接装备/卸下，不跳转到装备菜单。"""
        game = self.game
        slot_id = getattr(inst, "slot", None)
        if not slot_id:
            self.status_msg = f"{inst.name} 没有可装备的槽位。"
            return
        currently_equipped = game.equipment.get(slot_id) is inst
        if currently_equipped:
            game.equipment[slot_id] = None
            game.message = f"卸下了 {inst.name}。"
            self.status_msg = f"已卸下 {inst.name}。"
        else:
            old_inst = game.equipment.get(slot_id)
            game.equipment[slot_id] = inst
            if old_inst:
                game.message = f"卸下 {old_inst.name}，装备了 {inst.name}。"
                self.status_msg = f"已替换：{old_inst.name} → {inst.name}。"
            else:
                game.message = f"装备了 {inst.name}。"
                self.status_msg = f"已装备 {inst.name}。"

    def update(self):
        pass

    def render(self, stdscr):
        if not self.win:
            return
        self.win.erase()
        self.win.box()
        self.win.addstr(0, 2, " 背包 ")
        self.win.addstr(1, 2, "←→ 切换分类 ↑↓ 选择 Enter 装备/卸下 c 关闭")

        h, w = self.win.getmaxyx()

        x = 2
        for i, (_, name) in enumerate(CATEGORIES):
            attr = curses.A_REVERSE if i == self.tab else curses.A_NORMAL
            label = f"[{name}]"
            lw = display_width(label)
            if x + lw < w - 1:
                self.win.addstr(3, x, label, attr)
            x += lw + 1

        entries = self._current_entries()
        if not entries:
            self.win.addstr(5, 2, "（空）")
        else:
            for i, (item_id, item) in enumerate(entries):
                if 5 + i >= h - 3:
                    break
                if item.item_type == "equipment" and item.instance is not None:
                    name = getattr(item.instance, "name", item_id)
                    affixes = getattr(item.instance, "affixes", None)
                    line = f" {name}"
                    if affixes:
                        line += " [" + "|".join(affixes) + "]"
                    is_equipped = any(
                        self.game.equipment.get(sid) is item.instance
                        for sid in self.game.equipment
                    )
                    if is_equipped:
                        line += " [已装备]"
                else:
                    line = f" {item_id} x{item.count}"
                attr = curses.A_REVERSE if i == self.sel else curses.A_NORMAL
                self.win.addstr(5 + i, 2, line[:w - 4], attr)

        if self.status_msg:
            self.win.addstr(h - 2, 2, self.status_msg[:w - 4], curses.A_BOLD)

        self.win.noutrefresh()

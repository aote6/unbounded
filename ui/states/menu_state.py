"""MenuState - 通用层级菜单引擎。

菜单定义格式 (Python dict):
{
    "title": "菜单标题",
    "hint": "操作提示",
    "items": [
        {"name": "子菜单A", "menu": {...}},          # 嵌套子菜单
        {"name": "合成", "action": "craft"},          # 触发回调
        {"name": "装备", "state": "equipment"},       # 返回State类名
    ]
}
"""

import curses
from core.state_machine import State
from ui.states.window_mixin import CenteredWindowMixin


class MenuState(State, CenteredWindowMixin):
    def __init__(self, game, menu_def, on_action=None):
        self.game = game
        self.menu_def = menu_def
        self.on_action = on_action or {}
        self.win = None
        self.selected = 0
        self.scroll = 0
        self.items = menu_def.get("items", [])
        self.title = menu_def.get("title", "菜单")
        self.hint = menu_def.get("hint", "上下选择 Enter确认 q返回")

    def enter(self):
        h = min(len(self.items) + 5, curses.LINES - 2)
        w = min(50, curses.COLS - 2)
        self._open_centered_win(h, w)

    def exit(self):
        self._close_win()

    def handle_input(self, key):
        if key in (ord('q'), ord('Q'), 27):
            self.game.engine.pop_state()
            return None

        if key == curses.KEY_UP:
            self.selected = max(0, self.selected - 1)
        elif key == curses.KEY_DOWN:
            self.selected = min(len(self.items) - 1, self.selected + 1)
        elif key in (10, 13, curses.KEY_ENTER, ord(' ')):
            return self._activate()

        self._adjust_scroll()
        return None

    def _adjust_scroll(self):
        max_visible = self.win.getmaxyx()[0] - 4
        if self.selected < self.scroll:
            self.scroll = self.selected
        elif self.selected >= self.scroll + max_visible:
            self.scroll = self.selected - max_visible + 1

    def _activate(self):
        item = self.items[self.selected]
        if "menu" in item:
            return MenuState(self.game, item["menu"], self.on_action)
        if "action" in item:
            handler = self.on_action.get(item["action"])
            if handler:
                result = handler(self.game)
                if isinstance(result, State):
                    return result
        if "state" in item:
            from ui.states.crafting_state import CraftingState
            from ui.states.equipment_state import EquipmentState
            from ui.states.inventory_state import InventoryState
            from ui.states.build_state import BuildState
            from ui.states.chest_state import ChestState
            from ui.states.dig_state import DigState
            from ui.states.look_state import LookState
            state_map = {
                "craft": CraftingState,
                "equip": EquipmentState,
                "inventory": InventoryState,
                "build": BuildState,
                "chest": ChestState,
                "dig": DigState,
                "look": LookState,
            }
            cls = state_map.get(item["state"])
            if cls:
                return cls(self.game)
        return None

    def update(self):
        pass

    def render(self, stdscr):
        if not self.win:
            return
        self._draw_frame(f" {self.title} ", self.hint)
        max_visible = self.win.getmaxyx()[0] - 4
        for i in range(max_visible):
            idx = self.scroll + i
            if idx >= len(self.items):
                break
            item = self.items[idx]
            name = item.get("name", str(idx))
            if len(name) > 44:
                name = name[:41] + "..."
            attr = curses.A_REVERSE if idx == self.selected else curses.A_NORMAL
            self.win.addstr(2 + i, 2, name, attr)
        self.win.refresh()

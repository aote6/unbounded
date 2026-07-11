from systems.inventory_actions import add_equipment_instance
"""ChestState - 箱子交互界面状态"""

import curses
from core.state_machine import State
from systems.interaction import get_nearby_chest


class ChestState(State):
    """箱子存取界面。o/q 退出回到 PlayState。"""

    def __init__(self, game):
        self.game = game
        self.win = None
        self.chest = None
        self.viewing_chest = True
        self.selected = 0
        self.chest_mats = []
        self.chest_equips = []
        self.backpack_mats = []
        self.backpack_equips = []

    def enter(self):
        game = self.game
        pos = get_nearby_chest(game)
        if pos is None:
            game.message = "附近没有箱子。站到箱子旁边按 o 打开。"
            game.engine.pop_state()
            return
        self.chest = game.chests[pos]
        game.message = "箱子：,切换 | Enter取/存 | +全部转移 | o关闭"
        self._refresh_lists()

    def exit(self):
        if self.win:
            del self.win
            self.win = None
        self.game.engine.stdscr.touchwin()
        self.game.engine.stdscr.refresh()

    def _refresh_lists(self):
        chest = self.chest
        game = self.game
        self.chest_mats = list(chest["materials"].items())
        self.chest_equips = [(inst.name, inst)
                             for inst in chest["equipment_instances"]]
        self.backpack_mats = list(game.inventory.get_materials().items())
        self.backpack_equips = [(inst.name, inst)
                                for inst in game.inventory.get_equipment()]

    def _get_items(self):
        if self.viewing_chest:
            items = []
            for k, v in self.chest_mats:
                items.append(("material", k, v))
            for name, inst in self.chest_equips:
                affix = " [" + "|".join(inst.affixes) + \
                    "]" if inst.affixes else ""
                items.append(("equip", f"{name}{affix}", inst))
            return items, "箱子内容"
        else:
            items = []
            for k, v in self.backpack_mats:
                items.append(("material", k, v))
            for name, inst in self.backpack_equips:
                affix = " [" + "|".join(inst.affixes) + \
                    "]" if inst.affixes else ""
                items.append(("equip", f"{name}{affix}", inst))
            return items, "你的背包"

    def handle_input(self, key):
        items, _ = self._get_items()

        if key in (ord('o'), ord('q')):
            self.game.engine.pop_state()
            return None
        elif key == ord(','):
            self.viewing_chest = not self.viewing_chest
            self.selected = 0
            self._refresh_lists()
        elif key == curses.KEY_UP:
            self.selected = (self.selected - 1) % max(1, len(items))
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % max(1, len(items))
        elif key == ord('+'):
            self._transfer_all()
        elif items and key in (curses.KEY_ENTER, 10, 13):
            self._transfer_one(items)

        return None

    def _transfer_all(self):
        game = self.game
        chest = self.chest

        if self.viewing_chest:
            for item_id, item in list(game.inventory.all_items()):
                if item.item_type in ("material", "placeable"):
                    chest["materials"][item_id] = chest["materials"].get(
                        item_id, 0) + item.count
                    game.inventory.remove(item_id, item.count)
                elif item.item_type == "equipment":
                    chest["equipment_instances"].append(
                        item.instance.clone() if hasattr(
                            item.instance, "clone") else item.instance)
                    game.inventory.remove(item_id)
            game.message = "所有物品已存入箱子。"
        else:
            for k, v in list(chest["materials"].items()):
                game.inventory.add(k, v)
                del chest["materials"][k]
            for inst in list(chest["equipment_instances"]):
                add_equipment_instance(game, inst.name, inst)
                chest["equipment_instances"].remove(inst)
            game.message = "箱内所有物品已取出。"

        self.selected = 0
        self._refresh_lists()

    def _transfer_one(self, items):
        game = self.game
        chest = self.chest
        item = items[self.selected]

        if self.viewing_chest:
            if item[0] == "material":
                mat_name, count = item[1], item[2]
                game.inventory.add(mat_name, count)
                del chest["materials"][mat_name]
            else:
                inst = item[2]
                add_equipment_instance(game, inst.name, inst)
                chest["equipment_instances"].remove(inst)
            game.message = "已取出。"
        else:
            if item[0] == "material":
                mat_name, count = item[1], item[2]
                chest["materials"][mat_name] = chest["materials"].get(
                    mat_name, 0) + count
                game.inventory.remove(mat_name, count)
            else:
                inst = item[2]
                chest["equipment_instances"].append(
                    inst.clone() if hasattr(inst, "clone") else inst)
                game.inventory.remove(inst.name)
            game.message = "已存入。"

        self.selected = 0
        self._refresh_lists()

    def update(self):
        pass

    def render(self, stdscr):
        items, title = self._get_items()

        if self.selected >= max(1, len(items)):
            self.selected = 0

        h = max(len(items) + 5, 6)
        w = 45
        y = max(0, (curses.LINES - h) // 2)
        x = max(0, (curses.COLS - w) // 2)

        if self.win:
            try:
                del self.win
            except Exception:
                pass
        self.win = curses.newwin(h, w, y, x)
        self.win.keypad(True)
        self.win.erase()
        self.win.box()
        self.win.addstr(0, 2, f" {title} ")
        self.win.addstr(1, 2, ",切换 | Enter取/存 | +全部转移 | o关闭")

        if not items:
            self.win.addstr(3, 2, "（空）")
        else:
            for i, item in enumerate(items):
                if item[0] == "material":
                    line = f"  {item[1]} x{item[2]}"
                else:
                    line = f"  {item[1]}"
                attr = curses.A_REVERSE if i == self.selected else curses.A_NORMAL
                self.win.addstr(3 + i, 2, line[:w - 4], attr)

        self.win.refresh()

"""CraftingState - 合成界面状态"""

import curses
import random
from core.state_machine import State
from equipment import EquipmentInstance
import items as items_mod


# 矿石名到材质名映射
ORE_TO_MATERIAL = {
    "煤矿": "煤", "铜矿": "铜", "铁矿": "铁",
    "银矿": "银", "金矿": "金", "钻石矿": "钻石",
}


class CraftingState(State):
    """合成菜单状态。c/q 退出回到 PlayState。"""

    def __init__(self, game):
        self.game = game
        self.win = None
        self.recipes = game.recipes
        self.all_names = []
        self.categories = {}
        self.ordered_cats = []
        self.current_cat_idx = 0
        self.selected = 0
        self.status_msg = ""
        self._setup()

    def _setup(self):
        recipes = self.recipes
        if not recipes:
            return
        self.all_names = [k for k, v in recipes.items()
                          if isinstance(v, dict) and "ingredients" in v]
        for name in self.all_names:
            cat = recipes[name].get("category", "未分类")
            self.categories.setdefault(cat, []).append(name)

        cat_order = ["武器", "工具", "护甲", "建筑", "其他", "未分类"]
        self.ordered_cats = [c for c in cat_order if c in self.categories]
        self.ordered_cats += [c for c in self.categories if c not in cat_order]

    def enter(self):
        h, w = 18, 50
        y = max(0, (curses.LINES - h) // 2)
        x = max(0, (curses.COLS - w) // 2)
        self.win = curses.newwin(h, w, y, x)
        self.win.keypad(True)

    def exit(self):
        if self.win:
            self.win.clear()
            self.win.refresh()

    def handle_input(self, key):
        if not self.ordered_cats:
            self.game.engine.pop_state()
            return None

        cat_name = self.ordered_cats[self.current_cat_idx]
        names = self.categories[cat_name]
        if not names:
            self.game.engine.pop_state()
            return None

        if key in (ord('c'), ord('q')):
            self.game.engine.pop_state()
            return None
        elif key == ord(','):
            self.current_cat_idx = (self.current_cat_idx + 1) % len(self.ordered_cats)
            self.selected = 0
            self.status_msg = ""
        elif key == curses.KEY_UP:
            self.selected = (self.selected - 1) % len(names)
            self.status_msg = ""
        elif key == curses.KEY_DOWN:
            self.selected = (self.selected + 1) % len(names)
            self.status_msg = ""
        elif key in (curses.KEY_ENTER, 10, 13):
            self._craft(names[self.selected])

        return None

    def _craft(self, name):
        game = self.game
        r = self.recipes[name]
        can = all(game._count_material(m) >= c
                  for m, c in r.get("ingredients", {}).items())
        if not can:
            self.status_msg = "材料不足！按任意键继续。"
            return

        for m, c in r.get("ingredients", {}).items():
            game._remove_material(m, c)

        result_def = r.get("result", {})
        result_type = result_def.get("type", "") if result_def else ""

        if result_type == "generated_equipment":
            from item_generator import get_generator
            gen = get_generator()
            arch = result_def.get("archetype")
            mat = result_def.get("material")
            mat = ORE_TO_MATERIAL.get(mat, mat)
            affix_chance = result_def.get("affix_chance", 0.0)
            if affix_chance > 0 and random.random() < affix_chance:
                item_dict = gen.generate(archetype_name=arch, material_name=mat)
            else:
                item_dict = gen.generate(archetype_name=arch, material_name=mat, affix_count=0)
            inst = EquipmentInstance(
                name=item_dict["name"],
                slot=item_dict.get("slot"),
                attack_bonus=item_dict.get("attack_bonus", 0),
                defense_bonus=item_dict.get("defense_bonus", 0),
                tool_bonus=item_dict.get("tool_bonus", 0),
                damage_min=item_dict.get("damage_min", 0),
                damage_max=item_dict.get("damage_max", 0),
                hit_bonus=item_dict.get("hit_bonus", 0),
                affixes=item_dict.get("affixes", []),
                on_attack=item_dict.get("on_attack", []),
                lifesteal=item_dict.get("lifesteal", 0),
                speed_bonus=item_dict.get("speed_bonus", 0),
            )
            game._add_equipment_instance(inst.name, inst)
            affix_str = ""
            if inst.affixes:
                affix_str = " [" + "|".join(inst.affixes) + "]"
            self.status_msg = f"合成了 {inst.name}{affix_str}！(slot={inst.slot})"

        elif result_type == "material":
            mat_name = result_def.get("name", name)
            mat_count = result_def.get("count", 1)
            game._add_material(mat_name, mat_count)
            self.status_msg = f"合成了 {mat_name} x{mat_count}（共 {game._count_material(mat_name)}）"

        elif result_type == "placeable":
            game._add_material(name, 1)
            self.status_msg = f"合成了 {name} x1（共 {game._count_material(name)}）。按 b 放置。"

        elif items_mod.is_placeable(game.items, name):
            if name == "木箱":
                game._add_material(name, 1)
                self.status_msg = f"合成了 {name}！按 b 从背包选择放置位置（共 {game._count_material(name)}）。"
            else:
                game.place_mode = items_mod.get_place_tile(game.items, name)
                game.place_item_name = None
                game.last_place = game.place_mode
                game.last_place_item_name = None
                game.cursor_x, game.cursor_y = game.player_x, game.player_y
                game.message = f"合成了 {name}！建造模式：方向键移动光标，回车放置，c 退出。"
                self.game.engine.pop_state()
        else:
            game._add_equipment_instance(name)
            self.status_msg = f"合成了 {name} x1（共 {game._count_equipment(name)}）"

    def update(self):
        pass

    def render(self, stdscr):
        if not self.win or not self.ordered_cats:
            return
        self.win.erase()
        self.win.box()
        cat_name = self.ordered_cats[self.current_cat_idx]
        names = self.categories[cat_name]
        if self.selected >= len(names):
            self.selected = 0

        self.win.addstr(0, 2, f" 合成菜单 [{cat_name}] ")
        self.win.addstr(1, 2, ",切换分类 | ↑↓选择 | Enter合成 | c 关闭")

        h, w = self.win.getmaxyx()
        for i, name in enumerate(names):
            if i >= h - 5:
                self.win.addstr(3 + i, 2, f"  ... 还有 {len(names) - i} 项")
                break
            r = self.recipes[name]
            ing = " + ".join(f"{v}x{k}" for k, v in r.get("ingredients", {}).items())
            line = f" {name} <- {ing}"
            if r.get("desc"):
                line += f" ({r['desc']})"
            attr = curses.A_REVERSE if i == self.selected else curses.A_NORMAL
            self.win.addstr(3 + i, 2, line[:w - 4], attr)

        if self.status_msg:
            self.win.addstr(h - 2, 2, self.status_msg[:w - 4], curses.A_BOLD)

        self.win.refresh()

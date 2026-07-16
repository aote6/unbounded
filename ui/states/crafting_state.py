from inventory import ItemCategory
from equipment import EquipmentInstance
from core.state_machine import State
from config import KEY_CRAFT, KEY_CRAFT_UPPER, KEY_QUIT, KEY_QUIT_UPPER
import random
from systems.gameplay.inventory_actions import add_equipment_instance
from ui.states.window_mixin import CenteredWindowMixin
from ui.text_width import truncate_to_width
"""CraftingState - 合成界面状态"""

import curses

# 矿石名到材质名映射
ORE_TO_MATERIAL = {
    "煤矿": "煤", "铜矿": "铜", "铁矿": "铁",
    "银矿": "银", "金矿": "金", "钻石矿": "钻石",
}


# 矿石名到材质名映射


class CraftingState(State, CenteredWindowMixin):
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
        self._open_centered_win(18, 50)

    def exit(self):
        self._close_win()

    def handle_input(self, key):
        if not self.ordered_cats:
            self.game.engine.pop_state()
            return None

        cat_name = self.ordered_cats[self.current_cat_idx]
        names = self.categories[cat_name]
        if not names:
            self.game.engine.pop_state()
            return None

        if key in (KEY_CRAFT, KEY_CRAFT_UPPER, KEY_QUIT, KEY_QUIT_UPPER):
            self.game.engine.pop_state()
            return None
        elif key == ord(','):
            self.current_cat_idx = (
                self.current_cat_idx + 1) % len(self.ordered_cats)
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
        can = all(game.inventory.count(m) >= c
                  for m, c in r.get("ingredients", {}).items())
        if not can:
            self.status_msg = "材料不足！按任意键继续。"
            return

        for m, c in r.get("ingredients", {}).items():
            game.inventory.remove(m, c)
        # M27: 记录合成配方
        if not hasattr(game, "_crafted_this_life"):
            game._crafted_this_life = []
        if name not in game._crafted_this_life:
            game._crafted_this_life.append(name)

        result_def = r.get("result", {})
        result_type = result_def.get("type", "") if result_def else ""

        if result_type == ItemCategory.EQUIPMENT:
            from item_generator import get_generator
            gen = get_generator()
            gen_args = result_def.get("generator_args", {})
            arch = gen_args.get("archetype")
            mat = gen_args.get("material")
            mat = ORE_TO_MATERIAL.get(mat, mat)
            affix_chance = result_def.get("affix_chance", 0.0)
            if affix_chance > 0 and random.random() < affix_chance:
                item_dict = gen.generate(
                    archetype_name=arch, material_name=mat)
            else:
                item_dict = gen.generate(
                    archetype_name=arch, material_name=mat, affix_count=0)
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
            add_equipment_instance(game, inst.name, inst)
            affix_str = ""
            if inst.affixes:
                affix_str = " [" + "|".join(inst.affixes) + "]"
            self.status_msg = f"合成了 {inst.name}{affix_str}！(slot={inst.slot})"

        elif result_type == ItemCategory.MATERIAL:
            mat_name = result_def.get("name", name)
            mat_count = result_def.get("count", 1)
            game.inventory.add(mat_name, mat_count)
            self.status_msg = f"合成了 {mat_name} x{mat_count}（共 {
                game.inventory.count(mat_name)}）"

        elif result_type == ItemCategory.PLACEABLE:
            # 统一处理：先加材料到背包，让玩家按 b 放置
            # 修复：此前直接用配方key当物品名，与同文件MATERIAL分支
            # （上方）的正确写法result_def.get("name", name)不一致，
            # 若配方key与result.name不同会导致物品名错位。
            item_name = result_def.get("name", name)
            game.inventory.add(item_name, 1)
            self.status_msg = f"合成了 {item_name} x1（共 {
                game.inventory.count(item_name)}）。按 b 放置。"

        else:
            # 兜底分支改为报错，不再静默生成垃圾装备
            raise ValueError(
                f"配方 '{name}' 的 result.type='{result_type}' 不合法。"
                f"合法值: generated_equipment, material, placeable。"
                f"请检查 data/recipes.json。"
            )

    def update(self):
        pass

    def render(self, stdscr):
        if not self.win or not self.ordered_cats:
            return
        cat_name = self.ordered_cats[self.current_cat_idx]
        names = self.categories[cat_name]
        if self.selected >= len(names):
            self.selected = 0

        self._draw_frame(f" 合成菜单 [{cat_name}] ", ",切换分类 | ↑↓选择 | Enter合成 | c/q 关闭")

        h, w = self.win.getmaxyx()
        visible_rows = max(1, h - 5)
        total = len(names)
        if total <= visible_rows:
            scroll_offset = 0
        else:
            scroll_offset = max(
                0, min(self.selected - visible_rows + 1, total - visible_rows))

        visible_names = names[scroll_offset:scroll_offset + visible_rows]
        for i, name in enumerate(visible_names):
            idx = scroll_offset + i
            r = self.recipes[name]
            ing = " + ".join(f"{v}x{k}" for k,
                             v in r.get("ingredients", {}).items())
            line = f" {name} <- {ing}"
            if r.get("desc"):
                line += f" ({r['desc']})"
            attr = curses.A_REVERSE if idx == self.selected else curses.A_NORMAL
            self.win.addstr(3 + i, 2, truncate_to_width(line, w - 4), attr)

        if total > visible_rows:
            indicator = f" [{scroll_offset + 1}-{min(scroll_offset + visible_rows, total)}/{total}] "
            self.win.addstr(2, max(2, w - len(indicator) - 2), truncate_to_width(indicator, w - 4))

        if self.status_msg:
            self.win.addstr(h - 2, 2, truncate_to_width(self.status_msg, w - 4), curses.A_BOLD)

        self.win.refresh()

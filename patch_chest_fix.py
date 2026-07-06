#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一次性补丁：修复"合成后无法放置的可堆叠放置物"死结（当前只有木箱触发这个分支）。

做的事：
1. 删除 crafting_menu 里木箱分支的死代码（break 之后的几行永远不会执行）
2. 木箱合成后存进 self.materials（堆叠），而不是 self.equipment_instances
3. 新增 place_item_name / last_place_item_name 两个状态字段，记录"这次放置的对象
   是不是从背包里挑出来的可堆叠物品"，放置成功后才真正扣减背包
4. 新增独立的放置菜单 place_menu()，绑定按键 b：随时从背包里选择一个可放置物
   （目前只有木箱会进到这里）进入建造模式
5. 修正取消建造（c 键）逻辑：如果这次放置来自背包物品，取消时不做"退还合成材料"，
   因为材料压根没被扣（它还乖乖待在背包里）
6. _do_place 放置成功后，如果来源是背包物品，扣 1 个；扣完后自动退出建造模式
7. 删掉从未被使用过的 self.placeable_inventory 死代码声明

运行方式（在 Termux 项目根目录，main.py 所在目录）：
    python patch_chest_fix.py

脚本对 main.py 做的每一处替换都要求"原文恰好出现一次"，如果你的代码和我看到的版本
不完全一致，脚本会报错并停在原地，不会改坏文件（不会有任何写入），可以放心运行。
运行前脚本会自动生成 main.py.bak 备份。
"""
import sys
from pathlib import Path

TARGET = Path(__file__).parent / "main.py"

def apply_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        print(f"[跳过/失败] {label}: 在文件中找到 {count} 处匹配（需要恰好1处），"
              f"你的代码可能和预期版本不一致，请把这一步反馈给我，不做修改。")
        sys.exit(1)
    print(f"[OK] {label}")
    return text.replace(old, new, 1)


def main():
    if not TARGET.exists():
        print(f"找不到 {TARGET}，请把这个脚本放在 main.py 同一个目录下再运行。")
        sys.exit(1)

    src = TARGET.read_text(encoding="utf-8")
    backup = TARGET.with_suffix(".py.bak")
    backup.write_text(src, encoding="utf-8")
    print(f"已备份原文件到 {backup}")

    text = src

    # ── 1. 合成菜单：木箱分支去掉死代码，改存材料堆叠 ──
    old_1 = '''            elif items_mod.is_placeable(game.items, name):
                # 木箱不进建造模式，放进背包让玩家自己决定何时放置
                if name == "木箱":
                    game._add_equipment_instance(name)
                    break
                    game.message = f"合成了 {name}！方向键移动光标，回车放置，c 取消。\\n"
                    game.cursor_x, game.cursor_y = game.player_x, game.player_y
                    game.last_place = game.place_mode
                    game.place_mode = items_mod.get_place_tile(game.items, name)
                else:
                    game.place_mode = items_mod.get_place_tile(game.items, name)
                    game.last_place = game.place_mode
                    game.cursor_x, game.cursor_y = game.player_x, game.player_y
                    game.message = f"合成了 {name}！建造模式：方向键移动光标，回车放置，c 退出。"
                    break'''
    new_1 = '''            elif items_mod.is_placeable(game.items, name):
                if name == "木箱":
                    # 木箱不进建造模式，存进背包，玩家按 b 键随时选择放置
                    game._add_material(name, 1)
                    status_msg = f"合成了 {name}！按 b 从背包选择放置位置（共 {game._count_material(name)}）。"
                else:
                    game.place_mode = items_mod.get_place_tile(game.items, name)
                    game.place_item_name = None
                    game.last_place = game.place_mode
                    game.last_place_item_name = None
                    game.cursor_x, game.cursor_y = game.player_x, game.player_y
                    game.message = f"合成了 {name}！建造模式：方向键移动光标，回车放置，c 退出。"
                    break'''
    text = apply_one(text, old_1, new_1, "1/8 合成菜单木箱分支修复")

    # ── 2. 新增 place_menu()（放置菜单），插到 equipment_menu 函数后面 ──
    old_2 = '''# ═══════════════════════════════════
# Game 类
# ═══════════════════════════════════
class Game:'''
    new_2 = '''# ═══════════════════════════════════
# 放置菜单（从背包挑一个可放置物进入建造模式）
# ═══════════════════════════════════
def place_menu(stdscr, game):
    candidates = [name for name, count in game.materials.items()
                  if count > 0 and items_mod.is_placeable(game.items, name)]
    if not candidates:
        game.message = "背包里没有可放置的物品。"
        return
    selected = 0
    h, w = len(candidates) + 6, 45
    y, x = max(0, (curses.LINES - h) // 2), max(0, (curses.COLS - w) // 2)
    win = curses.newwin(h, w, y, x)
    win.keypad(True)
    while True:
        win.erase(); win.box()
        win.addstr(0, 2, " 放置物品 ")
        win.addstr(1, 2, "↑↓ 选择 Enter 进入建造 c 关闭")
        for i, name in enumerate(candidates):
            line = f" {name} x{game.materials.get(name, 0)}"
            attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
            win.addstr(3 + i, 2, line[:w - 4], attr)
        win.refresh()
        key = win.getch()
        if key in (ord('c'), ord('q')):
            break
        elif key == curses.KEY_UP:
            selected = (selected - 1) % len(candidates)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(candidates)
        elif key in (curses.KEY_ENTER, 10, 13):
            name = candidates[selected]
            game.place_mode = items_mod.get_place_tile(game.items, name)
            game.place_item_name = name
            game.last_place = game.place_mode
            game.last_place_item_name = name
            game.cursor_x, game.cursor_y = game.player_x, game.player_y
            game.message = f"建造模式：放置 {name}，方向键移动光标，回车放置，c 退出。"
            break
    del win; game.stdscr.touchwin(); game.stdscr.refresh()

# ═══════════════════════════════════
# Game 类
# ═══════════════════════════════════
class Game:'''
    text = apply_one(text, old_2, new_2, "2/8 新增 place_menu 函数")

    # ── 3. __init__ 里加状态字段、删掉死代码 placeable_inventory ──
    old_3 = '''        self.chests = {}  # {(x,y): {"materials": {}, "equipment_instances": [...]}}
        self.placeable_inventory = {}  # {"木箱": 1, "石墙": 3} 可放置物品暂存'''
    new_3 = '''        self.chests = {}  # {(x,y): {"materials": {}, "equipment_instances": [...]}}'''
    text = apply_one(text, old_3, new_3, "3/8 删除未使用的 placeable_inventory")

    old_4 = '''        self.message = "欢迎。世界无限延伸。hjkl 移动，c 合成，e 装备，d 挖掘，q 退出。S 存档，L 读档。"
        self.place_mode = None; self.last_place = None'''
    new_4 = '''        self.message = "欢迎。世界无限延伸。hjkl 移动，c 合成，e 装备，d 挖掘，q 退出。S 存档，L 读档。"
        self.place_mode = None; self.last_place = None
        self.place_item_name = None; self.last_place_item_name = None'''
    text = apply_one(text, old_4, new_4, "4/8 __init__ 增加 place_item_name 字段")

    # ── 4. new_game 里同步加字段 ──
    old_5 = '''        self.message = "新游戏开始。S 存档，L 读档。"
        self.place_mode = None; self.last_place = None'''
    new_5 = '''        self.message = "新游戏开始。S 存档，L 读档。"
        self.place_mode = None; self.last_place = None
        self.place_item_name = None; self.last_place_item_name = None'''
    text = apply_one(text, old_5, new_5, "5/8 new_game 增加 place_item_name 字段")

    # ── 5. load_game 里同步加字段 ──
    old_6 = '''            self.monsters.append(m)
        self.place_mode = None; self.last_place = None'''
    new_6 = '''            self.monsters.append(m)
        self.place_mode = None; self.last_place = None
        self.place_item_name = None; self.last_place_item_name = None'''
    text = apply_one(text, old_6, new_6, "6/8 load_game 增加 place_item_name 字段")

    # ── 6. _do_place：放置成功后按来源扣背包 ──
    old_7 = '''    def _do_place(self):
        bx, by = self.cursor_x, self.cursor_y
        if self._monster_at(bx, by):
            self.message = "有怪物挡住了建造位置。"; return
        if self.world.get_tile(bx, by)["tile"] != TILE_AIR:
            self.message = "这里不是空地，无法放置。"; return
        if bx == self.player_x and by == self.player_y:
            push_order = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            pushed = False
            for pdx, pdy in push_order:
                px, py = self.player_x + pdx, self.player_y + pdy
                if (self.world.get_tile(px, py)["tile"] == TILE_AIR
                        and not self._monster_at(px, py)
                        and not self._monster_has_position(px, py)):
                    self.player_x, self.player_y = px, py; pushed = True; break
            if not pushed:
                self.message = "玩家没有空间后退，无法在脚下放置。"; return
        self.world.set_tile(bx, by, self.place_mode)
        self.modified_tiles[(bx, by)] = self.place_mode
        # 如果放置的是箱子，初始化空箱子
        if self.place_mode == "木箱":
            self.chests[(bx, by)] = {"materials": {}, "equipment_instances": []}
        self.message = f"放置了 {self.place_mode}（建造模式中，c 退出）"'''
    new_7 = '''    def _do_place(self):
        if self.place_item_name and self._count_material(self.place_item_name) <= 0:
            self.message = f"背包里已经没有 {self.place_item_name} 了。"
            self.place_mode = None; self.place_item_name = None
            return
        bx, by = self.cursor_x, self.cursor_y
        if self._monster_at(bx, by):
            self.message = "有怪物挡住了建造位置。"; return
        if self.world.get_tile(bx, by)["tile"] != TILE_AIR:
            self.message = "这里不是空地，无法放置。"; return
        if bx == self.player_x and by == self.player_y:
            push_order = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            pushed = False
            for pdx, pdy in push_order:
                px, py = self.player_x + pdx, self.player_y + pdy
                if (self.world.get_tile(px, py)["tile"] == TILE_AIR
                        and not self._monster_at(px, py)
                        and not self._monster_has_position(px, py)):
                    self.player_x, self.player_y = px, py; pushed = True; break
            if not pushed:
                self.message = "玩家没有空间后退，无法在脚下放置。"; return
        self.world.set_tile(bx, by, self.place_mode)
        self.modified_tiles[(bx, by)] = self.place_mode
        # 如果放置的是箱子，初始化空箱子
        if self.place_mode == "木箱":
            self.chests[(bx, by)] = {"materials": {}, "equipment_instances": []}
        if self.place_item_name:
            self._remove_material(self.place_item_name, 1)
            if self._count_material(self.place_item_name) <= 0:
                self.message = f"放置了 {self.place_mode}（背包中已无更多，退出建造模式）"
                self.place_mode = None; self.place_item_name = None
                return
        self.message = f"放置了 {self.place_mode}（建造模式中，c 退出）"'''
    text = apply_one(text, old_7, new_7, "7/8 _do_place 按来源扣减背包")

    # ── 7. run()：'c' 取消建造 分流 + 新增 'b' 建按键 + '.' 重复建造带上来源 ──
    old_8 = '''            elif key in (ord('c'), ord('C')):
                if self.place_mode:
                    # 取消建造，退还材料
                    tile_info = self.items.get(self.place_mode, {})
                    ingredients = self.recipes.get(self.place_mode, {}).get("ingredients", {})
                    if not ingredients:
                        # 尝试用配方名匹配
                        for rname, rdata in self.recipes.items():
                            if rname == self.place_mode or rdata.get("result", {}).get("archetype") == self.place_mode:
                                ingredients = rdata.get("ingredients", {})
                                break
                    if ingredients:
                        for mat, count in ingredients.items():
                            self._add_material(mat, count)
                        self.message = f"取消建造 {self.place_mode}，材料已退还。"
                    else:
                        self.message = "退出了建造模式。"
                    self.place_mode = None
                else:
                    crafting_menu(self.stdscr, self); self.draw(); continue
            elif key == ord('e'):
                equipment_menu(self.stdscr, self); self.draw(); continue
            elif key in (curses.KEY_ENTER, 10, 13):
                if self.place_mode: self._do_place(); acted = True
                self.draw(); continue
            elif key == ord('.'):
                if self.last_place:
                    self.place_mode = self.last_place
                    self.cursor_x, self.cursor_y = self.player_x, self.player_y
                    self.message = f"建造模式：放置 {self.last_place}，方向键移动光标，回车放置，c 取消。"
                else:
                    self.message = "还没有建造过任何东西。合成一个石墙或木箱。"
                self.draw(); continue'''
    new_8 = '''            elif key in (ord('c'), ord('C')):
                if self.place_mode:
                    if self.place_item_name:
                        # 这次放置来自背包已有物品，材料本来就没被扣，取消不用退还
                        self.message = f"退出了建造模式，{self.place_item_name} 仍在背包里。"
                        self.place_mode = None
                        self.place_item_name = None
                    else:
                        # 合成后立即建造：取消时退还配方材料
                        ingredients = self.recipes.get(self.place_mode, {}).get("ingredients", {})
                        if not ingredients:
                            # 尝试用配方名匹配
                            for rname, rdata in self.recipes.items():
                                if rname == self.place_mode or rdata.get("result", {}).get("archetype") == self.place_mode:
                                    ingredients = rdata.get("ingredients", {})
                                    break
                        if ingredients:
                            for mat, count in ingredients.items():
                                self._add_material(mat, count)
                            self.message = f"取消建造 {self.place_mode}，材料已退还。"
                        else:
                            self.message = "退出了建造模式。"
                        self.place_mode = None
                else:
                    crafting_menu(self.stdscr, self); self.draw(); continue
            elif key == ord('e'):
                equipment_menu(self.stdscr, self); self.draw(); continue
            elif key == ord('b'):
                place_menu(self.stdscr, self); self.draw(); continue
            elif key in (curses.KEY_ENTER, 10, 13):
                if self.place_mode: self._do_place(); acted = True
                self.draw(); continue
            elif key == ord('.'):
                if self.last_place:
                    self.place_mode = self.last_place
                    self.place_item_name = self.last_place_item_name
                    self.cursor_x, self.cursor_y = self.player_x, self.player_y
                    self.message = f"建造模式：放置 {self.last_place}，方向键移动光标，回车放置，c 取消。"
                else:
                    self.message = "还没有建造过任何东西。合成一个石墙，或按 b 放置背包里的木箱。"
                self.draw(); continue'''
    text = apply_one(text, old_8, new_8, "8/8 run() 按键处理更新")

    # ── 8. 底部帮助文字加上 b 键说明 ──
    old_9 = '''                "移动 | c 合成 | e 装备 | x 查看 | d 挖掘 | o 箱子 | . 重复建造 | 回车 放置 | r 重载 | S 存档 | L 读档 | q 退出")'''
    new_9 = '''                "移动 | c 合成 | e 装备 | b 放置 | x 查看 | d 挖掘 | o 箱子 | . 重复建造 | 回车 放置 | r 重载 | S 存档 | L 读档 | q 退出")'''
    if old_9 in text:
        text = apply_one(text, old_9, new_9, "9/9 帮助文字增加 b 键提示")
    else:
        print("[提示] 帮助文字那一行和预期不完全一致，跳过（不影响功能，可以自己手动在帮助文字里加一个 'b 放置'）。")

    TARGET.write_text(text, encoding="utf-8")
    print("\n全部替换完成，main.py 已更新。")
    print("如果游戏运行有问题，恢复备份：mv main.py.bak main.py")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""自动连续挖掘：按住方向键持续挖掘，不用反复按"""
from pathlib import Path

BASE = Path(__file__).parent

def apply_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        print(f"[跳过] {label}: 匹配 {count} 处（需1处）")
        return text
    print(f"[OK] {label}")
    return text.replace(old, new, 1)

fp = BASE / "main.py"
src = fp.read_text("utf-8")

# 1. __init__ 加连续挖掘状态
old = '''        self.dig_progress = None; self.look_mode = False'''
new = '''        self.dig_progress = None; self.look_mode = False
        self.auto_dig_dir = None  # 持续挖掘方向 (dx, dy)'''
src = apply_one(src, old, new, "1/4 __init__ 加 auto_dig_dir")

# 2. new_game 同步
old = '''        self.dig_progress = None; self.look_mode = False
        self.recipes = load_recipes(); self.items = items_mod.load_items()'''
new = '''        self.dig_progress = None; self.look_mode = False
        self.auto_dig_dir = None
        self.recipes = load_recipes(); self.items = items_mod.load_items()'''
src = apply_one(src, old, new, "2/4 new_game 加 auto_dig_dir")

# 3. load_game 同步
old = '''        self.place_mode = None; self.last_place = None
        self.place_item_name = None; self.last_place_item_name = None
        self.dig_progress = None; self.look_mode = False'''
new = '''        self.place_mode = None; self.last_place = None
        self.place_item_name = None; self.last_place_item_name = None
        self.dig_progress = None; self.look_mode = False
        self.auto_dig_dir = None'''
src = apply_one(src, old, new, "3/4 load_game 加 auto_dig_dir")

# 4. run() 主循环：非方向键时清除 auto_dig_dir，方向键时记录并自动挖掘
old = '''            if key in DIRECTIONS:
                dx, dy = DIRECTIONS[key]; self.try_move_or_dig(dx, dy); acted = True
            if acted:'''
new = '''            if key in DIRECTIONS:
                dx, dy = DIRECTIONS[key]
                self.auto_dig_dir = (dx, dy)
                self.try_move_or_dig(dx, dy); acted = True
            elif self.auto_dig_dir and self.dig_progress and self.dig_progress["remaining"] > 0:
                # 持续挖掘：没有新按键但挖掘未完成，继续挖同一格
                dx, dy = self.auto_dig_dir
                self.try_move_or_dig(dx, dy); acted = True
            else:
                self.auto_dig_dir = None
            if acted:'''
src = apply_one(src, old, new, "4/4 run() 自动连续挖掘")

fp.write_text(src, "utf-8")
print("\n完成。按住方向键不放即可连续挖掘，松手自动停止。")

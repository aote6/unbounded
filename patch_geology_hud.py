#!/usr/bin/env python3
"""HUD 显示地质层名称，替代'第X层'"""
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

# 1. 添加地质层名称判定函数
old = '''    def _get_time_of_day(self):'''
new = '''    def _get_geology_zone(self, y):
        """根据 y 坐标返回地质层名称。"""
        if y > -8:
            return "地表沉积层"
        elif y > -25:
            return "浅层沉积岩"
        elif y > -45:
            return "热液矿脉带"
        elif y > -70:
            return "岩浆侵入带"
        else:
            return "深部变质基底"

    def _get_time_of_day(self):'''
src = apply_one(src, old, new, "1/2 添加地质层判定函数")

# 2. HUD 显示地质层而非"第X层"
old = '''        s1 = f"[{time_name}] 第{self.player_z}层 | {hp_str} | 技能 {sk_str} | ({self.player_x},{self.player_y})"'''
new = '''        zone = self._get_geology_zone(self.player_y)
        s1 = f"[{time_name}] {zone} | {hp_str} | 技能 {sk_str} | ({self.player_x},{self.player_y})"'''
src = apply_one(src, old, new, "2/2 HUD 显示地质层名称")

fp.write_text(src, "utf-8")
print("\n完成。HUD 现在根据 y 坐标显示地质层名称。")

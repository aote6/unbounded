#!/usr/bin/env python3
"""
一次性修复脚本 —— 在项目根目录下运行:
    python3 fix_crafting_bug.py

修复内容:
1. ui/states/crafting_state.py: 合成装备类物品时 mat / affix_chance
   未定义导致的 NameError 崩溃 (34个装备配方全部受影响)
2. main.py: 删除已被状态机取代的 crafting_menu/equipment_menu 死代码
   及其 import
3. main.py: 修复 f-string 嵌套同种引号的语法兼容性问题（需要 Python 3.12+
   才能跑，改成兼容写法）
4. 删除已经没有任何调用路径的 ui/equipment_ui.py、ui/crafting_ui.py

会先把改动的文件备份成 .bak，改错了可以随时恢复。
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent

PATCHES = [
    {
        "file": "ui/states/crafting_state.py",
        "old": '            arch = result_def.get("archetype")\n'
               '            if affix_chance > 0 and random.random() < affix_chance:',
        "new": '            arch = result_def.get("archetype")\n'
               '            mat = result_def.get("material")\n'
               '            mat = ORE_TO_MATERIAL.get(mat, mat)\n'
               '            affix_chance = result_def.get("affix_chance", 0.0)\n'
               '            if affix_chance > 0 and random.random() < affix_chance:',
    },
    {
        "file": "main.py",
        "old": 'from systems.save_system import build_save_data, apply_load_data\n'
               'from ui.equipment_ui import equipment_menu\n'
               'from ui.game_renderer import draw\n'
               'from ui.crafting_ui import crafting_menu\n'
               'from systems.tag_system import load_rules, check_interaction',
        "new": 'from systems.save_system import build_save_data, apply_load_data\n'
               'from ui.game_renderer import draw\n'
               'from systems.tag_system import load_rules, check_interaction',
    },
    {
        "file": "main.py",
        "old": '# ═══════════════════════════════════\n'
               '# 合成菜单\n'
               '# ═══════════════════════════════════\n'
               'def crafting_menu(stdscr, game):\n'
               '    from ui.crafting_ui import crafting_menu as _ui\n'
               '    _ui(stdscr, game)\n'
               '# ═══════════════════════════════════\n'
               '# 装备菜单\n'
               '# ═══════════════════════════════════\n'
               'def equipment_menu(stdscr, game):\n'
               '    from ui.equipment_ui import equipment_menu as _ui\n'
               '    _ui(stdscr, game)\n'
               '\n'
               '# ═══════════════════════════════════\n'
               '\n'
               'DIRECTIONS = {',
        "new": 'DIRECTIONS = {',
    },
    {
        "file": "main.py",
        "old": '                info += f" | {mon["name"]} HP:{mon["hp"]}/{mon["max_hp"]}"',
        "new": "                info += f\" | {mon['name']} HP:{mon['hp']}/{mon['max_hp']}\"",
    },
]

FILES_TO_DELETE = [
    "ui/equipment_ui.py",
    "ui/crafting_ui.py",
]


def apply_patches():
    touched = set()
    for p in PATCHES:
        path = ROOT / p["file"]
        if not path.exists():
            print(f"[跳过] 找不到文件: {p['file']}")
            continue
        text = path.read_text(encoding="utf-8")
        if p["old"] not in text:
            if p["new"] in text:
                print(f"[已是最新] {p['file']} 这处改动看起来已经打过了，跳过。")
            else:
                print(f"[!] 在 {p['file']} 里没找到预期的旧代码，可能文件内容和预期不一致，"
                      f"这处改动跳过，请手动检查。")
            continue
        if path not in touched:
            shutil.copy(path, str(path) + ".bak")
            touched.add(path)
        text = text.replace(p["old"], p["new"], 1)
        path.write_text(text, encoding="utf-8")
        print(f"[已修复] {p['file']}")

    for f in FILES_TO_DELETE:
        path = ROOT / f
        if path.exists():
            shutil.copy(path, str(path) + ".bak")
            path.unlink()
            print(f"[已删除死代码] {f} (备份为 {f}.bak)")
        else:
            print(f"[跳过] 找不到文件，可能已经删过: {f}")


if __name__ == "__main__":
    apply_patches()
    print("\n完成。建议跑一下: python3 -m py_compile main.py ui/states/crafting_state.py")

import re

def patch_file(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new, 1)
    # 删文件末尾空行
    content = content.rstrip('\n') + '\n'
    # 删空白行中的空格
    content = re.sub(r'^ +$', '', content, flags=re.MULTILINE)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[完成] {path}")

# save_manager.py: 删未使用的 import
patch_file("systems/core/save_manager.py", [
    ("import shutil\nimport json\nimport os\nimport logging",
     "import shutil\nimport json\nimport os\nimport logging"),
    ("from data_mappings import load_recipes\n", ""),
    ("import items as items_mod\n", ""),
    ("import monsters as monsters_mod\n", ""),
])

# inventory_actions.py: 删未使用的导入（只保留注释）
patch_file("systems/gameplay/inventory_actions.py", [
    ('''from systems.entity.monster_index import (
    build_monster_index,
    monster_moved,
    add_monster,
    remove_monster,
)''',
    '''# 怪物索引函数由 combat_system/monster_ai 等调用方直接从
# systems.entity.monster_index 导入，这里不再中转。'''),
])

# main_menu_state.py: 删重复的 COLOR 导入
patch_file("ui/states/main_menu_state.py", [
    ("from codex import COLOR\n", ""),
    ("COLOR = {\n", ""),
])

# test_save_roundtrip.py: 删未使用的导入
patch_file("tests/test_save_roundtrip.py", [
    ("import json\n", ""),
    ("import tempfile\n", ""),
    ("import os\n", ""),
])

# 修复行太长 - noise_engine.py
patch_file("systems/world/noise_engine.py", [
    ("    corners = (_hash_uniform(x - 1,\n                             y - 1,\n                             seed) + _hash_uniform(x + 1,\n                                                   y - 1,\n                                                   seed) + _hash_uniform(x - 1,\n                                                                         y + 1,\n                                                                         seed) + _hash_uniform(x + 1,\n                                                                                               y + 1,\n                                                                                               seed)) / 16",
     "    c1 = _hash_uniform(x - 1, y - 1, seed)\n    c2 = _hash_uniform(x + 1, y - 1, seed)\n    c3 = _hash_uniform(x - 1, y + 1, seed)\n    c4 = _hash_uniform(x + 1, y + 1, seed)\n    corners = (c1 + c2 + c3 + c4) / 16"),
])

# 修复行太长 - game_renderer.py (120字符)
patch_file("ui/game_renderer.py", [
    ("                    logger.warning(\n                        f\"地图渲染越界: row={row}, x={x}, text_len={len(text)}, \"\n                        f\"screen=({max_y},{max_x})\"\n                    )",
     "                    logger.warning(\n                        f\"地图渲染越界: row={row}, x={x}, \"\n                        f\"text_len={len(text)}, screen=({max_y},{max_x})\"\n                    )"),
    ("            if screen_h > VIEW_HEIGHT + 6:\n                logger.warning(f\"HUD 渲染异常（屏幕高度足够却报错）: {e}, screen_h={screen_h}\")",
     "            if screen_h > VIEW_HEIGHT + 6:\n                logger.warning(\n                    f\"HUD 渲染异常（屏幕高度足够却报错）: \"\n                    f\"{e}, screen_h={screen_h}\"\n                )"),
])

# 修复行太长 - main_menu_state.py (110字符，改内容)
patch_file("ui/states/main_menu_state.py", [
    ("游戏已保存。", "已保存。"),
])

# 修复行太长 - 测试文件
patch_file("tests/smoke_test_full.py", [
    ("        self.assertTrue(any(m['name'] == '史莱姆' for m in game.monsters), \"应该生成史莱姆\")",
     "        has_slime = any(m['name'] == '史莱姆' for m in game.monsters)\n        self.assertTrue(has_slime, \"应该生成史莱姆\")"),
])

patch_file("tests/test_inventory.py", [
    ("        self.assertEqual(inv.count('木材'), 3, \"添加5个木材后应该减去3个还剩2个\")",
     "        self.assertEqual(inv.count('木材'), 3,\n                         \"添加5个木材后应该减去3个还剩2个\")"),
])

patch_file("tests/test_simulation.py", [
    ("        self.assertLess(abs(len(game.monsters) - initial_count) / max(1, initial_count), 0.5,",
     "        ratio = abs(len(game.monsters) - initial_count) / max(1, initial_count)\n        self.assertLess(ratio, 0.5,"),
])

# 修复多余空行
patch_file("systems/gameplay/player_action.py", [
    ("\n\n\n", "\n\n"),
])

patch_file("systems/world/room_system.py", [
    ("\n\n\n", "\n\n"),
])

print("\n全部完成。")

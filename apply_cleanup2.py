def patch_file(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new, 1)
    content = content.rstrip('\n') + '\n'
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[完成] {path}")

# monsters.py: 删末尾空行
patch_file("monsters.py", [("\n\n", "\n")])

# 行太长 - inventory_actions.py
patch_file("systems/gameplay/inventory_actions.py", [
    ("def count_equipment(game, name):\n    return sum(1 for _, item in game.inventory.all_items() if item.item_type ==\n               ItemCategory.EQUIPMENT and item.instance and item.instance.name == name)",
     "def count_equipment(game, name):\n    return sum(\n        1 for _, item in game.inventory.all_items()\n        if item.item_type == ItemCategory.EQUIPMENT\n        and item.instance and item.instance.name == name\n    )"),
])

# 行太长 - smoke_test_full.py
patch_file("tests/smoke_test_full.py", [
    ("        has_slime = any(m['name'] == '史莱姆' for m in game.monsters)\n        self.assertTrue(has_slime, \"应该生成史莱姆\")",
     "        has_slime = any(\n            m['name'] == '史莱姆' for m in game.monsters\n        )\n        self.assertTrue(has_slime, \"应该生成史莱姆\")"),
])

# 行太长 - test_inventory.py
patch_file("tests/test_inventory.py", [
    ("        self.assertEqual(inv.count('木材'), 3,\n                         \"添加5个木材后应该减去3个还剩2个\")",
     "        msg = \"添加5个木材后应该减去3个还剩2个\"\n        self.assertEqual(inv.count('木材'), 3, msg)"),
])

# 行太长 - test_simulation.py
patch_file("tests/test_simulation.py", [
    ("        ratio = abs(len(game.monsters) - initial_count) / max(1, initial_count)\n        self.assertLess(ratio, 0.5,",
     "        ratio = abs(len(game.monsters) - initial_count)\n        ratio /= max(1, initial_count)\n        self.assertLess(ratio, 0.5,"),
])

# 行太长 - game_renderer.py (120, 113)
patch_file("ui/game_renderer.py", [
    ("                logger.warning(\n                    f\"地图渲染越界: row={row}, x={x}, \"\n                    f\"text_len={len(text)}, screen=({max_y},{max_x})\"\n                )",
     "                logger.warning(\n                    f\"地图渲染越界: row={row}, x={x}\"\n                    f\", text_len={len(text)}\"\n                    f\", screen=({max_y},{max_x})\"\n                )"),
    ("                logger.warning(\n                    f\"HUD 渲染异常（屏幕高度足够却报错）: \"\n                    f\"{e}, screen_h={screen_h}\"\n                )",
     "                logger.warning(\n                    f\"HUD 渲染异常: {e}\"\n                    f\", screen_h={screen_h}\"\n                )"),
])

# 行太长 - main_menu_state.py (110)
patch_file("ui/states/main_menu_state.py", [
    ("已保存。", "游戏已保存。"),
])

# 多余空行
patch_file("systems/gameplay/player_action.py", [("\n\n\n", "\n\n")])
patch_file("systems/world/room_system.py", [("\n\n\n", "\n\n")])

# E302 空行
patch_file("systems/gameplay/player_action.py", [
    ('"""玩家动作系统', '\n"""玩家动作系统'),
])
patch_file("systems/world/room_system.py", [
    ('"""房间检测系统', '\n"""房间检测系统'),
])
patch_file("tests/test_save_roundtrip.py", [
    ('def test_save_roundtrip', '\n\ndef test_save_roundtrip'),
])

print("\n完成")

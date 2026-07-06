#!/usr/bin/env python3
"""补上水/树在 tile_props 和 main 中的定义"""
from pathlib import Path

BASE = Path(__file__).parent

def apply_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        print(f"[跳过] {label}: 匹配 {count} 处（需1处）")
        return text
    print(f"[OK] {label}")
    return text.replace(old, new, 1)

# tile_props.py：导入 TILE_WATER, TILE_TREE
fp = BASE / "tile_props.py"
src = fp.read_text("utf-8")
old = "    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,\n)"
new = "    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,\n    TILE_WATER, TILE_TREE,\n)"
src = apply_one(src, old, new, "tile_props 导入水/树")

# 加水/树属性
old = '''    TILE_OBSIDIAN: {
        "name": "黑曜石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 10.0,
        "drop": "黑曜石", "char": "\\u25a0",
    },
}'''
new = '''    TILE_OBSIDIAN: {
        "name": "黑曜石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 10.0,
        "drop": "黑曜石", "char": "\\u25a0",
    },
    TILE_WATER: {
        "name": "水域", "passable": False, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 999.0,
        "drop": None, "char": "~",
    },
    TILE_TREE: {
        "name": "树木", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 1.5,
        "drop": "泥土", "char": "\\u2663",
    },
}'''
src = apply_one(src, old, new, "tile_props 水/树属性")
fp.write_text(src, "utf-8")

# main.py：导入和字符
fp2 = BASE / "main.py"
src2 = fp2.read_text("utf-8")
old = "    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,\n)"
new = "    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,\n    TILE_WATER, TILE_TREE,\n)"
src2 = apply_one(src2, old, new, "main 导入水/树")

old = '''    "楼梯上": "<",
}'''
new = '''    "楼梯上": "<",
    TILE_WATER: "~",
    TILE_TREE: "\\u2663",
}'''
src2 = apply_one(src2, old, new, "main TILE_CHARS 水/树")
fp2.write_text(src2, "utf-8")

print("\n修复完成，可以启动了。")

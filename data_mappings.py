"""游戏数据映射表——从 config.py 拆分出来，独立维护。"""

# ═══════════════════════════════════
# 矿石 → 材质映射（合成装备时使用）
# ═══════════════════════════════════
ORE_TO_MATERIAL = {
    "石头": "石头", "泥土": "皮",
    "煤矿": "铁",
    "铜矿石": "石头",
    "铁矿石": "铁",
    "银矿石": "铁",
    "金矿石": "钢",
    "钻石原石": "黑曜石",
    "硫磺": "骨",
    "盐矿石": "石头",
    "黏土": "皮",
    "沙子": "石头",
    "石灰岩": "石头",
    "大理石": "铁",
    "花岗岩": "铁",
    "黑曜石": "黑曜石",
    "史莱姆凝胶": "骨",
}

import json
from pathlib import Path

RECIPES_FILE = Path(__file__).parent / "data" / "recipes.json"

def load_recipes():
    """加载合成配方。"""
    if not RECIPES_FILE.exists():
        print(f"[recipes] 文件不存在: {RECIPES_FILE}")
        return {}
    try:
        with open(RECIPES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        import logging; logging.warning(f"recipes.json 解析失败: {e}")
        return {}

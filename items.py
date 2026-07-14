""" items.py 道具与装备系统。数据从 data/items.json 加载。"""
from inventory import ItemCategory
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
ITEMS_FILE = BASE_DIR / "data" / "items.json"


def load_items():
    if not ITEMS_FILE.exists():
        print(f"[items] 文件不存在: {ITEMS_FILE}")
        return {}
    try:
        with open(ITEMS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        import logging
        logging.warning(f"items.json 解析失败: {e}")
        return {}


def is_placeable(items, name):
    return items.get(name, {}).get("type") == ItemCategory.PLACEABLE


def get_place_tile(items, name):
    """放置后tile名固定等于物品名（key）。
    历史上曾有独立的place_tile字段允许两者不同，但全项目数据审计
    (2026-07-14)确认16个placeable物品100%二者一致、从未被实际用到过
    这个自由度，字段已删除以消除两套key体系分裂的隐患，此函数保留
    仅为兼容调用方签名。"""
    return name


def get_drop_on_mine(items, name):
    return items.get(name, {}).get("drop_on_mine", {})

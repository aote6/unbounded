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
    return items.get(name, {}).get("place_tile", name)


def get_drop_on_mine(items, name):
    return items.get(name, {}).get("drop_on_mine", {})

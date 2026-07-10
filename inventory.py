""" inventory.py 统一背包系统。所有物品通过统一接口存取。"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

# 物品类型枚举
from enum import Enum


class ItemCategory(str, Enum):
    MATERIAL = "material"
    PLACEABLE = "placeable"
    EQUIPMENT = "equipment"
    CONSUMABLE = "consumable"
    CONTAINER = "container"


@dataclass
class InventoryItem:
    """背包中的单个物品条目"""
    item_id: str
    item_type: str  # material / placeable / equipment / consumable
    count: int = 1  # 堆叠数量（equipment类型始终为1）
    instance: Optional[Any] = None  # 装备实例数据（仅equipment类型）
    properties: Dict[str, Any] = field(default_factory=dict)  # 扩展属性


class Inventory:
    """统一背包。内部是一个 dict，key=物品名，value=InventoryItem。"""

    def __init__(self):
        self._items: Dict[str, InventoryItem] = {}
        self._id_counter = 0

    # ── 核心操作 ──
    def add(
            self,
            item_id: str,
            count: int = 1,
            item_type: str = ItemCategory.MATERIAL,
            instance: Any = None,
            **kwargs):
        """添加物品。已存在的堆叠物品自动合并。"""
        if item_id in self._items:
            existing = self._items[item_id]
            if existing.item_type in (
                    ItemCategory.MATERIAL,
                    ItemCategory.PLACEABLE,
                    ItemCategory.CONSUMABLE):
                existing.count += count
            else:
                # equipment 类型不堆叠，用编号区分
                new_id = f"{item_id}#{self._next_id()}"
                self._items[new_id] = InventoryItem(
                    item_id=item_id, item_type=item_type,
                    count=1, instance=instance, properties=kwargs
                )
                return new_id
        else:
            self._items[item_id] = InventoryItem(
                item_id=item_id, item_type=item_type,
                count=count, instance=instance, properties=kwargs
            )
        return item_id

    def remove(self, item_id: str, count: int = 1) -> bool:
        """移除物品。返回是否成功。"""
        if item_id not in self._items:
            return False
        item = self._items[item_id]
        if item.count < count:
            return False
        item.count -= count
        if item.count <= 0:
            del self._items[item_id]
        return True

    def has(self, item_id: str, count: int = 1) -> bool:
        """检查是否有足够数量的物品。"""
        item = self._items.get(item_id)
        return item is not None and item.count >= count

    def count(self, item_id: str) -> int:
        """获取物品数量。"""
        item = self._items.get(item_id)
        return item.count if item else 0

    # ── 查询 ──
    def items_of_type(self, item_type: str) -> List[str]:
        """获取指定类型的所有物品ID。"""
        return [item_id for item_id, item in self._items.items()
                if item.item_type == item_type]

    def get_materials(self) -> Dict[str, int]:
        """获取所有堆叠材料的 {名称: 数量} 字典（兼容旧代码）。"""
        return {
            item.item_id: item.count for item in self._items.values() if item.item_type in (
                ItemCategory.MATERIAL,
                ItemCategory.PLACEABLE,
                ItemCategory.CONSUMABLE)}

    def get_equipment(self) -> List[Any]:
        """获取所有装备实例列表（兼容旧代码）。"""
        return [item.instance for item in self._items.values(
        ) if item.item_type == ItemCategory.EQUIPMENT and item.instance is not None]

    def is_placeable(self, item_id: str) -> bool:
        """检查物品是否可放置。"""
        item = self._items.get(item_id)
        return item is not None and item.item_type == ItemCategory.PLACEABLE

    # ── 迭代 ──
    def all_items(self):
        """遍历所有物品。"""
        return self._items.items()

    def __len__(self):
        return len(self._items)

    def total_count(self) -> int:
        """总物品数量（含堆叠）。"""
        return sum(item.count for item in self._items.values())

    # ── 存档 ──
    def to_dict(self) -> dict:
        """序列化为 JSON 兼容的 dict。"""
        result = {}
        for item_id, item in self._items.items():
            data = {
                "item_id": item.item_id,
                "item_type": item.item_type,
                "count": item.count,
            }
            if item.instance is not None:
                if hasattr(item.instance, 'to_dict'):
                    data["instance"] = item.instance.to_dict()
                else:
                    data["instance"] = item.instance
            if item.properties:
                data["properties"] = item.properties
            result[item_id] = data
        return result

    @classmethod
    def from_dict(cls, data: dict) -> "Inventory":
        """从 dict 反序列化。"""
        inv = cls()
        for item_id, item_data in data.items():
            instance = item_data.get("instance")
            if instance and isinstance(instance, dict) and "name" in instance:
                # 是装备实例
                from equipment import EquipmentInstance
                instance = EquipmentInstance.from_dict(instance)
            inv._items[item_id] = InventoryItem(
                item_id=item_data.get("item_id", item_id),
                item_type=item_data.get("item_type", ItemCategory.MATERIAL),
                count=item_data.get("count", 1),
                instance=instance,
                properties=item_data.get("properties", {})
            )
        # 恢复 _id_counter 到最大值+1，避免读档后ID碰撞
        max_id = 0
        for k in inv._items:
            if "#" in k:
                try:
                    n = int(k.split("#")[1])
                    if n > max_id:
                        max_id = n
                except ValueError:
                    pass
        inv._id_counter = max_id
        return inv

    def _next_id(self):
        """生成唯一编号。"""
        self._id_counter += 1
        return self._id_counter


# 单例（可选）
_inventory_instance = None


def get_inventory() -> Inventory:
    global _inventory_instance
    if _inventory_instance is None:
        _inventory_instance = Inventory()
    return _inventory_instance


def clear_inventory_instance():
    global _inventory_instance
    _inventory_instance = None

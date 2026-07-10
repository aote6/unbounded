"""Entity 统一基类 — 所有游戏实体的抽象。

Player / NPC / Monster / Animal 共享：
- 位置 (x, y)
- 生命值 (hp, max_hp)
- 属性字典 (stats) — 可扩展
- 行为列表 (behaviors) — Goal → Behavior → Action
- 标签 (tags)

差异在数据，不在类定义。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class Entity:
    """统一实体基类。"""
    entity_id: str                    # 唯一标识
    name: str                         # 显示名称
    category: str                     # player | monster | npc | animal
    x: int = 0
    y: int = 0
    char: str = "?"                   # 渲染字符
    hp: int = 10
    max_hp: int = 10
    stats: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    faction: str = "neutral"

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    @property
    def pos(self) -> tuple:
        return (self.x, self.y)

    def take_damage(self, amount: int) -> int:
        """受到伤害，返回实际伤害值。"""
        actual = min(amount, self.hp)
        self.hp -= actual
        return actual

    def heal(self, amount: int) -> int:
        """恢复生命，返回实际恢复值。"""
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual

    def move_to(self, x: int, y: int):
        """移动到新位置。"""
        self.x = x
        self.y = y

    def to_dict(self) -> dict:
        """序列化为字典（兼容旧存档格式）。"""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "category": self.category,
            "x": self.x, "y": self.y,
            "char": self.char,
            "hp": self.hp, "max_hp": self.max_hp,
            "stats": self.stats,
            "tags": self.tags,
            "faction": self.faction,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """从字典反序列化。"""
        return cls(
            entity_id=data.get("entity_id", data.get("name", "unknown")),
            name=data.get("name", "?"),
            category=data.get("category", "monster"),
            x=data.get("x", 0), y=data.get("y", 0),
            char=data.get("char", "?"),
            hp=data.get("hp", 10), max_hp=data.get("max_hp", 10),
            stats=data.get("stats", {}),
            tags=data.get("tags", []),
            faction=data.get("faction", "hostile"),
        )


# ═══════════════════════════════════
# 工厂函数：从 monsters.json 创建 Entity
# ═══════════════════════════════════

def monster_to_entity(name: str, x: int, y: int, monster_data: dict) -> Entity:
    """将旧版 monster 字典转换为 Entity。
    
    暂时保留此适配层，等怪物系统完全迁移后删除。
    """
    t = monster_data.get(name, {})
    return Entity(
        entity_id=f"monster_{name}_{x}_{y}",
        name=name,
        category="monster",
        x=x, y=y,
        char=t.get("char", "?"),
        hp=t.get("hp", 10),
        max_hp=t.get("hp", 10),
        stats={
            "attack_power": tuple(t.get("attack_power", [1, 3])),
            "hit_chance": t.get("hit_chance", 0.7),
            "vision": t.get("vision", 6),
            "flee_at_hp_ratio": t.get("flee_at_hp_ratio", 0.3),
            "scores": t.get("scores", {}),
            "drop": t.get("drop", {}),
            "corpse_tile": t.get("corpse_tile"),
            "split_into": t.get("split_into"),
            "special_behavior": t.get("special_behavior"),
        },
        tags=t.get("tags", []),
        faction=t.get("faction", "hostile"),
    )

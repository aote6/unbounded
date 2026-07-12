"""Entity 统一基类 — 所有游戏实体的抽象。"""
from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class Entity:
    """统一实体基类。"""
    entity_id: str
    name: str
    category: str
    x: int = 0
    y: int = 0
    char: str = "?"
    hp: int = 10
    max_hp: int = 10
    stats: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    faction: str = "neutral"

    @property
    def is_alive(self) -> bool:
        """Whether the entity's HP is greater than zero."""
        return self.hp > 0

    @property
    def pos(self) -> tuple:
        """The entity's current (x, y) position."""
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


class Monster(dict):
    """兼容旧代码的怪物对象：既是字典又是 Entity。"""
    __slots__ = ('_entity',)

    def __init__(self, entity: Entity, extra: dict = None):
        """Initialize a Monster wrapper around an Entity.

        Args:
            entity: The underlying Entity instance to wrap.
            extra: Optional dict of additional key-value pairs.
        """
        self._entity = entity
        d = {
            "name": entity.name, "char": entity.char,
            "x": entity.x, "y": entity.y,
            "hp": entity.hp, "max_hp": entity.max_hp,
            "faction": entity.faction, "tags": entity.tags,
        }
        if extra:
            d.update(extra)
        super().__init__(d)

    def __getattr__(self, key):
        """Look up an attribute on the wrapped Entity, falling back to dict keys."""
        if hasattr(self._entity, key):
            return getattr(self._entity, key)
        if key in self:
            return self[key]
        raise AttributeError(key)

    def __setattr__(self, key, value):
        """Set an attribute, syncing the value to the wrapped Entity when applicable."""
        if key in ('_entity',) or key in self.__slots__:
            super().__setattr__(key, value)
        elif hasattr(self._entity, key):
            setattr(self._entity, key, value)
            if key in self:
                self[key] = value
        else:
            self[key] = value

    def __getitem__(self, key):
        """Get a dict item by key."""
        return dict.__getitem__(self, key)

    def __setitem__(self, key, value):
        """Set a dict item, syncing selected keys back to the wrapped Entity."""
        dict.__setitem__(self, key, value)
        if key == "x":
            self._entity.x = value
        elif key == "y":
            self._entity.y = value
        elif key == "hp":
            self._entity.hp = value
        elif key == "max_hp":
            self._entity.max_hp = value

    def get(self, key, default=None):
        """Get a dict value with a default fallback."""
        return super().get(key, default)


def monster_to_entity(name: str, x: int, y: int, monster_data: dict) -> Monster:
    """创建怪物：返回兼容字典+属性的 Monster 对象。"""
    t = monster_data.get(name, {})
    entity = Entity(
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
        },
        tags=t.get("tags", []),
        faction=t.get("faction", "hostile"),
    )
    extra = {
        "scores": t.get("scores", {}),
        "drop": t.get("drop", {}),
        "corpse_tile": t.get("corpse_tile"),
        "split_into": t.get("split_into"),
        "special_behavior": t.get("special_behavior"),
        "properties": t.get("properties", {}),
        "attack_power": tuple(t.get("attack_power", [1, 3])),
        "hit_chance": t.get("hit_chance", 0.7),
        "vision": t.get("vision", 6),
        "flee_at_hp_ratio": t.get("flee_at_hp_ratio", 0.3),
    }
    return Monster(entity, extra)

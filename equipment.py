"""装备实例数据类"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EquipmentInstance:
    """装备实例。独立于模板数据，每个实例拥有自己的属性。"""
    name: str
    slot: Optional[str] = None
    attack_bonus: int = 0
    defense_bonus: int = 0
    tool_bonus: int = 0
    damage_min: int = 0
    damage_max: int = 0
    hit_bonus: int = 0
    affixes: List[str] = field(default_factory=list)
    on_attack: List[str] = field(default_factory=list)
    lifesteal: int = 0
    speed_bonus: int = 0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """序列化为普通 dict（用于 JSON 存档）。"""
        return {
            "name": self.name, "slot": self.slot,
            "attack_bonus": self.attack_bonus, "defense_bonus": self.defense_bonus,
            "tool_bonus": self.tool_bonus, "damage_min": self.damage_min,
            "damage_max": self.damage_max, "hit_bonus": self.hit_bonus,
            "affixes": self.affixes, "on_attack": self.on_attack,
            "lifesteal": self.lifesteal, "speed_bonus": self.speed_bonus,
            "tags": self.tags,
        }

    def clone(self) -> "EquipmentInstance":
        """深拷贝，杜绝引用污染（箱子存取/物品拆分时使用）。"""
        return EquipmentInstance(
            name=self.name, slot=self.slot,
            attack_bonus=self.attack_bonus, defense_bonus=self.defense_bonus,
            tool_bonus=self.tool_bonus, damage_min=self.damage_min,
            damage_max=self.damage_max, hit_bonus=self.hit_bonus,
            affixes=list(self.affixes), on_attack=list(self.on_attack),
            lifesteal=self.lifesteal, speed_bonus=self.speed_bonus,
            tags=list(self.tags),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "EquipmentInstance":
        """从 dict 反序列化。"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

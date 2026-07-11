from systems.combat.combat_system import kill_monster
"""Buff系统：统一管理所有实体（玩家+怪物）的状态效果。
from systems.combat.combat_system import kill_monster
from systems.combat.combat_system import kill_monster

替换原有的三种格式：
- on_fire (int)        → Buff("on_fire", ...)
- burning (dict)       → Buff("burning", ...)
- poisoned (int)       → Buff("poisoned", ...)

设计原则：
- BuffManager 挂载在 Game 实例上 (game.buff_manager)
- 支持玩家和怪物统一接入
- 兼容旧存档：读取时自动转换旧格式
"""

from dataclasses import dataclass
from typing import Callable, Any, Optional


@dataclass
class Buff:
    """单个状态效果实例。"""
    name: str                    # "on_fire" / "burning" / "poisoned"
    duration: int                # 剩余回合数
    damage_per_turn: int = 0     # 每回合伤害
    source: str = "unknown"      # "fire" / "poison" / "bleed"

    # 可选钩子（预留给 M21+ 扩展）
    on_apply: Optional[Callable] = None
    on_remove: Optional[Callable] = None

    def tick_damage(self) -> int:
        """返回本回合造成的伤害。"""
        return self.damage_per_turn

    def expired(self) -> bool:
        return self.duration <= 0


class BuffManager:
    """管理实体的 Buff 列表。

    用法：
        manager = BuffManager()
        manager.add(entity, "burning", duration=5, damage_per_turn=2, source="fire")
        manager.tick_all(game)  # 每回合调用
    """

    def __init__(self):
        # {id(entity): [Buff, ...]}
        self._buffs: dict[int, list[Buff]] = {}
        # 玩家 eid 缓存
        self._player_eid: Optional[int] = None

    # ── 公共 API ──

    def add(self, entity, name: str, duration: int,
            damage_per_turn: int = 0, source: str = "unknown"):
        """给实体添加一个 Buff。同名 Buff 会刷新叠加（非堆叠）。

        entity 可以是怪物 dict 或 Game 实例（玩家）。
        """
        buff = Buff(name=name, duration=duration,
                    damage_per_turn=damage_per_turn, source=source)
        eid = id(entity)
        if eid not in self._buffs:
            self._buffs[eid] = []

        # 同名替换：移除旧的同名 Buff
        self._buffs[eid] = [b for b in self._buffs[eid] if b.name != name]
        self._buffs[eid].append(buff)

    def get_buffs(self, entity) -> list[Buff]:
        """获取实体的所有 Buff。"""
        return self._buffs.get(id(entity), [])

    def remove_entity(self, entity):
        """实体死亡/移除时清理。"""
        self._buffs.pop(id(entity), None)

    # ── 每回合处理 ──

    def tick_all(self, game) -> list[str]:
        """处理所有实体的 Buff 回合效果。返回消息列表。

        调用时机：advance_turn() 中，替代 tick_status_effects()。
        支持怪物（dict with 'hp'）和玩家（Game object with 'player_hp'）。
        """
        msgs = []
        dead_entities = set()
        # 缓存玩家 eid
        self._player_eid = id(game)

        for eid, buffs in list(self._buffs.items()):
            entity = self._find_entity(game, eid)
            if entity is None:
                continue

            # 获取实体的 hp 引用方式
            is_player = (eid == self._player_eid)

            for buff in buffs[:]:
                dmg = buff.tick_damage()
                if dmg > 0:
                    if is_player:
                        game.player_hp -= dmg
                    else:
                        entity["hp"] -= dmg

                buff.duration -= 1

                if buff.expired():
                    buffs.remove(buff)

                # 检查死亡
                hp = game.player_hp if is_player else entity.get("hp", 0)
                if hp <= 0:
                    dead_entities.add(eid)
                    if not is_player:
                        kill_monster(game, entity, cause=buff.source)
                    # 玩家死亡在 check_death 中处理，这里只做标记
                    break

            if eid in self._buffs and not self._buffs[eid]:
                del self._buffs[eid]

        return msgs

    # ── 内部辅助 ──

    def _find_entity(self, game, eid) -> Optional[Any]:
        """根据 id 找到实体（玩家或怪物）。"""
        if eid == self._player_eid:
            return game  # 返回 game 作为"玩家实体"
        for m in game.monsters:
            if id(m) == eid:
                return m
        return None

    # ── 旧存档兼容 ──

    def migrate_legacy(self, entity):
        """将实体的旧格式状态转换为 Buff。

        支持格式：
        - entity["on_fire"] = 3
        - entity["burning"] = {"duration": 3, "damage_per_turn": 2}
        - entity["poisoned"] = 3
        """
        # 旧版 on_fire
        of = entity.get("on_fire", 0)
        if isinstance(of, int) and of > 0:
            self.add(entity, "on_fire", duration=of,
                     damage_per_turn=2, source="fire")
            del entity["on_fire"]

        # 新版 burning（标签触发）
        burn = entity.get("burning")
        if isinstance(burn, dict) and burn.get("duration", 0) > 0:
            self.add(entity, "burning", duration=burn["duration"],
                     damage_per_turn=burn.get("damage_per_turn", 2),
                     source="fire")
            del entity["burning"]

        # 中毒
        poi = entity.get("poisoned", 0)
        if isinstance(poi, int) and poi > 0:
            self.add(entity, "poisoned", duration=poi,
                     damage_per_turn=1, source="poison")
            del entity["poisoned"]


def create_buff_manager() -> BuffManager:
    """工厂函数，创建新的 BuffManager。"""
    return BuffManager()

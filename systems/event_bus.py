"""轻量事件总线：发布-订阅模式，解耦游戏逻辑。"""
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum, auto


class EventType(Enum):
    TURN_START = auto()       # 回合开始
    DAMAGE_DEALT = auto()      # 造成伤害（攻击者, 目标, 伤害值, 伤害类型）
    MONSTER_KILLED = auto()    # 怪物死亡（怪物, 死因）
    PLAYER_HEALED = auto()     # 玩家回血（回复量, 来源）
    STATUS_APPLIED = auto()    # 状态施加（目标, 状态名, 持续回合）
    TILE_CHANGED = auto()      # 地块变化（x, y, 旧tile, 新tile）


@dataclass
class GameEvent:
    type: EventType
    data: dict = field(default_factory=dict)
    handled: bool = False


class EventBus:
    """全局事件总线，单例模式。"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
        return cls._instance

    def subscribe(self, event_type: EventType, handler: Callable):
        """注册事件处理器。handler 接收 (GameEvent, game) 两个参数。"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event: GameEvent, game):
        """广播事件给所有注册的处理器。"""
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            handler(event, game)
            if event.handled:
                break  # 如果事件被标记为已处理，停止传播

    def clear(self):
        """清除所有注册（用于新游戏）。"""
        self._handlers.clear()

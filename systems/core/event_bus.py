"""轻量事件总线：发布-订阅模式，解耦游戏逻辑。"""
import logging
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum, auto

logger = logging.getLogger(__name__)


class EventType(Enum):
    TURN_START = auto()
    DAMAGE_DEALT = auto()
    MONSTER_KILLED = auto()
    PLAYER_HEALED = auto()
    STATUS_APPLIED = auto()
    TILE_CHANGED = auto()


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
        """注册事件处理器，handler 接收 (GameEvent, game)。"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def emit(self, event: GameEvent, game):
        """广播事件给所有注册的处理器。无订阅者时记录debug日志。"""
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            logger.debug(f"事件 {event.type.name} 无订阅者，已丢弃: {event.data}")
            return
        for handler in handlers:
            handler(event, game)
            if event.handled:
                break

    def clear(self):
        """清除所有注册（用于新游戏）。"""
        self._handlers.clear()

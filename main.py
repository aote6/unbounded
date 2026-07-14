from systems.core.save_manager import save_game as sys_save_game, load_game as sys_load_game
from systems.core.save_manager import new_game as sys_new_game
""" main.py —— 纯入口与顶级状态聚合。
    业务逻辑已完全迁移至 systems/ 和 ui/states/。
    底层数据隔离为 PlayerState/WorldState/UIState，
    通过 @property 保持向后兼容（game.player_x 仍可用）。
"""
import json
import curses
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple

# ── 数据与系统层导入 ──
from inventory import Inventory
from items import load_items
from monsters import load_monsters
from systems.entity.status_system import register as register_status
from systems.entity.buff_system import create_buff_manager
from systems.entity.tag_system import load_rules
from systems.gameplay import skill_system
from config import PLAYER_INITIAL_HP, SPAWN_INITIAL_COUNTDOWN, VIEW_WIDTH, VIEW_HEIGHT

BASE_DIR = Path(__file__).parent
logger = logging.getLogger(__name__)


def _setup_logging():
    from logging.handlers import RotatingFileHandler
    log_path = BASE_DIR / "unbounded_debug.log"
    handler = RotatingFileHandler(
        str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


# ═══════════════════════════════════
# 领域模型 (Domain Models)
# ═══════════════════════════════════

@dataclass
class PlayerState:
    """玩家核心数据：持久化边界（死亡后可保留装备/物品）"""
    x: int = 0
    y: int = 0
    z: int = 0
    hp: int = PLAYER_INITIAL_HP
    max_hp: int = PLAYER_INITIAL_HP
    skills: Dict[str, int] = field(default_factory=lambda: {
                                   "digging": 0, "combat": 0, "defense": 0})
    skill_levels: Dict[str, int] = field(
        default_factory=lambda: {"digging": 1, "combat": 1, "defense": 1})
    inventory: Inventory = field(default_factory=Inventory)
    equipment: Dict[str, Any] = field(default_factory=dict)

    def equipment_bonus(self, attr: str) -> int:
        return sum(
            getattr(
                inst,
                attr,
                0) or 0 for inst in self.equipment.values() if inst)


@dataclass
class WorldState:
    """世界运行状态：每次重生可重置"""
    map_data: Any = None
    seed: int = 0
    respawn_x: int = 0
    respawn_y: int = 0
    bed_x: Optional[int] = None
    bed_y: Optional[int] = None

    monsters: List[Any] = field(default_factory=list)
    monster_index: Dict[Tuple[int, int], Any] = field(default_factory=dict)
    spawn_counter: Dict[str, int] = field(
        default_factory=lambda: {"count": SPAWN_INITIAL_COUNTDOWN})

    corpses: Dict[Tuple[int, int], Any] = field(default_factory=dict)
    modified_tiles: Dict[Tuple[int, int], Any] = field(default_factory=dict)
    chests: Dict[Tuple[int, int], Any] = field(default_factory=dict)
    burning_tiles: Dict[Tuple[int, int], int] = field(default_factory=dict)
    found_specials: Set[Tuple[int, int]] = field(default_factory=set)


@dataclass
class UIState:
    """界面与交互临时状态。messages为队列，避免同回合多系统写message互相覆盖。"""
    messages: List[str] = field(default_factory=lambda: ["欢迎。世界无限延伸。hjkl 移动，c 合成，e 装备，d 挖掘，q 退出。"])
    cursor_x: int = 0
    cursor_y: int = 0
    place_mode: Optional[str] = None
    last_place: Optional[str] = None
    place_item_name: Optional[str] = None
    last_place_item_name: Optional[str] = None
    dig_progress: Optional[dict] = None
    look_mode: bool = False


@dataclass
class GoalState:
    """目标系统状态"""
    current: str = "build_first_room"
    completed: List[str] = field(default_factory=list)
    message_shown: bool = False


@dataclass
class LifeStats:
    """本局角色统计（死亡时结算进 legacy_system 的跨局遗产，不要与跨局遗产本身混淆）"""
    monsters_killed: int = 0
    blocks_placed: int = 0
    crafted: List[str] = field(default_factory=list)


# ═══════════════════════════════════
# 顶级容器
# ═══════════════════════════════════


class StaticDataRegistry:
    _instance = None

    def __init__(self):
        self.recipes: dict = {}
        self.items: dict = {}
        self.monster_data: dict = {}
        self._loaded = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def load(self):
        if self._loaded:
            return
        recipe_path = BASE_DIR / "data" / "recipes.json"
        if recipe_path.exists():
            try:
                with open(recipe_path, "r", encoding="utf-8") as f:
                    self.recipes = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"recipes.json 格式错误: {e}")
        else:
            logger.warning(f"缺少配方文件: {recipe_path}")
        try:
            self.items = load_items()
        except Exception as e:
            logger.error(f"加载物品失败: {e}")
        try:
            self.monster_data = load_monsters()
        except Exception as e:
            logger.error(f"加载怪物失败: {e}")
        from systems.entity.entity_validator import validate_all
        try:
            validate_all()
        except Exception as e:
            logger.error(f"数据一致性校验失败: {e}")
            raise
        self._loaded = True


class Game:
    """顶级聚合根 (Aggregate Root)。底层存储为结构化 dataclass，
       通过 @property 保持 game.player_x 等旧调用方式兼容。
    """

    def __init__(self):
        self.player = PlayerState()
        self.world_state = WorldState()
        self.ui = UIState()
        self.goal_state = GoalState()
        self.life_stats = LifeStats()

        self.recipes: dict = {}
        self.items: dict = {}
        self.monster_data: dict = {}
        self.turn: int = 0
        self.buff_manager = create_buff_manager()
        self.engine: Any = None

        self._load_static_data()

    def save_game(self):
        return sys_save_game(self)

    def load_game(self):
        return sys_load_game(self)

    def new_game(self, inherit_world=False):
        return sys_new_game(self, inherit_world)

    # ═══════════════════════════════════
    # 向后兼容 property — PlayerState
    # ═══════════════════════════════════
    @property
    def player_x(self): return self.player.x
    @player_x.setter
    def player_x(self, v): self.player.x = v

    @property
    def player_y(self): return self.player.y
    @player_y.setter
    def player_y(self, v): self.player.y = v

    @property
    def player_z(self): return self.player.z
    @player_z.setter
    def player_z(self, v): self.player.z = v

    @property
    def player_hp(self): return self.player.hp
    @player_hp.setter
    def player_hp(self, v): self.player.hp = v

    @property
    def player_max_hp(self): return self.player.max_hp
    @player_max_hp.setter
    def player_max_hp(self, v): self.player.max_hp = v

    @property
    def skills(self): return self.player.skills
    @skills.setter
    def skills(self, v): self.player.skills = v

    @property
    def skill_levels(self): return self.player.skill_levels
    @skill_levels.setter
    def skill_levels(self, v): self.player.skill_levels = v

    @property
    def inventory(self): return self.player.inventory
    @inventory.setter
    def inventory(self, v): self.player.inventory = v

    @property
    def equipment(self): return self.player.equipment
    @equipment.setter
    def equipment(self, v): self.player.equipment = v

    # ── 数值计算 property（从 PlayerState 代理）──
    @property
    def _equipment_bonus(
        self): return lambda attr: self.player.equipment_bonus(attr)

    def _combat_damage_bonus(self):
        return skill_system.combat_damage_bonus(self)

    def _player_defense(self):
        return skill_system.defense_bonus(self)

    def _best_equipped_tool_bonus(self, tool_type):
        return skill_system.best_equipped_tool_bonus(self, tool_type)

    def _digging_speed_bonus(self):
        return skill_system.digging_speed_bonus(self)

    def _gain_skill(self, name, amount=1):
        skill_system.gain_skill(self, name, amount)

    # ═══════════════════════════════════
    # 向后兼容 property — WorldState
    # ═══════════════════════════════════
    @property
    def world(self): return self.world_state.map_data
    @world.setter
    def world(self, v): self.world_state.map_data = v

    @property
    def respawn_x(self): return self.world_state.respawn_x
    @respawn_x.setter
    def respawn_x(self, v): self.world_state.respawn_x = v

    @property
    def respawn_y(self): return self.world_state.respawn_y
    @respawn_y.setter
    def respawn_y(self, v): self.world_state.respawn_y = v

    @property
    def bed_x(self): return self.world_state.bed_x
    @bed_x.setter
    def bed_x(self, v): self.world_state.bed_x = v

    @property
    def bed_y(self): return self.world_state.bed_y
    @bed_y.setter
    def bed_y(self, v): self.world_state.bed_y = v

    @property
    def monsters(self): return self.world_state.monsters
    @monsters.setter
    def monsters(self, v): self.world_state.monsters = v

    @property
    def _monster_index(self): return self.world_state.monster_index
    @_monster_index.setter
    def _monster_index(self, v): self.world_state.monster_index = v

    @property
    def spawn_counter(self): return self.world_state.spawn_counter
    @spawn_counter.setter
    def spawn_counter(self, v): self.world_state.spawn_counter = v

    @property
    def corpses(self): return self.world_state.corpses
    @corpses.setter
    def corpses(self, v): self.world_state.corpses = v

    @property
    def modified_tiles(self): return self.world_state.modified_tiles
    @modified_tiles.setter
    def modified_tiles(self, v): self.world_state.modified_tiles = v

    @property
    def chests(self): return self.world_state.chests
    @chests.setter
    def chests(self, v): self.world_state.chests = v

    @property
    def _burning_tiles(self): return self.world_state.burning_tiles
    @_burning_tiles.setter
    def _burning_tiles(self, v): self.world_state.burning_tiles = v

    @property
    def _found_specials(self): return self.world_state.found_specials
    @_found_specials.setter
    def _found_specials(self, v): self.world_state.found_specials = v

    def _monster_at(self, x, y):
        return self.world_state.monster_index.get((x, y))

    def _monster_has_position(self, x, y):
        return (x, y) in self.world_state.monster_index

    # ═══════════════════════════════════
    # 向后兼容 property — UIState
    # ═══════════════════════════════════
    @property
    def message(self): return self.ui.messages[-1] if self.ui.messages else ""
    @message.setter
    def message(self, v):
        self.ui.messages.append(v)
        if len(self.ui.messages) > 5:
            self.ui.messages.pop(0)

    @property
    def cursor_x(self): return self.ui.cursor_x
    @cursor_x.setter
    def cursor_x(self, v): self.ui.cursor_x = v

    @property
    def cursor_y(self): return self.ui.cursor_y
    @cursor_y.setter
    def cursor_y(self, v): self.ui.cursor_y = v

    @property
    def place_mode(self): return self.ui.place_mode
    @place_mode.setter
    def place_mode(self, v): self.ui.place_mode = v

    @property
    def last_place(self): return self.ui.last_place
    @last_place.setter
    def last_place(self, v): self.ui.last_place = v

    @property
    def place_item_name(self): return self.ui.place_item_name
    @place_item_name.setter
    def place_item_name(self, v): self.ui.place_item_name = v

    @property
    def last_place_item_name(self): return self.ui.last_place_item_name
    @last_place_item_name.setter
    def last_place_item_name(self, v): self.ui.last_place_item_name = v

    @property
    def dig_progress(self): return self.ui.dig_progress
    @dig_progress.setter
    def dig_progress(self, v): self.ui.dig_progress = v

    @property
    def look_mode(self): return self.ui.look_mode
    @look_mode.setter
    def look_mode(self, v): self.ui.look_mode = v

    # ═══════════════════════════════════
    # 向后兼容 property — GoalState
    # ═══════════════════════════════════
    @property
    def goal(self): return self.goal_state.current
    @goal.setter
    def goal(self, v): self.goal_state.current = v

    @property
    def goals_completed(self): return self.goal_state.completed
    @goals_completed.setter
    def goals_completed(self, v): self.goal_state.completed = v

    @property
    def goal_message_shown(self): return self.goal_state.message_shown
    @goal_message_shown.setter
    def goal_message_shown(self, v): self.goal_state.message_shown = v

    # ═══════════════════════════════════
    # 向后兼容 property — LifeStats（本局统计，非跨局遗产）
    # ═══════════════════════════════════
    @property
    def _monsters_killed_this_life(self): return self.life_stats.monsters_killed
    @_monsters_killed_this_life.setter
    def _monsters_killed_this_life(self, v): self.life_stats.monsters_killed = v

    @property
    def _blocks_placed_this_life(self): return self.life_stats.blocks_placed
    @_blocks_placed_this_life.setter
    def _blocks_placed_this_life(self, v): self.life_stats.blocks_placed = v

    @property
    def _crafted_this_life(self): return self.life_stats.crafted
    @_crafted_this_life.setter
    def _crafted_this_life(self, v): self.life_stats.crafted = v

    # ═══════════════════════════════════
    # 静态数据加载
    # ═══════════════════════════════════

    def _load_static_data(self):
        registry = StaticDataRegistry.instance()
        registry.load()
        self.recipes = registry.recipes
        self.items = registry.items
        self.monster_data = registry.monster_data

    # ═══════════════════════════════════
    # 视口
    # ═══════════════════════════════════

    def get_viewport_origin(self):
        if self.engine and self.engine.stdscr:
            vw = self.engine.stdscr.getmaxyx()[1]
            vh = self.engine.stdscr.getmaxyx()[0] - 8
        else:
            vw, vh = VIEW_WIDTH, VIEW_HEIGHT
        return (self.player.x - vw // 2, self.player.y - vh // 2)


# ═══════════════════════════════════
# 入口
# ═══════════════════════════════════

def main(stdscr):
    from ui.terminal import setup_curses
    from ui.states.main_menu_state import MainMenuState
    from core.state_machine import Engine

    _setup_logging()
    setup_curses(stdscr)
    register_status()
    from systems.core.event_bus import EventBus, EventType
    from systems.world.room_system import check_room_formation
    EventBus().subscribe(EventType.TILE_CHANGED, lambda e, g: check_room_formation(g))
    load_rules()
    game = Game()
    game.engine = Engine(stdscr)
    game.engine.run(MainMenuState(game))


if __name__ == "__main__":
    curses.wrapper(main)

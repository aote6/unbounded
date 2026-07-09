""" main.py —— 纯入口 + GameState 数据容器。
    所有业务逻辑已迁移至 systems/ 和 ui/states/。
    Game 类只放属性 + 最简单的 getter，不放任何业务逻辑。
"""
import json
import curses
from pathlib import Path

# ── 数据层 ──
from inventory import Inventory, ItemCategory
from items import load_items
from monsters import load_monsters

# ── 系统层（初始化需要）──
from systems.event_bus import EventBus, EventType
from systems.status_system import register as register_status
from systems.buff_system import create_buff_manager
from systems.tag_system import load_rules

# ── 配置 ──
from config import (
    PLAYER_INITIAL_HP,
    SPAWN_INITIAL_COUNTDOWN,
    VIEW_WIDTH,
    VIEW_HEIGHT,
)

BASE_DIR = Path(__file__).parent


class Game:
    """纯数据容器。不包含业务逻辑。"""

    def __init__(self):
        # ── 世界与坐标 ──
        self.world = None
        self.player_x = self.player_y = 0
        self.player_z = 0
        self.cursor_x = self.cursor_y = 0
        self.respawn_x = self.respawn_y = 0
        self.bed_x = None
        self.bed_y = None

        # ── 角色状态 ──
        self.player_hp = PLAYER_INITIAL_HP
        self.player_max_hp = PLAYER_INITIAL_HP
        self.turn = 0
        self.inventory = Inventory()
        self.equipment = {}
        self.skills = {"digging": 0, "combat": 0, "defense": 0}
        self.skill_levels = {"digging": 1, "combat": 1, "defense": 1}

        # ── 静态数据（从 JSON 加载）──
        self.recipes = {}
        self.items = {}
        self.monster_data = {}
        self._load_static_data()

        # ── 实体 ──
        self.monsters = []
        self._monster_index = {}
        self.spawn_counter = {"count": SPAWN_INITIAL_COUNTDOWN}

        # ── 地图状态 ──
        self.corpses = {}
        self.modified_tiles = {}
        self.chests = {}
        self._burning_tiles = set()
        self._found_specials = set()

        # ── UI 临时状态 ──
        self.message = "欢迎。世界无限延伸。hjkl 移动，c 合成，e 装备，d 挖掘，q 退出。"
        self.place_mode = None
        self.last_place = None
        self.place_item_name = None
        self.last_place_item_name = None
        self.dig_progress = None
        self.look_mode = False

        # ── 目标系统 ──
        self.goal = "build_first_room"
        self.goals_completed = []
        self.goal_message_shown = False

        # ── 事件与 Buff ──
        register_status()
        self.buff_manager = create_buff_manager()
        load_rules()

        # ── 遗产统计 ──
        self._monsters_killed_this_life = 0
        self._blocks_placed_this_life = 0
        self._crafted_this_life = []

        # ── 引擎引用（由 main() 设置）──
        self.engine = None

    def _load_static_data(self):
        """加载 recipes.json / items.json / monsters.json"""
        try:
            with open(BASE_DIR / "data" / "recipes.json", "r", encoding="utf-8") as f:
                self.recipes = json.load(f)
        except Exception:
            self.recipes = {}
        try:
            self.items = load_items()
        except Exception:
            self.items = {}
        try:
            self.monster_data = load_monsters()
        except Exception:
            self.monster_data = {}

    # ═══════════════════════════════════
    # 简单 getter（被外部广泛调用，保留）
    # ═══════════════════════════════════

    def get_viewport_origin(self):
        """返回视口左上角坐标"""
        return (self.player_x - VIEW_WIDTH // 2, self.player_y - VIEW_HEIGHT // 2)

    def _monster_at(self, x, y):
        return self._monster_index.get((x, y))

    def _monster_has_position(self, x, y):
        return self._monster_at(x, y)

    def _gain_skill(self, name, amount=1):
        self.skills[name] = self.skills.get(name, 0) + amount

    def _equipment_bonus(self, attr):
        total = 0
        for inst in self.equipment.values():
            if inst and hasattr(inst, attr):
                total += getattr(inst, attr, 0) or 0
        return total

    def _best_equipped_tool_bonus(self, tool_type):
        best = 0
        for inst in self.equipment.values():
            if inst and hasattr(inst, "tool_bonus"):
                tags = getattr(inst, "tags", [])
                if tool_type in tags:
                    best = max(best, inst.tool_bonus or 0)
        return best

    def _digging_speed_bonus(self):
        return self._best_equipped_tool_bonus("digging")

    def _combat_damage_bonus(self):
        base = self._equipment_bonus("attack_bonus")
        base += self.skills.get("combat", 0) // 3
        return base

    def _player_defense(self):
        base = self._equipment_bonus("defense_bonus")
        base += self.skills.get("defense", 0) // 3
        return base

    def _count_rooms_nearby(self):
        # 占位，由 goal_system 覆盖
        return 0

    def _check_special_location(self):
        # 占位，由 goal_system 覆盖
        pass


# ═══════════════════════════════════
# 入口
# ═══════════════════════════════════

def main(stdscr):
    from ui.terminal import setup_curses
    setup_curses(stdscr)
    from ui.states.main_menu_state import MainMenuState
    from core.state_machine import Engine

    game = Game()
    game.engine = Engine(stdscr)
    game.engine.run(MainMenuState(game))


if __name__ == "__main__":
    curses.wrapper(main)

""" main.py 终端版游戏主循环——俯视图 + 技能 + 存档。"""
import curses, json, random, traceback, os
from pathlib import Path
from world_gen import (
    generate_world, find_spawn, World,
    TILE_AIR, TILE_DROPS, CHUNK_SIZE,
    TILE_WATER, TILE_TREE,
)
from tile_props import get_tile_props
from systems.save_system import build_save_data, apply_load_data
from ui.game_renderer import draw
from systems.tag_system import load_rules
from systems.scent_map import rebuild_scent_map

from systems.monster_ai import tick_monsters, try_spawn_monster, tick_corpses, tick_status_effects
from config import (
    VIEW_WIDTH, VIEW_HEIGHT, WORLD_SEED,
    PLAYER_INITIAL_HP,
    SPAWN_INITIAL_COUNTDOWN, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    SPAWN_MIN_DISTANCE,
    DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START,
)
import monsters as monsters_mod
import items as items_mod
from inventory import Inventory

from data_mappings import load_recipes
from systems.room_system import detect_room, check_room_formation, count_rooms_nearby
from systems.goal_system import check_goals, check_special_location
from systems.player_action import dig_adjacent, do_place, dig_any_tile, try_move_or_dig
from systems.time_system import get_time_of_day, get_geology_zone
from systems.skill_system import gain_skill, digging_speed_bonus, combat_damage_bonus, defense_reduction
from systems.legacy_system import drop_items_on_ground, place_grave, save_world_on_death, check_death, show_death_screen
from systems.player_items import add_equipment_instance, get_equipment_instance, count_equipment, get_item_attr, equipment_bonus, best_equipped_tool_bonus, collect_attack_effects
from systems.monster_index import build_monster_index, monster_at, monster_has_position, monster_moved, add_monster, remove_monster
from ui.terminal import setup_curses, check_terminal_size

BASE_DIR = Path(__file__).parent
SAVE_FILE = BASE_DIR / "data" / "save.json"
CORPSE_DECAY_TURNS = 50
CHUNK_KEEP_RADIUS = 3
SKILL_LEVEL_THRESHOLD = 10

# 矿石→材质映射表（合成时自动转换）

# ═══════════════════════════════════
# Game 类
# ═══════════════════════════════════
class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self._setup_curses()
        self.world = None
        self.player_x = self.player_y = 0
        self.player_z = 0
        self.cursor_x = self.cursor_y = 0
        self.player_hp = PLAYER_INITIAL_HP
        self.player_max_hp = PLAYER_INITIAL_HP
        self.turn = 0
        self.equipment = {}  # slot_name -> EquipmentInstance or None                # 装备槽: {"main_hand": "石剑"}
        self.message = "欢迎。世界无限延伸。hjkl 移动，c 合成，e 装备，d 挖掘，q 退出。S 存档，L 读档。"
        self.place_mode = None; self.last_place = None
        self.place_item_name = None; self.last_place_item_name = None
        self.dig_progress = None; self.look_mode = False
        self.recipes = load_recipes()
        self.items = items_mod.load_items()
        self.monster_data = monsters_mod.load_monsters()
        self.monsters = []
        self._monster_index = {}
        self.spawn_counter = {"count": SPAWN_INITIAL_COUNTDOWN}
        load_rules()  # 加载交互规则矩阵
        self.corpses = {}
        self.modified_tiles = {}
        self.chests = {}  # {(x,y): {"materials": {}, "equipment_instances": [...]}}
        self.skills = {"digging": 0, "combat": 0, "defense": 0}
        self.respawn_x = 0
        self.respawn_y = 0
        self.bed_x = None
        self.bed_y = None
        # 目标系统
        self.goal = "build_first_room"
        self.goals_completed = []
        self.goal_message_shown = False
        self.skill_levels = {"digging": 1, "combat": 1, "defense": 1}
        # 事件总线
        from systems.event_bus import EventBus
        from systems.status_system import register as register_status
        register_status()
        from systems.buff_system import create_buff_manager
        from systems.buff_system import create_buff_manager
        self.buff_manager = create_buff_manager()
        # 订阅方块变更事件 → 房间检测
        from systems.event_bus import EventBus, EventType
        EventBus().subscribe(EventType.TILE_CHANGED, lambda e, g: g._check_room_formation())
        # M27: 跨局遗产统计
        self._monsters_killed_this_life = 0
        self._blocks_placed_this_life = 0
        self._crafted_this_life = []
        self.engine = None  # 状态机引擎，由 run() 设置

    # ── 材料系统（堆叠物品） ──
    def _count_material(self, name):
        return self.inventory.count(name)

    def _add_material(self, name, count):
        self.inventory.add(name, count)

    def _remove_material(self, name, count):
        self.inventory.remove(name, count)

    def _add_equipment_instance(self, name, instance_data=None):
        add_equipment_instance(self, name, instance_data)

    def _get_equipment_instance(self, name):
        return get_equipment_instance(self, name)

    def _count_equipment(self, name):
        return count_equipment(self, name)

    def _get_item_attr(self, item_name, field_name):
        return get_item_attr(self, item_name, field_name)

    def _equipment_bonus(self, field_name):
        return equipment_bonus(self, field_name)

    def _best_equipped_tool_bonus(self):
        return best_equipped_tool_bonus(self)

    def _collect_attack_effects(self):
        return collect_attack_effects(self)

    def _build_monster_index(self):
        build_monster_index(self)

    def _monster_at(self, x, y):
        return monster_at(self, x, y)

    def _monster_has_position(self, x, y):
        return monster_has_position(self, x, y)

    def _monster_moved(self, monster, old_x, old_y):
        monster_moved(self, monster, old_x, old_y)

    def _add_monster(self, monster):
        add_monster(self, monster)

    def _remove_monster(self, monster):
        remove_monster(self, monster)

    def new_game(self, inherit_world=False):
        # M26: inherit_world=True 保留世界 Chunk 和世界状态
        import shutil, json
        from world_gen import SAVE_DIR
        
        if not inherit_world:
            if SAVE_DIR.exists():
                shutil.rmtree(SAVE_DIR)
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            self.world = generate_world(seed=WORLD_SEED)
        else:
            world_path = BASE_DIR / "data" / "world_meta.json"
            if SAVE_DIR.exists() and world_path.exists():
                with open(world_path) as f:
                    world_data = json.load(f)
                seed = world_data.get("seed", WORLD_SEED)
                self.world = generate_world(seed=seed)
                from systems.save_system import _apply_world_data
                _apply_world_data(self, world_data)
            else:
                if SAVE_DIR.exists():
                    shutil.rmtree(SAVE_DIR)
                SAVE_DIR.mkdir(parents=True, exist_ok=True)
                self.world = generate_world(seed=WORLD_SEED)
        
        for p in [SAVE_FILE, BASE_DIR / "data" / "player.json"]:
            if p.exists():
                p.unlink()
        
        sx, sy = find_spawn(self.world, start_x=0)
        self.player_x, self.player_y = sx, sy
        self.respawn_x, self.respawn_y = sx, sy
        self.player_z = 0
        self.cursor_x, self.cursor_y = sx, sy
        self.player_hp = PLAYER_INITIAL_HP; self.player_max_hp = PLAYER_INITIAL_HP
        self.turn = 0
        self.inventory = Inventory()
        self.equipment = {}  # slot_name -> EquipmentInstance or None
        # M27: 应用跨局遗产增益
        from systems.legacy_system import apply_legacy_perks
        apply_legacy_perks(self)
        from systems.buff_system import create_buff_manager
        self.buff_manager = create_buff_manager()
        # 订阅方块变更事件 → 房间检测
        from systems.event_bus import EventBus, EventType
        EventBus().subscribe(EventType.TILE_CHANGED, lambda e, g: g._check_room_formation())
        self.message = "欢迎来到新世界。" if not inherit_world else "你在这个熟悉的世界醒来..."
        self.place_mode = None; self.last_place = None
        self.place_item_name = None; self.last_place_item_name = None
        self.dig_progress = None; self.look_mode = False
        self.recipes = load_recipes(); self.items = items_mod.load_items()
        self.monster_data = monsters_mod.load_monsters()
        self.monsters = []; self._monster_index = {}
        self.spawn_counter = {"count": SPAWN_INITIAL_COUNTDOWN}
        self.corpses = {}; self.modified_tiles = {}
        self.chests = {}
        self.skills = {"digging": 0, "combat": 0, "defense": 0}
        self.skill_levels = {"digging": 1, "combat": 1, "defense": 1}

    def save_game(self):
        """保存游戏状态到磁盘。M25: 拆分为 player.json + world_meta.json + save.json 兼容。"""
        player_data, world_data = build_save_data(self)
        save_data = {"player": player_data, "world": world_data}
        
        player_path = BASE_DIR / "data" / "player.json"
        world_path = BASE_DIR / "data" / "world_meta.json"
        
        try:
            SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            # 新格式：独立文件
            with open(player_path, "w", encoding="utf-8") as f:
                json.dump(player_data, f, ensure_ascii=False, indent=2)
            with open(world_path, "w", encoding="utf-8") as f:
                json.dump(world_data, f, ensure_ascii=False, indent=2)
            # 保留旧格式兼容
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            self.message = "游戏已保存。"
        except Exception as e:
            self.message = f"存档失败: {e}"

    def _setup_curses(self):
        setup_curses(self.stdscr)

    def _check_terminal_size(self):
        return check_terminal_size(self.stdscr)
    def load_game(self):
        """从磁盘读取存档并恢复游戏状态。M25: 优先读取 player.json + world_meta.json。"""
        player_path = BASE_DIR / "data" / "player.json"
        world_path = BASE_DIR / "data" / "world_meta.json"
        
        if player_path.exists() and world_path.exists():
            try:
                with open(player_path, "r", encoding="utf-8") as f:
                    player_data = json.load(f)
                with open(world_path, "r", encoding="utf-8") as f:
                    world_data = json.load(f)
                data = {"player": player_data, "world": world_data}
            except Exception as e:
                self.message = f"读档失败: {e}"
                return False
        elif SAVE_FILE.exists():
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                self.message = f"读档失败: {e}"
                return False
        else:
            self.message = "没有找到存档文件。"
            return False
        
        seed = data.get("seed") or (data.get("world", {}).get("seed") if "world" in data else WORLD_SEED)
        self.world = generate_world(seed=seed, decorate=False)
        apply_load_data(self, data)
        # M21: 迁移怪物旧状态格式
        if hasattr(self, 'buff_manager'):
            for m in self.monsters:
                self.buff_manager.migrate_legacy(m)
        return True

    def _maybe_cancel_dig(self, x, y):
        if self.dig_progress and (self.dig_progress["x"] != x or self.dig_progress["y"] != y):
            self.dig_progress = None

    def _dig_any_tile(self, x, y):
        return dig_any_tile(self, x, y)

    def _gain_skill(self, skill_name):
        gain_skill(self, skill_name)

    def _digging_speed_bonus(self):
        return digging_speed_bonus(self.skill_levels)

    def _combat_damage_bonus(self):
        return combat_damage_bonus(self.skill_levels)

    def _defense_reduction(self):
        return defense_reduction(self.skill_levels)

    def _dig_natural_tile(self, x, y):
        tile = self.world.get_tile(x, y)["tile"]
        if tile not in TILE_DROPS and not ("尸体" in str(tile) or "残骸" in str(tile)):
            return False
        return self._dig_any_tile(x, y)

    def try_move_or_dig(self, dx, dy):
        try_move_or_dig(self, dx, dy)

    def _do_place(self):
        do_place(self)

    def _attack_monster(self, monster):
        from systems.combat_system import CombatSystem
        if not hasattr(self, '_combat_system'):
            self._combat_system = CombatSystem(self)
        self._combat_system.attack_monster(monster)

    def _kill_monster(self, monster, cause="attack"):
        # M27: 本局击杀计数
        self._monsters_killed_this_life += 1
        mx, my = monster["x"], monster["y"]
        mname = monster["name"]
        from systems.event_bus import EventBus, EventType, GameEvent
        EventBus().emit(GameEvent(EventType.MONSTER_KILLED, {"monster": monster, "cause": cause}), self)
        corpse_tile = monster.get("corpse_tile")
        splits = monsters_mod.get_split_spawns(monster, self.monster_data)
        drop_name, drop_obj = monsters_mod.generate_loot_for(self.player_y, mname)
        if drop_name and drop_obj:
            if isinstance(drop_obj, dict) and "count" in drop_obj:
                self._add_material(drop_name, drop_obj.get("count", 1))
            else:
                self._add_equipment_instance(drop_name, drop_obj)
        self._remove_monster(monster)
        if corpse_tile and self.world.get_tile(mx, my)["tile"] == TILE_AIR:
            old_tile = self.world.get_tile(mx, my)["tile"]
            self.world.set_tile(mx, my, corpse_tile)
            from systems.event_bus import EventBus, EventType, GameEvent
            EventBus().emit(GameEvent(EventType.TILE_CHANGED, {"x": mx, "y": my, "old": old_tile, "new": corpse_tile}), self)
            self.modified_tiles[(mx, my)] = corpse_tile
            self.corpses[(mx, my)] = CORPSE_DECAY_TURNS
        if splits:
            for s in splits:
                self._add_monster(s)
        cause_msg = {
            "attack": f"打倒了 {mname}！",
            "burn": f"{mname} 被烧死了！",
            "poison": f"{mname} 中毒身亡！",
        }.get(cause, f"{mname} 死了。")
        if splits:
            cause_msg += f"它分裂成了 {len(splits)} 只小史莱姆！"
        elif drop_name:
            cause_msg += f"掉落了 {drop_name}。"
        self.message = cause_msg

    def _tick_status_effects(self):
        tick_status_effects(self)

    def _tick_corpses(self):
        tick_corpses(self)

    def dig_adjacent(self, dx, dy):
        dig_adjacent(self, dx, dy)

    def _player_defense(self):
        return self._equipment_bonus("defense_bonus") + defense_reduction(self.skill_levels)

    def _tick_monsters(self):
        tick_monsters(self)

    def _try_spawn_monster(self):
        try_spawn_monster(self)

    def _drop_items_on_ground(self, x, y):
        drop_items_on_ground(self, x, y)
    
    def _place_grave(self, x, y):
        place_grave(self, x, y)

    def _save_world_on_death(self):
        save_world_on_death(self)

    def check_death(self):
        return check_death(self)

    def show_death_screen(self):
        self.stdscr.erase()
        m1, m2 = "你死了。", f"物品掉落在 ({self.player_x},{self.player_y})"
        m3 = "世界保留，新角色将继承一切。"
        m4 = "按任意键打开遗产商店..."
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(h//2-3, max(0, w//2-len(m1)//2), m1, curses.A_BOLD | curses.color_pair(7))
        self.stdscr.addstr(h//2-1, max(0, w//2-len(m2)//2), m2)
        self.stdscr.addstr(h//2, max(0, w//2-len(m3)//2), m3)
        self.stdscr.addstr(h//2+2, max(0, w//2-len(m4)//2), m4)
        self.stdscr.refresh(); self.stdscr.getch()
        # 打开遗产商店
        from ui.states.legacy_state import LegacyState
        if self.engine:
            self.engine.push_state(LegacyState(self))

    def get_viewport_origin(self):
        vx = self.player_x - VIEW_WIDTH // 2
        vy = self.player_y - VIEW_HEIGHT // 2
        return vx, vy

    def tile_attr(self, tile):
        props = get_tile_props(tile); name = props["name"]
        if name == "树木":
            return curses.color_pair(6) | curses.A_BOLD  # 绿色加粗，不受夜晚压暗影响
        _, ambient = self._get_time_of_day()
        if ambient <= 2:
            return curses.color_pair(4)
        elif name == "石头":
            return curses.color_pair(1)
        elif name == "泥土":
            return curses.color_pair(2)
        elif "尸体" in name or "残骸" in name:
            return curses.color_pair(9) | curses.A_BOLD
        elif not props["passable"]:
            return curses.color_pair(4) | curses.A_BOLD
        return curses.A_NORMAL

    def _get_geology_zone(self, y):
        return get_geology_zone(y)

    
    def _check_room_formation(self):
        return check_room_formation(self)
    
    
    def _get_time_of_day(self):
        return get_time_of_day(self.turn)

    def advance_turn(self):
        rebuild_scent_map(self)
        self.buff_manager.tick_all(self)
        self._tick_corpses()
        self._tick_monsters()
        self._try_spawn_monster()
        self.world.keep_radius(self.player_x, self.player_y, CHUNK_KEEP_RADIUS)
        # 目标推进
        self._check_goals()
    
    def _check_goals(self):
        check_goals(self)
    
    def _count_rooms_nearby(self):
        return count_rooms_nearby(self)
    
    def _check_special_location(self):
        check_special_location(self)

    def _handle_reload(self):
        self.recipes = load_recipes()
        self.items = items_mod.load_items()
        self.monster_data = monsters_mod.load_monsters()
        self.message = "数据已重载"

    def _handle_save(self):
        self.save_game()

    def _handle_load(self):
        self.load_game()

    def _handle_dig_mode(self):
        self.message = "挖掘模式：按方向键选择要拆除的方块（包括尸体），其他键取消。"
        draw(self)
        key2 = self.stdscr.getch()
        dirs = {
            curses.KEY_LEFT: (-1,0), curses.KEY_RIGHT: (1,0),
            curses.KEY_UP: (0,-1), curses.KEY_DOWN: (0,1),
            ord("h"): (-1,0), ord("l"): (1,0), ord("k"): (0,-1), ord("j"): (0,1),
        }
        if key2 in dirs:
            dx, dy = dirs[key2]
            self.dig_adjacent(dx, dy)
            return True
        else:
            self.message = "取消挖掘。"
            return False

def main(stdscr):
    from ui.states.main_menu_state import MainMenuState
    from core.state_machine import Engine
    game = Game(stdscr)
    game.engine = Engine(stdscr)
    game.engine.run(MainMenuState(game))

if __name__ == "__main__":
    curses.wrapper(main)

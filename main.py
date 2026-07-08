""" main.py 终端版游戏主循环——俯视图 + 技能 + 存档。"""
import curses, json, random, traceback, os
from pathlib import Path
from world_gen import (
    generate_world, find_spawn, World,
    TILE_AIR, TILE_DIRT, TILE_STONE, TILE_DROPS, CHUNK_SIZE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
    TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_SAND,
    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,
    TILE_WATER, TILE_TREE,
)
from tile_props import get_tile_props, get_tile_char, get_dig_turns
from systems.interaction import get_nearby_chest
from systems.save_system import build_save_data, apply_load_data
from ui.game_renderer import draw
from systems.tag_system import load_rules, check_interaction
from systems.scent_map import rebuild_scent_map
from systems.tile_interaction import tick_tile_interactions, tick_burning_tiles
from systems.monster_ai import tick_monsters, try_spawn_monster, tick_corpses, tick_status_effects
from config import (
    VIEW_WIDTH, VIEW_HEIGHT, WORLD_SEED,
    PLAYER_INITIAL_HP,
    PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX, PLAYER_BASE_HIT_CHANCE,
    SPAWN_INITIAL_COUNTDOWN, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    SPAWN_MIN_DISTANCE,
    DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START,
    WORLD_LAYERS, LAYER_DEPTH_OFFSET,
    ORE_TO_MATERIAL,
)
import monsters as monsters_mod
import items as items_mod
from inventory import Inventory, ItemCategory

from equipment import EquipmentInstance


BASE_DIR = Path(__file__).parent
RECIPES_FILE = BASE_DIR / "data" / "recipes.json"
SAVE_FILE = BASE_DIR / "data" / "save.json"
MIN_TERM_H = VIEW_HEIGHT + 8
MIN_TERM_W = VIEW_WIDTH
CORPSE_DECAY_TURNS = 50
CHUNK_KEEP_RADIUS = 3
SKILL_LEVEL_THRESHOLD = 10


# 矿石→材质映射表（合成时自动转换）


def load_recipes():
    if not RECIPES_FILE.exists():
        print(f"[recipes] 文件不存在: {RECIPES_FILE}"); return {}
    try:
        with open(RECIPES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[recipes] JSON 解析失败: {e}"); return {}

DIRECTIONS = {
    curses.KEY_LEFT: (-1,0), curses.KEY_RIGHT: (1,0),
    curses.KEY_UP: (0,-1), curses.KEY_DOWN: (0,1),
    ord("h"): (-1,0), ord("l"): (1,0), ord("k"): (0,-1), ord("j"): (0,1),
}

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

    # ── 装备实例系统（独立物品） ──
    def _add_equipment_instance(self, name, instance_data=None):
        """添加一个装备实例到背包。"""
        if instance_data is None:
            item_data = self.items.get(name, {})
            inst = EquipmentInstance(
                name=name,
                slot=item_data.get("slot"),
                attack_bonus=item_data.get("attack_bonus", 0),
                defense_bonus=item_data.get("defense_bonus", 0),
                tool_bonus=item_data.get("tool_bonus", 0),
                damage_min=item_data.get("damage_min", 0),
                damage_max=item_data.get("damage_max", 0),
                hit_bonus=item_data.get("hit_bonus", 0),
                affixes=item_data.get("affixes", []),
                on_attack=item_data.get("on_attack", []),
                lifesteal=item_data.get("lifesteal", 0),
                speed_bonus=item_data.get("speed_bonus", 0),
            )
        elif isinstance(instance_data, EquipmentInstance):
            inst = instance_data
        else:
            inst = EquipmentInstance.from_dict(instance_data)
        self.inventory.add(name, item_type=ItemCategory.EQUIPMENT, instance=inst)

    def _get_equipment_instance(self, name):
        for item_id, item in self.inventory.all_items():
            if item.item_type == ItemCategory.EQUIPMENT and item.instance and item.instance.name == name:
                return item.instance
        return None

    def _count_equipment(self, name):
        return sum(1 for _, item in self.inventory.all_items() 
               if item.item_type == ItemCategory.EQUIPMENT and item.instance and item.instance.name == name)

    def _get_item_attr(self, item_name, field_name):
        """获取装备实例的属性。优先从装备槽查找（O(1)）。"""
        # 先从装备槽查找
        for inst in self.equipment.values():
            if inst and inst.name == item_name:
                return getattr(inst, field_name, 0)
        # 回退：遍历背包（兼容非装备槽中的物品）
        inst = self._get_equipment_instance(item_name)
        if inst:
            return getattr(inst, field_name, 0)
        return 0

    def _get_nearby_chest(self):
        return get_nearby_chest(self)


    def _equipment_bonus(self, field_name):
        """从装备槽实例直接读取属性（O(1)，不再遍历背包）。"""
        total = 0
        for inst in self.equipment.values():
            if inst is None:
                continue
            if field_name == "attack_bonus":
                dmg_min = getattr(inst, "damage_min", 0)
                dmg_max = getattr(inst, "damage_max", 0)
                if dmg_max > 0:
                    total += (dmg_min + dmg_max) // 2
                else:
                    total += getattr(inst, "attack_bonus", 0)
            else:
                total += getattr(inst, field_name, 0)
        return total

    def _best_equipped_tool_bonus(self):
        best = 0
        for item_name in self.equipment.values():
            inst = self._get_equipment_instance(item_name)
            if inst:
                best = max(best, inst.tool_bonus)
            else:
                best = max(best, self.items.get(item_name, {}).get("tool_bonus", 0))
        return best

    def _collect_attack_effects(self):
        effects = []
        for item_name in self.equipment.values():
            inst = self._get_equipment_instance(item_name)
            if inst:
                effects.extend(inst.on_attack)
            else:
                effects.extend(self.items.get(item_name, {}).get("on_attack", []))
        return effects

    # ── 怪物空间索引（持久字典，O(1) 查找） ──
    def _build_monster_index(self):
        """全量重建空间索引（仅在读档/新游戏时调用）。"""
        self._monster_index = {(m["x"], m["y"]): m for m in self.monsters}

    def _monster_at(self, x, y):
        """O(1) 查找指定坐标的怪物。"""
        return self._monster_index.get((x, y))

    def _monster_has_position(self, x, y):
        """检查坐标是否有怪物占用。"""
        return (x, y) in self._monster_index

    def _monster_moved(self, monster, old_x, old_y):
        """怪物移动后更新索引（AI 调用）。"""
        self._monster_index.pop((old_x, old_y), None)
        self._monster_index[(monster["x"], monster["y"])] = monster

    def _add_monster(self, monster):
        """添加怪物并更新索引。"""
        self.monsters.append(monster)
        self._monster_index[(monster["x"], monster["y"])] = monster

    def _remove_monster(self, monster):
        """移除怪物并更新索引。"""
        if monster in self.monsters:
            self.monsters.remove(monster)
        self._monster_index.pop((monster["x"], monster["y"]), None)

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
        curses.curs_set(0); curses.noecho(); curses.start_color(); curses.use_default_colors()
        curses.init_pair(1,curses.COLOR_WHITE,-1)
        curses.init_pair(2,curses.COLOR_YELLOW,-1)
        curses.init_pair(3,curses.COLOR_CYAN,-1)
        curses.init_pair(4,curses.COLOR_WHITE,curses.COLOR_BLACK)
        curses.init_pair(5,curses.COLOR_YELLOW,curses.COLOR_BLACK)
        curses.init_pair(6,curses.COLOR_GREEN,-1)
        curses.init_pair(7,curses.COLOR_RED,-1)
        curses.init_pair(8,curses.COLOR_MAGENTA,-1)
        curses.init_pair(9,curses.COLOR_BLACK,curses.COLOR_YELLOW)
        self.stdscr.keypad(True)
        self.stdscr.nodelay(False)

    def _check_terminal_size(self):
        term_h, term_w = self.stdscr.getmaxyx()
        if term_h < MIN_TERM_H or term_w < MIN_TERM_W:
            self.stdscr.erase()
            msg1 = "终端窗口太小！"
            msg2 = f"当前: {term_w}x{term_h} 需要至少: {MIN_TERM_W}x{MIN_TERM_H}"
            msg3 = "请缩小字号、横屏或调整窗口大小后按任意键..."
            h, w = term_h, term_w
            self.stdscr.addstr(max(0,h//2-1), max(0,w//2-len(msg1)//2), msg1, curses.A_BOLD)
            self.stdscr.addstr(max(0,h//2), max(0,w//2-len(msg2)//2), msg2)
            self.stdscr.addstr(max(0,h//2+1), max(0,w//2-len(msg3)//2), msg3)
            self.stdscr.refresh(); self.stdscr.getch()
            return False
        return True
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
        from systems.player_action import dig_any_tile
        return dig_any_tile(self, x, y)

    def _gain_skill(self, skill_name):
        self.skills[skill_name] += 1
        if self.skills[skill_name] >= self.skill_levels[skill_name] * SKILL_LEVEL_THRESHOLD:
            self.skill_levels[skill_name] += 1
            names_cn = {"digging": "挖掘", "combat": "战斗", "defense": "防御"}
            self.message = f"【{names_cn[skill_name]}】升到了 {self.skill_levels[skill_name]} 级！"

    def _digging_speed_bonus(self):
        return (self.skill_levels["digging"] - 1) // 10

    def _combat_damage_bonus(self):
        return (self.skill_levels["combat"] - 1) // 10

    def _defense_reduction(self):
        return (self.skill_levels["defense"] - 1) // 10

    def _dig_natural_tile(self, x, y):
        tile = self.world.get_tile(x, y)["tile"]
        if tile not in TILE_DROPS and not ("尸体" in str(tile) or "残骸" in str(tile)):
            return False
        return self._dig_any_tile(x, y)


    def try_move_or_dig(self, dx, dy):
        from systems.player_action import try_move_or_dig
        try_move_or_dig(self, dx, dy)

    def _do_place(self):
        if self.place_item_name and self.inventory.count(self.place_item_name) <= 0:
            self.message = f"背包里已经没有 {self.place_item_name} 了。"
            self.place_mode = None; self.place_item_name = None
            return
        bx, by = self.cursor_x, self.cursor_y
        if self._monster_at(bx, by):
            self.message = "有怪物挡住了建造位置。"; return
        if self.world.get_tile(bx, by)["tile"] != TILE_AIR:
            self.message = "这里不是空地，无法放置。"; return
        if bx == self.player_x and by == self.player_y:
            push_order = [(0, -1), (0, 1), (-1, 0), (1, 0)]
            pushed = False
            for pdx, pdy in push_order:
                px, py = self.player_x + pdx, self.player_y + pdy
                if (self.world.get_tile(px, py)["tile"] == TILE_AIR
                        and not self._monster_at(px, py)
                        and not self._monster_has_position(px, py)):
                    self.player_x, self.player_y = px, py; pushed = True; break
            if not pushed:
                self.message = "玩家没有空间后退，无法在脚下放置。"; return
        old_tile = self.world.get_tile(bx, by)["tile"]
        self.world.set_tile(bx, by, self.place_mode)
        self.modified_tiles[(bx, by)] = self.place_mode
        from systems.event_bus import EventBus, EventType, GameEvent
        EventBus().emit(GameEvent(EventType.TILE_CHANGED, {"x": bx, "y": by, "old": old_tile, "new": self.place_mode}), self)
        # 如果放置的是箱子，初始化空箱子
        # M27: 本局放置计数
        self._blocks_placed_this_life += 1
        if self.place_mode == "木箱":
            self.chests[(bx, by)] = {"materials": {}, "equipment_instances": []}
        if self.place_item_name:
            self._remove_material(self.place_item_name, 1)
            if self._count_material(self.place_item_name) <= 0:
                self.message = f"放置了 {self.place_mode}（背包中已无更多，退出建造模式）"
                self.place_mode = None; self.place_item_name = None
                return
        self.message = f"放置了 {self.place_mode}（建造模式中，c 退出）"

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
        pass  # M21: 已由 advance_turn 中 buff_manager.tick_all() 统一处理

    def _tick_corpses(self):
        tick_corpses(self)

    def dig_adjacent(self, dx, dy):
        nx, ny = self.player_x + dx, self.player_y + dy
        if self._monster_at(nx, ny):
            self.message = "有怪物挡住了挖掘位置。"; return
        tile = self.world.get_tile(nx, ny)["tile"]
        drop_info = items_mod.get_drop_on_mine(self.items, tile)
        if drop_info:
            self._maybe_cancel_dig(nx, ny)
            for d, c in drop_info.items():
                self._add_material(d, c)
            old_tile = self.world.get_tile(nx, ny)["tile"]
            self.world.set_tile(nx, ny, TILE_AIR)
            self.modified_tiles[(nx, ny)] = TILE_AIR
            from systems.event_bus import EventBus, EventType, GameEvent
            EventBus().emit(GameEvent(EventType.TILE_CHANGED, {"x": nx, "y": ny, "old": old_tile, "new": TILE_AIR}), self)
            if (nx, ny) in self.corpses:
                del self.corpses[(nx, ny)]
            # 如果拆除的是箱子，掉落里面所有物品到地上
            if (nx, ny) in self.chests:
                chest = self.chests.pop((nx, ny))
                for mat, count in chest["materials"].items():
                    self._add_material(mat, count)
                for inst in chest["equipment_instances"]:
                    self._add_equipment_instance(inst.name, inst)
                self.message = f"拆掉了 {tile}，箱内物品已回收。"
            else:
                self.message = f"拆掉了 {tile}，回收材料。"
            self._gain_skill("digging")
        elif get_tile_props(tile)["diggable"]:
            self._dig_any_tile(nx, ny)
        else:
            self.message = "这里无法挖掘。"

    def _player_defense(self):
        return self._equipment_bonus("defense_bonus") + self._defense_reduction()

    def _tick_monsters(self):
        msgs = []
        for m in self.monsters:
            old_x, old_y = m["x"], m["y"]
            act = monsters_mod.ai_act(m, self.world, self.player_x, self.player_y,
                                      self.turn, self._monster_index)
            # 如果怪物移动了，更新空间索引
            if m["x"] != old_x or m["y"] != old_y:
                self._monster_moved(m, old_x, old_y)
            if isinstance(act, int):
                if act > 0:
                    dmg = max(1, act - self._player_defense())
                    self.player_hp -= dmg
                    msgs.append(f"{m['name']} 攻击了你，造成 {dmg} 点伤害！")
                    self._gain_skill("defense")
                else:
                    msgs.append(f"{m['name']} 的攻击落空了。")
        if msgs:
            self.message = " ".join(msgs[-2:])

    def _try_spawn_monster(self):
        m = monsters_mod.try_spawn(
            self.world, self.player_x, self.player_y,
            self.monsters, self.spawn_counter, self.monster_data,
            interval_min=SPAWN_INTERVAL_MIN, interval_max=SPAWN_INTERVAL_MAX,
            min_dist=SPAWN_MIN_DISTANCE,
        )
        if m:
            self._add_monster(m)
            self.message = f"一只 {m['name']} 出现了！"

    def _drop_items_on_ground(self, x, y):
        """将背包内容掉落到地面附近"""
        # 将材料和装备实例掉落为尸体形式的容器
        # 简化实现：把掉落物信息存在消息里，物品暂不丢失（后续可改进为墓碑容器）
        lost_items = self.inventory.to_dict()
        self.inventory = Inventory()
        # 清空装备槽
        self.equipment = {}  # slot_name -> EquipmentInstance or None
        self.message = f"你的物品散落在 ({x},{y}) 附近。"
    
    def _place_grave(self, x, y):
        """M26: 在死亡位置生成墓碑"""
        from world_gen import TILE_AIR
        tile = self.world.get_tile(x, y).get("tile", TILE_AIR)
        if tile == TILE_AIR:
            old_tile = self.world.get_tile(x, y)["tile"]
            self.world.set_tile(x, y, "墓碑")
            self.modified_tiles[(x, y)] = "墓碑"
            from systems.event_bus import EventBus, EventType, GameEvent
            EventBus().emit(GameEvent(EventType.TILE_CHANGED, {"x": x, "y": y, "old": old_tile, "new": "墓碑"}), self)

    def _save_world_on_death(self):
        """M26: 死亡时保存世界状态"""
        import json
        from systems.save_system import build_save_data
        _, world_data = build_save_data(self)
        world_data["last_death_x"] = self.player_x
        world_data["last_death_y"] = self.player_y
        world_data["last_death_turn"] = self.turn
        world_data["total_deaths"] = world_data.get("total_deaths", 0) + 1
        world_path = BASE_DIR / "data" / "world_meta.json"
        with open(world_path, "w") as f:
            json.dump(world_data, f, indent=2, ensure_ascii=False)

    def check_death(self):
        if self.player_hp <= 0:
            self.buff_manager.remove_entity(self)
            self._drop_items_on_ground(self.player_x, self.player_y)
            self._place_grave(self.player_x, self.player_y)
            self._save_world_on_death()
            # M27: 记录遗产
            from systems.legacy_system import record_death
            points = record_death(self)
            self.message = f"你死了。获得 {points} 遗产点数。世界保留。"
            self.message = "你死了。世界保留，新角色继承一切。"
            return True
        return False

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
        """根据 y 坐标返回地质层名称。"""
        if y > -8:
            return "地表沉积层"
        elif y > -25:
            return "浅层沉积岩"
        elif y > -45:
            return "热液矿脉带"
        elif y > -70:
            return "岩浆侵入带"
        else:
            return "深部变质基底"

    def _detect_room(self, start_x, start_y):
        """从 (start_x, start_y) 开始 flood fill，检测是否是封闭空间"""
        from tile_props import get_tile_props
        from world_gen import TILE_AIR
        
        if self.world.get_tile(start_x, start_y)["tile"] != TILE_AIR:
            return None  # 起点必须是空气
        
        visited = set()
        queue = [(start_x, start_y)]
        has_door = False
        has_torch = False
        has_chest = False
        blocked = True
        
        while queue and len(visited) < 500:
            x, y = queue.pop(0)
            if (x, y) in visited:
                continue
            visited.add((x, y))
            
            for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
                nx, ny = x+dx, y+dy
                tile = self.world.get_tile(nx, ny)["tile"]
                props = get_tile_props(tile)
                
                if tile == "木门":
                    has_door = True
                    visited.add((nx, ny))
                    continue
                if tile == "火把":
                    has_torch = True
                    continue
                if tile == "木箱":
                    has_chest = True
                    continue
                if (nx, ny) in visited:
                    continue
                if props.get("passable", False) and not props.get("blocks_vision", False):
                    continue
                if abs(nx - start_x) > 40 or abs(ny - start_y) > 40:
                    blocked = False
                    continue
                if not props.get("passable", False):
                    queue.append((nx, ny))
        
        area = len(visited)
        if blocked and 15 <= area <= 400:
            return {"area": area, "has_door": has_door, "has_torch": has_torch, "has_chest": has_chest, "tiles": visited}
        return None
    
    def _check_room_formation(self):
        """检查玩家四周是否形成了封闭房间，并评级"""
        from world_gen import TILE_AIR
        for dx, dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]:
            cx, cy = self.player_x + dx, self.player_y + dy
            if self.world.get_tile(cx, cy)["tile"] == TILE_AIR:
                room = self._detect_room(cx, cy)
                if room:
                    return self._rate_room(room)
        return False
    
    def _rate_room(self, room):
        """给房间评级"""
        area = room["area"]
        has_door = room["has_door"]
        has_torch = room["has_torch"]
        has_chest = room["has_chest"]
        
        # 扫描房间内的高级建材
        luxury_count = 0
        for x, y in room.get("tiles", set()):
            tile = self.world.get_tile(x, y)["tile"]
            if tile in ("丝绸墙纸", "玻璃窗", "地毯", "石砖墙", "骨墙"):
                luxury_count += 1
        
        # 评级
        if has_door and has_torch and has_chest:
            if luxury_count >= 8:
                rating = "豪华基地"
                emoji = "👑"
            elif luxury_count >= 4:
                rating = "舒适小屋"
                emoji = "🏠"
            else:
                rating = "简陋木屋"
                emoji = "🛖"
            self.message = f"【{emoji}{rating}】面积{area}格，高级建材{luxury_count}个。"
        elif has_door:
            self.message = f"【房间】面积{area}格。放火把和箱子升级为基地！"
        elif has_torch:
            self.message = f"【空间】有火把，还缺个门。面积{area}格。"
        else:
            self.message = f"【空间】封闭空间，面积{area}格。"
        return True
    
    def _get_time_of_day(self):
        t = self.turn % DAY_LENGTH
        if DAWN_START <= t < DAY_START:
            return "黎明", 4
        elif DAY_START <= t < DUSK_START:
            return "白天", 9
        elif DUSK_START <= t < NIGHT_START:
            return "黄昏", 4
        else:
            return "夜晚", 1

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
        """根据玩家进度推进目标"""
        # 建了第一个房间 → 探索
        if self.goal == "build_first_room" and self._count_rooms_nearby() >= 1:
            self.goal = "explore_cave"
            self.message = "【目标】家已建成！深入地下探索吧。"
        # 探索到一定深度 → 狩猎
        elif self.goal == "explore_cave" and self.player_y < -20:
            self.goal = "kill_spiders"
            self.message = "【目标】你进入了深层地下！狩猎怪物收集稀有材料。"
        # 杀了一定数量怪物 → 建造豪华基地
        elif self.goal == "kill_spiders" and self.turn > 500:
            self.goal = "build_luxury"
            self.message = "【目标】收集了足够的材料，建造豪华基地吧！"
    
    def _count_rooms_nearby(self):
        """统计附近的房间数量"""
        count = 0
        for dx in range(-20, 21, 5):
            for dy in range(-20, 21, 5):
                room = self._detect_room(self.player_x + dx, self.player_y + dy)
                if room and room.get("has_door"):
                    count += 1
        return count
    
    def _check_special_location(self):
        """检测玩家是否进入特殊地貌"""
        if not hasattr(self.world, 'special_locations'):
            return
        for x, y, name in self.world.special_locations:
            if abs(self.player_x - x) <= 6 and abs(self.player_y - y) <= 6:
                if not hasattr(self, '_found_specials'):
                    self._found_specials = set()
                if (x, y) not in self._found_specials:
                    self._found_specials.add((x, y))
                    self.message = f"🔍 你发现了【{name}】！这里似乎有稀有资源..."
                    # 给奖励
                    loot_tables = {
                        "废弃矿洞": {"铁矿石": 10, "石头": 20},
                        "蜘蛛巢穴": {"蜘蛛丝": 15},
                        "水晶洞穴": {"钻石原石": 3, "玻璃": 8},
                        "地下湖": {"沙子": 15},
                        "远古遗迹": {"金矿石": 5, "大理石": 10},
                        "蘑菇洞": {"黏土": 20},
                        "硫磺温泉": {"硫磺": 10},
                    }
                    loot = loot_tables.get(name, {})
                    for item, count in loot.items():
                        self._add_material(item, count)
                    self.message += f" 获得: {', '.join(f'{c}x{k}' for k,c in loot.items())}"
                break

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
        if key2 in DIRECTIONS:
            dx, dy = DIRECTIONS[key2]
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

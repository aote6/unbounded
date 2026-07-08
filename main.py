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
from systems.interaction import get_nearby_chest, open_chest_menu
from systems.save_system import build_save_data, apply_load_data
from ui.equipment_ui import equipment_menu
from ui.game_renderer import draw
from ui.crafting_ui import crafting_menu
from systems.tag_system import load_rules, check_interaction
from config import (
    VIEW_WIDTH, VIEW_HEIGHT, WORLD_SEED,
    PLAYER_INITIAL_HP,
    PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX, PLAYER_BASE_HIT_CHANCE,
    SPAWN_INITIAL_COUNTDOWN, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    SPAWN_MIN_DISTANCE,
    DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START,
    WORLD_LAYERS, LAYER_DEPTH_OFFSET,
)
import monsters as monsters_mod
import items as items_mod
from inventory import Inventory

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
ORE_TO_MATERIAL = {
    "石头": "石头", "泥土": "皮",
    "煤矿": "铁",        # 煤作为铁的助熔剂，归入铁系
    "铜矿石": "石头",    # 劣质金属 → 石级
    "铁矿石": "铁",
    "银矿石": "铁",      # 银 ≈ 铁级，未来可改
    "金矿石": "钢",      # 金 → 钢级（精炼金属）
    "钻石原石": "黑曜石", # 钻石 → 顶级材质
    "硫磺": "骨",        # 硫磺 → 骨级（轻脆）
    "盐矿石": "石头",    # 盐 → 石级
    "黏土": "皮",        # 黏土 → 皮级（柔性）
    "沙子": "石头",      # 沙 → 石级
    "石灰岩": "石头",
    "大理石": "铁",      # 大理石 → 铁级（建筑用）
    "花岗岩": "铁",      # 花岗岩 → 铁级（硬石）
    "黑曜石": "黑曜石",
    "史莱姆凝胶": "骨",
}

def load_recipes():
    if not RECIPES_FILE.exists():
        print(f"[recipes] 文件不存在: {RECIPES_FILE}"); return {}
    try:
        with open(RECIPES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[recipes] JSON 解析失败: {e}"); return {}

# ═══════════════════════════════════
# 合成菜单
# ═══════════════════════════════════
def crafting_menu(stdscr, game):
    from ui.crafting_ui import crafting_menu as _ui
    _ui(stdscr, game)
# ═══════════════════════════════════
# 装备菜单
# ═══════════════════════════════════
def equipment_menu(stdscr, game):
    from ui.equipment_ui import equipment_menu as _ui
    _ui(stdscr, game)

# ═══════════════════════════════════
# 放置菜单（从背包挑一个可放置物进入建造模式）
# ═══════════════════════════════════
def place_menu(stdscr, game):
    candidates = [name for name, count in game.inventory.get_materials().items()
                  if count > 0 and items_mod.is_placeable(game.items, name)]
    if not candidates:
        game.message = "背包里没有可放置的物品。"
        return
    selected = 0
    h, w = len(candidates) + 6, 45
    y, x = max(0, (curses.LINES - h) // 2), max(0, (curses.COLS - w) // 2)
    win = curses.newwin(h, w, y, x)
    win.keypad(True)
    while True:
        win.erase(); win.box()
        win.addstr(0, 2, " 放置物品 ")
        win.addstr(1, 2, "↑↓ 选择 Enter 进入建造 c 关闭")
        for i, name in enumerate(candidates):
            line = f" {name} x{game.inventory.count(name)}"
            attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
            win.addstr(3 + i, 2, line[:w - 4], attr)
        win.refresh()
        key = win.getch()
        if key in (ord('c'), ord('q')):
            break
        elif key == curses.KEY_UP:
            selected = (selected - 1) % len(candidates)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(candidates)
        elif key in (curses.KEY_ENTER, 10, 13):
            name = candidates[selected]
            game.place_mode = items_mod.get_place_tile(game.items, name)
            game.place_item_name = name
            game.last_place = game.place_mode
            game.last_place_item_name = name
            game.cursor_x, game.cursor_y = game.player_x, game.player_y
            game.message = f"建造模式：放置 {name}，方向键移动光标，回车放置，c 退出。"
            break
    del win; game.stdscr.touchwin(); game.stdscr.refresh()

# ═══════════════════════════════════
# Game 类
# ═══════════════════════════════════

DIRECTIONS = {
    curses.KEY_LEFT: (-1,0), curses.KEY_RIGHT: (1,0),
    curses.KEY_UP: (0,-1), curses.KEY_DOWN: (0,1),
    ord("h"): (-1,0), ord("l"): (1,0), ord("k"): (0,-1), ord("j"): (0,1),
}
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
        self.equipment = {}                # 装备槽: {"main_hand": "石剑"}
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
        self.inventory.add(name, item_type="equipment", instance=inst)

    def _get_equipment_instance(self, name):
        for item_id, item in self.inventory.all_items():
            if item.item_type == "equipment" and item.instance and item.instance.name == name:
                return item.instance
        return None

    def _count_equipment(self, name):
        return sum(1 for _, item in self.inventory.all_items() 
               if item.item_type == "equipment" and item.instance and item.instance.name == name)

    def _get_item_attr(self, item_name, field_name):
        """获取装备实例的属性，兼容旧 items dict。"""
        inst = self._get_equipment_instance(item_name)
        if inst:
            return getattr(inst, field_name, 0)
        return self.items.get(item_name, {}).get(field_name, 0)

    def _get_nearby_chest(self):
        return get_nearby_chest(self)

    def open_chest_menu(self):
        open_chest_menu(self)

    def _equipment_bonus(self, field_name):
        total = 0
        for item_name in self.equipment.values():
            if field_name == "attack_bonus":
                dmg_min = self._get_item_attr(item_name, "damage_min")
                dmg_max = self._get_item_attr(item_name, "damage_max")
                if dmg_max > 0:
                    total += (dmg_min + dmg_max) // 2
                else:
                    total += self._get_item_attr(item_name, "attack_bonus")
            else:
                total += self._get_item_attr(item_name, field_name)
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

    def new_game(self):
        # 清理旧存档的 chunk 差分数据，防止跨存档污染
        import shutil
        from world_gen import SAVE_DIR
        if SAVE_DIR.exists():
            shutil.rmtree(SAVE_DIR)
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        if SAVE_FILE.exists():
            SAVE_FILE.unlink()
        self.world = generate_world(seed=WORLD_SEED)
        sx, sy = find_spawn(self.world, start_x=0)
        self.player_x, self.player_y = sx, sy
        self.respawn_x, self.respawn_y = sx, sy
        self.player_z = 0
        self.cursor_x, self.cursor_y = sx, sy
        self.player_hp = PLAYER_INITIAL_HP; self.player_max_hp = PLAYER_INITIAL_HP
        self.turn = 0
        self.inventory = Inventory()
        self.equipment = {}
        self.message = "新游戏开始。S 存档，L 读档。"
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
        """保存游戏状态到磁盘。"""
        data = build_save_data(self)
        try:
            SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.message = "游戏已保存。"
        except Exception as e:
            self.message = f"存档失败: {e}"
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
        """从磁盘读取存档并恢复游戏状态。"""
        if not SAVE_FILE.exists():
            self.message = "没有找到存档文件。"
            return False
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.message = f"读档失败: {e}"
            return False
        self.world = generate_world(seed=data.get("seed", WORLD_SEED), decorate=False)
        apply_load_data(self, data)
        return True



    def _maybe_cancel_dig(self, x, y):
        if self.dig_progress and (self.dig_progress["x"] != x or self.dig_progress["y"] != y):
            self.dig_progress = None

    def _dig_any_tile(self, x, y):
        tile = self.world.get_tile(x, y)["tile"]
        props = get_tile_props(tile)
        if not props["diggable"]:
            return False
        if not (self.dig_progress and self.dig_progress["x"] == x and self.dig_progress["y"] == y):
            tool_power = 1 + self._best_equipped_tool_bonus()
            base_turns = get_dig_turns(tile, tool_power)
            speed_bonus = self._digging_speed_bonus()
            total = max(1, base_turns - speed_bonus)
            self.dig_progress = {"x": x, "y": y, "remaining": total, "total": total}
        self.dig_progress["remaining"] -= 1
        if self.dig_progress["remaining"] <= 0:
            drop = props.get("drop")
            if drop:
                self._add_material(drop, 1)
                self.message = f"挖到了 {drop} x1（共 {self._count_material(drop)}）"
            else:
                self.message = f"挖掉了 {props['name']}。"
            self.world.set_tile(x, y, TILE_AIR)
            self.modified_tiles[(x, y)] = TILE_AIR
            if (x, y) in self.corpses:
                del self.corpses[(x, y)]
            self.dig_progress = None
            self._gain_skill("digging")
        else:
            self.message = f"挖掘中...还需 {self.dig_progress['remaining']} 回合"
        return True

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
        nx, ny = self.player_x + dx, self.player_y + dy
        tile = self.world.get_tile(nx, ny)["tile"]
        mon = self._monster_at(nx, ny)
        if self.place_mode is not None:
            self._move_cursor(dx, dy); return
        if mon:
            self._maybe_cancel_dig(nx, ny); self._attack_monster(mon); return
        props = get_tile_props(tile)
        if props["passable"]:
            # 树虽然可穿过，但应该自动挖掘
            from world_gen import TILE_TREE
            if tile == TILE_TREE:
                self._dig_any_tile(nx, ny)
                return
            if self._monster_has_position(nx, ny):
                return
            self._maybe_cancel_dig(nx, ny)
            self.player_x, self.player_y = nx, ny
            # 检查是否进入特殊地貌
            self._check_special_location()
        elif props["diggable"]:
            self._dig_natural_tile(nx, ny)

    def _move_cursor(self, dx, dy):
        nx, ny = self.cursor_x + dx, self.cursor_y + dy
        self.cursor_x, self.cursor_y = nx, ny
        self.message = f"建造光标 ({self.cursor_x},{self.cursor_y})，回车放置，c 退出。"

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
        self.world.set_tile(bx, by, self.place_mode)
        self.modified_tiles[(bx, by)] = self.place_mode
        # 如果放置的是箱子，初始化空箱子
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
        if random.random() > PLAYER_BASE_HIT_CHANCE:
            self.message = f"攻击 {monster['name']}，但未命中！"; self.turn += 1; return
        dmg = random.randint(PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX)
        dmg += self._equipment_bonus("attack_bonus")
        dmg += self._combat_damage_bonus()
        armor = monster.get("properties", {}).get("natural_armor", 0)
        dmg = max(1, dmg - armor)
        monster["hp"] -= dmg
        # 发送伤害事件（状态效果、吸血等由事件处理器处理）
        from systems.event_bus import EventBus, EventType, GameEvent
        bus = EventBus()
        bus.emit(GameEvent(EventType.DAMAGE_DEALT, {"attacker": "player", "target": monster, "damage": dmg}), self)
        self._gain_skill("combat")
        self._gain_skill("combat")
        if monster["hp"] <= 0:
            self._kill_monster(monster, cause="attack")
        else:
            hp_ratio = monster["hp"] / monster["max_hp"]
            if hp_ratio < 0.3:
                self.message = f"攻击 {monster['name']}，造成 {dmg} 点伤害。它快不行了！"
            else:
                self.message = f"攻击 {monster['name']}，造成 {dmg} 点伤害。"

    def _kill_monster(self, monster, cause="attack"):
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
            self.world.set_tile(mx, my, corpse_tile)
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
        for m in list(self.monsters):
            # 旧版 on_fire
            if m.get("on_fire", 0) > 0:
                m["hp"] -= 2; m["on_fire"] -= 1
                if m["hp"] <= 0:
                    self._kill_monster(m, cause="burn"); continue
            # 新版 burning（标签系统触发）
            burn = m.get("burning")
            if burn and burn.get("duration", 0) > 0:
                m["hp"] -= burn.get("damage_per_turn", 2)
                burn["duration"] -= 1
                if burn["duration"] <= 0:
                    del m["burning"]
                if m["hp"] <= 0:
                    self._kill_monster(m, cause="burn"); continue
            if m.get("poisoned", 0) > 0:
                m["hp"] -= 1; m["poisoned"] -= 1
                if m["hp"] <= 0:
                    self._kill_monster(m, cause="poison")

    def _tick_corpses(self):
        decayed = []
        for (cx, cy), remaining in self.corpses.items():
            remaining -= 1
            if remaining <= 0:
                if self.world.get_tile(cx, cy)["tile"] != TILE_AIR:
                    self.world.set_tile(cx, cy, TILE_AIR)
                    self.modified_tiles[(cx, cy)] = TILE_AIR
                decayed.append((cx, cy))
            else:
                self.corpses[(cx, cy)] = remaining
        for pos in decayed:
            del self.corpses[pos]

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
            self.world.set_tile(nx, ny, TILE_AIR)
            self.modified_tiles[(nx, ny)] = TILE_AIR
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
        # 卸下装备
        for slot in list(self.equipment.keys()):
            self.equipment.pop(slot, None)
        self.message = f"你的物品散落在 ({x},{y}) 附近。"
    
    def check_death(self):
        if self.player_hp <= 0:
            # 掉落背包到原地
            self._drop_items_on_ground(self.player_x, self.player_y)
            # 在复活点重生
            if self.bed_x is not None:
                self.player_x, self.player_y = self.bed_x, self.bed_y
            else:
                self.player_x, self.player_y = self.respawn_x, self.respawn_y
            self.player_hp = self.player_max_hp
            self.message = "你死了。物品掉落在原地。"
            return True
        return False

    def show_death_screen(self):
        self.stdscr.erase()
        m1, m2 = "你死了。", f"物品掉落在 ({self.player_x},{self.player_y})"
        m3 = "你将在出生点复活。"
        m4 = "按任意键继续..."
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(h//2-3, max(0, w//2-len(m1)//2), m1, curses.A_BOLD | curses.color_pair(7))
        self.stdscr.addstr(h//2-1, max(0, w//2-len(m2)//2), m2)
        self.stdscr.addstr(h//2, max(0, w//2-len(m3)//2), m3)
        self.stdscr.addstr(h//2+2, max(0, w//2-len(m4)//2), m4)
        self.stdscr.refresh(); self.stdscr.getch()

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
        self._tick_corpses()
        self._tick_monsters()
        self._tick_status_effects()
        self._try_spawn_monster()
        self.world.keep_radius(self.player_x, self.player_y, CHUNK_KEEP_RADIUS)
        if self.turn % 10 == 0:
            self._check_room_formation()
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

    def _handle_open_chest(self):
        self.open_chest_menu()

    def _handle_craft(self):
        if self.place_mode:
            if self.place_item_name:
                self.message = f"退出了建造模式，{self.place_item_name} 仍在背包里。"
                self.place_mode = None
                self.place_item_name = None
            else:
                ingredients = self.recipes.get(self.place_mode, {}).get("ingredients", {})
                if not ingredients:
                    for rname, rdata in self.recipes.items():
                        if rname == self.place_mode or rdata.get("result", {}).get("archetype") == self.place_mode:
                            ingredients = rdata.get("ingredients", {})
                            break
                if ingredients:
                    for mat, count in ingredients.items():
                        self._add_material(mat, count)
                    self.message = f"取消建造 {self.place_mode}，材料已退还。"
                else:
                    self.message = "退出了建造模式。"
                self.place_mode = None
        else:
            crafting_menu(self.stdscr, self)

    def _handle_equip(self):
        equipment_menu(self.stdscr, self)

    def _handle_place_menu(self):
        place_menu(self.stdscr, self)

    def _handle_confirm_place(self):
        if self.place_mode:
            self._do_place()
            return True
        return False

    def _handle_repeat_build(self):
        if self.last_place:
            self.place_mode = self.last_place
            self.place_item_name = self.last_place_item_name
            self.cursor_x, self.cursor_y = self.player_x, self.player_y
            self.message = f"建造模式：放置 {self.last_place}，方向键移动光标，回车放置，c 取消。"
        else:
            self.message = "还没有建造过任何东西。合成一个石墙，或按 b 放置背包里的木箱。"

    def _handle_reload(self):
        self.recipes = load_recipes()
        self.items = items_mod.load_items()
        self.monster_data = monsters_mod.load_monsters()
        self.message = "数据已重载"

    def _handle_save(self):
        self.save_game()

    def _handle_load(self):
        self.load_game()

    def _handle_look_mode(self):
        self.look_mode = True
        self.cursor_x, self.cursor_y = self.player_x, self.player_y
        self.message = "查看模式：方向键移动光标(+)，显示光标处信息，其他键退出。"
        draw(self)
        while True:
            cx, cy = self.cursor_x, self.cursor_y
            tile = self.world.get_tile(cx, cy)
            tile_id = tile["tile"]
            props = get_tile_props(tile_id)
            name = props.get("name", "未知")
            hardness = props.get("hardness", 0)
            drop = props.get("drop", "无")
            diggable = props.get("diggable", False)
            extra = tile.get("extra", {})
            info = f"({cx},{cy}) {name}"
            if diggable:
                info += f" | 可挖 | 硬度:{hardness}"
                if drop: info += f" | 掉落:{drop}"
            else:
                info += " | 不可挖"
            if extra: info += f" | {extra}"
            mon = self._monster_at(cx, cy)
            if mon:
                info += f" | {mon["name"]} HP:{mon["hp"]}/{mon["max_hp"]}"
            self.message = info
            draw(self)
            key2 = self.stdscr.getch()
            if key2 in DIRECTIONS:
                dx, dy = DIRECTIONS[key2]
                ox2, oy2 = self.get_viewport_origin()
                nx, ny = self.cursor_x + dx, self.cursor_y + dy
                if ox2 <= nx < ox2 + VIEW_WIDTH and oy2 <= ny < oy2 + VIEW_HEIGHT:
                    self.cursor_x, self.cursor_y = nx, ny
            else:
                self.look_mode = False
                self.message = "退出查看模式。"
                break

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
    def run(self):
        """主循环：获取按键 → 分发处理 → 推进回合。"""
        draw(self)
        while True:
            if self.check_death():
                self.show_death_screen()
                import shutil
                from world_gen import SAVE_DIR
                if SAVE_DIR.exists():
                    shutil.rmtree(SAVE_DIR)
                SAVE_DIR.mkdir(parents=True, exist_ok=True)
                if SAVE_FILE.exists():
                    SAVE_FILE.unlink()
                self.message = "你死了。存档已清除。"
                self.new_game()
                continue
            key = self.stdscr.getch()
            curses.flushinp()
            acted = False
            if key in (ord("q"), ord("Q")):
                break
            elif key in (ord("o"), ord("O")):
                self._handle_open_chest()
            elif key in (ord("c"), ord("C")):
                self._handle_craft()
            elif key == ord("e"):
                self._handle_equip()
            elif key == ord("b"):
                self._handle_place_menu()
            elif key in (curses.KEY_ENTER, 10, 13):
                acted = self._handle_confirm_place()
            elif key == ord("."):
                self._handle_repeat_build()
            elif key in (ord("r"), ord("R")):
                self._handle_reload()
            elif key in (ord("s"), ord("S")):
                self._handle_save()
            elif key in (ord("l"), ord("L")):
                self._handle_load()
            elif key == ord("x"):
                self._handle_look_mode()
            elif key == ord("d"):
                acted = self._handle_dig_mode()
            elif key in DIRECTIONS:
                dx, dy = DIRECTIONS[key]
                self.try_move_or_dig(dx, dy)
                acted = True
            if acted:
                self.advance_turn()
                draw(self)
def main(stdscr):
    game = Game(stdscr)
    # 检查是否有存档
    if SAVE_FILE.exists():
        game.stdscr.erase()
        h, w = game.stdscr.getmaxyx()
        msg1 = "检测到存档文件"
        msg2 = "按 L 继续上次游戏"
        msg3 = "按 N 开始新游戏（会覆盖存档）"
        game.stdscr.addstr(h//2-2, max(0,w//2-15), msg1, curses.A_BOLD)
        game.stdscr.addstr(h//2, max(0,w//2-15), msg2)
        game.stdscr.addstr(h//2+1, max(0,w//2-15), msg3)
        game.stdscr.refresh()
        while True:
            key = game.stdscr.getch()
            if key in (ord('l'), ord('L')):
                if game.load_game():
                    break
                else:
                    game.new_game()
                    break
            elif key in (ord('n'), ord('N')):
                # 删旧存档
                import shutil
                from world_gen import SAVE_DIR
                if SAVE_FILE.exists():
                    SAVE_FILE.unlink()
                if SAVE_DIR.exists():
                    shutil.rmtree(SAVE_DIR)
                game.new_game()
                break
    else:
        game.new_game()
    game.run()

if __name__ == "__main__":
    curses.wrapper(main)

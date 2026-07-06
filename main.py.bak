""" main.py 终端版游戏主循环——俯视图 + 技能 + 存档。"""
import curses, json, random, traceback, os
from pathlib import Path
from world_gen import (
    generate_world, find_spawn, World,
    TILE_AIR, TILE_DIRT, TILE_STONE, TILE_DROPS, CHUNK_SIZE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
    TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_SAND,
    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,
)
from tile_props import get_tile_props, get_tile_char, get_dig_turns
from config import (
    VIEW_WIDTH, VIEW_HEIGHT, WORLD_SEED,
    PLAYER_INITIAL_HP,
    PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX, PLAYER_BASE_HIT_CHANCE,
    SPAWN_INITIAL_COUNTDOWN, SPAWN_INTERVAL_MIN, SPAWN_INTERVAL_MAX,
    SPAWN_MIN_DISTANCE,
    DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START,
)
import monsters as monsters_mod
import items as items_mod

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

    def to_dict(self) -> dict:
        """序列化为普通 dict（用于 JSON 存档）。"""
        return {
            "name": self.name, "slot": self.slot,
            "attack_bonus": self.attack_bonus, "defense_bonus": self.defense_bonus,
            "tool_bonus": self.tool_bonus, "damage_min": self.damage_min,
            "damage_max": self.damage_max, "hit_bonus": self.hit_bonus,
            "affixes": self.affixes, "on_attack": self.on_attack,
            "lifesteal": self.lifesteal, "speed_bonus": self.speed_bonus,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EquipmentInstance":
        """从 dict 反序列化。"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


BASE_DIR = Path(__file__).parent
RECIPES_FILE = BASE_DIR / "data" / "recipes.json"
SAVE_FILE = BASE_DIR / "data" / "save.json"
MIN_TERM_H = VIEW_HEIGHT + 8
MIN_TERM_W = VIEW_WIDTH
CORPSE_DECAY_TURNS = 50
CHUNK_KEEP_RADIUS = 3
SKILL_LEVEL_THRESHOLD = 10

TILE_CHARS = {
    TILE_AIR: " ", TILE_DIRT: ".", TILE_STONE: "#",
    TILE_COAL: "\u263b", TILE_COPPER: "\u25cb", TILE_IRON: "\u2642",
    TILE_SILVER: "\u263c", TILE_GOLD: "\u2600", TILE_DIAMOND: "\u2666",
    TILE_SULFUR: "\u263f", TILE_SALT: "\u25a1", TILE_CLAY: "\u2248",
    TILE_SAND: "\u2591", TILE_LIMESTONE: "\u2593", TILE_MARBLE: "\u2592",
    TILE_GRANITE: "\u2588", TILE_OBSIDIAN: "\u25a0",
    "石墙": "\u2588", "木墙": "\u2593", "火把": "\u2020",
    "史莱姆尸体": "%", "巨型史莱姆尸体": "%", "蝙蝠尸体": ",",
    "岩石傀儡残骸": "\u2588",
}

DIRECTIONS = {
    curses.KEY_LEFT: (-1,0), curses.KEY_RIGHT: (1,0),
    curses.KEY_UP: (0,-1), curses.KEY_DOWN: (0,1),
    ord('h'): (-1,0), ord('l'): (1,0), ord('k'): (0,-1), ord('j'): (0,1),
}

SLOT_NAMES = {"main_hand":"主手","off_hand":"副手","body":"身体","accessory":"饰品"}

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
    recipes = game.recipes
    if not recipes:
        game.message = "（没有可用配方）"; return
    names = list(recipes.keys())
    selected = 0
    h, w = len(names)+7, 50
    y, x = max(0,(curses.LINES-h)//2), max(0,(curses.COLS-w)//2)
    win = curses.newwin(h,w,y,x)
    win.keypad(True)
    status_msg = ""
    def redraw():
        win.erase(); win.box()
        win.addstr(0,2," 合成菜单 ")
        win.addstr(1,2,"↑↓ 选择 Enter 合成 c 关闭")
        for i,name in enumerate(names):
            r = recipes[name]
            ing = " + ".join(f"{v}x{k}" for k,v in r.get("ingredients",{}).items())
            line = f" {name} ← {ing}"
            if r.get("desc"): line += f" ({r['desc']})"
            attr = curses.A_REVERSE if i==selected else curses.A_NORMAL
            win.addstr(3+i,2,line[:w-4],attr)
        if status_msg:
            win.addstr(h-2,2,status_msg[:w-4],curses.A_BOLD)
        win.refresh()
    while True:
        redraw()
        key = win.getch()
        if key in (ord('c'), ord('q')): status_msg = ""; break
        elif key == curses.KEY_UP: selected = (selected-1) % len(names); status_msg = ""
        elif key == curses.KEY_DOWN: selected = (selected+1) % len(names); status_msg = ""
        elif key in (curses.KEY_ENTER, 10, 13):
            name = names[selected]; r = recipes[name]
            can = all(game._count_material(m) >= c for m,c in r.get("ingredients",{}).items())
            if not can:
                status_msg = "材料不足！按任意键继续。"
                redraw(); win.getch(); status_msg = ""; continue
            for m,c in r.get("ingredients",{}).items():
                game._remove_material(m, c)
            if items_mod.is_placeable(game.items, name):
                game.place_mode = items_mod.get_place_tile(game.items, name)
                game.last_place = game.place_mode
                game.cursor_x, game.cursor_y = game.player_x, game.player_y
                game.message = f"合成了 {name}！建造模式：方向键移动光标，回车放置，c 退出。"
                break
            game._add_equipment_instance(name)
            status_msg = f"合成了 {name} x1（共 {game._count_equipment(name)}）"
    del win; game.stdscr.touchwin(); game.stdscr.refresh()

# ═══════════════════════════════════
# 装备菜单
# ═══════════════════════════════════
def equipment_menu(stdscr, game):
    slots = [("main_hand","主手"),("off_hand","副手"),("body","身体"),("accessory","饰品")]
    sel_slot = 0
    h, w = len(slots)+6, 50
    y, x = max(0,(curses.LINES-h)//2), max(0,(curses.COLS-w)//2)
    win = curses.newwin(h,w,y,x)
    win.keypad(True)
    status_msg = ""
    def redraw():
        win.erase(); win.box()
        win.addstr(0,2," 装备菜单 ")
        win.addstr(1,2,"↑↓ 选槽位 Enter 换装 c 关闭")
        for i,(slot_id,slot_name) in enumerate(slots):
            equipped = game.equipment.get(slot_id, "（空）")
            line = f" {slot_name}: {equipped}"
            if equipped != "（空）":
                inst = game._get_equipment_instance(equipped)
                if inst:
                    if inst.affixes: line += " [" + "|".join(inst.affixes) + "]"
            attr = curses.A_REVERSE if i==sel_slot else curses.A_NORMAL
            win.addstr(3+i,2,line[:w-4],attr)
        if status_msg:
            win.addstr(h-2,2,status_msg[:w-4],curses.A_BOLD)
        win.refresh()
    while True:
        redraw()
        key = win.getch()
        if key in (ord('c'), ord('q')): break
        elif key == curses.KEY_UP: sel_slot = (sel_slot-1) % len(slots); status_msg = ""
        elif key == curses.KEY_DOWN: sel_slot = (sel_slot+1) % len(slots); status_msg = ""
        elif key in (curses.KEY_ENTER, 10, 13):
            slot_id, slot_name = slots[sel_slot]
            candidates = []
            for inst in game.equipment_instances:
                if inst.slot == slot_id:
                    candidates.append(inst.name)
            if game.equipment.get(slot_id):
                candidates.insert(0, "__unequip__")
            if not candidates:
                status_msg = f"背包里没有能装备到{slot_name}的物品。按任意键继续。"
                redraw(); win.getch(); status_msg = ""; continue
            sub_sel = 0; sub_h = len(candidates)+4; sub_w = 40
            sub_y = max(0, (curses.LINES-sub_h)//2); sub_x = max(0, (curses.COLS-sub_w)//2)
            sub = curses.newwin(sub_h, sub_w, sub_y, sub_x); sub.keypad(True)
            while True:
                sub.erase(); sub.box()
                sub.addstr(0,2,f" 选择{slot_name} 装备 ")
                for ci, cname in enumerate(candidates):
                    label = "（卸下）" if cname == "__unequip__" else cname
                    attr = curses.A_REVERSE if ci==sub_sel else curses.A_NORMAL
                    sub.addstr(2+ci,2,label[:sub_w-4],attr)
                sub.refresh()
                sk = sub.getch()
                if sk in (ord('c'), ord('q')): break
                elif sk == curses.KEY_UP: sub_sel = (sub_sel-1) % len(candidates)
                elif sk == curses.KEY_DOWN: sub_sel = (sub_sel+1) % len(candidates)
                elif sk in (curses.KEY_ENTER, 10, 13):
                    chosen = candidates[sub_sel]; old = game.equipment.get(slot_id)
                    if chosen == "__unequip__":
                        if old: game.equipment.pop(slot_id, None)
                        game.message = f"卸下了 {old}。"
                    else:
                        if old: game.equipment.pop(slot_id, None)
                        game.equipment[slot_id] = chosen
                        game.message = f"装备了 {chosen} 到{slot_name}。"
                    break
            del sub
    del win; game.stdscr.touchwin(); game.stdscr.refresh()

# ═══════════════════════════════════
# Game 类
# ═══════════════════════════════════
class Game:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self._setup_curses()
        self.world = None
        self.player_x = self.player_y = 0
        self.cursor_x = self.cursor_y = 0
        self.player_hp = PLAYER_INITIAL_HP
        self.player_max_hp = PLAYER_INITIAL_HP
        self.turn = 0
        self.materials = {}                # 堆叠材料: {"石头": 15}
        self.equipment_instances = []      # 装备实例列表: [{"name":"石剑","slot":"main_hand","attack_bonus":2,...}]
        self.equipment = {}                # 装备槽: {"main_hand": "石剑"}
        self.message = "欢迎。世界无限延伸。hjkl 移动，c 合成，e 装备，d 挖掘，q 退出。S 存档，L 读档。"
        self.place_mode = None; self.last_place = None
        self.dig_progress = None; self.look_mode = False
        self.recipes = load_recipes()
        self.items = items_mod.load_items()
        self.monster_data = monsters_mod.load_monsters()
        self.monsters = []
        self._monster_index = {}
        self.spawn_counter = {"count": SPAWN_INITIAL_COUNTDOWN}
        self.corpses = {}
        self.modified_tiles = {}
        self.skills = {"digging": 0, "combat": 0, "defense": 0}
        self.skill_levels = {"digging": 1, "combat": 1, "defense": 1}

    # ── 材料系统（堆叠物品） ──
    def _count_material(self, name):
        return self.materials.get(name, 0)

    def _add_material(self, name, count):
        self.materials[name] = self.materials.get(name, 0) + count

    def _remove_material(self, name, count):
        if name in self.materials:
            self.materials[name] -= count
            if self.materials[name] <= 0:
                del self.materials[name]

    # ── 装备实例系统（独立物品） ──
    def _add_equipment_instance(self, name, instance_data=None):
        """添加一个装备实例到背包（创建 EquipmentInstance 对象）。"""
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
        self.equipment_instances.append(inst)

    def _get_equipment_instance(self, name):
        for inst in self.equipment_instances:
            if inst.name == name:
                return inst
        return None

    def _remove_equipment_instance(self, name):
        for i, inst in enumerate(self.equipment_instances):
            if inst.name == name:
                self.equipment_instances.pop(i)
                return True
        return False

    def _count_equipment(self, name):
        return sum(1 for inst in self.equipment_instances if inst.name == name)

    def _get_item_attr(self, item_name, field_name):
        """获取装备实例的属性，兼容旧 items dict。"""
        inst = self._get_equipment_instance(item_name)
        if inst:
            return getattr(inst, field_name, 0)
        return self.items.get(item_name, {}).get(field_name, 0)

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
        self.cursor_x, self.cursor_y = sx, sy
        self.player_hp = PLAYER_INITIAL_HP; self.player_max_hp = PLAYER_INITIAL_HP
        self.turn = 0
        self.materials = {}
        self.equipment_instances = []
        self.equipment = {}
        self.message = "新游戏开始。S 存档，L 读档。"
        self.place_mode = None; self.last_place = None
        self.dig_progress = None; self.look_mode = False
        self.recipes = load_recipes(); self.items = items_mod.load_items()
        self.monster_data = monsters_mod.load_monsters()
        self.monsters = []; self._monster_index = {}
        self.spawn_counter = {"count": SPAWN_INITIAL_COUNTDOWN}
        self.corpses = {}; self.modified_tiles = {}
        self.skills = {"digging": 0, "combat": 0, "defense": 0}
        self.skill_levels = {"digging": 1, "combat": 1, "defense": 1}

    def save_game(self):
        # 先让 World 保存所有脏 chunk 到磁盘
        self.world.save_all()
        # 只保存玩家状态和怪物数据，地形修改全部由 chunk 管理
        data = {
            "seed": WORLD_SEED,
            "player_x": self.player_x, "player_y": self.player_y,
            "player_hp": self.player_hp, "player_max_hp": self.player_max_hp,
            "turn": self.turn,
            "materials": self.materials,
            "equipment_instances": [inst.to_dict() for inst in self.equipment_instances],
            "equipment": self.equipment,
            "skills": self.skills, "skill_levels": self.skill_levels,
            "spawn_counter": self.spawn_counter,
            "corpses": {f"{x},{y}": v for (x, y), v in self.corpses.items()},
            "monsters": [{"name": m["name"], "x": m["x"], "y": m["y"],
                          "hp": m["hp"], "max_hp": m["max_hp"]} for m in self.monsters],
        }
        try:
            SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.message = "游戏已保存。"
        except Exception as e:
            self.message = f"存档失败: {e}"

    def load_game(self):
        if not SAVE_FILE.exists():
            self.message = "没有找到存档文件。"; return False
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.message = f"读档失败: {e}"; return False
        self.world = generate_world(seed=data.get("seed", WORLD_SEED))
        self.player_x = data["player_x"]; self.player_y = data["player_y"]
        self.cursor_x, self.cursor_y = self.player_x, self.player_y
        self.player_hp = data["player_hp"]; self.player_max_hp = data["player_max_hp"]
        self.turn = data["turn"]
        self.materials = data.get("materials", {})
        self.equipment_instances = [
            EquipmentInstance.from_dict(d) if isinstance(d, dict) else d
            for d in data.get("equipment_instances", [])
        ]
        self.equipment = data.get("equipment", {})
        self.skills = data.get("skills", {"digging": 0, "combat": 0, "defense": 0})
        self.skill_levels = data.get("skill_levels", {"digging": 1, "combat": 1, "defense": 1})
        self.spawn_counter = data.get("spawn_counter", {"count": SPAWN_INITIAL_COUNTDOWN})
        self.modified_tiles = {}  # 保留兼容，但不再主动使用
        self.corpses = {}
        for key, val in data.get("corpses", {}).items():
            x_str, y_str = key.split(",")
            self.corpses[(int(x_str), int(y_str))] = val
        self.monsters = []
        self._monster_index = {}
        for md in data.get("monsters", []):
            template = self.monster_data.get(md["name"], {})
            m = {
                "name": md["name"], "char": template.get("char", "?"),
                "x": md["x"], "y": md["y"], "hp": md["hp"], "max_hp": md["max_hp"],
                "attack_power": tuple(template.get("attack_power", [1, 3])),
                "hit_chance": template.get("hit_chance", 0.7),
                "vision": template.get("vision", 6),
                "flee_at_hp_ratio": template.get("flee_at_hp_ratio", 0.3),
                "scores": template.get("scores", {}),
                "drop": template.get("drop", {}),
                "corpse_tile": template.get("corpse_tile"),
                "split_into": template.get("split_into"),
                "special_behavior": template.get("special_behavior"),
                "properties": template.get("properties", {}),
            }
            self.monsters.append(m)
        self.place_mode = None; self.last_place = None
        self.dig_progress = None; self.look_mode = False
        self.recipes = load_recipes(); self.items = items_mod.load_items()
        self.monster_data = monsters_mod.load_monsters()
        # 地形修改已在 World._load_chunk 时从磁盘恢复，无需遍历
        self._build_monster_index()
        self.message = f"读档成功。位置 ({self.player_x},{self.player_y})。"
        return True

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
            # 也要检查是否有怪物挡路（空间索引 O(1)）
            if self._monster_has_position(nx, ny):
                return
            self._maybe_cancel_dig(nx, ny)
            self.player_x, self.player_y = nx, ny
        elif props["diggable"]:
            self._dig_natural_tile(nx, ny)

    def _move_cursor(self, dx, dy):
        nx, ny = self.cursor_x + dx, self.cursor_y + dy
        self.cursor_x, self.cursor_y = nx, ny
        self.message = f"建造光标 ({self.cursor_x},{self.cursor_y})，回车放置，c 退出。"

    def _do_place(self):
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
        effects = self._collect_attack_effects()
        for effect in effects:
            if effect == "fire":
                monster["on_fire"] = 3
            elif effect == "poison":
                monster["poisoned"] = 5
        lifesteal_total = 0
        for item_name in self.equipment.values():
            lifesteal_total += self._get_item_attr(item_name, "lifesteal")
        if lifesteal_total > 0:
            heal = min(lifesteal_total, dmg)
            self.player_hp = min(self.player_max_hp, self.player_hp + heal)
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
        corpse_tile = monster.get("corpse_tile")
        splits = monsters_mod.get_split_spawns(monster, self.monster_data)
        drop_name, drop_obj = monsters_mod.generate_loot_for(self.player_y)
        if drop_name:
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
            if m.get("on_fire", 0) > 0:
                m["hp"] -= 2; m["on_fire"] -= 1
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

    def check_death(self):
        return self.player_hp <= 0

    def show_death_screen(self):
        self.stdscr.erase()
        m1, m2 = "你死了。", f"位置 ({self.player_x},{self.player_y})"
        mats = " ".join(f"{k}:{v}" for k, v in self.materials.items()) or "（空）"
        eq_names = [v for v in self.equipment.values() if v]
        eq = " ".join(f"{SLOT_NAMES.get(k,k)}:{v}" for k,v in self.equipment.items()) or "（空）"
        sk = f"挖掘:{self.skill_levels['digging']} 战斗:{self.skill_levels['combat']} 防御:{self.skill_levels['defense']}"
        m3, m4, m5 = f"材料: {mats}", f"装备: {eq}", f"技能等级: {sk}"
        m6 = "按任意键退出。"
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(h//2-4, max(0, w//2-len(m1)//2), m1, curses.A_BOLD | curses.color_pair(7))
        self.stdscr.addstr(h//2-2, max(0, w//2-len(m2)//2), m2)
        self.stdscr.addstr(h//2-1, max(0, w//2-len(m3)//2), m3)
        self.stdscr.addstr(h//2, max(0, w//2-len(m4)//2), m4)
        self.stdscr.addstr(h//2+1, max(0, w//2-len(m5)//2), m5)
        self.stdscr.addstr(h//2+3, max(0, w//2-len(m6)//2), m6)
        self.stdscr.refresh(); self.stdscr.getch()

    def get_viewport_origin(self):
        vx = self.player_x - VIEW_WIDTH // 2
        vy = self.player_y - VIEW_HEIGHT // 2
        return vx, vy

    def tile_attr(self, tile):
        props = get_tile_props(tile); name = props["name"]
        # 全局色调：夜晚暗一些
        _, ambient = self._get_time_of_day()
        if ambient <= 2:
            return curses.color_pair(4)  # 夜晚暗色
        if name == "石头":
            return curses.color_pair(1)
        elif name == "泥土":
            return curses.color_pair(2)
        elif "尸体" in name or "残骸" in name:
            return curses.color_pair(9) | curses.A_BOLD
        elif not props["passable"]:
            return curses.color_pair(4) | curses.A_BOLD
        return curses.A_NORMAL

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

    def draw(self):
        if not self._check_terminal_size():
            return
        self.stdscr.erase()
        ox, oy = self.get_viewport_origin()
        time_name, ambient = self._get_time_of_day()

        for row in range(VIEW_HEIGHT):
            wy = oy + row
            for col in range(VIEW_WIDTH):
                wx = ox + col
                if self._monster_has_position(wx, wy):
                    m = self._monster_at(wx, wy); ch = m["char"]
                    if m["hp"] < m["max_hp"] * 0.5:
                        attr = curses.color_pair(7) | curses.A_BOLD
                    else:
                        attr = curses.color_pair(6) | curses.A_BOLD
                elif wx == self.player_x and wy == self.player_y:
                    ch, attr = "@", curses.color_pair(3) | curses.A_BOLD
                elif (self.place_mode or self.look_mode) and wx == self.cursor_x and wy == self.cursor_y:
                    ch, attr = "+", curses.color_pair(8) | curses.A_BOLD
                else:
                    tile = self.world.get_tile(wx, wy)["tile"]
                    ch = TILE_CHARS.get(tile, get_tile_char(tile))
                    attr = self.tile_attr(tile)
                # 夜晚全局压暗
                if ambient <= 2:
                    attr = curses.color_pair(4)
                try:
                    self.stdscr.addstr(row, col, ch, attr)
                except curses.error:
                    pass

        mats = " ".join(f"{k}:{v}" for k, v in self.materials.items()) or "（空）"
        eq_parts = []
        for slot_id in ("main_hand", "off_hand", "body", "accessory"):
            eq = self.equipment.get(slot_id, "空")
            eq_parts.append(f"{SLOT_NAMES[slot_id]}:{eq}")
        eq_str = " | ".join(eq_parts)
        def_bonus = self._player_defense()
        hp_str = f"HP: {self.player_hp}/{self.player_max_hp}"
        if def_bonus > 0:
            hp_str += f" 防:{def_bonus}"
        sk_str = f"挖掘:{self.skill_levels['digging']} 战斗:{self.skill_levels['combat']} 防御:{self.skill_levels['defense']}"
        s1 = f"[{time_name}] | {hp_str} | 技能 {sk_str} | ({self.player_x},{self.player_y})"
        if self.place_mode:
            s1 += f" | [建造: {self.place_mode}]"
        if self.dig_progress:
            s1 += f" | [挖掘中 {self.dig_progress['remaining']}/{self.dig_progress['total']}]"
        s1 += f" | 怪物:{len(self.monsters)} 尸体:{len(self.corpses)}"
        s2 = f"装备: {eq_str}"
        s3 = f"材料: {mats}"
        try:
            self.stdscr.addstr(VIEW_HEIGHT+1, 0, s1, curses.A_BOLD)
            self.stdscr.addstr(VIEW_HEIGHT+2, 0, s2)
            self.stdscr.addstr(VIEW_HEIGHT+3, 0, s3)
            self.stdscr.addstr(VIEW_HEIGHT+4, 0, self.message)
            self.stdscr.addstr(VIEW_HEIGHT+6, 0,
                "移动 | c 合成 | e 装备 | x 查看 | d 挖掘 | . 重复建造 | 回车 放置 | r 重载 | S 存档 | L 读档 | q 退出")
        except curses.error:
            pass
        self.stdscr.refresh()

    def advance_turn(self):
        self._tick_corpses()
        self._tick_monsters()
        self._tick_status_effects()
        self._try_spawn_monster()
        self.world.keep_radius(self.player_x, self.player_y, CHUNK_KEEP_RADIUS)

    def run(self):
        self.draw()
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
            acted = False
            if key in (ord('q'), ord('Q')): break
            elif key in (ord('c'), ord('C')):
                if self.place_mode:
                    self.place_mode = None; self.message = "退出了建造模式。"
                else:
                    crafting_menu(self.stdscr, self); self.draw(); continue
            elif key == ord('e'):
                equipment_menu(self.stdscr, self); self.draw(); continue
            elif key in (curses.KEY_ENTER, 10, 13):
                if self.place_mode: self._do_place(); acted = True
                self.draw(); continue
            elif key == ord('.'):
                if self.last_place:
                    self.place_mode = self.last_place
                    self.cursor_x, self.cursor_y = self.player_x, self.player_y
                    self.message = f"重复建造 {self.last_place}（建造模式）"
                else:
                    self.message = "还没有建造过任何东西。"
                self.draw(); continue
            elif key in (ord('r'), ord('R')):
                self.recipes = load_recipes()
                self.items = items_mod.load_items()
                self.monster_data = monsters_mod.load_monsters()
                self.message = "数据已重载"
                self.draw(); continue
            elif key in (ord('s'), ord('S')):
                self.save_game(); self.draw(); continue
            elif key in (ord('l'), ord('L')):
                if self.load_game(): pass
                self.draw(); continue
            elif key == ord('x'):
                self.look_mode = True
                self.cursor_x, self.cursor_y = self.player_x, self.player_y
                self.message = "查看模式：方向键移动光标(+)，显示光标处信息，其他键退出。"
                self.draw()
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
                        info += f" | {mon['name']} HP:{mon['hp']}/{mon['max_hp']}"
                    self.message = info
                    self.draw()
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
                self.draw(); continue
            elif key == ord('d'):
                self.message = "挖掘模式：按方向键选择要拆除的方块（包括尸体），其他键取消。"
                self.draw()
                key2 = self.stdscr.getch()
                if key2 in DIRECTIONS:
                    dx, dy = DIRECTIONS[key2]; self.dig_adjacent(dx, dy); acted = True
                else:
                    self.message = "取消挖掘。"
                self.draw(); continue
            elif key in DIRECTIONS:
                dx, dy = DIRECTIONS[key]; self.try_move_or_dig(dx, dy); acted = True
            if acted:
                self.advance_turn()
                self.draw()

def main(stdscr):
    game = Game(stdscr)
    if not game.load_game():
        game.new_game()
    game.run()

if __name__ == "__main__":
    curses.wrapper(main)

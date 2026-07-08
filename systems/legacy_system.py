"""跨局遗产系统：死亡积累点数，新角色兑换增益"""
from inventory import ItemCategory
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LEGACY_FILE = BASE_DIR / "data" / "legacy.json"

# 遗产商店配置
PERKS = {
    "start_with_sword": {
        "name": "石剑开局",
        "cost": 2,
        "desc": "新角色出生时携带一把石剑",
        "type": "item",
        "item_name": "石剑",
    },
    "start_with_pickaxe": {
        "name": "石镐开局",
        "cost": 2,
        "desc": "新角色出生时携带一把石镐",
        "type": "item",
        "item_name": "石镐",
    },
    "start_with_bread": {
        "name": "食物开局",
        "cost": 1,
        "desc": "新角色出生时携带5个面包",
        "type": ItemCategory.MATERIAL,
        "item_name": "面包",
        "count": 5,
    },
    "bonus_skill_digging": {
        "name": "挖掘经验",
        "cost": 3,
        "desc": "新角色初始挖掘技能+2",
        "type": "skill",
        "skill": "digging",
        "bonus": 2,
    },
    "bonus_skill_combat": {
        "name": "战斗经验",
        "cost": 3,
        "desc": "新角色初始战斗技能+2",
        "type": "skill",
        "skill": "combat",
        "bonus": 2,
    },
    "bonus_hp": {
        "name": "生命强化",
        "cost": 4,
        "desc": "新角色初始生命+20",
        "type": "hp_bonus",
        "bonus": 20,
    },
    "unlock_iron_recipes": {
        "name": "铁器时代",
        "cost": 5,
        "desc": "永久解锁所有铁制装备配方",
        "type": "recipe_unlock",
        "recipes": ["铁剑", "铁镐", "铁斧", "铁甲"],
    },
    "start_with_chest": {
        "name": "随身木箱",
        "cost": 2,
        "desc": "新角色出生时携带一个木箱",
        "type": "item",
        "item_name": "木箱",
    },
}


def load_legacy():
    """加载遗产数据，不存在则创建默认"""
    if LEGACY_FILE.exists():
        with open(LEGACY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    default = {
        "version": 1,
        "total_deaths": 0,
        "legacy_points": 0,
        "unlocked_recipes": [],
        "unlocked_perks": [],
        "highest_depth": 0,
        "total_monsters_killed": 0,
        "total_blocks_placed": 0,
        "previous_lives": [],
    }
    save_legacy(default)
    return default


def save_legacy(data):
    with open(LEGACY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def record_death(game):
    """角色死亡时调用：记录前世信息，计算遗产点数"""
    legacy = load_legacy()
    
    # 记录前世
    life_record = {
        "death_turn": game.turn,
        "death_x": game.player_x,
        "death_y": game.player_y,
        "death_z": game.player_z,
        "skills": dict(game.skills),
        "monsters_killed_this_life": getattr(game, '_monsters_killed_this_life', 0),
    }
    legacy["previous_lives"].append(life_record)
    
    # 更新统计
    legacy["total_deaths"] += 1
    legacy["highest_depth"] = max(legacy.get("highest_depth", 0), abs(game.player_z))
    legacy["total_monsters_killed"] += getattr(game, '_monsters_killed_this_life', 0)
    legacy["total_blocks_placed"] += getattr(game, '_blocks_placed_this_life', 0)
    
    # 计算遗产点数：基于本局成就
    points = 1  # 基础
    points += min(game.skills.get("digging", 0) // 3, 3)    # 挖掘每3级+1，最多3
    points += min(game.skills.get("combat", 0) // 3, 3)     # 战斗每3级+1，最多3
    if game.player_z <= -20:
        points += 2  # 深度奖励
    if getattr(game, '_monsters_killed_this_life', 0) >= 10:
        points += 2  # 狩猎奖励
    
    legacy["legacy_points"] += points
    
    # 记录解锁的配方（本局合成过的）
    if hasattr(game, '_crafted_this_life'):
        for recipe_name in game._crafted_this_life:
            if recipe_name not in legacy["unlocked_recipes"]:
                legacy["unlocked_recipes"].append(recipe_name)
    
    save_legacy(legacy)
    return points


def apply_legacy_perks(game):
    """新角色出生时应用已购买的遗产增益"""
    legacy = load_legacy()
    
    for perk_id in legacy.get("unlocked_perks", []):
        perk = PERKS.get(perk_id)
        if not perk:
            continue
        
        if perk["type"] == "item":
            game._add_equipment_instance(perk["item_name"])
        elif perk["type"] == ItemCategory.MATERIAL:
            game._add_material(perk["item_name"], perk.get("count", 1))
        elif perk["type"] == "skill":
            game.skills[perk["skill"]] = game.skills.get(perk["skill"], 0) + perk["bonus"]
        elif perk["type"] == "hp_bonus":
            game.player_hp += perk["bonus"]
            game.player_max_hp += perk["bonus"]
    
    # 应用解锁的配方
    for recipe_name in legacy.get("unlocked_recipes", []):
        if recipe_name in game.recipes:
            game.recipes[recipe_name]["unlocked"] = True


def get_legacy_points():
    return load_legacy().get("legacy_points", 0)


def get_perks_shop():
    """返回可购买的遗产增益列表"""
    legacy = load_legacy()
    points = legacy.get("legacy_points", 0)
    unlocked = set(legacy.get("unlocked_perks", []))
    
    available = []
    for perk_id, perk in PERKS.items():
        if perk_id not in unlocked:
            available.append({
                "id": perk_id,
                "name": perk["name"],
                "cost": perk["cost"],
                "desc": perk["desc"],
                "affordable": points >= perk["cost"],
                "owned": False,
            })
    
    return available


def purchase_perk(perk_id):
    """购买遗产增益"""
    legacy = load_legacy()
    perk = PERKS.get(perk_id)
    if not perk:
        return False, "未知的增益"
    if perk_id in legacy.get("unlocked_perks", []):
        return False, "已拥有"
    if legacy["legacy_points"] < perk["cost"]:
        return False, f"点数不足（需要 {perk['cost']}，当前 {legacy['legacy_points']}）"
    
    legacy["legacy_points"] -= perk["cost"]
    legacy.setdefault("unlocked_perks", []).append(perk_id)
    save_legacy(legacy)
    return True, f"解锁了【{perk['name']}】！"

from world_gen import TILE_AIR
from systems.event_bus import EventBus, EventType, GameEvent
from inventory import Inventory
import json
from pathlib import Path
from systems.save_system import build_save_data

BASE_DIR = Path(__file__).parent.parent


def drop_items_on_ground(game, x, y):
    """将背包内容掉落到地面附近。"""
    game.inventory = Inventory()
    game.equipment = {}
    game.message = f"你的物品散落在 ({x},{y}) 附近。"


def place_grave(game, x, y):
    """在死亡位置生成墓碑。"""
    tile = game.world.get_tile(x, y).get("tile", TILE_AIR)
    if tile == TILE_AIR:
        old_tile = game.world.get_tile(x, y)["tile"]
        game.world.set_tile(x, y, "墓碑")
        game.modified_tiles[(x, y)] = "墓碑"
        EventBus().emit(GameEvent(EventType.TILE_CHANGED, {"x": x, "y": y, "old": old_tile, "new": "墓碑"}), game)


def save_world_on_death(game):
    """死亡时保存世界状态。"""
    _, world_data = build_save_data(game)
    world_data["last_death_x"] = game.player_x
    world_data["last_death_y"] = game.player_y
    world_data["last_death_turn"] = game.turn
    world_data["total_deaths"] = world_data.get("total_deaths", 0) + 1
    world_path = BASE_DIR / "data" / "world_meta.json"
    with open(world_path, "w") as f:
        json.dump(world_data, f, indent=2, ensure_ascii=False)


def check_death(game):
    """检查玩家死亡，处理遗产和墓碑。"""
    if game.player_hp <= 0:
        game.buff_manager.remove_entity(game)
        drop_items_on_ground(game, game.player_x, game.player_y)
        place_grave(game, game.player_x, game.player_y)
        save_world_on_death(game)
        points = record_death(game)
        game.message = f"你死了。获得 {points} 遗产点数。世界保留。"
        return True
    return False


def show_death_screen(game):
    """显示死亡画面并打开遗产商店。"""
    import curses
    game.stdscr.erase()
    m1, m2 = "你死了。", f"物品掉落在 ({game.player_x},{game.player_y})"
    m3 = "世界保留，新角色将继承一切。"
    m4 = "按任意键打开遗产商店..."
    h, w = game.stdscr.getmaxyx()
    game.stdscr.addstr(h//2-3, max(0, w//2-len(m1)//2), m1, curses.A_BOLD | curses.color_pair(7))
    game.stdscr.addstr(h//2-1, max(0, w//2-len(m2)//2), m2)
    game.stdscr.addstr(h//2, max(0, w//2-len(m3)//2), m3)
    game.stdscr.addstr(h//2+2, max(0, w//2-len(m4)//2), m4)
    game.stdscr.refresh()
    game.stdscr.getch()
    from ui.states.legacy_state import LegacyState
    if game.engine:
        game.engine.push_state(LegacyState(game))

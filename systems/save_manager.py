"""存档管理器：新游戏、保存、加载。"""
import shutil
import json
from pathlib import Path
from world_gen import generate_world, find_spawn, SAVE_DIR
from config import WORLD_SEED, PLAYER_INITIAL_HP, SPAWN_INITIAL_COUNTDOWN
from inventory import Inventory, clear_inventory_instance
from systems.scent_map import clear_global_scent_map
from systems.save_system import build_save_data, apply_load_data, _apply_world_data
from systems.legacy_system import apply_legacy_perks
from systems.buff_system import create_buff_manager
from systems.event_bus import EventBus, EventType
from systems.room_system import check_room_formation
from data_mappings import load_recipes
import items as items_mod
import monsters as monsters_mod

BASE_DIR = Path(__file__).parent.parent
SAVE_FILE = BASE_DIR / "data" / "save.json"


def new_game(game, inherit_world=False):
    """开始新游戏，可选继承世界。"""
    clear_inventory_instance()
    clear_global_scent_map()
    if not inherit_world:
        if SAVE_DIR.exists():
            shutil.rmtree(SAVE_DIR)
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        game.world = generate_world(seed=WORLD_SEED)
    else:
        world_path = BASE_DIR / "data" / "world_meta.json"
        if SAVE_DIR.exists() and world_path.exists():
            with open(world_path) as f:
                world_data = json.load(f)
            seed = world_data.get("seed", WORLD_SEED)
            # decorate=False: 跳过洞穴/树木/特殊地貌重新雕刻，
            # 这些内容已经作为 chunk delta 存盘，靠 chunk 懒加载时 load_from_disk 自动恢复。
            # 重新雕刻不仅浪费几十秒，还会在雕刻范围内产生大量无意义的临时计算。
            game.world = generate_world(seed=seed, decorate=False)
            _apply_world_data(game, world_data)
        else:
            if SAVE_DIR.exists():
                shutil.rmtree(SAVE_DIR)
            SAVE_DIR.mkdir(parents=True, exist_ok=True)
            game.world = generate_world(seed=WORLD_SEED)

    for p in [SAVE_FILE, BASE_DIR / "data" / "player.json"]:
        if p.exists():
            p.unlink()

    sx, sy = find_spawn(game.world, start_x=0)
    game.player_x, game.player_y = sx, sy
    game.respawn_x, game.respawn_y = sx, sy
    game.player_z = 0
    game.cursor_x, game.cursor_y = sx, sy
    game.player_hp = PLAYER_INITIAL_HP
    game.player_max_hp = PLAYER_INITIAL_HP
    game.turn = 0
    game.inventory = Inventory()
    game.equipment = {}
    game.buff_manager = create_buff_manager()
    apply_legacy_perks(game)
    EventBus().subscribe(EventType.TILE_CHANGED, lambda e, g: check_room_formation(g))
    game.message = "欢迎来到新世界。" if not inherit_world else "你在这个熟悉的世界醒来..."
    game.place_mode = None
    game.last_place = None
    game.place_item_name = None
    game.last_place_item_name = None
    game.dig_progress = None
    game.look_mode = False
    game.recipes = load_recipes()
    game.items = items_mod.load_items()
    game.monster_data = monsters_mod.load_monsters()
    game.monsters = []
    game._monster_index = {}
    game.spawn_counter = {"count": SPAWN_INITIAL_COUNTDOWN}
    game.corpses = {}
    game.modified_tiles = {}
    game.chests = {}
    game.skills = {"digging": 0, "combat": 0, "defense": 0}
    game.skill_levels = {"digging": 1, "combat": 1, "defense": 1}
    game._monsters_killed_this_life = 0
    game._blocks_placed_this_life = 0
    game._crafted_this_life = []


def save_game(game):
    """保存游戏状态。M25: player.json + world_meta.json + save.json 兼容。"""
    # 把所有还在内存里、尚未被 keep_radius 自然卸载的脏 chunk 一并落盘，
    # 否则挖矿/建造等地形修改如果没走出半径就存档退出，会在下次读档时丢失。
    if game.world:
        game.world.save_all()
    player_data, world_data = build_save_data(game)
    save_data = {"player": player_data, "world": world_data}
    player_path = BASE_DIR / "data" / "player.json"
    world_path = BASE_DIR / "data" / "world_meta.json"

    try:
        SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(player_path, "w", encoding="utf-8") as f:
            json.dump(player_data, f, ensure_ascii=False, indent=2)
        with open(world_path, "w", encoding="utf-8") as f:
            json.dump(world_data, f, ensure_ascii=False, indent=2)
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        game.message = "游戏已保存。"
    except Exception as e:
        game.message = f"存档失败: {e}"


def load_game(game):
    """读取存档。M25: 优先 player.json + world_meta.json。"""
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
            game.message = f"读档失败: {e}"
            return False
    elif SAVE_FILE.exists():
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            game.message = f"读档失败: {e}"
            return False
    else:
        game.message = "没有找到存档文件。"
        return False

    seed = data.get("seed") or (data.get("world", {}).get(
        "seed") if "world" in data else WORLD_SEED)
    game.world = generate_world(seed=seed, decorate=False)
    apply_load_data(game, data)
    if hasattr(game, 'buff_manager'):
        for m in game.monsters:
            game.buff_manager.migrate_legacy(m)
    return True

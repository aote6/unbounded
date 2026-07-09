"""存档系统：构建/恢复 + 存档管理 API"""
from systems.inventory_actions import add_monster
import json, shutil
from pathlib import Path
from world_gen import SAVE_DIR
from equipment import EquipmentInstance
from inventory import Inventory
import monsters as monsters_mod
import items as items_mod

BASE_DIR = Path(__file__).parent.parent
SAVE_FILE = BASE_DIR / "data" / "save.json"
PLAYER_PATH = BASE_DIR / "data" / "player.json"
WORLD_PATH = BASE_DIR / "data" / "world_meta.json"
LEGACY_SAVE_FILE = BASE_DIR / "data" / "save.json"

CURRENT_SAVE_VERSION = 2


def _get_load_recipes():
    from data_mappings import load_recipes
    return load_recipes


def build_save_data(game):
    player_data = {
        "version": CURRENT_SAVE_VERSION,
        "player_x": game.player_x,
        "player_y": game.player_y,
        "player_z": game.player_z,
        "player_hp": game.player_hp,
        "player_max_hp": game.player_max_hp,
        "turn": game.turn,
        "equipment": game.equipment,
        "inventory": game.inventory.to_dict(),
        "skills": game.skills,
        "respawn_x": game.respawn_x,
        "respawn_y": game.respawn_y,
        "bed_x": game.bed_x,
        "bed_y": game.bed_y,
    }
    world_data = {
        "monsters": [_serialize_monster(m) for m in game.monsters],
        "corpses": {f"{x},{y}": v for (x, y), v in game.corpses.items()},
        "chests": _serialize_chests(game.chests),
        "spawn_counter": game.spawn_counter,
        "seed": game.world.seed if hasattr(game.world, 'seed') else None,
    }
    return player_data, world_data


def _serialize_monster(m):
    return {
        "name": m["name"], "hp": m["hp"], "max_hp": m["max_hp"],
        "x": m["x"], "y": m["y"], "faction": m.get("faction", "hostile"),
        "tags": m.get("tags", []),
    }


def _serialize_chests(chests):
    result = {}
    for (cx, cy), data in chests.items():
        key = f"{cx},{cy}"
        result[key] = {
            "materials": data.get("materials", {}),
            "equipment_instances": [
                inst.to_dict() if hasattr(inst, 'to_dict') else inst
                for inst in data.get("equipment_instances", [])
            ],
        }
    return result


def apply_load_data(game, data):
    save_version = data.get("player", {}).get("version", data.get("version", 1))
    if save_version < CURRENT_SAVE_VERSION:
        game.message = f"旧版本存档(v{save_version})已自动升级到v{CURRENT_SAVE_VERSION}"
    if "player" in data:
        _apply_player_data(game, data["player"])
        _apply_world_data(game, data["world"])
    else:
        _apply_player_data(game, data)
        _apply_world_data(game, data)
    game.message = f"读档成功。位置 ({game.player_x},{game.player_y})。"


def _apply_player_data(game, data):
    game.player_x = data.get("player_x", 0)
    game.player_y = data.get("player_y", 0)
    game.player_z = data.get("player_z", 0)
    game.player_hp = data.get("player_hp", game.player_max_hp)
    game.player_max_hp = data.get("player_max_hp", game.player_max_hp)
    game.turn = data.get("turn", 0)
    game.equipment = data.get("equipment", {})
    game.skills = data.get("skills", {"digging": 0, "combat": 0, "defense": 0})
    game.respawn_x = data.get("respawn_x", 0)
    game.respawn_y = data.get("respawn_y", 0)
    game.bed_x = data.get("bed_x")
    game.bed_y = data.get("bed_y")
    inv_data = data.get("inventory", {})
    game.inventory = Inventory.from_dict(inv_data) if inv_data else Inventory()


def _apply_world_data(game, data):
    game.monsters = []
    game._monster_index = {}
    for md in data.get("monsters", []):
        m = monsters_mod.make_monster(md["name"], md["x"], md["y"], game.monster_data)
        if m:
            m["hp"] = md.get("hp", m["max_hp"])
            add_monster(game, m)
    game.corpses = {}
    for key_str, val in data.get("corpses", {}).items():
        parts = key_str.split(",")
        if len(parts) == 2:
            game.corpses[(int(parts[0]), int(parts[1]))] = val
    game.chests = {}
    chests_data = data.get("chests", {})
    if isinstance(chests_data, dict):
        for key_str, cdata in chests_data.items():
            parts = key_str.split(",")
            if len(parts) == 2:
                cx, cy = int(parts[0]), int(parts[1])
                game.chests[(cx, cy)] = {
                    "materials": cdata.get("materials", {}),
                    "equipment_instances": [
                        EquipmentInstance.from_dict(ei) if isinstance(ei, dict) else ei
                        for ei in cdata.get("equipment_instances", [])
                    ],
                }
    game.spawn_counter = data.get("spawn_counter", {"count": 5})
    game.modified_tiles = {}



# ═══════════════════════════════════
# 存档状态检查（供主菜单使用）
# ═══════════════════════════════════

def check_save_status():
    """返回存档状态: 'full' / 'world_only' / 'none'"""
    import shutil
    from pathlib import Path
    from world_gen import SAVE_DIR
    BASE_DIR = Path(__file__).parent.parent
    PLAYER_PATH = BASE_DIR / "data" / "player.json"
    WORLD_PATH = BASE_DIR / "data" / "world_meta.json"
    LEGACY_SAVE_FILE = BASE_DIR / "data" / "save.json"

    if PLAYER_PATH.exists() or LEGACY_SAVE_FILE.exists():
        return 'full'
    if WORLD_PATH.exists():
        return 'world_only'
    return 'none'


def clear_all_saves():
    """清空所有存档"""
    import shutil
    from pathlib import Path
    from world_gen import SAVE_DIR
    BASE_DIR = Path(__file__).parent.parent
    LEGACY_SAVE_FILE = BASE_DIR / "data" / "save.json"
    PLAYER_PATH = BASE_DIR / "data" / "player.json"
    WORLD_PATH = BASE_DIR / "data" / "world_meta.json"

    for p in [LEGACY_SAVE_FILE, PLAYER_PATH, WORLD_PATH]:
        if p.exists():
            p.unlink()
    if SAVE_DIR.exists():
        shutil.rmtree(SAVE_DIR)

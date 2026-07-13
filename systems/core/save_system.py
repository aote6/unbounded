"""存档系统：构建/恢复 + 存档管理 API"""
from systems.entity.monster_index import add_monster
from pathlib import Path
from equipment import EquipmentInstance
from inventory import Inventory
import monsters as monsters_mod

BASE_DIR = Path(__file__).parent.parent
SAVE_FILE = BASE_DIR / "data" / "save.json"
PLAYER_PATH = BASE_DIR / "data" / "player.json"
WORLD_PATH = BASE_DIR / "data" / "world_meta.json"
LEGACY_SAVE_FILE = BASE_DIR / "data" / "save.json"

CURRENT_SAVE_VERSION = 2


def _get_load_recipes():
    """Lazily import and return the recipe-loading function.

    Returns:
        Callable: The `load_recipes` function from `data_mappings`.
    """
    from data_mappings import load_recipes
    return load_recipes


def build_save_data(game):
    """Build serializable player and world data dicts from the current game state.

    Args:
        game: The current game state object.

    Returns:
        tuple: A (player_data, world_data) pair of dicts ready for JSON
        serialization.
    """
    player_data = {
        "version": CURRENT_SAVE_VERSION,
        "player_x": game.player_x,
        "player_y": game.player_y,
        "player_z": game.player_z,
        "player_hp": game.player_hp,
        "player_max_hp": game.player_max_hp,
        "turn": game.turn,
        "equipment": _serialize_equipment(game.equipment),
        "inventory": game.inventory.to_dict(),
        "skills": game.skills,
        "respawn_x": game.respawn_x,
        "respawn_y": game.respawn_y,
        "bed_x": game.bed_x,
        "bed_y": game.bed_y,
    }
    world_data = {
        "version": CURRENT_SAVE_VERSION,
        "monsters": [_serialize_monster(m) for m in game.monsters],
        "corpses": {f"{x},{y}": v for (x, y), v in game.corpses.items()},
        "chests": _serialize_chests(game.chests),
        "spawn_counter": game.spawn_counter,
        "seed": game.world.seed if hasattr(game.world, 'seed') else None,
        "found_specials": [list(p) for p in getattr(game, '_found_specials', set())],
    }
    return player_data, world_data


def _serialize_equipment(equipment):
    """把 equipment 字典里的 EquipmentInstance 对象转换成可 JSON 序列化的 dict。"""
    result = {}
    for slot_id, inst in equipment.items():
        if inst is None:
            result[slot_id] = None
        elif hasattr(inst, "to_dict"):
            result[slot_id] = inst.to_dict()
        else:
            result[slot_id] = inst  # 兼容旧存档里可能存的纯字符串
    return result


def _deserialize_equipment(data):
    """把存档里的 equipment dict 还原成 EquipmentInstance 对象。"""
    from equipment import EquipmentInstance
    result = {}
    for slot_id, val in data.items():
        if val is None:
            result[slot_id] = None
        elif isinstance(val, dict):
            result[slot_id] = EquipmentInstance.from_dict(val)
        else:
            result[slot_id] = val  # 兼容旧存档里可能存的纯字符串
    return result


def _serialize_monster(m):
    """Serialize a monster into a minimal JSON-compatible dict.

    Args:
        m: The monster dict/entity to serialize.

    Returns:
        dict: A dict containing the monster's name, HP, position,
        faction, and tags.
    """
    return {
        "name": m["name"], "hp": m["hp"], "max_hp": m["max_hp"],
        "x": m["x"], "y": m["y"], "faction": m.get("faction", "hostile"),
        "tags": m.get("tags", []),
    }


def _serialize_chests(chests):
    """Serialize the chests mapping into a JSON-compatible dict.

    Args:
        chests: Mapping of (x, y) position tuples to chest data dicts.

    Returns:
        dict: A dict keyed by "x,y" strings, each mapping to a dict
        with the chest's materials and serialized equipment instances.
    """
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


def _detect_save_version(data):
    """探测存档数据的版本号。

    v1 存档是早期的扁平格式（所有字段直接平铺在根节点，没有
    "player"/"world" 分组），当时没有显式的 version 字段，
    因此探测到扁平格式即视为 v1。v2 起存档拆分为
    {"player": {...}, "world": {...}} 两个子节点，且各自带有
    "version" 字段。

    Args:
        data: 从磁盘读入的原始存档 dict。

    Returns:
        int: 探测到的存档版本号。
    """
    if "player" in data:
        return data["player"].get("version", data.get("version", 1))
    return data.get("version", 1)


def _migrate_v1_to_v2(data):
    """把 v1 扁平格式存档迁移为 v2 的 {"player","world"} 分组格式。

    v1 存档所有字段（player_x、monsters、chests……）平铺在同一
    个 dict 里，没有 player/world 分组。v2 起 save_manager 把
    存档拆成 player.json + world_meta.json 两个文件，读取时统一
    包装成 {"player": ..., "world": ...} 结构。此函数只做结构
    包装，不改变任何字段的语义或数值。

    Args:
        data: v1 格式的扁平存档 dict。

    Returns:
        dict: 迁移后的 v2 格式 {"player": data, "world": data}。
        v1 存档里 player 和 world 字段本就混在一起，两侧共用
        同一份 data 是安全的，因为 _apply_player_data /
        _apply_world_data 各自只读取自己关心的 key，互不干扰。
    """
    return {"player": data, "world": data}


# 版本迁移链：key 是"迁移前"版本号，value 是对应的迁移函数。
# 以后升到 v3，只需要新增一个 _migrate_v2_to_v3 函数并在此注册，
# migrate_save_data 会自动串联执行，不需要改动 apply_load_data。
_MIGRATIONS = {
    1: _migrate_v1_to_v2,
}


def migrate_save_data(data):
    """将任意旧版本存档逐步迁移到 CURRENT_SAVE_VERSION。

    依次应用 _MIGRATIONS 中登记的迁移函数，直到版本号达到
    CURRENT_SAVE_VERSION 或没有更多迁移步骤可用为止。

    Args:
        data: 从磁盘读入的原始存档 dict，可能是任意历史版本。

    Returns:
        tuple: (迁移后的 data dict, 原始版本号, 是否发生了迁移)。
    """
    original_version = _detect_save_version(data)
    version = original_version
    migrated = False
    while version < CURRENT_SAVE_VERSION and version in _MIGRATIONS:
        data = _MIGRATIONS[version](data)
        migrated = True
        version += 1
    return data, original_version, migrated


def apply_load_data(game, data):
    """Apply loaded save data to the current game state.

    先探测存档版本并按需迁移到当前版本，再把 player/world 数据
    应用到 game 对象上。

    Args:
        game: The current game state object to populate.
        data: The loaded save data dict.
    """
    data, original_version, migrated = migrate_save_data(data)
    if migrated:
        game.message = f"旧版本存档(v{original_version})已自动升级到v{CURRENT_SAVE_VERSION}"
    _apply_player_data(game, data["player"])
    _apply_world_data(game, data["world"])
    if not migrated:
        game.message = f"读档成功。位置 ({game.player_x},{game.player_y})。"


def _apply_player_data(game, data):
    """Apply loaded player-related fields onto the game state.

    Args:
        game: The current game state object to populate.
        data: The loaded player data dict.
    """
    game.player_x = data.get("player_x", 0)
    game.player_y = data.get("player_y", 0)
    game.player_z = data.get("player_z", 0)
    game.player_hp = data.get("player_hp", game.player_max_hp)
    game.player_max_hp = data.get("player_max_hp", game.player_max_hp)
    game.turn = data.get("turn", 0)
    game.equipment = _deserialize_equipment(data.get("equipment", {}))
    game.skills = data.get("skills", {"digging": 0, "combat": 0, "defense": 0})
    game.respawn_x = data.get("respawn_x", 0)
    game.respawn_y = data.get("respawn_y", 0)
    game.bed_x = data.get("bed_x")
    game.bed_y = data.get("bed_y")
    inv_data = data.get("inventory", {})
    game.inventory = Inventory.from_dict(inv_data) if inv_data else Inventory()


def _apply_world_data(game, data):
    """Apply loaded world-related fields onto the game state.

    Restores monsters, corpses, chests, spawn counter, and discovered
    special locations from the loaded data.

    Args:
        game: The current game state object to populate.
        data: The loaded world data dict.
    """
    game.monsters = []
    game._monster_index = {}
    for md in data.get("monsters", []):
        m = monsters_mod.make_monster(
            md["name"], md["x"], md["y"], game.monster_data)
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
    _found_raw = data.get("found_specials", [])
    game._found_specials = {
        tuple(item) if isinstance(item, list) and len(item) == 2 else item
        for item in _found_raw
    }


# ═══════════════════════════════════
# 存档状态检查（供主菜单使用）
# ═══════════════════════════════════

def check_save_status():
    """返回存档状态: 'full' / 'world_only' / 'none'"""
    from pathlib import Path
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

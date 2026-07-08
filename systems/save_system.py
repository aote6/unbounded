"""存档系统：构建存档数据 / 应用读档数据。

M25: 拆分为 player_data + world_data，支持新格式（player.json + world_meta.json）
     和旧格式（save.json）两种读写方式，向后兼容。
"""
from config import WORLD_SEED
from inventory import Inventory
from equipment import EquipmentInstance
import monsters as monsters_mod
import items as items_mod


def _get_load_recipes():
    from main import load_recipes
    return load_recipes


# ═══════════════════════════════════════════════
# 序列化
# ═══════════════════════════════════════════════

def build_save_data(game):
    """返回 (player_data, world_data) 两个 dict。"""
    game.world.save_all()
    
    player_data = {
        "player_x": game.player_x,
        "player_y": game.player_y,
        "player_z": game.player_z,
        "player_hp": game.player_hp,
        "player_max_hp": game.player_max_hp,
        "turn": game.turn,
        "equipment": game.equipment,
        "inventory": game.inventory.to_dict(),
        "skills": game.skills,
        "skill_levels": game.skill_levels,
        "respawn_x": game.respawn_x,
        "respawn_y": game.respawn_y,
        "bed_x": game.bed_x,
        "bed_y": game.bed_y,
    }
    
    world_data = {
        "seed": WORLD_SEED,
        "monsters": [_serialize_monster(m) for m in game.monsters],
        "corpses": {f"{x},{y}": v for (x, y), v in game.corpses.items()},
        "chests": _serialize_chests(game.chests),
        "spawn_counter": game.spawn_counter,
    }
    
    return player_data, world_data


def _serialize_monster(m):
    return {
        "name": m["name"],
        "hp": m["hp"],
        "max_hp": m["max_hp"],
        "x": m["x"],
        "y": m["y"],
        "faction": m.get("faction", "hostile"),
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


# ═══════════════════════════════════════════════
# 反序列化
# ═══════════════════════════════════════════════

def apply_load_data(game, data):
    """恢复存档。兼容新格式 {"player":..., "world":...} 和旧格式（扁平 dict）。"""
    if "player" in data:
        _apply_player_data(game, data["player"])
        _apply_world_data(game, data["world"])
    else:
        # 旧格式兼容
        _apply_player_data(game, data)
        _apply_world_data(game, data)
    
    game.cursor_x, game.cursor_y = game.player_x, game.player_y
    game.place_mode = None
    game.last_place = None
    game.place_item_name = None
    game.last_place_item_name = None
    game.dig_progress = None
    game.look_mode = False
    game.modified_tiles = {}
    game.recipes = _get_load_recipes()()
    game.items = items_mod.load_items()
    game.monster_data = monsters_mod.load_monsters()
    
    inv_summary = (
        ", ".join(f"{k}:{v}" for k, v in game.inventory.get_materials().items()) or "空"
    )
    game.message = f"读档成功。位置 ({game.player_x},{game.player_y})。背包: {inv_summary}"


def _apply_player_data(game, data):
    game.player_x = data.get("player_x", 0)
    game.player_y = data.get("player_y", 0)
    game.player_z = data.get("player_z", 0)
    game.player_hp = data.get("player_hp", game.player_max_hp)
    game.player_max_hp = data.get("player_max_hp", game.player_max_hp)
    game.turn = data.get("turn", 0)
    game.equipment = data.get("equipment", {})
    game.skills = data.get("skills", {"digging": 0, "combat": 0, "defense": 0})
    game.skill_levels = data.get("skill_levels", {"digging": 1, "combat": 1, "defense": 1})
    game.respawn_x = data.get("respawn_x", 0)
    game.respawn_y = data.get("respawn_y", 0)
    game.bed_x = data.get("bed_x")
    game.bed_y = data.get("bed_y")
    
    inv_data = data.get("inventory", {})
    game.inventory = Inventory.from_dict(inv_data) if inv_data else Inventory()


def _apply_world_data(game, data):
    # 怪物
    game.monsters = []
    game._monster_index = {}
    for md in data.get("monsters", []):
        template = game.monster_data.get(md["name"], {})
        m = {
            "name": md["name"],
            "char": template.get("char", "?"),
            "x": md["x"],
            "y": md["y"],
            "hp": md.get("hp", template.get("hp", 10)),
            "max_hp": md.get("max_hp", template.get("hp", 10)),
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
            "tags": template.get("tags", []),
            "faction": template.get("faction", "hostile"),
        }
        game._add_monster(m)
    
    # 尸体
    game.corpses = {}
    for key_str, val in data.get("corpses", {}).items():
        parts = key_str.split(",")
        if len(parts) == 2:
            game.corpses[(int(parts[0]), int(parts[1]))] = val
    
    # 箱子
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

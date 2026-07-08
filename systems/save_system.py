"""存档系统：构建存档数据 / 应用读档数据。"""
from config import WORLD_SEED
from inventory import Inventory
from equipment import EquipmentInstance
import monsters as monsters_mod
import items as items_mod

# 从 main 导入 load_recipes（避免循环导入，在函数内部延迟导入）
def _get_load_recipes():
    from main import load_recipes
    return load_recipes


def build_save_data(game):
    """从 Game 对象构建可序列化的存档字典。"""
    game.world.save_all()
    return {
        "seed": WORLD_SEED,
        "player_x": game.player_x,
        "player_y": game.player_y,
        "player_z": game.player_z,
        "player_hp": game.player_hp,
        "player_max_hp": game.player_max_hp,
        "turn": game.turn,
        "inventory": game.inventory.to_dict(),
        "equipment": game.equipment,
        "skills": game.skills,
        "skill_levels": game.skill_levels,
        "spawn_counter": game.spawn_counter,
        "corpses": {f"{x},{y}": v for (x, y), v in game.corpses.items()},
        "monsters": [
            {
                "name": m["name"],
                "x": m["x"],
                "y": m["y"],
                "hp": m["hp"],
                "max_hp": m["max_hp"],
            }
            for m in game.monsters
        ],
        "chests": {
            f"{x},{y}": {
                "materials": c["materials"],
                "equipment_instances": [
                    inst.to_dict() for inst in c["equipment_instances"]
                ],
            }
            for (x, y), c in game.chests.items()
        },
    }


def apply_load_data(game, data):
    """将存档字典恢复到 Game 对象。"""
    game.player_x = data["player_x"]
    game.player_y = data["player_y"]
    game.player_z = data.get("player_z", 0)
    game.cursor_x, game.cursor_y = game.player_x, game.player_y
    game.player_hp = data["player_hp"]
    game.player_max_hp = data["player_max_hp"]
    game.turn = data["turn"]
    game.inventory = Inventory.from_dict(data.get("inventory", {}))
    game.equipment = data.get("equipment", {})
    game.skills = data.get("skills", {"digging": 0, "combat": 0, "defense": 0})
    game.skill_levels = data.get(
        "skill_levels", {"digging": 1, "combat": 1, "defense": 1}
    )
    game.spawn_counter = data.get("spawn_counter", {})

    # 尸体
    game.corpses = {}
    for key, val in data.get("corpses", {}).items():
        x_str, y_str = key.split(",")
        game.corpses[(int(x_str), int(y_str))] = val

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
            "hp": md["hp"],
            "max_hp": md["max_hp"],
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
        game.monsters.append(m)

    # 箱子
    game.chests = {}
    for key, cdata in data.get("chests", {}).items():
        x_str, y_str = key.split(",")
        game.chests[(int(x_str), int(y_str))] = {
            "materials": cdata.get("materials", {}),
            "equipment_instances": [
                EquipmentInstance.from_dict(d) if isinstance(d, dict) else d
                for d in cdata.get("equipment_instances", [])
            ],
        }

    game._build_monster_index()
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

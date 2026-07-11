# -*- coding: utf-8 -*-
"""P0/P1 修复脚本：save_manager/world_gen/entity/inventory_actions/event_bus"""

def patch_file(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        if old not in content:
            print(f"[跳过] {path}: 未找到匹配片段，可能已经改过或代码有出入，请手动检查")
            continue
        if content.count(old) > 1:
            print(f"[警告] {path}: 匹配片段出现多次，只替换第一处")
        content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[完成] {path}")


# ══════════════════ systems/save_manager.py ══════════════════
save_manager_replacements = [
    (
'''"""存档管理器：新游戏、保存、加载。"""
import shutil
import json
from pathlib import Path
from world_gen import generate_world, find_spawn, SAVE_DIR
from config import WORLD_SEED, PLAYER_INITIAL_HP, SPAWN_INITIAL_COUNTDOWN
from inventory import Inventory, clear_inventory_instance
from systems.world.scent_map import clear_global_scent_map
from systems.core.save_system import build_save_data, apply_load_data, _apply_world_data
from systems.gameplay.legacy_system import apply_legacy_perks
from systems.entity.buff_system import create_buff_manager
from systems.core.event_bus import EventBus, EventType
from systems.world.room_system import check_room_formation
from data_mappings import load_recipes
import items as items_mod
import monsters as monsters_mod

BASE_DIR = Path(__file__).parent.parent
SAVE_FILE = BASE_DIR / "data" / "save.json"''',
'''"""存档管理器：新游戏、保存、加载。"""
import shutil
import json
import os
import logging
from pathlib import Path
from world_gen import generate_world, find_spawn, SAVE_DIR
from config import WORLD_SEED, PLAYER_INITIAL_HP, SPAWN_INITIAL_COUNTDOWN
from inventory import Inventory, clear_inventory_instance
from systems.world.scent_map import clear_global_scent_map
from systems.core.save_system import build_save_data, apply_load_data, _apply_world_data
from systems.gameplay.legacy_system import apply_legacy_perks
from systems.entity.buff_system import create_buff_manager
from systems.core.event_bus import EventBus, EventType
from systems.world.room_system import check_room_formation
from data_mappings import load_recipes
import items as items_mod
import monsters as monsters_mod

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent.parent
SAVE_FILE = BASE_DIR / "data" / "save.json"


def _write_json_atomic(path: Path, data):
    """原子写入 + 自动备份：先写 .tmp 再 os.replace，写入前旧文件轮换成 .bak。"""
    tmp_path = path.with_name(path.name + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    if path.exists():
        bak_path = path.with_name(path.name + ".bak")
        try:
            os.replace(path, bak_path)
        except OSError as e:
            logger.warning(f"旧存档备份失败（不影响本次写入）: {path}: {e}")
    os.replace(tmp_path, path)'''
    ),
    (
'''    try:
        SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(player_path, "w", encoding="utf-8") as f:
            json.dump(player_data, f, ensure_ascii=False, indent=2)
        with open(world_path, "w", encoding="utf-8") as f:
            json.dump(world_data, f, ensure_ascii=False, indent=2)
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)
        game.message = "游戏已保存。"
    except Exception as e:
        game.message = f"存档失败: {e}"''',
'''    try:
        SAVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(player_path, player_data)
        _write_json_atomic(world_path, world_data)
        _write_json_atomic(SAVE_FILE, save_data)
        game.message = "游戏已保存。"
    except Exception as e:
        logger.error(f"存档写入失败: {e}", exc_info=True)
        game.message = f"⚠ 存档失败: {e}（旧存档应仍完好，见 unbounded_debug.log）"'''
    ),
    (
'''    game.recipes = load_recipes()
    game.items = items_mod.load_items()
    game.monster_data = monsters_mod.load_monsters()
    game.monsters = []''',
'''    # recipes/items/monster_data 不在这里重新加载 —— Game.__init__ 时
    # 已经通过 StaticDataRegistry 单例加载过，静态配置不会因新游戏而变化。
    game.monsters = []'''
    ),
    (
'''        except Exception as e:
            game.message = f"读档失败: {e}"
            return False
    elif SAVE_FILE.exists():''',
'''        except Exception as e:
            logger.error(f"读档失败(player/world_meta): {e}", exc_info=True)
            game.message = f"读档失败: {e}"
            return False
    elif SAVE_FILE.exists():'''
    ),
    (
'''            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            game.message = f"读档失败: {e}"
            return False
    else:''',
'''            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"读档失败(save.json): {e}", exc_info=True)
            game.message = f"读档失败: {e}"
            return False
    else:'''
    ),
]

# ══════════════════ world_gen.py ══════════════════
world_gen_replacements = [
    (
'''from systems.world.noise_engine import (
    perlin_2d,
    generate_tile,
    clear_perlin_cache)
import json
from pathlib import Path''',
'''from systems.world.noise_engine import (
    perlin_2d,
    generate_tile,
    clear_perlin_cache)
import json
import logging
import random
from pathlib import Path

logger = logging.getLogger(__name__)'''
    ),
    (
'''        except Exception as e:
            print(f"[Chunk] 保存失败 {self.cx},{self.cy}: {e}")''',
'''        except Exception as e:
            logger.error(f"Chunk 保存失败 ({self.cx},{self.cy}): {e}", exc_info=True)'''
    ),
    (
'''        except Exception as e:
            print(f"[Chunk] 加载失败 {self.cx},{self.cy}: {e}")
            return False''',
'''        except Exception as e:
            logger.error(f"Chunk 加载失败 ({self.cx},{self.cy}): {e}", exc_info=True)
            return False'''
    ),
    (
'''    # 最终保底：返回原点并强制设为空气
    world.set_tile(0, 0, TILE_AIR)
    world.set_tile(0, 1, TILE_DIRT)

    """在每层挖出横向洞穴通道，确保有行走空间"""
    import random
    rng = random.Random(world.seed + 9999)

    # 额外：在出生点附近清理一片空地
    for x in range(-10, 10):
        for y in range(-2, 3):
            world.set_tile(x, y, TILE_AIR)
    world.set_tile(0, 1, TILE_DIRT)  # 确保脚下有东西

    for depth_band in [(-15, -3), (-35, -15), (-55, -35)]:
        for _ in range(rng.randint(3, 5)):
            x = rng.randint(-200, 200)
            y = rng.randint(depth_band[0], depth_band[1])
            length = rng.randint(100, 250)
            height = rng.randint(3, 5)

            for step in range(length):
                # 挖出横向通道
                for dy in range(-height // 2, height // 2 + 1):
                    try:
                        tile = world.get_tile(x, y + dy)["tile"]
                        if tile in (
                                TILE_STONE,
                                TILE_DIRT,
                                TILE_COAL,
                                TILE_COPPER,
                                TILE_IRON,
                                TILE_SILVER,
                                TILE_GOLD,
                                TILE_LIMESTONE,
                                TILE_MARBLE,
                                TILE_GRANITE,
                                TILE_CLAY,
                                TILE_SAND):
                            world.set_tile(x, y + dy, TILE_AIR)
                    except BaseException:
                        pass

                # 随机游走，偏向水平
                x += rng.choice([-1, 0, 1, 1, 1])
                y += rng.choice([-1, 0, 0, 0, 0, 1])''',
'''    # 最终保底：80格范围内全是水域等极端情况才会走到这里。
    # 原代码这里设完保底 tile 后没有 return，继续跑一段重复清地逻辑
    # 加一段旧版废弃隧道挖掘代码，跑完落到函数末尾隐式返回 None ——
    # 调用方 `sx, sy = find_spawn(...)` 解包 None 直接崩溃。
    logger.warning(
        f"find_spawn: 在 start_x={start_x} 附近 80 格范围内未找到合适出生点，"
        f"使用保底原点 (0, 0)"
    )
    _clear_spawn_area(world)
    return 0, 0'''
    ),
    (
'''def _scatter_trees(world):
    """在地表随机撒树，确保有足够的树可砍"""
    import random
    rng = random.Random(world.seed + 8888)''',
'''def _scatter_trees(world):
    """在地表随机撒树，确保有足够的树可砍。
    注：generate_world() 目前没有调用这个函数（Feature Engine 的
    tree_feature 已在地形生成阶段统一撒树），这是孤立的死函数，
    是否启用/删除需要你自己决定，这里只做 import 提到顶层的清理。"""
    rng = random.Random(world.seed + 8888)'''
    ),
    (
'''def _place_special_locations(world):
    """在地图里埋藏特殊地貌，给玩家探索的惊喜"""
    import random
    rng = random.Random(world.seed + 4444)''',
'''def _place_special_locations(world):
    """在地图里埋藏特殊地貌，给玩家探索的惊喜"""
    rng = random.Random(world.seed + 4444)'''
    ),
]

# ══════════════════ systems/entity.py ══════════════════
entity_replacements = [
    (
'''    def __getattr__(self, key):
        if hasattr(self._entity, key):
            return getattr(self._entity, key)
        raise AttributeError(key)''',
'''    def __getattr__(self, key):
        if hasattr(self._entity, key):
            return getattr(self._entity, key)
        # 修复读写不对称：__setattr__ 对 _entity 没有的 key 会写进 dict，
        # 但这里原来查不到 _entity 就直接报错，导致 monster.xxx=v 能写、
        # monster.xxx 却读不出来（只能用 monster['xxx']）。
        if key in self:
            return self[key]
        raise AttributeError(key)'''
    ),
]

# ══════════════════ systems/inventory_actions.py ══════════════════
inventory_actions_replacements = [
    (
'''"""物品与怪物操作函数。所有函数接收 game 作为第一参数，不依赖 Game 类。"""
from equipment import EquipmentInstance
from inventory import ItemCategory''',
'''"""物品与怪物操作函数。所有函数接收 game 作为第一参数，不依赖 Game 类。"""
from equipment import EquipmentInstance
from inventory import ItemCategory

# 怪物空间索引的写操作，跟 monster_index.py 曾是两份逐字符相同的重复代码。
# monster_index.py 同时持有读操作（monster_at/monster_has_position），
# 读写应在同一处维护，这里改为直接导入。
from systems.entity.monster_index import (
    build_monster_index,
    monster_moved,
    add_monster,
    remove_monster,
)'''
    ),
    (
'''# ═══════════════════════════════════
# 怪物空间索引
# ═══════════════════════════════════

def build_monster_index(game):
    """全量重建空间索引（仅在读档/新游戏时调用）。"""
    game._monster_index = {(m["x"], m["y"]): m for m in game.monsters}


def monster_moved(game, monster, old_x, old_y):
    """怪物移动后更新索引。"""
    game._monster_index.pop((old_x, old_y), None)
    game._monster_index[(monster["x"], monster["y"])] = monster


def add_monster(game, monster):
    """添加怪物并更新索引。"""
    game.monsters.append(monster)
    game._monster_index[(monster["x"], monster["y"])] = monster


def remove_monster(game, monster):
    """移除怪物并更新索引。"""
    if monster in game.monsters:
        game.monsters.remove(monster)
    game._monster_index.pop((monster["x"], monster["y"]), None)''',
'''# ═══════════════════════════════════
# 怪物空间索引：已从文件顶部导入 systems.monster_index，不再重复定义。
# ═══════════════════════════════════'''
    ),
]

# ══════════════════ systems/event_bus.py ══════════════════
event_bus_replacements = [
    (
'''"""轻量事件总线：发布-订阅模式，解耦游戏逻辑。"""
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum, auto''',
'''"""轻量事件总线：发布-订阅模式，解耦游戏逻辑。"""
import logging
from dataclasses import dataclass, field
from typing import Callable
from enum import Enum, auto

logger = logging.getLogger(__name__)'''
    ),
    (
'''    def emit(self, event: GameEvent, game):
        """广播事件给所有注册的处理器。"""
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            handler(event, game)
            if event.handled:
                break  # 如果事件被标记为已处理，停止传播''',
'''    def emit(self, event: GameEvent, game):
        """广播事件给所有注册的处理器。"""
        handlers = self._handlers.get(event.type, [])
        if not handlers:
            logger.debug(f"事件 {event.type.name} 无订阅者，已丢弃: {event.data}")
            return
        for handler in handlers:
            handler(event, game)
            if event.handled:
                break  # 如果事件被标记为已处理，停止传播'''
    ),
]

if __name__ == "__main__":
    patch_file("systems/save_manager.py", save_manager_replacements)
    patch_file("world_gen.py", world_gen_replacements)
    patch_file("systems/entity.py", entity_replacements)
    patch_file("systems/inventory_actions.py", inventory_actions_replacements)
    patch_file("systems/event_bus.py", event_bus_replacements)
    print("\n全部完成。建议逐个校验语法")

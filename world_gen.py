""" world_gen.py 无限世界生成模块。基于绝对坐标的懒加载 chunk 系统。
每个 Chunk 管理自身生命周期，支持脏标记与差分持久化。"""

# 噪声函数已迁移至 systems/noise_engine.py
from systems.noise_engine import (_hash2d, _hash_uniform, _smooth_noise,
    _interpolated_noise, perlin_2d, generate_tile, clear_perlin_cache)
import json
from pathlib import Path

CHUNK_SIZE = 16
SAVE_DIR = Path(__file__).parent / "data" / "chunks"

TILE_AIR = 0
TILE_DIRT = 1
TILE_STONE = 2
TILE_COAL = 3
TILE_COPPER = 4
TILE_IRON = 5
TILE_SILVER = 6
TILE_GOLD = 7
TILE_DIAMOND = 8
TILE_SULFUR = 9
TILE_SALT = 10
TILE_CLAY = 11
TILE_SAND = 12
TILE_LIMESTONE = 13
TILE_MARBLE = 14
TILE_GRANITE = 15
TILE_OBSIDIAN = 16
TILE_STAIRS_DOWN = 17
TILE_STAIRS_UP = 18
TILE_WATER = 19
TILE_TREE = 20

TILE_DROPS = {
    TILE_DIRT: "泥土", TILE_STONE: "石头",
    TILE_COAL: "煤矿", TILE_COPPER: "铜矿石", TILE_IRON: "铁矿石",
    TILE_SILVER: "银矿石", TILE_GOLD: "金矿石", TILE_DIAMOND: "钻石原石",
    TILE_SULFUR: "硫磺", TILE_SALT: "盐矿石", TILE_CLAY: "黏土",
    TILE_SAND: "沙子", TILE_LIMESTONE: "石灰岩", TILE_MARBLE: "大理石",
    TILE_GRANITE: "花岗岩", TILE_OBSIDIAN: "黑曜石",
    TILE_STAIRS_DOWN: "楼梯下", TILE_STAIRS_UP: "楼梯上",
    TILE_WATER: "水域", TILE_TREE: "树木",
}


# ═══════════════════════════════════════
# Perlin 噪声生成（纯函数，无状态）
# ═══════════════════════════════════════

class Chunk:
    """16×16 区块。管理自身地形数据与脏状态。"""
    __slots__ = ('cx', 'cy', 'tiles', 'is_dirty', '_seed')

    def __init__(self, cx: int, cy: int, seed: int):
        self.cx = cx
        self.cy = cy
        self._seed = seed
        self.tiles = self._generate_tiles()
        self.is_dirty = False

    def _generate_tiles(self):
        """根据世界种子生成 16×16 的地形数据。"""
        start_x = self.cx * CHUNK_SIZE
        start_y = self.cy * CHUNK_SIZE
        rows = []
        for dy in range(CHUNK_SIZE):
            row = []
            for dx in range(CHUNK_SIZE):
                row.append(generate_tile(start_x + dx, start_y + dy, self._seed))
            rows.append(row)
        return rows

    def get_tile(self, local_x: int, local_y: int) -> int:
        """读取本地坐标的 tile ID。"""
        return self.tiles[local_y][local_x]

    def set_tile(self, local_x: int, local_y: int, tile_id: int):
        """写入本地坐标的 tile ID，并标记脏数据。"""
        self.tiles[local_y][local_x] = tile_id
        self.is_dirty = True

    def apply_delta(self, delta: dict):
        """读档时批量应用玩家的修改记录。"""
        for key, tile_id in delta.items():
            lx_str, ly_str = key.split(",")
            lx, ly = int(lx_str), int(ly_str)
            self.tiles[ly][lx] = tile_id
        self.is_dirty = True

    def get_delta(self) -> dict:
        """返回该 chunk 中所有被修改过的格子（用于存档）。
        对比当前 tile 与生成时的 tile，只存差异。"""
        start_x = self.cx * CHUNK_SIZE
        start_y = self.cy * CHUNK_SIZE
        delta = {}
        for ly in range(CHUNK_SIZE):
            for lx in range(CHUNK_SIZE):
                current = self.tiles[ly][lx]
                original = generate_tile(start_x + lx, start_y + ly, self._seed)
                if current != original:
                    delta[f"{lx},{ly}"] = current
        return delta

    def save_to_disk(self):
        """如果 chunk 被修改过，将差异写入磁盘。"""
        if not self.is_dirty:
            return
        delta = self.get_delta()
        if not delta:
            self.is_dirty = False
            return
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        filepath = SAVE_DIR / f"chunk_{self.cx}_{self.cy}.json"
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(delta, f, ensure_ascii=False)
        except Exception as e:
            print(f"[Chunk] 保存失败 {self.cx},{self.cy}: {e}")

    def load_from_disk(self):
        """尝试从磁盘加载该 chunk 的差异数据。返回 True 表示有存档数据。"""
        filepath = SAVE_DIR / f"chunk_{self.cx}_{self.cy}.json"
        if not filepath.exists():
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                delta = json.load(f)
            self.apply_delta(delta)
            return True
        except Exception as e:
            print(f"[Chunk] 加载失败 {self.cx},{self.cy}: {e}")
            return False


# ═══════════════════════════════════════
# World 类：无限世界容器
# ═══════════════════════════════════════

class World:
    """无限世界容器。管理已加载的 chunk，对外透明如普通网格。"""

    def __init__(self, seed: int = 12345):
        self.seed = seed
        self._chunks = {}

    def _chunk_key(self, x: int, y: int):
        return (x // CHUNK_SIZE, y // CHUNK_SIZE)

    def _load_chunk(self, cx: int, cy: int):
        """懒加载一个 chunk。已存在则跳过，否则尝试从磁盘恢复。"""
        if (cx, cy) in self._chunks:
            return
        chunk = Chunk(cx, cy, self.seed)
        chunk.load_from_disk()
        self._chunks[(cx, cy)] = chunk

    def _unload_chunk(self, cx: int, cy: int):
        """卸载一个 chunk。如果是脏数据，先写入磁盘。"""
        if (cx, cy) in self._chunks:
            self._chunks[(cx, cy)].save_to_disk()
            del self._chunks[(cx, cy)]

    def get_tile(self, x: int, y: int) -> dict:
        """获取 (x, y) 的 tile 数据，返回 {"tile": int, "extra": {}} 兼容旧接口。"""
        cx, cy = self._chunk_key(x, y)
        self._load_chunk(cx, cy)
        local_x = x - cx * CHUNK_SIZE
        local_y = y - cy * CHUNK_SIZE
        tile_id = self._chunks[(cx, cy)].get_tile(local_x, local_y)
        return {"tile": tile_id, "extra": {}}

    def set_tile(self, x: int, y: int, tile_id: int):
        """修改 (x, y) 的 tile ID。"""
        cx, cy = self._chunk_key(x, y)
        self._load_chunk(cx, cy)
        local_x = x - cx * CHUNK_SIZE
        local_y = y - cy * CHUNK_SIZE
        self._chunks[(cx, cy)].set_tile(local_x, local_y, tile_id)

    def keep_radius(self, center_x: int, center_y: int, chunk_radius: int = 3):
        """保留中心周围一定半径的 chunk，卸载其余。"""
        ccx, ccy = self._chunk_key(center_x, center_y)
        to_unload = []
        for (cx, cy) in self._chunks:
            if abs(cx - ccx) > chunk_radius or abs(cy - ccy) > chunk_radius:
                to_unload.append((cx, cy))
        for key in to_unload:
            self._unload_chunk(*key)

    def save_all(self):
        """保存所有已修改的 chunk 到磁盘。"""
        for chunk in self._chunks.values():
            chunk.save_to_disk()

# ═══════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════

def find_spawn(world: World, start_x: int = 0) -> tuple:
    """寻找合适的出生点。确保玩家站在实体上，且周围有空位。"""
    for offset in range(80):
        for x in (start_x + offset, start_x - offset):
            for y in range(-3, 15):
                current = world.get_tile(x, y)["tile"]
                below = world.get_tile(x, y + 1)["tile"]
                # 必须站在实体方块上，头顶是空气
                if current == TILE_AIR and below not in (TILE_AIR, TILE_WATER, TILE_TREE):
                    # 在出生点周围5格内种3-5棵树
                    import random
                    rng = random.Random(x * 1000 + y)
                    for _ in range(5):
                        tx = x + rng.randint(-5, 5)
                        ty = y + rng.randint(-2, 1)
                        if world.get_tile(tx, ty)["tile"] in (TILE_AIR, TILE_DIRT):
                            world.set_tile(tx, ty, TILE_TREE)
                    return x, y
    # 最终保底：返回原点并强制设为空气
    world.set_tile(0, 0, TILE_AIR)
    world.set_tile(0, 1, TILE_DIRT)
    return 0, 0

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
                for dy in range(-height//2, height//2 + 1):
                    try:
                        tile = world.get_tile(x, y+dy)["tile"]
                        if tile in (TILE_STONE, TILE_DIRT, TILE_COAL, TILE_COPPER, 
                                   TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_LIMESTONE,
                                   TILE_MARBLE, TILE_GRANITE, TILE_CLAY, TILE_SAND):
                            world.set_tile(x, y+dy, TILE_AIR)
                    except:
                        pass
                
                # 随机游走，偏向水平
                x += rng.choice([-1, 0, 1, 1, 1])
                y += rng.choice([-1, 0, 0, 0, 0, 1])

def _carve_caves(world):
    """在每层挖出横向洞穴通道，确保有行走空间"""
    import random
    rng = random.Random(world.seed + 9999)
    for x in range(-10, 10):
        for y in range(-2, 3):
            world.set_tile(x, y, TILE_AIR)
    world.set_tile(0, 1, TILE_DIRT)
    for depth_band in [(-15, -3), (-35, -15), (-55, -35)]:
        for _ in range(rng.randint(3, 5)):
            x = rng.randint(-200, 200)
            y = rng.randint(depth_band[0], depth_band[1])
            length = rng.randint(100, 250)
            height = rng.randint(3, 5)
            for step in range(length):
                for dy in range(-height//2, height//2 + 1):
                    try:
                        tile = world.get_tile(x, y+dy)["tile"]
                        if tile in (TILE_STONE, TILE_DIRT, TILE_COAL, TILE_COPPER,
                                   TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_LIMESTONE,
                                   TILE_MARBLE, TILE_GRANITE, TILE_CLAY, TILE_SAND):
                            world.set_tile(x, y+dy, TILE_AIR)
                    except:
                        pass
                x += rng.choice([-1, 0, 1, 1, 1])
                y += rng.choice([-1, 0, 0, 0, 0, 1])

def _scatter_trees(world):
    """在地表随机撒树，确保有足够的树可砍"""
    import random
    rng = random.Random(world.seed + 8888)
    
    planted = 0
    for _ in range(200):
        x = rng.randint(-60, 60)
        y = rng.randint(-3, 1)
        tile = world.get_tile(x, y)["tile"]
        # 在泥土或空气上种树（但不能种在水上）
        if tile == TILE_DIRT:
            world.set_tile(x, y, TILE_TREE)
            planted += 1
            if planted >= 50:
                break
    # 如果还不够，在空气上也种一些
    for _ in range(200):
        x = rng.randint(-60, 60)
        y = rng.randint(-3, 1)
        tile = world.get_tile(x, y)["tile"]
        if tile == TILE_AIR:
            world.set_tile(x, y, TILE_TREE)
            planted += 1
            if planted >= 60:
                break

def _place_special_locations(world):
    """在地图里埋藏特殊地貌，给玩家探索的惊喜"""
    import random
    rng = random.Random(world.seed + 4444)
    
    locations = [
        ("废弃矿洞", TILE_STONE, 5, {"铁矿石": 15, "石头": 30}),
        ("蜘蛛巢穴", TILE_DIRT, 3, {"蜘蛛丝": 20}),
        ("水晶洞穴", TILE_STONE, 4, {"钻石原石": 5, "玻璃": 10}),
        ("地下湖", TILE_AIR, 6, {"沙子": 20}),
        ("远古遗迹", TILE_GRANITE, 5, {"金矿石": 8, "大理石": 15}),
        ("蘑菇洞", TILE_DIRT, 3, {"黏土": 25}),
        ("硫磺温泉", TILE_STONE, 3, {"硫磺": 15}),
    ]
    
    placed = []
    for name, base_tile, size, loot in locations:
        for _ in range(30):
            x = rng.randint(-150, 150)
            y = rng.randint(-60, -8)
            # 确保不重叠
            too_close = any(abs(x-px) < 15 and abs(y-py) < 15 for px, py, _ in placed)
            if not too_close:
                # 挖出一个空间
                for dx in range(-size, size+1):
                    for dy in range(-size, size+1):
                        world.set_tile(x+dx, y+dy, TILE_AIR)
                # 放标志物
                world.set_tile(x, y, "火把")
                placed.append((x, y, name))
                break
    
    return placed

def generate_world(seed: int = 12345, layer: int = 0, decorate: bool = True):
    """返回 World 对象。decorate=False 用于读档，跳过洞穴/树木/特殊地貌生成，
    避免覆盖玩家已建造的内容（这是之前读档丢失bug的根源）。"""
    clear_perlin_cache()
    w = World(seed=seed + layer * 10000)
    if decorate:
        _carve_caves(w)
        _scatter_trees(w)
        w.special_locations = _place_special_locations(w)
    else:
        w.special_locations = []
    return w


# ═══════════════════════════════════════
# 模块导出
# ═══════════════════════════════════════

__all__ = [
    'CHUNK_SIZE', 'SAVE_DIR',
    'TILE_AIR', 'TILE_DIRT', 'TILE_STONE',
    'TILE_COAL', 'TILE_COPPER', 'TILE_IRON', 'TILE_SILVER', 'TILE_GOLD', 'TILE_DIAMOND',
    'TILE_SULFUR', 'TILE_SALT', 'TILE_CLAY', 'TILE_SAND',
    'TILE_LIMESTONE', 'TILE_MARBLE', 'TILE_GRANITE', 'TILE_OBSIDIAN', 'TILE_STAIRS_DOWN', 'TILE_STAIRS_UP', 'TILE_WATER', 'TILE_TREE',
    'TILE_DROPS',
    'World', 'Chunk', 'generate_tile', 'find_spawn', 'perlin_2d', 'generate_world',
]

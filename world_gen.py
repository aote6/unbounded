""" world_gen.py 无限世界生成模块。基于绝对坐标的懒加载 chunk 系统。
每个 Chunk 管理自身生命周期，支持脏标记与差分持久化。"""

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

TILE_DROPS = {
    TILE_DIRT: "泥土", TILE_STONE: "石头",
    TILE_COAL: "煤矿", TILE_COPPER: "铜矿石", TILE_IRON: "铁矿石",
    TILE_SILVER: "银矿石", TILE_GOLD: "金矿石", TILE_DIAMOND: "钻石原石",
    TILE_SULFUR: "硫磺", TILE_SALT: "盐矿石", TILE_CLAY: "黏土",
    TILE_SAND: "沙子", TILE_LIMESTONE: "石灰岩", TILE_MARBLE: "大理石",
    TILE_GRANITE: "花岗岩", TILE_OBSIDIAN: "黑曜石",
}


# ═══════════════════════════════════════
# Perlin 噪声生成（纯函数，无状态）
# ═══════════════════════════════════════

def _hash2d(x: int, y: int, seed: int) -> int:
    h = seed
    h ^= x * 0x7FEB352D
    h ^= y * 0x846CA68B
    h *= 0x27D4EB2D
    h ^= (h >> 13)
    h *= 0x8E3779B9
    h ^= (h >> 16)
    return h & 0x7FFFFFFF

def _hash_uniform(x: int, y: int, seed: int) -> float:
    return _hash2d(x, y, seed) / 0x7FFFFFFF

def _smooth_noise(x: int, y: int, seed: int) -> float:
    corners = (_hash_uniform(x-1, y-1, seed) + _hash_uniform(x+1, y-1, seed) +
               _hash_uniform(x-1, y+1, seed) + _hash_uniform(x+1, y+1, seed)) / 16.0
    sides = (_hash_uniform(x-1, y, seed) + _hash_uniform(x+1, y, seed) +
             _hash_uniform(x, y-1, seed) + _hash_uniform(x, y+1, seed)) / 8.0
    center = _hash_uniform(x, y, seed) / 4.0
    return corners + sides + center

def _interpolated_noise(x: float, y: float, seed: int) -> float:
    int_x = int(x); frac_x = x - int_x
    int_y = int(y); frac_y = y - int_y
    v1 = _smooth_noise(int_x, int_y, seed)
    v2 = _smooth_noise(int_x + 1, int_y, seed)
    v3 = _smooth_noise(int_x, int_y + 1, seed)
    v4 = _smooth_noise(int_x + 1, int_y + 1, seed)
    i1 = v1 * (1 - frac_x) + v2 * frac_x
    i2 = v3 * (1 - frac_x) + v4 * frac_x
    return i1 * (1 - frac_y) + i2 * frac_y

def perlin_2d(x: float, y: float, seed: int = 0,
              persistence: float = 0.5, octaves: int = 4) -> float:
    total = 0.0; freq = 1.0; amp = 1.0; max_val = 0.0
    for _ in range(octaves):
        total += _interpolated_noise(x * freq, y * freq, seed) * amp
        max_val += amp
        freq *= 2.0; amp *= persistence
    return total / max_val


# ═══════════════════════════════════════
# 单格地形生成（纯函数）
# ═══════════════════════════════════════

def generate_tile(x: int, y: int, seed: int = 12345) -> int:
    """返回该格的 tile ID（纯函数，无副作用）。"""
    elevation = perlin_2d(x * 0.125, y * 0.125, seed=seed, octaves=6)
    depth_factor = y * 0.03125
    adjusted = elevation - depth_factor * 0.3

    if adjusted > 0.55:
        tile = TILE_STONE
        ore_seed = seed + 7777
        ore_val = perlin_2d(x / 3.0, y / 3.0, seed=ore_seed, octaves=3)
        depth_bonus = max(0, -y / 80.0)
        if ore_val + depth_bonus > 0.72:
            tile = TILE_DIAMOND
        elif ore_val + depth_bonus > 0.65:
            tile = TILE_GOLD
        elif ore_val + depth_bonus > 0.58:
            tile = TILE_SILVER
        elif ore_val > 0.52:
            tile = TILE_IRON
        elif ore_val > 0.45:
            tile = TILE_COPPER
        elif ore_val > 0.38:
            tile = TILE_COAL
        elif ore_val < 0.20:
            spec_val = perlin_2d(x / 7.0, y / 7.0, seed=seed + 8888, octaves=2)
            if spec_val < 0.15:
                tile = TILE_SULFUR
            elif spec_val < 0.22:
                tile = TILE_SALT
        return tile
    elif adjusted > 0.30:
        tile = TILE_DIRT
        surface_val = perlin_2d(x / 5.0, y / 5.0, seed=seed + 9999, octaves=2)
        if surface_val > 0.60:
            tile = TILE_CLAY
        elif surface_val < 0.25:
            tile = TILE_SAND
        return tile
    else:
        return TILE_AIR


# ═══════════════════════════════════════
# Chunk 类：自管理生命周期 + 差分持久化
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

    @property
    def loaded_chunk_count(self):
        return len(self._chunks)


# ═══════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════

def find_spawn(world: World, start_x: int = 0) -> tuple:
    """寻找合适的出生点。"""
    for offset in range(200):
        for x in (start_x + offset, start_x - offset):
            for y in range(-20, 80):
                current = world.get_tile(x, y)["tile"]
                below = world.get_tile(x, y + 1)["tile"]
                if current == TILE_AIR and below in (TILE_DIRT, TILE_STONE):
                    return x, y
    return 0, 0

def generate_world(seed: int = 12345):
    """兼容旧接口——返回 World 对象。"""
    return World(seed=seed)


# ═══════════════════════════════════════
# 模块导出
# ═══════════════════════════════════════

__all__ = [
    'CHUNK_SIZE', 'SAVE_DIR',
    'TILE_AIR', 'TILE_DIRT', 'TILE_STONE',
    'TILE_COAL', 'TILE_COPPER', 'TILE_IRON', 'TILE_SILVER', 'TILE_GOLD', 'TILE_DIAMOND',
    'TILE_SULFUR', 'TILE_SALT', 'TILE_CLAY', 'TILE_SAND',
    'TILE_LIMESTONE', 'TILE_MARBLE', 'TILE_GRANITE', 'TILE_OBSIDIAN',
    'TILE_DROPS',
    'World', 'Chunk', 'generate_tile', 'find_spawn', 'perlin_2d', 'generate_world',
]

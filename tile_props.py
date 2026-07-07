""" tile_props.py 方块属性统一查询表。"""

from world_gen import (
    TILE_AIR, TILE_DIRT, TILE_STONE,
    TILE_COAL, TILE_COPPER, TILE_IRON, TILE_SILVER, TILE_GOLD, TILE_DIAMOND,
    TILE_SULFUR, TILE_SALT, TILE_CLAY, TILE_SAND,
    TILE_LIMESTONE, TILE_MARBLE, TILE_GRANITE, TILE_OBSIDIAN,
    TILE_WATER, TILE_TREE,
)

TILE_PROPS = {
    TILE_AIR: {
        "name": "空气", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 0.0,
        "drop": None, "char": " ",
    },
    TILE_DIRT: {
        "name": "泥土", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 1.5,
        "drop": "泥土", "char": ".",
    },
    TILE_STONE: {
        "name": "石头", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 4.0,
        "drop": "石头", "char": "#",
    },
    TILE_COAL: {
        "name": "煤矿", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 3.0,
        "drop": "煤矿", "char": "\u263b",
    },
    TILE_COPPER: {
        "name": "铜矿石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 3.5,
        "drop": "铜矿石", "char": "\u25cb",
    },
    TILE_IRON: {
        "name": "铁矿石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 4.5,
        "drop": "铁矿石", "char": "\u2642",
    },
    TILE_SILVER: {
        "name": "银矿石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 5.0,
        "drop": "银矿石", "char": "\u263c",
    },
    TILE_GOLD: {
        "name": "金矿石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 6.0,
        "drop": "金矿石", "char": "\u2600",
    },
    TILE_DIAMOND: {
        "name": "钻石原石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 8.0,
        "drop": "钻石原石", "char": "\u2666",
    },
    TILE_SULFUR: {
        "name": "硫磺", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 3.0,
        "drop": "硫磺", "char": "\u263f",
    },
    TILE_SALT: {
        "name": "盐矿石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 2.5,
        "drop": "盐矿石", "char": "\u25a1",
    },
    TILE_CLAY: {
        "name": "黏土", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 2.0,
        "drop": "黏土", "char": "\u2248",
    },
    TILE_SAND: {
        "name": "沙子", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 1.0,
        "drop": "沙子", "char": "\u2591",
    },
    TILE_LIMESTONE: {
        "name": "石灰岩", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 4.0,
        "drop": "石灰岩", "char": "\u2593",
    },
    TILE_MARBLE: {
        "name": "大理石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 5.5,
        "drop": "大理石", "char": "\u2592",
    },
    TILE_GRANITE: {
        "name": "花岗岩", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 6.0,
        "drop": "花岗岩", "char": "\u2588",
    },
    TILE_OBSIDIAN: {
        "name": "黑曜石", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 10.0,
        "drop": "黑曜石", "char": "\u25a0",
    },
    TILE_WATER: {
        "name": "水域", "passable": False, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 999.0,
        "drop": None, "char": "~",
    },
    TILE_TREE: {
        "name": "树木", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 1.5,
        "drop": "木材", "drop_count": 2, "char": "\u2663",
    },
}

PLACEABLE_PROPS = {
    "石墙": {
        "name": "石墙", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 5.0, "char": "\u2588",
    },
    "木墙": {
        "name": "木墙", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 2.0, "char": "\u2593",
    },
    "火把": {
        "name": "火把", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 0.5, "char": "\u2020",
    },
    "石灰岩墙": {
        "name": "石灰岩墙", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 4.0, "char": "\u2593",
    },
    "大理石柱": {
        "name": "大理石柱", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 5.5, "char": "\u2588",
    },
    "花岗岩砖": {
        "name": "花岗岩砖", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 6.0, "char": "\u2588",
    },
    "玻璃窗": {
        "name": "玻璃窗", "passable": False, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 1.5, "char": "\u2591",
    },
    "砖墙": {
        "name": "砖墙", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 3.0, "char": "\u2593",
    },
    "砂岩墙": {
        "name": "砂岩墙", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 2.0, "char": "\u2591",
    },
    "盐灯": {
        "name": "盐灯", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 1.0, "char": "\u263c",
    },
    "硫磺灯": {
        "name": "硫磺灯", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 1.0, "char": "\u263f",
    },
    "木箱": {
        "name": "木箱", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 2.0, "char": "\u25a1",
    },
    "史莱姆尸体": {
        "name": "史莱姆尸体", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": True, "hardness": 0.5,
        "drop": "史莱姆凝胶", "char": "%",
    },
    "巨型史莱姆尸体": {
        "name": "巨型史莱姆尸体", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": True, "hardness": 1.0,
        "drop": "史莱姆凝胶", "char": "%",
    },
    "蝙蝠尸体": {
        "name": "蝙蝠尸体", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": True, "hardness": 0.3, "char": ",",
    },
    "岩石傀儡残骸": {
        "name": "岩石傀儡残骸", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": True, "hardness": 4.0,
        "drop": "石头", "char": "\u2588",
    },
    "楼梯下": {
        "name": "向下的楼梯", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 999.0, "char": ">",
    },
    "楼梯上": {
        "name": "向上的楼梯", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 999.0, "char": "<",
    },
    "木地板": {
        "name": "木地板", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 1.5, "char": "=",
    },
    "木门": {
        "name": "木门", "passable": True, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 2.0, "char": "+",
    },
    "木桌": {
        "name": "木桌", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 1.5, "char": "\u253c",
    },
    "木椅": {
        "name": "木椅", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 1.0, "char": "\u2534",

    "骨墙": {
        "name": "骨墙", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 3.0, "char": "\u263a",
    },
    "丝绸墙纸": {
        "name": "丝绸墙纸", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 1.0, "char": "\u2591",
    },
    "石砖墙": {
        "name": "石砖墙", "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 6.0, "char": "\u2588",
    },
    "地毯": {
        "name": "地毯", "passable": True, "transparent": True,
        "blocks_vision": False, "diggable": False, "hardness": 0.5, "char": "\u2248",
    },
    },
}


def get_tile_props(tile):
    """统一查询入口。tile 可以是 int tile ID、字符串名称、或带 extra 的 dict。"""
    if isinstance(tile, dict):
        tile = tile.get("tile", TILE_AIR)
    if isinstance(tile, int):
        return TILE_PROPS.get(tile, {
            "name": f"未知方块({tile})", "passable": False, "transparent": False,
            "blocks_vision": True, "diggable": True, "hardness": 3.0,
            "drop": None, "char": "?",
        })
    # 字符串类型：可能是放置物或尸体
    return PLACEABLE_PROPS.get(tile, {
        "name": str(tile), "passable": False, "transparent": False,
        "blocks_vision": True, "diggable": False, "hardness": 3.0, "char": "?",
    })

def get_tile_char(tile):
    return get_tile_props(tile)["char"]

def get_dig_turns(tile, tool_power=1):
    props = get_tile_props(tile)
    hardness = props.get("hardness", 3.0)
    if hardness <= 0:
        return 1
    return max(1, int((hardness * 2) / max(1, tool_power)))

def get_light_radius(tile):
    """返回方块的光照半径，无光照返回0"""
    props = get_tile_props(tile)
    return props.get("light_radius", 0)

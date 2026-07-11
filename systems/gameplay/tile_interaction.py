"""方块交互系统：每回合检查相邻方块之间的 Tag 规则触发"""

from systems.entity.tag_system import check_interaction
from tile_props import get_tile_props
from world_gen import TILE_AIR


BURNING_TILE = "火"


def _get_tile_tags(tile):
    if tile == TILE_AIR:
        return []
    if isinstance(tile, int):
        return []
    props = get_tile_props(tile)
    return props.get("tags", [])


def tick_tile_interactions(game):
    from systems.core.event_bus import EventBus, EventType, GameEvent

    checked = set()
    to_ignite = []

    positions = list(game.modified_tiles.keys())
    for (cx, cy) in positions:
        for dx, dy in [(-1, -1), (-1, 0), (-1, 1), (0, -1),
                       (0, 1), (1, -1), (1, 0), (1, 1)]:
            nx, ny = cx + dx, cy + dy
            pair = ((cx, cy), (nx, ny))
            if pair in checked:
                continue
            checked.add(pair)

            tile1 = game.world.get_tile(cx, cy)["tile"]
            tile2 = game.world.get_tile(nx, ny)["tile"]

            tags1 = _get_tile_tags(tile1)
            tags2 = _get_tile_tags(tile2)

            for source_tags, target_tags, sx, sy, tx, ty in [
                (tags1, tags2, cx, cy, nx, ny),
                (tags2, tags1, nx, ny, cx, cy),
            ]:
                rules = check_interaction(source_tags, target_tags)
                for rule in rules:
                    effect = rule.get("effect", "")
                    if effect in ("ignite_tile", "apply_burning"):
                        to_ignite.append(
                            (tx, ty, rule.get(
                                "burn_duration", rule.get(
                                    "duration", 5))))
                    elif effect == "extinguish":
                        target_tile = game.world.get_tile(tx, ty)["tile"]
                        if target_tile != TILE_AIR:
                            game.world.set_tile(tx, ty, TILE_AIR)
                            game.modified_tiles[(tx, ty)] = TILE_AIR

    for (ix, iy, duration) in to_ignite:
        current = game.world.get_tile(ix, iy)["tile"]
        if current == TILE_AIR:
            continue
        props = get_tile_props(current)
        if "burning" in props.get("tags", []):
            continue
        game.world.set_tile(ix, iy, BURNING_TILE)
        game.modified_tiles[(ix, iy)] = BURNING_TILE
        if not hasattr(game, '_burning_tiles'):
            game._burning_tiles = {}
        game._burning_tiles[(ix, iy)] = duration
        EventBus().emit(GameEvent(
            EventType.TILE_CHANGED,
            {"x": ix, "y": iy, "old": current, "new": BURNING_TILE, "cause": "ignite"}
        ), game)


def tick_burning_tiles(game):
    if not hasattr(game, '_burning_tiles'):
        return

    expired = []
    for (bx, by), duration in list(game._burning_tiles.items()):
        game._burning_tiles[(bx, by)] = duration - 1
        if duration <= 1:
            expired.append((bx, by))

    for pos in expired:
        del game._burning_tiles[pos]
        if game.world.get_tile(pos[0], pos[1])["tile"] == BURNING_TILE:
            game.world.set_tile(pos[0], pos[1], TILE_AIR)
            game.modified_tiles[pos] = TILE_AIR

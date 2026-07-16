"""游戏渲染器 - 负责绘制游戏画面和HUD

M23: 双缓冲优化 — 地图绘制从逐格 addstr 改为行内合并连续同色字符。
"""
import curses
import logging
from config import VIEW_HEIGHT, DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START
from codex import get_char, get_color, COLOR

logger = logging.getLogger(__name__)


SLOT_NAMES = {
    "main_hand": "主手",
    "off_hand": "副手",
    "body": "身体",
    "accessory": "饰品"}


def _get_time_of_day(turn):
    t = turn % DAY_LENGTH
    if DAWN_START <= t < DAY_START:
        return "黎明", 4
    elif DAY_START <= t < DUSK_START:
        return "白天", 9
    elif DUSK_START <= t < NIGHT_START:
        return "黄昏", 4
    else:
        return "夜晚", 1


# 256色颜色对缓存
_color_pairs = {}


def _init_color_pair(pair_num, fg_256):
    if pair_num not in _color_pairs:
        curses.init_pair(pair_num, fg_256, -1)
        _color_pairs[pair_num] = True


def _tile_attr(tile):
    color_idx = get_color(tile)
    pair_num = color_idx + 1
    _init_color_pair(pair_num, color_idx)
    return curses.color_pair(pair_num)


def _compute_cell(game, wx, wy):
    import curses
    if game._monster_has_position(wx, wy):
        m = game._monster_at(wx, wy)
        ch = m["char"]
        attr = curses.color_pair(198) | curses.A_BOLD  # 亮红
    elif wx == game.player_x and wy == game.player_y:
        ch, attr = "@", curses.color_pair(53) | curses.A_BOLD  # 琥珀黄
    elif (game.place_mode or game.look_mode) and wx == game.cursor_x and wy == game.cursor_y:
        ch, attr = "+", curses.color_pair(228) | curses.A_BOLD  # 亮黄
    else:
        tile = game.world.get_tile(wx, wy)["tile"]
        ch = get_char(tile)
        attr = _tile_attr(tile)
    for eff in game.effect_manager.active():
        if eff.kind == "hit_flash" and eff.x == wx and eff.y == wy:
            attr = curses.color_pair(51) | curses.A_BOLD
            break
    return ch, attr


def _draw_map_row(stdscr, game, row, ox, oy, ambient):
    segments = []
    current_attr = None
    current_chars = []
    wy = oy + row
    vw = stdscr.getmaxyx()[1]
    for col in range(vw):
        wx = ox + col
        ch, attr = _compute_cell(game, wx, wy)
        if ambient <= 2:
            attr = curses.color_pair(4)
        if attr != current_attr:
            if current_chars:
                segments.append((current_attr, ''.join(current_chars)))
            current_attr = attr
            current_chars = [ch]
        else:
            current_chars.append(ch)
    if current_chars:
        segments.append((current_attr, ''.join(current_chars)))
    x = 0
    max_y, max_x = stdscr.getmaxyx()
    for attr, text in segments:
        try:
            stdscr.addstr(row, x, text, attr)
        except curses.error:
            if not (row >= max_y - 1 and x + len(text) >= max_x):
                logger.warning(
                    f"地图渲染越界: row={row}, x={x}, text_len={len(text)}, "
                    f"screen=({max_y},{max_x})"
                )
        x += len(text)

    for eff in game.effect_manager.active():
        if eff.kind == "hit_flash":
            continue
        if eff.y != wy:
            continue
        ecol = eff.x - ox
        if ecol < 0 or ecol >= max_x:
            continue
        available = max_x - ecol
        eff_text = eff.char[:available]
        try:
            stdscr.addstr(row, ecol, eff_text, curses.color_pair(51) | curses.A_BOLD)
        except curses.error:
            pass


def draw(game):
    stdscr = game.engine.stdscr
    stdscr.erase()
    ox, oy = game.get_viewport_origin()
    time_name, ambient = _get_time_of_day(game.turn)
    from systems.world.weather_system import get_weather_at
    weather = get_weather_at(
        game.player_x,
        game.player_y,
        game.world.seed,
        game.turn)

    # 确保实体颜色对已注册（256色需要 init_pair，统一从 codex.COLOR 读取，避免双源不同步）
    for pair_id, fg in [
        (198, COLOR["monster_red"]),
        (11, COLOR["player_green"]),
        (228, COLOR["cursor_amber"]),
        (50, COLOR["hud_green"]),
        (51, COLOR["hud_warning"]),
        (52, COLOR["cursor_amber"]),
        (53, COLOR["gold"]),
    ]:
        _init_color_pair(pair_id, fg)

    for row in range(VIEW_HEIGHT):
        _draw_map_row(stdscr, game, row, ox, oy, ambient)

    # HUD
    def_bonus = game._player_defense()
    hp_str = f"HP: {game.player_hp}/{game.player_max_hp}"
    if def_bonus > 0:
        hp_str += f" 防:{def_bonus}"
    goal_names = {
        "build_first_room": "建造第一个房间",
        "explore_cave": "深入地下探索",
        "kill_spiders": "狩猎怪物收集材料",
        "build_luxury": "建造豪华基地",
        "survive": "活下去",
    }
    goal_text = goal_names.get(game.goal, game.goal)
    hud1 = f"[{time_name}] {hp_str} {weather['name']}"
    hud2 = f"({game.player_x},{game.player_y}) 目标:{goal_text} 怪物:{len(game.monsters)} 尸体:{len(game.corpses)}"
    if game.place_mode:
        hud2 += f" [建造:{game.place_mode}]"
    if game.dig_progress:
        hud2 += f" [挖掘中{game.dig_progress['remaining']}/{game.dig_progress['total']}]"
    try:
        low_hp = game.player_hp < game.player_max_hp * 0.3
        hud_attr = (curses.color_pair(51) if low_hp else curses.color_pair(50)) | curses.A_BOLD
        stdscr.addstr(VIEW_HEIGHT + 1, 0, hud1, hud_attr)
        stdscr.addstr(VIEW_HEIGHT + 2, 0, hud2, curses.color_pair(50))
        stdscr.addstr(VIEW_HEIGHT + 3, 0, "> " + (game.message if game.message else " "), curses.color_pair(3))

        # 旁白窗口
        narration = game.ui.narration[-11:]
        if len(narration) > 1 and narration[-1] == game.narration:
            narration = narration[:-1]
        for i in range(11):
            text = narration[i] if i < len(narration) else ""
            max_w = stdscr.getmaxyx()[1] - 4
            if len(text) > max_w:
                text = text[:max_w - 3] + "..."
            try:
                stdscr.addstr(VIEW_HEIGHT + 4 + i, 2, text, curses.color_pair(6))
            except curses.error:
                pass
    except curses.error as e:
        screen_h, _ = stdscr.getmaxyx()
        if screen_h > VIEW_HEIGHT + 15:
            logger.warning(f"HUD 渲染异常: {e}")
    stdscr.refresh()

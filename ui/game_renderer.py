"""游戏渲染器 - 负责绘制游戏画面和HUD

M23: 双缓冲优化 — 地图绘制从逐格 addstr 改为行内合并连续同色字符。
"""
import curses
from config import VIEW_HEIGHT, VIEW_WIDTH, DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START
from tile_props import get_tile_props, get_tile_char
from codex import get_display, get_char, get_color


SLOT_NAMES = {"main_hand": "主手", "off_hand": "副手", "body": "身体", "accessory": "饰品"}


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
        ch, attr = "@", curses.color_pair(11) | curses.A_BOLD  # 亮绿
    elif (game.place_mode or game.look_mode) and wx == game.cursor_x and wy == game.cursor_y:
        ch, attr = "+", curses.color_pair(228) | curses.A_BOLD  # 亮黄
    else:
        tile = game.world.get_tile(wx, wy)["tile"]
        ch = get_char(tile)
        attr = _tile_attr(tile)
    return ch, attr


def _draw_map_row(stdscr, game, row, ox, oy, ambient):
    segments = []
    current_attr = None
    current_chars = []
    wy = oy + row
    view_w = stdscr.getmaxyx()[1]
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
    for attr, text in segments:
        try:
            stdscr.addstr(row, x, text, attr)
        except curses.error:
            pass
        x += len(text)


def draw(game):
    stdscr = game.engine.stdscr
    stdscr.erase()
    ox, oy = game.get_viewport_origin()
    view_w = stdscr.getmaxyx()[1]
    time_name, ambient = _get_time_of_day(game.turn)
    from systems.weather_system import get_weather_at
    weather = get_weather_at(game.player_x, game.player_y, game.world.seed, game.turn)

    # 确保实体颜色对已注册（256色需要 init_pair）
    for pair_id, fg in [(198, 197), (11, 10), (228, 227)]:
        _init_color_pair(pair_id, fg)

    for row in range(VIEW_HEIGHT):
        _draw_map_row(stdscr, game, row, ox, oy, ambient)

    # HUD
    mats = " ".join(f"{k}:{v}" for k, v in game.inventory.get_materials().items()) or "（空）"
    eq_parts = []
    for slot_id in ("main_hand", "off_hand", "body", "accessory"):
        eq = game.equipment.get(slot_id)
        eq_name = eq.name if hasattr(eq, "name") else (eq if eq else "空")
        eq_parts.append(f"{SLOT_NAMES[slot_id]}:{eq_name}")
    eq_str = " | ".join(eq_parts)
    def_bonus = game._player_defense()
    hp_str = f"HP: {game.player_hp}/{game.player_max_hp}"
    if def_bonus > 0:
        hp_str += f" 防:{def_bonus}"
    from systems.age_system import get_age, get_age_bonus
    age = get_age()
    bonus = get_age_bonus()
    sk_str = f"年龄:{age}岁 闪避:{bonus['evasion']}%"
    goal_names = {"build_first_room": "建造第一个房间", "explore_cave": "深入地下探索",
                  "kill_spiders": "狩猎怪物收集材料", "build_luxury": "建造豪华基地", "survive": "活下去"}
    goal_text = goal_names.get(game.goal, game.goal)
    s1 = f"[{time_name}] | {hp_str} | {sk_str} | ({game.player_x},{game.player_y}) | 目标:{goal_text} | {weather["name"]}"
    if game.place_mode:
        s1 += f" | [建造: {game.place_mode}]"
    if game.dig_progress:
        s1 += f" | [挖掘中 {game.dig_progress['remaining']}/{game.dig_progress['total']}]"
    s1 += f" | 怪物:{len(game.monsters)} 尸体:{len(game.corpses)}"
    s2 = f"装备: {eq_str}"
    equips = [inst.name for inst in game.inventory.get_equipment() if inst]
    equip_str = " | ".join(equips) if equips else "无"
    s3 = f"材料: {mats} | 装备: {equip_str}"
    try:
        stdscr.addstr(VIEW_HEIGHT + 1, 0, s1, curses.A_BOLD)
        stdscr.addstr(VIEW_HEIGHT + 2, 0, s2)
        stdscr.addstr(VIEW_HEIGHT + 3, 0, s3)
        stdscr.addstr(VIEW_HEIGHT + 4, 0, game.message)
        stdscr.addstr(VIEW_HEIGHT + 6, 0,
            "移动 | c 合成 | e 装备 | b 放置 | x 查看 | d 挖掘 | o 箱子 | . 重复建造 | < > 换层 | 回车 放置 | r 重载 | S 存档 | L 读档 | q 退出")
    except curses.error:
        pass
    stdscr.refresh()

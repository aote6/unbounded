"""游戏渲染器 - 负责绘制游戏画面和HUD

M23: 双缓冲优化 — 地图绘制从逐格 addstr 改为行内合
并连续同色字符，大幅减少 curses 调用次数。
"""
import curses
from config import VIEW_HEIGHT, VIEW_WIDTH
from tile_props import get_tile_props, get_tile_char


TILE_CHARS = {
    " ": " ", ".": ".", "#": "#",
    "煤矿": "\u263b", "铜矿石": "\u25cb", "铁矿石": "\u2642",
    "银矿石": "\u263c", "金矿石": "\u2600", "钻石原石": "\u2666",
    "硫磺": "\u263f", "盐矿石": "\u25a1", "黏土": "\u2248",
    "沙子": "\u2591", "石灰岩": "\u2593", "大理石": "\u2592",
    "花岗岩": "\u2588", "黑曜石": "\u25a0",
    "石墙": "\u2588", "木墙": "\u2593", "火把": "\u2020",
    "史莱姆尸体": "%", "巨型史莱姆尸体": "%", "蝙蝠尸体": ",",
    "岩石傀儡残骸": "\u2588",
    "楼梯下": ">", "楼梯上": "<",
    "~": "~",
    "T": "T",
}

SLOT_NAMES = {"main_hand": "主手", "off_hand": "副手", "body": "身体", "accessory": "饰品"}


def _compute_cell(game, wx, wy):
    """计算单个格子的字符和属性，从原 draw() 提取。"""
    if game._monster_has_position(wx, wy):
        m = game._monster_at(wx, wy)
        ch = m["char"]
        if m["hp"] < m["max_hp"] * 0.5:
            attr = curses.color_pair(7) | curses.A_BOLD
        else:
            attr = curses.color_pair(3) | curses.A_BOLD
    elif wx == game.player_x and wy == game.player_y:
        ch, attr = "@", curses.color_pair(3) | curses.A_BOLD
    elif (game.place_mode or game.look_mode) and wx == game.cursor_x and wy == game.cursor_y:
        ch, attr = "+", curses.color_pair(8) | curses.A_BOLD
    else:
        tile = game.world.get_tile(wx, wy)["tile"]
        ch = TILE_CHARS.get(tile, get_tile_char(tile))
        attr = game.tile_attr(tile)
    return ch, attr


def _draw_map_row(game, row, ox, oy, ambient):
    """将一行地图单元格合并为连续同色段，一次性写入。
    从 VIEW_WIDTH 次 addstr 降至每行 1-5 次。
    """
    segments = []  # [(attr, string)]
    current_attr = None
    current_chars = []

    wy = oy + row
    for col in range(VIEW_WIDTH):
        wx = ox + col
        ch, attr = _compute_cell(game, wx, wy)

        # 夜晚全局压暗
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

    # 写入该行
    x = 0
    for attr, text in segments:
        try:
            game.stdscr.addstr(row, x, text, attr)
        except curses.error:
            pass
        x += len(text)


def draw(game):
    """绘制整个游戏画面：地图 + HUD。
    
    M23: 地图使用行内合并策略，消除逐格 addstr 的闪烁。
    """
    if not game._check_terminal_size():
        return
    game.stdscr.erase()
    ox, oy = game.get_viewport_origin()
    time_name, ambient = game._get_time_of_day()

    # 绘制地图（行合并优化）
    for row in range(VIEW_HEIGHT):
        _draw_map_row(game, row, ox, oy, ambient)

    # 绘制 HUD
    mats = " ".join(f"{k}:{v}" for k, v in game.inventory.get_materials().items()) or "（空）"
    eq_parts = []
    for slot_id in ("main_hand", "off_hand", "body", "accessory"):
        eq = game.equipment.get(slot_id, "空")
        eq_parts.append(f"{SLOT_NAMES[slot_id]}:{eq}")
    eq_str = " | ".join(eq_parts)
    def_bonus = game._player_defense()
    hp_str = f"HP: {game.player_hp}/{game.player_max_hp}"
    if def_bonus > 0:
        hp_str += f" 防:{def_bonus}"
    sk_str = f"挖掘:{game.skill_levels['digging']} 战斗:{game.skill_levels['combat']} 防御:{game.skill_levels['defense']}"
    zone = game._get_geology_zone(game.player_y)
    goal_names = {"build_first_room": "建造第一个房间", "explore_cave": "深入地下探索",
                  "kill_spiders": "狩猎怪物收集材料", "build_luxury": "建造豪华基地", "survive": "活下去"}
    goal_text = goal_names.get(game.goal, game.goal)
    s1 = f"[{time_name}] {zone} | {hp_str} | 技能 {sk_str} | ({game.player_x},{game.player_y}) | 目标:{goal_text}"
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
        game.stdscr.addstr(VIEW_HEIGHT + 1, 0, s1, curses.A_BOLD)
        game.stdscr.addstr(VIEW_HEIGHT + 2, 0, s2)
        game.stdscr.addstr(VIEW_HEIGHT + 3, 0, s3)
        game.stdscr.addstr(VIEW_HEIGHT + 4, 0, game.message)
        game.stdscr.addstr(VIEW_HEIGHT + 6, 0,
            "移动 | c 合成 | e 装备 | b 放置 | x 查看 | d 挖掘 | o 箱子 | . 重复建造 | < > 换层 | 回车 放置 | r 重载 | S 存档 | L 读档 | q 退出")
    except curses.error:
        pass
    game.stdscr.refresh()

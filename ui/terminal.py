"""终端设置：curses 初始化、颜色、窗口大小检查。"""
import curses
from config import VIEW_WIDTH, VIEW_HEIGHT


def setup_curses(stdscr):
    """初始化颜色对和终端设置。"""
    curses.curs_set(0)
    curses.noecho()
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)
    curses.init_pair(2, curses.COLOR_YELLOW, -1)
    curses.init_pair(3, curses.COLOR_CYAN, -1)
    curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_GREEN, -1)
    curses.init_pair(7, curses.COLOR_RED, -1)
    curses.init_pair(8, curses.COLOR_MAGENTA, -1)
    curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    stdscr.keypad(True)
    stdscr.nodelay(False)


MIN_TERM_H = VIEW_HEIGHT + 8
MIN_TERM_W = VIEW_WIDTH


def check_terminal_size(stdscr):
    """检查终端窗口是否足够大。"""
    term_h, term_w = stdscr.getmaxyx()
    if term_h < MIN_TERM_H or term_w < MIN_TERM_W:
        stdscr.erase()
        msg1 = "终端窗口太小！"
        msg2 = f"当前: {term_w}x{term_h} 需要至少: {MIN_TERM_W}x{MIN_TERM_H}"
        msg3 = "请缩小字号、横屏或调整窗口大小后按任意键..."
        h, w = term_h, term_w
        stdscr.addstr(max(0, h // 2 - 1), max(0, w // 2 - len(msg1) // 2), msg1, curses.A_BOLD)
        stdscr.addstr(max(0, h // 2), max(0, w // 2 - len(msg2) // 2), msg2)
        stdscr.addstr(max(0, h // 2 + 1), max(0, w // 2 - len(msg3) // 2), msg3)
        stdscr.refresh()
        stdscr.getch()
        return False
    return True

def tile_attr(game, tile):
    """根据方块类型返回 curses 颜色属性。"""
    import curses
    from tile_props import get_tile_props
    props = get_tile_props(tile)
    name = props["name"]
    if name == "树木":
        return curses.color_pair(6) | curses.A_BOLD
    from systems.time_system import get_time_of_day
    _, ambient = get_time_of_day(game.turn)
    if ambient <= 2:
        return curses.color_pair(4)
    elif name == "石头":
        return curses.color_pair(1)
    elif name == "泥土":
        return curses.color_pair(2)
    elif "尸体" in name or "残骸" in name:
        return curses.color_pair(9) | curses.A_BOLD
    elif not props["passable"]:
        return curses.color_pair(4) | curses.A_BOLD
    return curses.A_NORMAL

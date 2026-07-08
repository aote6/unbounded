"""查看模式状态：方向键移动光标，显示方块/怪物信息"""
import curses
from core.state_machine import State
from config import VIEW_WIDTH, VIEW_HEIGHT
from ui.game_renderer import draw
from tile_props import get_tile_props


DIRECTIONS = {
    curses.KEY_LEFT: (-1, 0), curses.KEY_RIGHT: (1, 0),
    curses.KEY_UP: (0, -1), curses.KEY_DOWN: (0, 1),
    ord("h"): (-1, 0), ord("l"): (1, 0),
    ord("k"): (0, -1), ord("j"): (0, 1),
}


class LookState(State):
    def __init__(self, game):
        self.game = game
        game.cursor_x, game.cursor_y = game.player_x, game.player_y
        game.look_mode = True
        game.message = "查看模式：方向键移动光标(+)，显示光标处信息，其他键退出。"

    def enter(self):
        pass

    def exit(self):
        self.game.look_mode = False

    def handle_input(self, key):
        game = self.game

        if key in DIRECTIONS:
            dx, dy = DIRECTIONS[key]
            ox, oy = game.get_viewport_origin()
            nx, ny = game.cursor_x + dx, game.cursor_y + dy
            if ox <= nx < ox + VIEW_WIDTH and oy <= ny < oy + VIEW_HEIGHT:
                game.cursor_x, game.cursor_y = nx, ny
            self._update_info()
            return None

        # 其他任意键退出
        game.look_mode = False
        game.message = "退出查看模式。"
        game.engine.pop_state()
        return None

    def _update_info(self):
        game = self.game
        cx, cy = game.cursor_x, game.cursor_y
        tile = game.world.get_tile(cx, cy)
        tile_id = tile["tile"]
        props = get_tile_props(tile_id)
        name = props.get("name", "未知")
        hardness = props.get("hardness", 0)
        drop = props.get("drop", "无")
        diggable = props.get("diggable", False)
        extra = tile.get("extra", {})

        info = f"({cx},{cy}) {name}"
        if diggable:
            info += f" | 可挖 | 硬度:{hardness}"
            if drop:
                info += f" | 掉落:{drop}"
        else:
            info += " | 不可挖"
        if extra:
            info += f" | {extra}"

        mon = game._monster_at(cx, cy)
        if mon:
            info += f" | {mon['name']} HP:{mon['hp']}/{mon['max_hp']}"

        game.message = info

    def update(self):
        pass

    def render(self, stdscr):
        draw(self.game)

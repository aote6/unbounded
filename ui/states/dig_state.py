"""挖掘模式状态：按方向键拆除方块，其他键取消"""
import curses
from core.state_machine import State
from ui.game_renderer import draw




class DigState(State):
    def __init__(self, game):
        self.game = game
        game.message = "挖掘模式：按方向键选择要拆除的方块（包括尸体），其他键取消。"

    def enter(self):
        pass

    def exit(self):
        pass

    def handle_input(self, key):
        game = self.game

        if key in DIRECTIONS:
            dx, dy = DIRECTIONS[key]
            game.dig_adjacent(dx, dy)
            game.advance_turn()
            game.engine.pop_state()
            return None

        # 其他键取消
        game.message = "取消挖掘。"
        game.engine.pop_state()
        return None

    def update(self):
        pass

    def render(self, stdscr):
        draw(self.game)

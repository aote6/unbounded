"""挖掘模式状态：按方向键拆除方块，其他键取消"""
from core.state_machine import State
from config import DIRECTIONS
from ui.game_renderer import draw

from systems.turn_system import advance_turn


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
            from systems.player_action import dig_adjacent
            dig_adjacent(game, dx, dy)
            advance_turn(game)
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

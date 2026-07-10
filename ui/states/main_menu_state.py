"""主菜单状态：存档检测 + 新游戏/继续/继承世界"""
import curses
from core.state_machine import State
from systems.save_system import check_save_status, clear_all_saves
from systems.save_manager import new_game, load_game
from ui.states.play_state import PlayState


class MainMenuState(State):
    def __init__(self, game):
        self.game = game
        self.save_status = check_save_status()

    def enter(self):
        pass

    def exit(self):
        pass

    def handle_input(self, key):
        if key in (ord('q'), ord('Q')):
            self.game.engine._running = False
            return None

        if self.save_status == 'full':
            if key in (ord('l'), ord('L')):
                if not load_game(self.game):
                    new_game(self.game)
                return PlayState(self.game)
            elif key in (ord('n'), ord('N')):
                clear_all_saves()
                new_game(self.game)
                return PlayState(self.game)

        elif self.save_status == 'world_only':
            if key in (ord('i'), ord('I')):
                new_game(self.game, inherit_world=True)
                return PlayState(self.game)
            elif key in (ord('n'), ord('N')):
                clear_all_saves()
                new_game(self.game)
                return PlayState(self.game)

        else:
            if key in (ord('n'), ord('N')):
                new_game(self.game)
                return PlayState(self.game)

        return None

    def update(self):
        pass

    def render(self, stdscr):
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        title = "Unbounded - 无尽地下城"
        stdscr.addstr(h // 2 - 4, max(0, w // 2 -
                      len(title) // 2), title, curses.A_BOLD)

        if self.save_status == 'full':
            stdscr.addstr(h // 2 - 2, max(0, w // 2 - 15),
                          "检测到存档文件", curses.A_BOLD)
            stdscr.addstr(h // 2, max(0, w // 2 - 15), "按 L 继续上次游戏")
            stdscr.addstr(h // 2 + 1, max(0, w // 2 - 15), "按 N 开始新游戏（会覆盖存档）")
        elif self.save_status == 'world_only':
            stdscr.addstr(h // 2 - 2, max(0, w // 2 - 15),
                          "发现一个遗留的世界", curses.A_BOLD)
            stdscr.addstr(h // 2, max(0, w // 2 - 15), "按 I 继承世界（新角色）")
            stdscr.addstr(h // 2 + 1, max(0, w // 2 - 15), "按 N 开始全新游戏")
        else:
            stdscr.addstr(h // 2, max(0, w // 2 - 10), "按 N 开始新游戏")

        stdscr.addstr(h // 2 + 3, max(0, w // 2 - 10), "按 Q 退出游戏")
        stdscr.refresh()

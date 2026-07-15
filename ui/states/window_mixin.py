"""CenteredWindowMixin - 弹窗类State的公共窗口创建/绘制/清理逻辑。

抽取自: chest_state / crafting_state / equipment_state /
       inventory_state / legacy_state / build_state
六个文件里重复的居中开窗 + box绘制 + 关闭清理代码。

不改变各State自己的业务逻辑，只统一"怎么开窗/怎么画框/怎么关窗"这三件事。
"""

import curses


class CenteredWindowMixin:
    def _open_centered_win(self, h, w):
        y = max(0, (curses.LINES - h) // 2)
        x = max(0, (curses.COLS - w) // 2)
        self.win = curses.newwin(h, w, y, x)
        self.win.keypad(True)
        return self.win

    def _close_win(self):
        if self.win:
            del self.win
            self.win = None
        self.game.engine.stdscr.touchwin()
        self.game.engine.stdscr.refresh()

    def _draw_frame(self, title, hint):
        self.win.erase()
        self.win.box()
        self.win.addstr(0, 2, title)
        self.win.addstr(1, 2, hint)

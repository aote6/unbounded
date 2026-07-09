"""
状态机引擎 - M17 核心架构
"""

from abc import ABC, abstractmethod


class State(ABC):

    def enter(self):
        pass

    def exit(self):
        pass

    def handle_input(self, key):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def render(self, stdscr):
        raise NotImplementedError


class Engine:

    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.state_stack = []
        self._running = False

    def push_state(self, state):
        if self.state_stack:
            self.state_stack[-1].exit()
        self.state_stack.append(state)
        state.enter()

    def pop_state(self):
        if len(self.state_stack) <= 1:
            self._running = False
            return
        self.state_stack.pop().exit()
        self.state_stack[-1].enter()

    def replace_state(self, state):
        if self.state_stack:
            self.state_stack.pop().exit()
        self.state_stack.append(state)
        state.enter()

    def run(self, initial_state):
        self._running = True
        self.push_state(initial_state)
        import curses, traceback, datetime
        while self._running and self.state_stack:
            try:
                current = self.state_stack[-1]
                # 清空输入缓冲
                self.stdscr.nodelay(True)
                key = -1
                while True:
                    k = self.stdscr.getch()
                    if k == -1:
                        break
                    key = k
                self.stdscr.nodelay(False)
                if key != -1:
                    result = current.handle_input(key)
                    if result is not None:
                        self.push_state(result)
                        continue
                current.update()
                current.render(self.stdscr)
                curses.doupdate()
            except Exception as e:
                # 安全退出 curses
                try:
                    curses.nocbreak()
                    self.stdscr.keypad(False)
                    curses.echo()
                    curses.endwin()
                except Exception:
                    pass
                # 写入崩溃日志
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(f"crash_{ts}.log", "w", encoding="utf-8") as f:
                    f.write(f"Unbounded Crash Report - {ts}\n")
                    f.write(f"Error: {type(e).__name__}: {e}\n")
                    f.write(f"State stack: {[type(s).__name__ for s in self.state_stack]}\n\n")
                    traceback.print_exc(file=f)
                # 打印到终端
                print(f"\n[游戏崩溃] {type(e).__name__}: {e}")
                print(f"完整日志已写入 crash_{ts}.log")
                traceback.print_exc()
                input("\n按回车键退出...")
                self._running = False

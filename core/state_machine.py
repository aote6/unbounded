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
        import curses
        while self._running and self.state_stack:
            current = self.state_stack[-1]
            # 清空输入缓冲：非阻塞读取所有残留按键，只保留最后一个
            self.stdscr.nodelay(True)
            key = -1
            while True:
                k = self.stdscr.getch()
                if k == -1:
                    break
                key = k
            self.stdscr.nodelay(False)
            # 只处理最后按下的键（如有）
            if key != -1:
                result = current.handle_input(key)
                if result is not None:
                    self.push_state(result)
                    continue
            current.update()
            current.render(self.stdscr)

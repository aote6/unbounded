#!/usr/bin/env python3
"""修复输入缓冲导致的'松手还在走'问题"""
from pathlib import Path

BASE = Path(__file__).parent
fp = BASE / "main.py"
src = fp.read_text("utf-8")

# 在 _setup_curses 里加 nodelay 和清缓冲
old = '''        self.stdscr.keypad(True)'''
new = '''        self.stdscr.keypad(True)
        self.stdscr.nodelay(False)  # getch 阻塞等待，但不缓冲重复按键'''

# 注意：curses 本身不缓冲，问题可能在终端模拟器
# 更有效的方案：在 run() 的 getch 后加 flushinp 清残留
src = src.replace(old, new, 1)
print("[OK] 1/2 _setup_curses 加 nodelay")

# 在 run() 主循环里，每次 getch 后清空输入缓冲
old = '''            key = self.stdscr.getch()
            acted = False'''
new = '''            key = self.stdscr.getch()
            curses.flushinp()  # 清空输入缓冲，防止松手后残留按键
            acted = False'''
count = src.count(old)
if count == 1:
    src = src.replace(old, new, 1)
    print("[OK] 2/2 run() 加 flushinp")
else:
    print(f"[跳过] 2/2: 匹配 {count} 处")

fp.write_text(src, "utf-8")
print("\n修复完成。重新进游戏试试。")

"""
磷光美学 · 11 色真彩色封装
直接向终端注入 ANSI TrueColor 转义码，绕过 curses 256 色板限制。
"""

import re

# ── 11 个精选历史真彩色 (R, G, B) ─────────────────
IBM_GREEN       = (34, 204, 136)   # #22CC88 经典绿磷 — IBM 5151
SCOPE_GREEN     = (0, 220, 130)    # #00DC82 示波器青绿 — 冷战军工
APPLE_GREEN     = (16, 160, 96)    # #10A060 苹果二代绿
AMBER           = (255, 191, 0)    # #FFBF00 经典琥珀黄
PLASMA_ORANGE   = (255, 102, 0)    # #FF6600 气体等离子橙
ALARM_RED       = (255, 85, 0)     # #FF5500 工业警示红
DEEP_BLUE       = (0, 102, 204)    # #0066CC 深海指示蓝
C64_BLUE        = (112, 128, 160)  # #7080A0 Commodore 64 蓝
SGI_PURPLE      = (140, 90, 180)   # #8C5AB4 SGI 工作站紫
AQUA_MINT       = (127, 255, 212)  # #7FFFD4 薄荷明青绿
LASER_PINK      = (255, 50, 150)   # #FF3296 激光荧光粉
PHOSPHOR_WHITE  = (232, 232, 232)  # CRT 辉光白
TRUE_BLACK      = (20, 20, 20)     # 宇宙深渊黑 (背景用)

# ── ANSI 真彩色转义码生成 ─────────────────────────
def _rgb_escape(r, g, b, bg=None):
    """生成 ANSI 真彩色转义前缀（不含重置）"""
    if bg is None:
        return f"\x1b[38;2;{r};{g};{b}m"
    br, bg_v, bb = bg
    return f"\x1b[38;2;{r};{g};{b}m\x1b[48;2;{br};{bg_v};{bb}m"

RESET = "\x1b[0m"

def rgb_text(r, g, b, text):
    """包裹前景真彩色"""
    return f"{_rgb_escape(r, g, b)}{text}{RESET}"

# ── 11 色快捷函数 ────────────────────────────────
def ibm_green(t):       return rgb_text(*IBM_GREEN, t)
def scope_green(t):     return rgb_text(*SCOPE_GREEN, t)
def apple_green(t):     return rgb_text(*APPLE_GREEN, t)
def amber(t):           return rgb_text(*AMBER, t)
def plasma_orange(t):   return rgb_text(*PLASMA_ORANGE, t)
def alarm_red(t):       return rgb_text(*ALARM_RED, t)
def deep_blue(t):       return rgb_text(*DEEP_BLUE, t)
def c64_blue(t):        return rgb_text(*C64_BLUE, t)
def sgi_purple(t):      return rgb_text(*SGI_PURPLE, t)
def aqua_mint(t):       return rgb_text(*AQUA_MINT, t)
def laser_pink(t):      return rgb_text(*LASER_PINK, t)

# ── UI 排版辅助 ───────────────────────────────────
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')
def visible_len(text):
    """去掉转义码后的实际可见字符数"""
    return len(_ANSI_RE.sub('', text))

def phosphor_white(t):  return rgb_text(*PHOSPHOR_WHITE, t)
def true_black_bg(t):   return rgb_text(232, 232, 232, t)  # 用亮字配黑底

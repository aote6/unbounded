"""文本显示宽度工具：处理中英文混排时的对齐问题（纯标准库，无第三方依赖）"""

import unicodedata


def display_width(text: str) -> int:
    """计算字符串在终端中的实际显示宽度（中文等宽字符算2，其余算1）"""
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            width += 2
        else:
            width += 1
    return width


def pad_to_width(text: str, target_width: int) -> str:
    """将字符串补空格到目标显示宽度（用于对齐列）"""
    w = display_width(text)
    if w >= target_width:
        return text
    return text + " " * (target_width - w)

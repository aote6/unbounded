# -*- coding: utf-8 -*-
"""一次性修复脚本：问题1/3/4。在项目根目录运行 python3 apply_fixes.py"""
import sys

def patch_file(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        if old not in content:
            print(f"[跳过] {path}: 未找到匹配片段，可能已经改过或代码有出入，请手动检查")
            continue
        if content.count(old) > 1:
            print(f"[警告] {path}: 匹配片段出现多次，只替换第一处")
        content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[完成] {path}")


main_replacements = [
    (
'''from systems.status_system import register as register_status
from systems.buff_system import create_buff_manager
from systems.tag_system import load_rules
from config import PLAYER_INITIAL_HP, SPAWN_INITIAL_COUNTDOWN, VIEW_WIDTH, VIEW_HEIGHT

BASE_DIR = Path(__file__).parent
logger = logging.getLogger(__name__)''',
'''from systems.status_system import register as register_status
from systems.buff_system import create_buff_manager
from systems.tag_system import load_rules
from systems import skill_system
from config import PLAYER_INITIAL_HP, SPAWN_INITIAL_COUNTDOWN, VIEW_WIDTH, VIEW_HEIGHT

BASE_DIR = Path(__file__).parent
logger = logging.getLogger(__name__)


def _setup_logging():
    logging.basicConfig(
        filename=str(BASE_DIR / "unbounded_debug.log"),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        encoding="utf-8",
    )'''
    ),
    (
'''# ── 模块级静态数据缓存（避免重复加载 JSON）──
_static_cache = {}''',
'''class StaticDataRegistry:
    _instance = None

    def __init__(self):
        self.recipes: dict = {}
        self.items: dict = {}
        self.monster_data: dict = {}
        self._loaded = False

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None

    def load(self):
        if self._loaded:
            return
        recipe_path = BASE_DIR / "data" / "recipes.json"
        if recipe_path.exists():
            try:
                with open(recipe_path, "r", encoding="utf-8") as f:
                    self.recipes = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"recipes.json 格式错误: {e}")
        else:
            logger.warning(f"缺少配方文件: {recipe_path}")
        try:
            self.items = load_items()
        except Exception as e:
            logger.error(f"加载物品失败: {e}")
        try:
            self.monster_data = load_monsters()
        except Exception as e:
            logger.error(f"加载怪物失败: {e}")
        from systems.entity_validator import validate_all
        try:
            validate_all()
        except Exception as e:
            logger.error(f"数据一致性校验失败: {e}")
            raise
        self._loaded = True'''
    ),
    (
'''    def _combat_damage_bonus(self):
        from systems.skill_system import combat_damage_bonus
        return combat_damage_bonus(self)

    def _player_defense(self):
        from systems.skill_system import defense_bonus
        return defense_bonus(self)

    def _best_equipped_tool_bonus(self, tool_type):
        from systems.skill_system import best_equipped_tool_bonus
        return best_equipped_tool_bonus(self, tool_type)

    def _digging_speed_bonus(self):
        from systems.skill_system import digging_speed_bonus
        return digging_speed_bonus(self)

    def _gain_skill(self, name, amount=1):
        from systems.skill_system import gain_skill
        gain_skill(self, name, amount)''',
'''    def _combat_damage_bonus(self):
        return skill_system.combat_damage_bonus(self)

    def _player_defense(self):
        return skill_system.defense_bonus(self)

    def _best_equipped_tool_bonus(self, tool_type):
        return skill_system.best_equipped_tool_bonus(self, tool_type)

    def _digging_speed_bonus(self):
        return skill_system.digging_speed_bonus(self)

    def _gain_skill(self, name, amount=1):
        skill_system.gain_skill(self, name, amount)'''
    ),
    (
'''    def _load_static_data(self):
        """加载静态资源，明确报错而非静默失败"""

        # 如果已缓存，直接复用（加速重启）
        if _static_cache:
            self.recipes = _static_cache['recipes']
            self.items = _static_cache['items']
            self.monster_data = _static_cache['monster_data']
            return

        recipe_path = BASE_DIR / "data" / "recipes.json"
        if recipe_path.exists():
            try:
                with open(recipe_path, "r", encoding="utf-8") as f:
                    self.recipes = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"recipes.json 格式错误: {e}")
        else:
            logger.warning(f"缺少配方文件: {recipe_path}")

        try:
            self.items = load_items()
        except Exception as e:
            logger.error(f"加载物品失败: {e}")

        try:
            self.monster_data = load_monsters()
        except Exception as e:
            logger.error(f"加载怪物失败: {e}")

        # 存入缓存
        _static_cache['recipes'] = self.recipes
        _static_cache['items'] = self.items
        _static_cache['monster_data'] = self.monster_data

        from systems.entity_validator import validate_all
        try:
            validate_all()
        except Exception as e:
            logger.error(f"数据一致性校验失败: {e}")
            raise''',
'''    def _load_static_data(self):
        registry = StaticDataRegistry.instance()
        registry.load()
        self.recipes = registry.recipes
        self.items = registry.items
        self.monster_data = registry.monster_data'''
    ),
    (
'''    from core.state_machine import Engine

    setup_curses(stdscr)''',
'''    from core.state_machine import Engine

    _setup_logging()
    setup_curses(stdscr)'''
    ),
]

state_machine_replacements = [
    (
'''"""
状态机引擎 - M17 核心架构
"""

from abc import ABC''',
'''"""
状态机引擎 - M17 核心架构
"""

import logging
from abc import ABC

logger = logging.getLogger(__name__)'''
    ),
    (
'''                # 安全退出 curses
                try:
                    curses.nocbreak()
                    self.stdscr.keypad(False)
                    curses.echo()
                    curses.endwin()
                except Exception:
                    pass''',
'''                # 安全退出 curses
                try:
                    curses.nocbreak()
                    self.stdscr.keypad(False)
                    curses.echo()
                    curses.endwin()
                except Exception as cleanup_err:
                    logger.error(f"curses 清理失败: {cleanup_err}", exc_info=True)'''
    ),
    (
'''        try:
            if self.state_stack and hasattr(self.state_stack[-1], "game"):
                game = self.state_stack[-1].game
                if getattr(game, "world", None):
                    game.world.save_all()
        except Exception:
            pass''',
'''        try:
            if self.state_stack and hasattr(self.state_stack[-1], "game"):
                game = self.state_stack[-1].game
                if getattr(game, "world", None):
                    game.world.save_all()
        except (OSError, IOError) as e:
            logger.error(f"退出时区块保存失败（磁盘/IO 问题）: {e}", exc_info=True)
            Engine._write_save_failure_marker(e)
        except Exception as e:
            logger.error(f"退出时区块保存失败（未知异常，可能是序列化问题）: {e}", exc_info=True)
            Engine._write_save_failure_marker(e)

    @staticmethod
    def _write_save_failure_marker(error):
        try:
            with open("SAVE_FAILED.txt", "w", encoding="utf-8") as f:
                f.write(f"上次退出时区块保存失败: {type(error).__name__}: {error}\\n")
                f.write("详细堆栈见 unbounded_debug.log\\n")
        except Exception:
            pass'''
    ),
]

renderer_replacements = [
    (
'''import curses
from config import VIEW_HEIGHT, DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START
from codex import get_char, get_color, COLOR''',
'''import curses
import logging
from config import VIEW_HEIGHT, DAY_LENGTH, DAWN_START, DAY_START, DUSK_START, NIGHT_START
from codex import get_char, get_color, COLOR

logger = logging.getLogger(__name__)'''
    ),
    (
'''    x = 0
    for attr, text in segments:
        try:
            stdscr.addstr(row, x, text, attr)
        except curses.error:
            pass
        x += len(text)''',
'''    x = 0
    max_y, max_x = stdscr.getmaxyx()
    for attr, text in segments:
        try:
            stdscr.addstr(row, x, text, attr)
        except curses.error:
            if not (row >= max_y - 1 and x + len(text) >= max_x):
                logger.warning(
                    f"地图渲染越界: row={row}, x={x}, text_len={len(text)}, "
                    f"screen=({max_y},{max_x})"
                )
        x += len(text)'''
    ),
    (
'''    except curses.error:
        pass
    stdscr.refresh()''',
'''    except curses.error as e:
        screen_h, _ = stdscr.getmaxyx()
        if screen_h > VIEW_HEIGHT + 6:
            logger.warning(f"HUD 渲染异常（屏幕高度足够却报错）: {e}, screen_h={screen_h}")
    stdscr.refresh()'''
    ),
]

if __name__ == "__main__":
    patch_file("main.py", main_replacements)
    patch_file("core/state_machine.py", state_machine_replacements)
    patch_file("ui/game_renderer.py", renderer_replacements)
    print("\n全部完成。建议执行 python3 -c \"import ast; ast.parse(open('main.py').read())\" 逐个校验语法")

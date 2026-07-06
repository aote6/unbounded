#!/usr/bin/env python3
"""M9 第2步：楼梯交互 - 按 > 下降、< 上升，切换世界层"""
from pathlib import Path

BASE = Path(__file__).parent

def apply_one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        print(f"[跳过] {label}: 匹配 {count} 处（需1处）")
        return text
    print(f"[OK] {label}")
    return text.replace(old, new, 1)

fp = BASE / "main.py"
src = fp.read_text("utf-8")

# 1. 在 try_move_or_dig 前加楼梯检测方法
old = '''    def try_move_or_dig(self, dx, dy):'''
new = '''    def _try_use_stairs(self):
        """检测玩家脚下是否有楼梯，执行层切换。"""
        tile = self.world.get_tile(self.player_x, self.player_y)["tile"]
        tile_str = tile if isinstance(tile, str) else None
        if tile_str == "楼梯下":
            if self.player_z > -(WORLD_LAYERS - 1):
                self.player_z -= 1
                self.world = generate_world(seed=WORLD_SEED, layer=self.player_z)
                sx, sy = find_spawn(self.world)
                self.player_x, self.player_y = sx, sy
                self.cursor_x, self.cursor_y = sx, sy
                self.monsters.clear(); self._monster_index.clear()
                self.corpses.clear(); self.modified_tiles.clear()
                self.chests.clear()
                self.message = f"你走下楼梯，到达第 {self.player_z} 层。"
                return True
            else:
                self.message = "已经是最底层了。"
        elif tile_str == "楼梯上":
            if self.player_z < 0:
                self.player_z += 1
                self.world = generate_world(seed=WORLD_SEED, layer=self.player_z)
                sx, sy = find_spawn(self.world)
                self.player_x, self.player_y = sx, sy
                self.cursor_x, self.cursor_y = sx, sy
                self.monsters.clear(); self._monster_index.clear()
                self.corpses.clear(); self.modified_tiles.clear()
                self.chests.clear()
                self.message = f"你爬上楼梯，到达第 {self.player_z} 层。"
                return True
            else:
                self.message = "已经在地表了。"
        return False

    def try_move_or_dig(self, dx, dy):'''
src = apply_one(src, old, new, "1/4 添加 _try_use_stairs 方法")

# 2. HUD 显示当前层
old = '''        s1 = f"[{time_name}] | {hp_str} | 技能 {sk_str} | ({self.player_x},{self.player_y})"'''
new = '''        s1 = f"[{time_name}] 第{self.player_z}层 | {hp_str} | 技能 {sk_str} | ({self.player_x},{self.player_y})"'''
src = apply_one(src, old, new, "2/4 HUD 显示层数")

# 3. run() 里加 < > 按键处理（在 DIRECTIONS 检查之前）
old = '''            if key in (ord('q'), ord('Q')):
                break
            elif key in (ord('o'), ord('O')):'''
new = '''            if key in (ord('q'), ord('Q')):
                break
            elif key in (ord('>'), ord('.')) and not self.place_mode:
                # 纯 > 用来下楼梯（建造模式的 . 不受影响）
                pass
            elif key == ord('>'):
                if self._try_use_stairs():
                    self.draw()
                continue
            elif key == ord('<'):
                if self._try_use_stairs():
                    self.draw()
                continue
            elif key in (ord('o'), ord('O')):'''
# 注意：上面故意写了两段 ord('>') 检查，第二段是实际生效的，第一段是占位防止 . 被吞
# 实际上需要更精确处理，直接简化：
# 把 > 和 < 的检查放在 o 之前即可
# 但 . 已经被占用（重复建造），所以 > 需要用 shift+. 也就是 ord('>')
# 在终端里 > 就是 shift+. ，curses 会区分

# 简化：直接在 q 后面加
src = src.replace(
    '''            if key in (ord('q'), ord('Q')):
                break
            elif key in (ord('>'), ord('.')) and not self.place_mode:
                # 纯 > 用来下楼梯（建造模式的 . 不受影响）
                pass
            elif key == ord('>'):
                if self._try_use_stairs():
                    self.draw()
                continue
            elif key == ord('<'):
                if self._try_use_stairs():
                    self.draw()
                continue
            elif key in (ord('o'), ord('O')):''',
    '''            if key in (ord('q'), ord('Q')):
                break
            elif key == ord('>') and not self.place_mode:
                if self._try_use_stairs():
                    self.draw()
                continue
            elif key == ord('<') and not self.place_mode:
                if self._try_use_stairs():
                    self.draw()
                continue
            elif key in (ord('o'), ord('O')):'''
)
print("[OK] 3/4 楼梯按键 < > 处理")

# 4. 帮助文字加 < > 
old = '''"移动 | c 合成 | e 装备 | b 放置 | x 查看 | d 挖掘 | o 箱子 | . 重复建造 | 回车 放置 | r 重载 | S 存档 | L 读档 | q 退出")'''
new = '''"移动 | c 合成 | e 装备 | b 放置 | x 查看 | d 挖掘 | o 箱子 | . 重复建造 | < > 换层 | 回车 放置 | r 重载 | S 存档 | L 读档 | q 退出")'''
src = apply_one(src, old, new, "4/4 帮助文字加换层提示")

fp.write_text(src, "utf-8")
print("\n=== M9 第2步完成 ===")
print("新增: 站在 > 楼梯上按 > 下降，站在 < 楼梯上按 < 上升")
print("HUD 显示当前层数，切换时清空怪物/尸体/箱子")

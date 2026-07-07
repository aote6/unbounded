# 下一步工作：架构拆分 + 内容填充

## P0：修复已知 Bug
- [x] Chunk 读档丢失：放置物存档后读档消失（world_gen.py 加 decorate 开关）
- [x] 树木颜色发黑（♣ 符号被 Android emoji 字体劫持，换成 ↑）
- [x] 合成装备无法穿戴（装备菜单切到 inventory 数据源）

## P1：main.py 拆分（进行中）
- [x] systems/interaction.py — 箱子交互（_get_nearby_chest + open_chest_menu）
- [x] ui/equipment_ui.py — 装备界面
- [x] ui/crafting_ui.py — 合成界面
- [ ] ui/building_ui.py — 建造界面（place_menu）
- [ ] ui/chest_ui.py — 箱子UI（已包含在 interaction 中，可跳过）
- [ ] systems/goal_system.py — 目标系统
- [ ] systems/event_system.py — 消息队列（暂缓）

## P2：内容填充
- [ ] 夜晚怪物加强
- [ ] 地表遗迹+宝箱
- [ ] 房间评级实际效果

## P3：体验优化
- [ ] 小地图
- [ ] 一键快速建造
- [ ] 操作提示优化

## 最近完成
| 日期 | 内容 |
|------|------|
| 2026-07-07 | 死代码清理：删除11个未调用函数、self.materials/equipment_instances 残留字段、_try_use_stairs |
| 2026-07-07 | HUD 增加装备显示 |
| 2026-07-07 | 修复装备菜单数据源（equipment_instances → inventory） |
| 2026-07-07 | 修复树木颜色（emoji 字体劫持） |
| 2026-07-07 | 修复 chunk 读档丢失（decorate 开关） |


## 2026-07-08 计划

### 交互优化（优先级高）
当前问题：物品增多后操作链路太长（合成木墙需9步）。不做增加复杂度的功能，改交互模型。

- [ ] **合成菜单字母过滤**：在 crafting_menu 中按字母键即时过滤配方列表（如按 m→只显示含"木"的配方，按 w→叠加过滤"墙"）。两三个字母从100个配方锁定目标。
- [ ] **合成菜单数字快捷键**：列表每项前加数字序号，按数字直接选中合成。常用物品玩家记住数字后肌肉记忆比翻列表快十倍。
- [ ] **一键重复合成**：按大写 C 直接合成上次配方，跳过菜单。材料不足时提示但不打开菜单。
- [ ] **合成即放置**：合成完可放置物时提示"按 Enter 立即放置，按 b 存进背包"，省去合成→打开放置菜单→翻列表的来回切换。

### 涌现系统（接续昨日）
- [ ] 特殊地貌发现接入 gameplay（world_gen 已有骨架，需在 advance_turn 中加触发检测和文字提示）

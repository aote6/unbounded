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

# Unbounded 开发路线图

## 全部里程碑

### 基础系统 (M0-M16)
M0-M16: 世界生成/怪物/装备/建造/背包/标签/状态统一

### 架构升级 (M17-M18)
M17: 状态机驱动架构 ✅
M18: 按键常量集中化 ✅

### 智能系统 (M19-M22)
M19: 气味地图寻路 ✅
M20: Tag扩展到方块 ✅
M21: Buff统一管理 ✅
M22: 中立生物+生态 ✅

### 渲染与存档 (M23-M26)
M23: 双缓冲渲染 ✅
M25: 存档分离 ✅
M26: 永久世界 ✅

### 玩法深度 (M27-M28)
M27: 跨局遗产 ✅
M28: 自定义键位 ✅

## 项目统计
- Python文件: 26个
- 总代码: ~5100行
- 生物: 10种 (7 hostile + 3 neutral)
- 方块: 26种
- 配方: 61个
- 词缀: 15个
- 按键: 20+可配置

Step 2: ItemCategory枚举 ✅ (2026-07-08)
  - inventory.py: ItemCategory(str, Enum) 替代 ITEM_TYPE 字典
  - main.py/crafting_state.py/items.py/legacy_system.py: 字符串硬编码替换为枚举
  - 共修改6个文件，枚举继承str保证JSON兼容

Step 3: 配方Schema重构 ✅ (2026-07-08)
  - recipes.json: 34个配方 "generated_equipment" → "equipment"，嵌入 generator_args
  - crafting_state.py: 从 generator_args 取 archetype/material，不再从 result_def 直接取
  - 现有 is_placeable 保留，不强制删除（build_state/inventory 仍在使用）

Phase 2: main.py 彻底重构 ✅ (2026-07-09)
  - main.py: 纯数据容器 GameState（43属性+11getter），零业务逻辑
  - systems/turn_system.py: 接管 advance_turn（气味/Buff/怪物/区块/目标）
  - systems/inventory_actions.py: 接管物品/怪物操作（9个函数）
  - systems/combat_system.py: 接管 kill_monster + collect_attack_effects
  - systems/save_manager.py: 接管 new_game/save_game/load_game（修复 self→game bug）
  - systems/save_system.py: 追加 check_death/place_grave/save_world_on_death
  - 与用户自建的 player_action.py/goal_system.py 无冲突

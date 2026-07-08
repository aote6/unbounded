# Unbounded 开发路线图

## 设计原则
- 每个新系统必须和至少一个现存系统产生涌现交互
- 数据字段必须在加入时就明确消费方
- 先验证机制对不对，再堆数量
- 所有物品通过统一接口存取

## 已完成

M0: 世界基础 — Perlin噪声无限世界、方块属性查表、连续挖掘
M1: 怪物系统 — 7种怪物、效用评分AI、碰撞检测、JSON驱动
M2: 装备与建造 — 装备槽位、合成菜单、建造模式、尸体/箱子系统
M3: 成长与存档 — 技能成长、存档读档、Chunk差分存档
M4: 物品三层模型 — 原型x材质x词缀、深度加权掉落、吸血效果
M5-M7: 生存/光照/深度生态 — 昼夜循环、怪物按深度生成
M8: 架构重构 — 统一Inventory、EquipmentInstance dataclass
M9: 物理世界地形 — 随机种子、高程系统、水域、地质分层
M10: 箱子系统完善 — 存取界面、全部存取、存档
M11: 性能优化 — Perlin缓存(58倍提升)
M12: 建造系统扩展 — 完整建材链、房间评级、特殊地貌、目标系统
M13: 统一背包系统 — Inventory类、清除双轨制
M14: main.py拆分 — 1396->1071行(-23%)、事件总线接入
M15: 标签系统+涌现机制 — tags字段、规则矩阵、燃烧系统
M16: 架构收敛-路线C — status_system统一副作用通道，修复5个逻辑漏洞

## 待完成

M17: 状态机驱动架构 ✅ (2026-07-08)
  - core/state_machine.py: State 基类 + Engine 栈式状态机
  - ui/states/: PlayState, CraftingState, EquipmentState, BuildState, ChestState
  - main.py run() 从 50 行 if/elif → 3 行引擎委托

M18: 按键常量集中化 ✅
  - config.py 20+ 按键常量，ord() 从 25 处降至 4 处

M19: 气味地图寻路 ✅ (2026-07-08)
  - systems/scent_map.py: BFS 气味场，怪物 O(1) 查询最佳方向
  - _move_toward 优先气味地图，回退贪心算法
  - 每回合 rebuild_scent_map()，天然解决卡墙角

M20: Tag 系统扩展到方块 ✅ (2026-07-08)
  - tile_props.py: 25 种可放置方块 + "火" 添加 tags
  - interaction_rules.json: ignite_tile, extinguish 规则
  - systems/tile_interaction.py: 相邻方块交互 + 火焰传播 + 燃烧计时
  - core/state_machine.py: State 基类 + Engine 栈式状态机
  - ui/states/play_state.py: 主游戏状态（移动/攻击/挖掘/查看）
  - ui/states/crafting_state.py: 合成界面（,切换分类/Enter合成）
  - ui/states/equipment_state.py: 装备界面（槽位选择/换装/卸下）
  - ui/states/build_state.py: 建造模式（选物品→光标放置/r重复）
  - ui/states/chest_state.py: 箱子存取（,切换/+全部转移）
  - main.py run() 改为委托 Engine.run(PlayState)
  - 菜单叠加通过 push/pop 栈自然支持

M18: 交互优化
  - 按键常量集中到 config.py
  - 合成菜单字母过滤、数字快捷键
  - 一键重复合成

M19: 气味地图寻路 + 怪物AI重构
  - Dijkstra气味场（Flow Map）替代贪心算法
  - 怪物AI接入事件总线
  - 不同怪物对气味敏感度不同

M20: Tag系统扩展到环境方块
  - 木墙[flammable] + 火把[heat_source] -> 点燃方块
  - 火焰传播：相邻可燃方块连锁
  - 水+电 = 范围伤害

M21: Buff/状态系统统一管理 ✅ (2026-07-08)
M22: 中立生物+生态
M23: 终端渲染优化（双缓冲）
M24: 多层地图（Z轴）

## 远期规划

M25: 存档分离 ✅ (2026-07-08) — player.json + world_meta.json，向后兼容旧 save.json
M26: 永久世界 — 角色死亡保留世界，新角色继承
M27: 跨局遗产 — 继承点数、前世记忆机制
M28: 自定义键位 — keybinds.json 外部配置

## 暂缓/不做
物品实例化(UUID)、载具、流体物理、FoV光照、Numpy

## 更新日志
2026-07-08 M16: 路线C架构收敛，status_system统一副作用通道，修复5个逻辑漏洞
2026-07-08 M15: 标签系统+涌现机制，tags字段/规则矩阵/燃烧系统
2026-07-08 M14: main.py拆分(-23%)、事件总线、战斗效果解耦
2026-07-07 M13: 统一背包、死代码清理、UI拆分
2026-07-07 M12: 建造扩展、房间评级、特殊地貌
2026-07-06 M9-M11: 地形优化、箱子系统、性能提升

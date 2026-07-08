# 设计理念与方向

## 核心定位

**终端俯视角 Roguelike 沙盒——规则涌现器。**

不是写好了公式等玩家填答案的数学题游戏，而是**提供规则积木，让玩家通过行为触发规则之间的碰撞，产生设计者从未预料到的结果。**

## 与其他游戏的差异

| 游戏 | 借鉴什么 | 本质区别 |
|------|---------|---------|
| CDDA | 生存资源管理、数据驱动 | 不做生存倒计时，压力来自**未知**而非饥饿度 |
| 矮人要塞 | 系统涌现、规则碰撞 | 终端单屏，信息密度和节奏完全不同 |
| Minecraft | 方块破坏与建造 | 不做画面物理模拟，用**属性规则**替代 |
| NetHack | 回合制、确定性生成、信息不对称 | 不做物品鉴定/诅咒，但保留你不知道前面有什么的紧张感 |

## 核心设计原则

1. **每个新系统必须和至少一个现存系统产生非预期的交互（涌现）**
2. **数据字段必须在加入时就明确消费方，不留死数据**
3. **先验证机制对不对，再堆数量**
4. **所有物品通过统一接口存取，扩展新类型不改核心代码**
5. **规则本身是可组合的积木——玩家不是在填公式，是用积木搭自己的东西**

## 架构演进（2026-07-08）

### 当前状态：事件总线作为副作用通道

M16（路线C）之后，所有状态效果通过事件总线统一分发：

_attack_monster -> DAMAGE_DEALT -> status_system（燃烧/中毒/吸血）
advance_turn   -> TURN_START    -> status_system（持续伤害）
_kill_monster  -> MONSTER_KILLED -> status_system（死亡特效，预留）

事件总线从外挂变成**唯一的副作用通道**。_attack_monster 不再硬编码 on_fire/poison/lifesteal，_tick_status_effects 清空。

### 下一步：状态机驱动架构（M17）

将 run() 中的 if/elif 输入分发链重构为 State 栈：

Engine.run()
  +-- state_stack[-1].handle_input(key)  -> 返回新 State 或 None
  +-- state_stack[-1].update()           -> 逻辑更新
  +-- state_stack[-1].render(stdscr)     -> 渲染

State 类型：
- PlayState：移动/攻击/挖掘/查看
- InventoryState：背包/装备
- CraftingState：合成菜单
- BuildState：建造模式
- ChestState：箱子交互
- DialogState：确认弹窗/死亡画面

每个 State 自己处理输入和渲染，状态切换通过 push/pop 栈实现。菜单叠加（如在游戏中打开背包）天然支持，不需要 while True 嵌套阻塞。

### 中期：气味地图寻路（M19）

当前怪物 AI 使用贪心直线逼近，在复杂洞穴地形会卡墙角。计划引入 Dijkstra 气味场（Flow Map）：

- 玩家每回合作为气味源，BFS 扩散气味梯度场
- 怪物只需检查周围 8 格的气味值，向最高处移动
- 天然解决绕墙问题，性能优于每怪独立 A*
- 可扩展：不同怪物对气味敏感度不同，隐身/潜行机制的基础

### 中期：Tag 系统扩展到环境方块

当前 Tag 交互只用于武器到怪物的燃烧效果。下一步扩展到方块：

- 木墙[flammable] + 火把[heat_source] -> 点燃方块
- 火焰向相邻可燃方块传播
- 水[wet] + 电[electric] -> 连锁伤害
- 事件总线是承载这种涌现交互的天然载体

### M19: 气味地图寻路 (2026-07-08)

当前怪物 AI 使用贪心直线逼近，在复杂洞穴地形会卡墙角。已引入 BFS 气味场：

- 每回合从玩家位置 BFS 扩散气味值（范围 30 格）
- 墙壁阻断气味，怪物位置可通过但不传播
- 怪物只需检查周围 8 格的气味值，向最高处移动
- _move_toward 优先使用气味地图，回退贪心算法
- 天然解决绕墙问题，性能优于每怪独立 A*

### M20: Tag 系统扩展到方块 (2026-07-08)

Tag 交互已从武器→怪物扩展到环境方块：

- 25 种可放置方块添加 tags（flammable/heat_source/nonflammable 等）
- "火" 方块：burning + heat_source + light
- interaction_rules.json 新增 ignite_tile、extinguish 规则
- systems/tile_interaction.py：每回合检查相邻方块交互
  - heat_source + flammable → 点燃为"火"
  - burning + flammable → 火焰传播到邻格
  - 燃烧方块有持续时间，到期变回 TILE_AIR
- 在 advance_turn 中 tick_tile_interactions + tick_burning_tiles

### 远期：存档分离与永久世界

当引入多角色/遗产机制时，分离存档：

- player.json：角色属性、背包、跨局继承点数
- world chunks/：世界地形差分（永久保留）
- 角色死亡 -> 只删除 player.json，世界保留
- 新角色 -> 继承被前代改造过的世界

### 近期：按键常量集中化（M18）

将散落在代码中的按键常量集中到 config.py，统一管理。

## 信息不对称机制

画面告诉玩家这里有什么，文字告诉玩家你感觉到什么。玩家知道的信息永远比能看到的少，每一步都带着猜测和风险。

- 画面层：字符网格，给直觉
- 文字层：描述文字，给线索
- 状态栏：精确数值，给确定感
- 发现机制：环境线索在接近时自动提示
- 元规则层：玩家不知道可燃+热源=着火，直到第一次触发

## 涌现案例

### 案例1：火把 + 木墙 = 意外火灾
玩家放置火把照亮木屋，火把有[heat_source]标签，木墙有[flammable]标签，规则矩阵匹配导致木墙着火。火焰沿可燃方块蔓延，烧掉半个基地。

### 案例2：熔岩傀儡 + 蜘蛛网 = 区域控制
熔岩傀儡[heat_source]穿过蜘蛛网[flammable]区域，蜘蛛网燃烧堵住追兵路线。

### 案例3：水 + 电 = 范围伤害
史莱姆[wet]在水里，玩家用带电武器攻击。导电规则触发，水中所有生物受到连锁伤害。

## 文件结构

main.py              # 主循环、Game类（1111行）
config.py            # 全局参数
inventory.py         # 统一背包系统
equipment.py         # 装备实例数据类
world_gen.py         # 无限世界生成、Chunk存档
monsters.py          # 怪物加载、AI、掉落
items.py             # 物品加载
item_generator.py    # 三层物品组装引擎
tile_props.py        # 方块属性查询
systems/
    event_bus.py     # 事件总线（6种事件类型）
    status_system.py # 统一状态管理
    tag_system.py    # 标签系统+规则矩阵
    interaction.py   # 箱子交互
    save_system.py   # 存档构建/恢复
ui/
    game_renderer.py # 渲染引擎
    equipment_ui.py  # 装备界面
    crafting_ui.py   # 合成界面
data/
    monsters.json    # 怪物定义（含tags）
    items.json       # 物品定义（含tags）
    interaction_rules.json  # 规则矩阵
    materials.json   # 材质定义
    recipes.json     # 合成配方
    archetypes.json  # 装备原型
    affixes.json     # 词缀

## 当前架构状态（2026-07-08）

Game.run()
  +-- 输入分发：11个 _handle_xxx() 方法
  +-- 战斗：_attack_monster -> DAMAGE_DEALT事件 -> status_system
  +-- 回合：advance_turn -> TURN_START事件 -> status_system
  +-- 怪物AI：_tick_monsters（效用评分驱动）
  +-- 世界：World对象（Perlin噪声无限生成）
  +-- 存储：Inventory统一背包 / Chunk差分存档

## 技术债务与已知限制

- systems/interaction.py 中 curses 渲染未剥离到 ui/ 层
- 怪物寻路使用贪心算法，复杂地形会卡墙角
- 输入按键散落在代码中，未集中管理
- Game 类仍为 God Object（1111行），需状态机拆分

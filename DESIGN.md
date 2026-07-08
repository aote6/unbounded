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

### 事件总线作为副作用通道

M16（路线C）之后，所有状态效果通过事件总线统一分发：

_attack_monster → DAMAGE_DEALT → status_system（燃烧/中毒/吸血）
advance_turn   → TURN_START    → status_system（持续伤害）
_kill_monster  → MONSTER_KILLED → status_system（死亡特效，预留）

事件总线从外挂变成**唯一的副作用通道**。_attack_monster 不再硬编码 on_fire/poison/lifesteal，_tick_status_effects 清空。所有状态变更集中在 status_system 中处理。

### 下一步：状态机 → Action 模式

路线 C 清理副作用后，run() 的 _handle_xxx() 方法可以拆为独立的 State 对象（M17），每个 State 只负责按键→Action。Action 执行后通过事件总线驱动副作用。这是路线 A 的踏脚石。

## 信息不对称机制

画面告诉玩家这里有什么，文字告诉玩家你感觉到什么。玩家知道的信息永远比能看到的少，每一步都带着猜测和风险。

- 画面层：字符网格，给直觉
- 文字层：描述文字，给线索
- 状态栏：精确数值，给确定感
- 发现机制：环境线索在接近时自动提示
- 元规则层：玩家不知道可燃+热源=着火，直到第一次触发

## 涌现案例（设计目标，非全部实现）

### 案例1：火把 + 木墙 = 意外火灾
玩家放置火把照亮木屋，火把有[heat_source]标签，木墙有[flammable]标签，规则矩阵匹配导致木墙着火。火焰沿可燃方块蔓延，烧掉半个基地。玩家学到：建造需要防火隔离带。

### 案例2：熔岩傀儡 + 蜘蛛网 = 区域控制
熔岩傀儡[heat_source]穿过蜘蛛网[flammable]区域，蜘蛛网燃烧堵住追兵路线。玩家可以利用环境怪物实现战术效果。

### 案例3：水 + 电 = 范围伤害
史莱姆[wet]在水里，玩家用带电武器攻击。导电规则触发，水中所有生物受到连锁伤害。单一规则×环境状态=范围效果。

## 文件结构

main.py              # 主循环、Game类（1111行，68个方法）
config.py            # 全局参数
inventory.py         # 统一背包系统
equipment.py         # 装备实例数据类
world_gen.py         # 无限世界生成、Chunk存档
monsters.py          # 怪物加载、AI、掉落
items.py             # 物品加载
item_generator.py    # 三层物品组装引擎
tile_props.py        # 方块属性查询
systems/
    event_bus.py     # 事件总线（单例，5种事件类型）
    status_system.py # 统一状态管理（燃烧/中毒/吸血）
    tag_system.py    # 标签系统+规则矩阵
    interaction.py   # 箱子交互
    save_system.py   # 存档构建/恢复
ui/
    game_renderer.py # 渲染引擎
    equipment_ui.py  # 装备界面
    crafting_ui.py   # 合成界面
data/
    monsters.json    # 怪物定义（7种，含tags）
    items.json       # 物品定义（29种，含tags）
    interaction_rules.json  # 规则矩阵
    materials.json   # 材质定义（含tags）
    recipes.json     # 合成配方（61个）
    archetypes.json  # 装备原型（8个）
    affixes.json     # 词缀（15个）

## 当前架构状态（2026-07-08）

Game.run()
  ├── 输入分发：11个 _handle_xxx() 方法
  ├── 战斗：_attack_monster → DAMAGE_DEALT事件 → status_system
  ├── 回合：advance_turn → TURN_START事件 → status_system
  ├── 怪物AI：_tick_monsters（效用评分驱动）
  ├── 世界：World对象（Perlin噪声无限生成）
  └── 存储：Inventory统一背包 / Chunk差分存档

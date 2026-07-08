# Unbounded

> 终端俯视角 Roguelike 沙盒游戏。无尽世界，向下挖掘，与怪物战斗，锻造装备。

## 特性

- 🌍 无限世界 — Perlin 噪声生成，x/y 轴无限延伸
- 👾 怪物 AI — 追逐、逃跑、分裂、瞬移
- ⚔️ 装备系统 — 原型 × 材质 × 词缀三层组装
- 🔨 合成建造 — 采集材料，合成工具武器，放置墙壁火把
- 🌙 昼夜循环 — 影响视野和怪物行为
- 📈 技能升级 — 挖掘、战斗、防御随使用成长
- 💀 涌现机制 — 事件总线 + 标签系统

## 快速开始

python3 main.py

## 操作说明

hjkl/方向键 = 移动/攻击/挖掘
d = 定向挖掘
c = 合成菜单
e = 装备菜单
b = 放置菜单
. = 重复上次建造
x = 查看模式
o = 打开附近箱子
Enter = 确认放置
r = 重载数据
S = 存档
L = 读档
q = 退出

## 依赖

Python 3.6+，curses 内置，无第三方依赖

## 项目结构

unbounded/
  main.py              # 主循环
  config.py            # 全局参数
  inventory.py         # 背包系统
  equipment.py         # 装备实例
  world_gen.py         # 世界生成
  monsters.py          # 怪物AI
  items.py             # 物品加载
  item_generator.py    # 物品组装引擎
  tile_props.py        # 方块属性
  systems/
    interaction.py     # 箱子交互
    save_system.py     # 存档
    event_bus.py       # 事件总线
    combat_effects.py  # 战斗效果
  ui/
    game_renderer.py   # 渲染
    equipment_ui.py    # 装备界面
    crafting_ui.py     # 合成界面
  data/
    items.json         # 物品定义
    recipes.json       # 合成配方
    monsters.json      # 怪物定义
    archetypes.json    # 装备原型
    materials.json     # 材质(含tags)
    affixes.json       # 词缀
    save.json          # 存档
    chunks/            # 地形存档

## 开发工具

micro = 编辑器
rg = 代码搜索
fd = 文件查找

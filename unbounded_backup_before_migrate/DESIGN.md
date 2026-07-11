# 设计理念与方向

## 核心定位

**终端俯视角 Roguelike 沙盒——规则涌现器。**

不是写好了公式等玩家填答案的数学题游戏，而是**提供规则积木，让玩家通过行为触发规则之间的碰撞，产生设计者从未预料到的结果。**

## 架构演进

### M17: 状态机驱动架构
Engine + State 栈，6种State。run() 从50行→3行。

### M19: 气味地图寻路
BFS气味场，怪物O(1)查询最佳方向，解决卡墙角。

### M20: Tag扩展到方块
25种方块+火添加tags，火焰点燃/传播/熄灭。

### M21: Buff统一管理
BuffManager统一 on_fire/burning/poisoned 三种格式。

### M22: 中立生物+生态
faction系统，兔子/鹿/狐狸，怪物猎杀中立生物。

### M23: 双缓冲渲染
合并连续同色字符，curses调用减少90%。

### M25: 存档分离
player.json + world_meta.json + chunks/。

### M26: 永久世界
角色死亡世界保留，新角色继承一切，墓碑。

### M27: 跨局遗产
遗产点数/商店/8种增益/前世记录/配方传承。

### M28: 自定义键位
keybinds.json外部配置，运行时重载。

## 技术债务
1. ui/crafting_ui.py 和 ui/equipment_ui.py 已被State替代，可删除
2. 词缀系统 on_attack 效果未完全落地
3. 狐狸 hunt_prey 未实现主动猎杀

# Unbounded

终端俯视角 Roguelike 沙盒游戏。无尽世界，向下挖掘，与怪物战斗，锻造装备。

## 快速开始

python3 main.py

## 架构

- main.py: 入口 + GameState 数据容器 (410行)
- config.py: View/World/Player/Spawn/Day 五组 dataclass
- systems/: 22个业务模块 (平均94行)
- ui/states/: 10个UI状态
- tests/: 15个测试用例 (单元+压力+5000回合仿真)

## 测试

python3 tests/smoke_test_full.py
python3 tests/test_stress.py
python3 tests/test_simulation.py

## 许可
MIT

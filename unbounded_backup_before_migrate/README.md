# Unbounded

> **Unbounded 不是 Open World，是 Open Rule World。**
> 
> 世界先存在。玩家后来进入。玩家离开以后，世界依然存在。
> 这是一个由规律驱动而非内容驱动的电子世界。
>
> 📖 [项目宪法](docs/00_PROJECT_PHILOSOPHY.md) | 🌍 [世界模型](docs/01_WORLD_MODEL.md) | 🏗 [架构](docs/02_ARCHITECTURE.md)

终端俯视角沙盒。无尽世界，遵循统一规律运行。

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

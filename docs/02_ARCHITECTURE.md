# Unbounded Project Constitution
## 第三章：工程架构（Architecture）

> "世界负责存在，系统负责运行，UI负责表达。"

---

## 一、整体架构

Unbounded采用分层架构。游戏最大的复杂度来自"世界规律"，而不是界面。

```
UI → State Machine → Systems → World/Entity → Data
```

数据永远在最底层。UI永远在最上层。所有依赖只能向下，不能反向依赖。

---

## 二、目录结构与职责

| 目录 | 职责 |
|------|------|
| `main.py` | Game对象装配，不写业务 |
| `config.py` | 程序参数 |
| `world_gen.py` | World/Chunk/Tile生成 |
| `systems/` | 所有世界规律 |
| `ui/` | 显示、输入、State切换 |
| `core/` | 框架（StateMachine等） |
| `data/` | JSON配置（物品/怪物/生态/配方） |
| `tests/` | 回归测试 |

---

## 三、核心原则

- **main.py不是游戏**，只是世界容器
- **core/不知道业务**，只提供运行机制
- **systems/每个回答一个问题**
- **ui/像窗口，看见世界但不改变规律**
- **data/优先增加JSON，而不是Python代码**
- **缓存只是优化**，删除缓存程序仍正确
- **Event不是业务**，只是通知
- **State决定交互**，System决定世界

---

## 四、依赖方向

永远保持：`UI → State → System → World → Data`

绝不能出现：Data依赖UI、World依赖UI、System依赖Renderer。

---

## 五、架构目标

最终目标不是模块越来越多，而是每个模块越来越简单。新增一个玩法应该只增加数据、少量规则、极少代码。

如果增加一个系统需要修改十几个文件，说明架构出了问题。正确架构应该让世界不断长大，而不是越来越复杂。


# Unbounded Project Constitution
## 第五章：世界层级（World Layers）

> "复杂世界，不来自复杂代码，而来自简单规律的层层演化。"

---

## 一、六层单向依赖

```
Seed → Physics → Geology → Climate → Ecology → Civilization → History
```

上一层决定下一层。下一层不能反过来改变上一层。这叫单向依赖。

---

## 各层定义

| 层 | 回答的问题 | 当前状态 |
|----|-----------|---------|
| **Physics** | 世界如何运行？时间/火/水/温度 | ✅ time_system, fire, Chunk |
| **Geology** | 为什么这里有这些石头？ | ✅ minerals.json 数据驱动 |
| **Climate** | 这里是什么环境？ | ✅ temperature/humidity noise, biome |
| **Ecology** | 谁生活在这里？ | ✅ natural.json, Feature Engine |
| **Civilization** | 智慧生命如何改变世界？ | ✅ civilizations.json, 事件驱动 |
| **History** | 世界过去发生了什么？ | 待建设 |

---

## 核心规则

- 每一层只影响下一层，不能跳层
- 不要让NPC决定天气、不要让村庄决定矿物
- 开发严格按层推进，不反过来
- 玩家不是第一层，世界永远先于玩家

---

## 最终目标

当玩家进入世界时，这个世界已经拥有自己的气候、生态、文明、历史。玩家不是来启动世界，而只是走进一个已经存在的世界。


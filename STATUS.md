# Unbounded 项目状态快照

> 最后更新：2026-07-14
> 用途：开新对话窗口时贴给AI，跳过重新探查项目结构。
> 维护规则：已解决的问题只留一行结论，过程细节不重复记录（git log已有）；技术债每条只出现一次。

---

## 一、项目定位

Termux/Python/curses 无限世界 Roguelike 沙盒。核心理念：世界先于玩法，规律优于内容，数据优于代码。设计目标：玩家体验"人生是一次不可重来的倒计时，意义自定义，终结而非过关"。

## 二、代码体量

约8400+行，60+文件。核心目录：`systems/`(世界规律) `ui/states/`(界面State) `core/`(状态机框架) `data/*.json`(数据) `tests/`(冒烟+仿真测试)

## 三、架构核心原则（判断"该不该改"的依据）

1. Tile=背景（几乎不变），Entity=内容（树/怪物/NPC，会变化）
2. 六层单向依赖：Seed→Physics→Geology→Climate→Ecology→Civilization→History，不可跳层不可反向
3. EventBus只负责广播通知，不负责决策逻辑
4. 数据优于代码：新增内容优先加JSON
5. 架构失控判断标准："改一个系统要不要牵动十几个文件"——目前不需要，健康
6. UI/输入层与游戏逻辑层严格分离：该不该动作是逻辑层(player_action.py)，怎么触发是输入层(play_state.py)

## 四、主回合循环（systems/gameplay/turn_system.py::advance_turn）

顺序：turn+=1 → rebuild_scent_map → buff_manager.tick_all → tick_corpses → tick_monsters → try_spawn_monster → tick_tile_interactions → tick_burning_tiles → world.keep_radius → check_goals(每10回合) → check_player_near_settlement → check_death

**重要坑**：`advance_turn`每次`handle_input`默认只调用一次。任何"一次输入触发多格移动"的功能（如疾走）必须显式循环调用对应次数，否则怪物/燃烧/buff会被跳过。

不在主循环、但设计如此触发的：`check_room_formation`（订阅TILE_CHANGED）、`check_special_location`（player_action.py里直接调用）

## 五、已确认健康、不需要动的部分

- 怪物Entity/Monster混合类，`monsters.py::make_monster()`统一入口
- `monster_index.py`空间索引，全项目统一走add/remove/moved
- EventBus是真实解耦机制，不是摆设
- `save_manager.py`是唯一存档入口，`save_system.py`是其依赖的底层实现
- Inventory/equipment.py数据层设计合理；背包已有独立浏览界面

## 六、已知技术债（唯一列表，按优先级）

1. ~~合成门窗功能缺失~~【2026-07-14已核实非bug】：门窗配方(木门/木门(简易)/玻璃窗)合成→放置全链路正常，此前只是游戏内未凑够材料实测。新发现：recipes.json里`result.place_tile`/`consume_item`字段全项目零引用（死字段，与items.json的同名`place_tile`是完全不同的两套东西，不要混淆），当前数据靠退化到`name`/配方key巧合对齐，未来新增配方避免误用这两个死字段。
2. ~~`place_tile`字段名实无实~~【2026-07-14已修复】：全数据审计确认16个物品100%字段值与key一致、从未用到"物品名≠tile名"的自由度，已删除该字段（`items.json`）并简化`get_place_tile()`为直接返回`name`，消除两套key体系分裂隐患。
3. **消息队列HUD展示待优化**：`game.message`已改为队列(`ui.messages`，最近5条)，但HUD仍只显示最后一条(`messages[-1]`)。是否升级为多行展示，待需求明确。
4. `EventBus()`模块级全局单例，多局测试并行可能互相污染
5. `Game`类偏"上帝对象"，职责过多，不紧急（未到"牵动十几个文件"的失控程度）
6. `ui/states/`下6个State文件窗口创建/边框绘制逻辑重复，可抽取公共Mixin
7. docstring风格不统一（中英混搭+中文标点残留），DeepSeek已有整理清单，优先级最低，顺手做

## 七、最近会话记录（滚动更新，只保留结论；超过3轮的历史随时可删，git log为准）

**2026-07-14**：确认4项已修复无新问题——消息队列改造、crafting_state.py PLACEABLE分支物品名对齐、`_Player.INITIAL_HP`死字段删除、`status_system.py::TURN_START`死订阅清理。核实`place_tile`不是死数据（被`get_place_tile()`实际读取并决定`game.place_mode`），是未触发的隐患，已归入第六节技术债#2，不重复记录。

**2026-07-13（第五轮）**：修复EventBus重复订阅累积bug（`TILE_CHANGED`订阅从`new_game()`移到`main()`，不再随重开局重复注册）。规划中：浮动文字反馈层（伤害数字/怪物飘字），需求已梳理，patch未写。发现地图渲染`_draw_map_row()`按字符数而非`display_width()`计算列位置，怪物汉字化前需先改造渲染核心，暂缓。

**2026-07-13（第四轮）**：键位系统清债完成——删除hjkl移动键（用户不用，且l与KEY_LOAD天生冲突），修复KEY_LOAD大小写bug，5个子菜单关闭逻辑统一为"开启键或q"。已实机验证。

**2026-07-13（第三轮）**：修复`legacy_state.py`悬空引用已删常量导致的死亡必崩溃（紧急）；修复遗产商店"item"类perk完全无效的问题（改为现场调用item_generator生成装备实例，不再反查items.json）。

**2026-07-13（第二轮）**：结构审计——确认backup目录/`.bak`文件已被gitignore排除，非隐患；修复`legacy`命名三方撞车（`main.py::LegacyState`→`LifeStats`）。

**2026-07-13（第一轮）**：键位/存档迁移/装备特效链路三块整顿，详见git log，此处不再展开。

**2026-07-12及更早**：背包界面、装备菜单简化、CJK宽度对齐修复、疾走功能、split-spawn递归深度保护——均已上线且稳定，无需重复描述。

## 八、给下次会话的建议

- 开新窗口先甩这份STATUS.md
- 判断"要不要动一段代码"，优先对照第三节架构原则
- 改动用"精确字符串匹配+assert校验"的Python patch脚本，assert失败先看清楚再改，不要绕过
- UI/输入相关改动，改完必须实机在Termux跑一次确认
- 每次会话结束前，只更新第六、七节；第七节超过3轮的旧记录随时可以删掉（git log是真正的历史来源）

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
~~4. `EventBus()`模块级全局单例~~【2026-07-14已修复】：根因非"重复注册"，而是test_simulation/test_stress/smoke_test三个脚本不经main()，从未调用register_status()，导致DAMAGE_DEALT/MONSTER_KILLED事件测试时静默丢弃(buff_manager死亡实体清理从未被验证)。已在四个测试文件补register_status()调用，顺带修复test_simulation/test_stress/smoke_test里sys.path.insert顺序错误(在import main之后，导致独立运行报ModuleNotFoundError)。
5. `Game`类偏"上帝对象"，职责过多，不紧急（未到"牵动十几个文件"的失控程度）
~~6. `ui/states/`下6个State文件窗口创建/边框绘制逻辑重复~~【2026-07-16已修复】：全面审计确认，6个State文件(inventory/crafting/chest/equipment/legacy/build)全部已接入CenteredWindowMixin，STATUS.md之前的"待完成"记录已多次与实际不符，以此次审计为准。
7. docstring风格不统一（中英混搭+中文标点残留），DeepSeek已有整理清单，优先级最低，顺手做

## 七、最近会话记录（滚动更新，只保留结论；超过3轮的历史随时可删，git log为准）

**2026-07-16（下下半场）**：视觉特效系统V1设计定案，未开始实施。核心结构：新建systems/effects.py，Effect(dataclass)+EffectManager(spawn/update/active/clear)，挂在Game层级下与BuffManager同级，不进存档。生命周期靠advance_turn()推进age，不用sleep/线程。V1范围收窄：只做SLASH+TEXT两种kind，只接入攻击命中/未命中/暴击三个点，且只用ASCII符号，不写中文——中文飘字会撞上2026-07-13第五轮记录的_draw_map_row()按字符数截断的旧bug，两个问题分开处理，不在这次一起修。ARCHITECTURE.md暂不改动（Effect是否算Tile/Entity之外第三类，等实现中真遇到具体冲突再补，不预先打补丁）。具体接入点见交接文档。

**2026-07-16**：crafting_state.py接入CenteredWindowMixin(技术债#6一项)；合成列表加滚动视口(以selected为中心动态显示，右上角[起始-结束/总数]提示替代原"还有N项"死截断)；text_width.py新增truncate_to_width()按显示宽度截断，修复crafting_state.py中文行(如"木墙(简易)")因len()截断溢出/错位到下一行的问题，3处addstr截断点已切换。
同日补充：chest_state.py/equipment_state.py完成CenteredWindowMixin接入。随后一次性审计发现技术债#6实际已全部完成，真正遗留问题是中文行截断：legacy_state.py/build_state.py/chest_state.py/inventory_state.py嘃1处截断点共计4处仍用`[:w-4]`按字符数截断，已全数改用truncate_to_width()并实机验证。至此技术债#6完全收尾，无遗留。

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

**2026-07-14（第二轮）**：EventBus技术债#4排查完毕并修复，见第六节。顺带修复3个测试文件的sys.path.insert执行顺序bug（独立运行会报ModuleNotFoundError）。





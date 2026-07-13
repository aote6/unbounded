# Unbounded 项目状态快照

> 最后更新：2026-07-12
> 用途：每次开新对话窗口时，把这份文件贴给 AI，跳过重新探查项目结构的过程，直接进入具体问题。

---

## 一、项目定位（一句话）

Termux/Python/curses 跑的无限世界 Roguelike 沙盒。核心理念：世界先于玩法，规律优于内容，数据优于代码。终极设计目标：让玩家在游戏里体验"人生是一次不可重来的倒计时，意义由玩家自己定义"，最终不是过关而是终结。详细哲学见 docs/00-06 七章宪法 + DESIGN.md + ROADMAP.md。

## 二、代码体量

- 总计约 8400+ 行 Python，60+ 文件（2026-07-11统计，本次会话未重新计数）
- 核心目录：
  systems/ — 所有世界规律（怪物AI、战斗、生态、气候、天气、文明、存档……）
  ui/states/ — 界面状态（State Machine模式，每个界面一个State类）
  core/ — 状态机框架本身
  data/*.json — 怪物/物品/配方/交互规则等数据
  tests/ — 冒烟测试 + 5000回合仿真测试

## 三、架构核心原则（判断"该不该改"的依据）

1. Tile vs Entity：Tile=背景（草地/岩石，几乎不变），Entity=内容（树/怪物/NPC，会变化/成长/死亡）
2. 六层单向依赖：Seed→Physics→Geology→Climate→Ecology→Civilization→History，上层决定下层，不可跳层不可反向
3. Event不是业务，只是通知：event_bus只负责广播，不负责决策逻辑
4. 数据优于代码：新增内容优先加JSON，不改Python
5. 判断架构是否失控的标准："改一个系统要不要牵动十几个文件"——目前答案是"不需要"，架构状态健康
6. UI/输入层与游戏逻辑层严格分离（本次会话新确认的原则）：移动/疾走的"该不该停"是纯逻辑（systems/gameplay/player_action.py），"怎么触发"是输入层的事（ui/states/play_state.py）。以后换成触屏点选寻路，只需要换输入层，不动逻辑层。

## 四、主回合循环实际调用链（systems/gameplay/turn_system.py::advance_turn）

执行顺序：
  turn += 1
  rebuild_scent_map(game)          仅附近20格内有怪物时才重建
  buff_manager.tick_all(game)      状态效果(燃烧/中毒等)
  tick_corpses(game)               尸体腐烂
  tick_monsters(game)              怪物AI决策+移动+攻击
  try_spawn_monster(game)          怪物/中立生物生成
  tick_tile_interactions(game)     方块间标签规则触发(点火等)
  tick_burning_tiles(game)         燃烧倒计时+熄灭
  world.keep_radius(...)           chunk卸载
  check_goals(game)                每10回合检查目标推进
  check_player_near_settlement(game)  聚落发现(每回合)
  check_death(game)                死亡检查+转生

重要坑（本次会话踩过）：advance_turn 默认每次 handle_input 只调用一次，不管玩家这次输入实际移动了几格。疾走功能上线时一度忘记这点，导致"疾走10步=只推进1个回合"，怪物/燃烧/buff全部被变相冻结。任何"一次输入触发多格移动"的新功能，都要显式循环调用 advance_turn 对应次数，不能依赖默认的单次调用。

不在主循环里、但通过其他方式触发的（不是遗漏，是设计如此）：
- check_room_formation — 订阅 EventType.TILE_CHANGED 事件触发
- check_special_location — 在 player_action.py 玩家移动动作里直接调用

## 五、已确认健康、不需要动的部分

- 怪物系统 Entity/Monster 混合类（systems/entity/entity.py）—— 全面接管怪物创建，monsters.py::make_monster() 统一入口
- systems/entity/monster_index.py —— 空间索引，全项目统一走 add/remove/moved
- Event Bus 实际使用情况 —— 是真实在跑的解耦机制，不是摆设
- systems/core/save_manager.py 是唯一存档入口，systems/core/save_system.py 是被它依赖的底层实现
- Inventory/equipment.py 数据层设计合理，不是"背包装备混乱"的根源（详见第六节）——真正缺的是背包没有独立浏览界面，本次已补上

## 六、会话完成记录（滚动更新，最新在最上）

2026-07-13 本次会话：
1. 键位系统整顿（技术债清偿，对应第七节旧待办第1条）：
   - 删除死配置文件 data/keybinds.json（从未被任何代码读取，且内容早已与生效配置 systems/data/keybinds.json 不同步）
   - 修复 keybind.py 中 DEFAULTS 的 save/save_upper 大小写bug：原来 "save":"S" 与 config.py 默认 KEY_SAVE=ord('s') 冲突，导致小写 s 保存键实际失效，现已修复为 save:"s" + save_upper:"S"
   - keybinds.json 补全新功能遗漏的键位字段：inventory、sprint
   - 删除 config.py 中全项目零引用的死常量 KEY_CLOSE / KEY_CLOSE_UPPER
   - 统一5个子菜单（build/inventory/equipment/chest/crafting）的关闭逻辑为"开启键或q/Q"，全部改用 config.KEY_XXX 常量，不再硬编码 ord('c')/ord('q')/ord('o')。原本 build_state 用 c 关闭、inventory_state 用 c 关闭，与各自开启键（b、i）不一致，是主要的键位混乱来源，现已理顺为 b/q 与 i/q
   - equipment_state.py 从"任意键关闭"改为 e/q 关闭，与其余菜单行为统一
   - 顺手修复 tests/smoke_test_full.py 中迁移遗留的孤儿导入路径：from systems import save_manager → from systems.core import save_manager（此前该测试因导入路径错误从未真正跑通，存档持久化功能实际从未被自动化验证过，现已验证通过）
   - smoke_test_full.py 全部6项测试通过

2026-07-12 本次会话：
1. 新增背包界面（ui/states/inventory_state.py，按键 i）—— 按材料/装备/消耗品/建材分类浏览，装备类可直接Enter装备/卸下（复用game.equipment，无需跳转装备菜单）
2. 装备菜单简化（ui/states/equipment_state.py）—— 从"操作菜单"降级为"只读状态一览"，避免和背包功能重复/行为不一致
3. CJK宽度对齐修复（新增 ui/text_width.py::display_width）—— 修复中英文混排时因len()按字符数而非显示宽度计算导致的UI错位。已排查确认目前只有背包界面受影响，其他界面暂无同类问题，但以后新写界面涉及中英混排对齐时应直接复用这个工具函数
4. 新增疾走功能（systems/gameplay/player_action.py::sprint_move + play_state.py）
   最终方案：独立按键 f 触发（按f进入待命提示，再按方向键才真正疾走），不是双击检测——双击方案曾短暂上线又废弃，原因是双击同方向键在"接近怪物→攻击"这个高频操作序列里必然误触发，导致战斗时经常打偏方向直接跑走。这是踩过的坑，以后不要再走回双击方案。
   停止条件：撞墙/遇到怪物(不自动攻击，交还玩家判断)/踩到特殊地块，没有"岔路口检测"（曾经加过，因为开阔地几乎每步都会误判成岔路口，导致疾走一步就停，已彻底移除，不要重新加）
   步数上限：5（用户明确要求"别走太远"，避免跑图跑过关键内容）
   已修复：疾走多步必须循环调用对应次数的advance_turn，否则怪物/燃烧/buff等回合制系统会被跳过（详见第四节）
5. P0-5修复：monsters.py::get_split_spawns 新增 MAX_SPLIT_DEPTH=3 递归深度保护，防止怪物 split_into 配置自我引用（A分裂出A）导致无限增殖崩溃。子怪物携带 split_depth 字段继承计数。
6. HUD提示栏更新（ui/game_renderer.py）—— 补充遗漏的 i 背包 提示，移除不存在的"换层"功能提示（Z轴多层地图M23尚未实现），改为 f 疾走
7. .gitignore 补充：排除 systems/data/*.json 存档文件和临时生成的依赖关系图（不应进版本控制）

历史记录（2026-07-11，来自手机备忘录迁移，未验证是否仍是最新状态）：
- _ai_hunt_prey 硬编码迁移到 tag_system.check_interaction()，规则数据化进 data/interaction_rules.json
- tick_burning_tiles 孤儿函数接入主循环（此前定义了但从未被调用，火点燃后永远不会熄灭）
- 连带修复 burning_tiles 数据类型错误（Set应为Dict）
- 验证：5000回合仿真通过

## 七、已知技术债 / 待核实事项（按优先级粗排）

高优先级（下次会话建议先看）：
1. ~~快捷键系统混乱~~【2026-07-13已解决，详见第六节】：keybind.py 默认配置里 close/close_upper 已删除（全项目零引用死常量），5个子菜单关闭逻辑已统一为"开启键或q"，save键大小写冲突已修复。
2. 合成门窗功能缺失：用户最初提出的具体诉求，建造系统目前无法合成门/窗，尚未排查具体在哪个环节缺失（crafting_state.py还是配方数据data/里缺配方）。

中优先级（DeepSeek协作分析产出，未逐条验证真实性，需要按需甄别）：
3. ~~generate_loot_for()重复读盘~~【2026-07-13核实：此条已过时，实际代码已通过StaticDataRegistry缓存monster_data，generate_loot_for只在registry未初始化时才回退读盘，正常游戏流程下不会触发。本条系文档滞后于代码，非真实待办，予以勾销。】
4. systems/core/event_bus.py::EventBus()是模块级全局单例，多局测试并行可能互相污染
5. main.py::Game类偏"上帝对象"，承载过多职责，可考虑拆分（不紧急，架构判断标准见第三节第5条，目前尚未到"改一个系统牵动十几个文件"的失控程度）
6. ui/states/下六个State文件（build/crafting/equipment/chest/dig/look）窗口创建、边框绘制等逻辑有重复，可抽取公共Mixin基类
7. docstring风格不统一（Google英文/简短英文/中文混搭）+ 中文标点残留，有DeepSeek整理好的统一修复清单可直接执行，纯粹的清洁工作，优先级最低，可以顺手做不用专门排期

其他：
8. DESIGN.md/ROADMAP.md内容滞后于实际代码（如M21"中立生物+生态"早已上线但仍标"待完成"），建议找时间通读代码校准
9. 词缀系统on_attack效果实际落地程度未核实（equipment.py、item_generator.py、combat_system.py::collect_attack_effects）

## 八、给下次会话/协作者的建议

- 开新窗口先甩这份 STATUS.md，不需要重新 find/cat 探查项目结构
- 判断"要不要动一段代码"时，优先对照第三节的架构原则，而不是凭直觉
- 改动优先用"精确字符串匹配 + assert校验"的Python patch脚本模式（本次会话全程采用），比sed/手改更不容易改错地方，assert失败时不要绕过，先看清楚实际内容再改
- 涉及UI/输入相关的改动，改完让用户实际在Termux里跑一次再确认，很多问题（连按识别、疾走步数、误触发）光看代码看不出来，必须实测
- 改完用语法检查验证：python3 -c "import ast; ast.parse(open('文件路径').read())"，这只是最低限度，涉及游戏逻辑的改动应尽量让用户实测一轮
- 每次会话结束前，花几句话更新这份STATUS.md的第六、七节，滚动记录，不要整篇重写

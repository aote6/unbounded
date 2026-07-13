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

2026-07-13 本次会话（第四轮，键位系统彻底清债）：
1. 【根源修复】KEY_LOAD/L 大小写撞车：keybind.py::DEFAULTS 里 "load": "L" 本身写错大小写（对照save/save_upper的正确写法），且缺失load_upper字段，导致KEY_LOAD被json覆盖成大写L、KEY_LOAD_UPPER退回默认值也是大写L，读档键实际只有大写L能用，小写l完全无效
2. 排查过程中发现更深层根源：小写l本身是hjkl移动键系统里的"右"（KEY_RIGHT），任何功能想用小写l都会天生冲突，不是配置写错，是设计层面的键位占用冲突
3. 用户反馈从未使用过hjkl移动键、手感别扭，决定彻底移除（而非绕开冲突改用大小写区分）：删除 config.py 中 KEY_LEFT/RIGHT/UP/DOWN=ord('h'/'l'/'k'/'j') 四个自定义常量及DIRECTIONS字典里对应四行映射（保留curses.KEY_LEFT等四个真正方向键映射不变）；删除 config.py::_init_keybinds() 中 KEY_MOVE_*_ALT 四行运行时注入；删除 keybind.py::DEFAULTS 中 move_up_alt/move_down_alt/move_left_alt/move_right_alt 四个字段。play_state.py 等消费方无需改动，因为全项目审计确认所有子菜单方向键判断均直接用curses.KEY_UP等真实键值，从未直接判断hjkl字符
4. 已实机验证：物理方向键正常移动，h/j/k/l 四个字母键按下无任何反应（不再触发移动），大写L正常触发读档
5. 排查中的操作失误记录（自我纠错）：中途误判"删除 data/keybinds.json"能让新默认值生效，实际运行时读取的是 systems/data/keybinds.json（另一路径），导致第一次尝试的patch未生效并造成一次误导性的"小写l触发移动"现象。教训：涉及配置文件生效路径的修改，必须先用find确认真实生效文件的完整路径，不能想当然沿用之前处理过的同名文件路径

2026-07-13 本次会话（第三轮，实机验证暴露的真实崩溃+功能性bug修复）：
1. 【紧急修复】legacy_state.py 悬空引用已删除常量导致的必崩溃：第一轮会话清理死常量时删除了 config.py 里的 KEY_CLOSE/KEY_CLOSE_UPPER，但 ui/states/legacy_state.py 仍在 import 使用它们，且该State在角色死亡时必定被push——即当前版本只要触发一次死亡，进入遗产商店瞬间必然ImportError崩溃。修复：新增对齐规范的 KEY_LEGACY_SHOP_UPPER("P")，legacy_state.py 关闭逻辑改为 (KEY_LEGACY_SHOP, KEY_LEGACY_SHOP_UPPER, KEY_QUIT, KEY_QUIT_UPPER)，与其余菜单"开启键或q"规范统一，同步修正过时提示文案。已实机验证：死亡→遗产商店正常弹出/正常关闭，不再崩溃
2. 【功能性修复】遗产商店"item"类型perk（石剑开局/石镐开局）完全无效：apply_legacy_perks() 原逻辑通过 items.json 按名字反查装备属性，但"石剑""石镐"这类装备实际由 item_generator 动态生成，从未存在于 items.json，导致反查拿到空字典，生成 slot=None/attack_bonus=0 的空壳装备，静默塞入背包但无法装备、不显示。修复：PERKS数据里 item_name 字段改为直接存 archetype/material（与配方名解耦，不再依赖反查recipes.json），apply_legacy_perks() 的 item 分支改为调用 item_generator 现场生成完整装备实例。已实机验证：死亡→购买perk→复活后背包/装备栏确认拿到真实可装备的武器
3. 【过程教训】补丁脚本执行时产生二次真实崩溃（NameError: EquipmentInstance未定义）：修复第2条时，用于"存在性检查后决定是否打补丁"的辅助脚本因预设的import匹配字符串与实际代码不符而跳过了本该执行的修改，但脚本本身没有assert报错、只打印了提示信息，这条提示被忽略后直接进入下一步，导致漏改。修复：核实legacy_system.py顶部实际import结构后手动补全。教训沉淀：以后补丁脚本里"未匹配到预期内容"的提示信息，必须停下来人工确认后再继续，不能因为脚本没有报错退出就默认判定为"已跳过、无影响"
4. 全局结构审计范围内确认非紧急、暂不处理的项：unbounded_backup_before_migrate/ 及根目录 _*.py/*.bak 已全部被 .gitignore 排除（git ls-files 计数为0），非真实隐患，已清理（详见下方"第二轮"记录）；main.py::_Player.INITIAL_HP（dataclass字段）与 config.py::PLAYER_INITIAL_HP（模块级平铺常量）并存，前者从未被任何代码读取，是又一例"新旧框架迁移未完全收尾"的死字段，本轮验证死亡流程时误改前者当场发现，暂不处理，已记入第七节技术债
5. crafting_state.py::_craft() PLACEABLE分支的脆弱隐患（详见下方历史记录第10条）本轮未处理，等待用户实机确认门窗放置是否存在问题后再排期

2026-07-13 本次会话（第二轮，结构审计）：
1. 全局结构审计（响应"隐藏在代码深处的结构问题"排查诉求）：
   - unbounded_backup_before_migrate/（1022K，与正式代码同名文件行数完全一致）+ 根目录下 _*.py/*.bak 一次性脚本：核实均已被 .gitignore 排除（git ls-files 计数为0），非真实隐患，非紧急清理项
   - legacy 命名三方撞车：main.py::LegacyState（dataclass，实际是"本局统计"）与 ui/states/legacy_state.py::LegacyState（State子类，遗产商店UI）同名不同义，且 main.py 原docstring错误标注"跨局遗产统计"（应为本局），是复制粘贴污染导致的认知陷阱
   - 已修复：main.py::LegacyState → LifeStats，self.legacy → self.life_stats，docstring改为"本局角色统计（死亡时结算进legacy_system的跨局遗产，不要与跨局遗产本身混淆）"，同步改 goal_system.py 一处引用。_xxx_this_life 系列property命名本身准确未动。改动面严格限定在2个文件、10处替换，字符串匹配+assert校验，smoke_test_full.py 6项全过
   - 排查方法沉淀：改名前必须先跑三层确认——类名引用面(grep ClassName)、实例属性引用面(grep .attr.field)、衍生命名引用面(grep this_life等)，确认改动不会漏改或误伤其他同名/近名符号

2026-07-13 本次会话（第一轮）：
1. 键位系统整顿（技术债清偿，对应第七节旧待办第1条）：
   - 删除死配置文件 data/keybinds.json（从未被任何代码读取，且内容早已与生效配置 systems/data/keybinds.json 不同步）
   - 修复 keybind.py 中 DEFAULTS 的 save/save_upper 大小写bug：原来 "save":"S" 与 config.py 默认 KEY_SAVE=ord('s') 冲突，导致小写 s 保存键实际失效，现已修复为 save:"s" + save_upper:"S"
   - keybinds.json 补全新功能遗漏的键位字段：inventory、sprint
   - 删除 config.py 中全项目零引用的死常量 KEY_CLOSE / KEY_CLOSE_UPPER
   - 统一5个子菜单（build/inventory/equipment/chest/crafting）的关闭逻辑为"开启键或q/Q"，全部改用 config.KEY_XXX 常量，不再硬编码 ord('c')/ord('q')/ord('o')。原本 build_state 用 c 关闭、inventory_state 用 c 关闭，与各自开启键（b、i）不一致，是主要的键位混乱来源，现已理顺为 b/q 与 i/q
   - equipment_state.py 从"任意键关闭"改为 e/q 关闭，与其余菜单行为统一
   - 顺手修复 tests/smoke_test_full.py 中迁移遗留的孤儿导入路径：from systems import save_manager → from systems.core import save_manager（此前该测试因导入路径错误从未真正跑通，存档持久化功能实际从未被自动化验证过，现已验证通过）
   - smoke_test_full.py 全部6项测试通过
2. 存档版本迁移机制显式化：
   - world_data 补充 version 字段，与 player_data 对齐
   - 原来隐藏在 if "player" in data / else 判断里的 v1(扁平)->v2(player/world分组) 格式转换，重构为可命名、可测试的 _migrate_v1_to_v2() 函数，并建立 _MIGRATIONS 注册表 + migrate_save_data() 统一入口，以后升级到v3只需新增 _migrate_v2_to_v3 并注册，不用再改 apply_load_data 主逻辑
3. 接通装备on_attack/lifesteal效果链路（对应第七节旧待办第9条）：
   - 核实发现 EventType.DAMAGE_DEALT 全项目从未被 emit 过，status_system.py 中订阅的 _on_damage_dealt（负责燃烧/中毒/吸血特效）是完全未被执行过的死代码
   - 在 player_action.py（玩家攻击怪物）和 monster_ai.py（怪物攻击玩家）两处补上 EventBus().emit(DAMAGE_DEALT)
   - 接通后连续暴露4处同类真bug：多个函数（collect_attack_effects、_player_attack_tags、吸血计算）都误把 game.equipment.values() 里的 EquipmentInstance 对象当字符串名字使用，导致"对象当dict key"的TypeError。逐一修复为直接读取对象属性（getattr(inst, field, default)），不再反查背包
   - status_system.py 里 game._collect_attack_effects()/game._get_item_attr() 两处调用了 Game 类根本不存在的方法，改为直接调用 combat_system.collect_attack_effects(game) 及 getattr
   - 实机验证：完整攻击-死亡-掉落流程通过，无崩溃
4. EventBus 全项目emit/subscribe配对审计（一次性系统排查，非逐条踩坑）：
   - TURN_START：只订阅（status_system._on_turn_start）没emit，但核实该handler函数体是空的pass，真正的buff结算已被turn_system.py直接调用game.buff_manager.tick_all(game)取代，是M21重构后的无害冗余订阅，不影响功能，可择机清理但不紧急
   - DAMAGE_DEALT：本次已修复接通（见上）
   - MONSTER_KILLED：emit/subscribe均存在，正常
   - PLAYER_HEALED / STATUS_APPLIED：定义了但全项目从未emit也从未subscribe，是纯粹的死枚举值，不影响任何功能，可考虑以后删除或留作扩展占位
   - TILE_CHANGED：emit（3处）/subscribe均存在，正常
   - 气候/天气/生态/文明系统（climate.py/weather_system.py/ecology.py/civilization.py）核实为纯坐标查询函数架构（get_xxx(x,y,seed)形式，基于种子确定性计算，不需要"tick"），不走EventBus，weather_system.get_weather_at 确认被 monster_ai.py 和 game_renderer.py 实际调用，链路正常，非断点
   - 结论：本次审计范围内（EventBus全部6个事件类型 + 气候/天气/生态调用链）未发现新的断线，DAMAGE_DEALT是本次审计前唯一的真实断点且已修复

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
10. crafting_state.py::_craft() 的 PLACEABLE 分支存在脆弱隐患：result_def 里的 place_tile/consume_item/name 字段从未被实际读取，直接用"配方名"当物品名塞入背包，目前门窗类配方能正常工作纯属"配方名==物品名==tile名"三者巧合一致，并非真正按数据驱动。风险：以后新增配方若三个名字对不齐，会静默出现"合成出的东西放不进世界"或错位，且难以联想到根因是这里。修复思路：改用 result_def.get("name", name) 和 result_def.get("place_tile", name) 显式读取，不再假设配方key等于物品名。（本条系2026-07-13结构审计中排查合成门窗问题时发现，未修复，按用户要求优先级让位于技术债清理，等待用户实机确认门窗是否真的能放置成功后再决定是否处理）

8. DESIGN.md/ROADMAP.md内容滞后于实际代码（如M21"中立生物+生态"早已上线但仍标"待完成"），建议找时间通读代码校准
9. ~~词缀系统on_attack效果实际落地程度~~【2026-07-13已解决，详见第六节】：核实发现DAMAGE_DEALT事件从未被emit，链路已接通，并修复了接通后暴露的4处game.equipment对象/字符串类型混淆bug。

## 八、给下次会话/协作者的建议

- 开新窗口先甩这份 STATUS.md，不需要重新 find/cat 探查项目结构
- 判断"要不要动一段代码"时，优先对照第三节的架构原则，而不是凭直觉
- 改动优先用"精确字符串匹配 + assert校验"的Python patch脚本模式（本次会话全程采用），比sed/手改更不容易改错地方，assert失败时不要绕过，先看清楚实际内容再改
- 涉及UI/输入相关的改动，改完让用户实际在Termux里跑一次再确认，很多问题（连按识别、疾走步数、误触发）光看代码看不出来，必须实测
- 改完用语法检查验证：python3 -c "import ast; ast.parse(open('文件路径').read())"，这只是最低限度，涉及游戏逻辑的改动应尽量让用户实测一轮
- 每次会话结束前，花几句话更新这份STATUS.md的第六、七节，滚动记录，不要整篇重写

## 九、历史架构演进摘要（归档自已删除的 DESIGN.md，2026-07-13起不再单独维护）

以下里程碑记录来自项目早期的 DESIGN.md，现已删除该文件（与 ROADMAP.md 长期互相矛盾且都滞后于代码，弃用后统一以本 STATUS.md 为唯一状态源）。保留此摘要仅作历史参考，不再滚动更新，新的技术债与进展一律记录在第六、七节。

- M17 状态机驱动架构：Engine + State 栈
- M19 气味地图寻路：BFS气味场，怪物O(1)查询最佳方向
- M20 Tag扩展到方块：方块+火添加tags，火焰点燃/传播/熄灭
- M21 Buff统一管理：BuffManager统一状态效果格式
- M22 中立生物+生态：faction系统，怪物猎杀中立生物
- M23 双缓冲渲染：合并连续同色字符，减少curses调用
- M25 存档分离：player.json + world_meta.json + chunks/
- M26 永久世界：角色死亡世界保留，新角色继承一切
- M27 跨局遗产：遗产点数/商店/增益/前世记录/配方传承
- M28 自定义键位：keybinds.json外部配置，运行时重载（本身在2026-07-13已被重新整顿，详见第六节）

注：ROADMAP.md 中曾把 M17/M20/M21/M22/M23 列为"待完成"，与 DESIGN.md 的"已完成"矛盾，且核实后（2026-07-13）确认这些功能均已实际存在于代码中，ROADMAP.md 的滞后记录已随文件一并删除。

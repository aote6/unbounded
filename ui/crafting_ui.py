"""合成界面：配方分类浏览，材料检查，合成执行。"""
import curses


def crafting_menu(stdscr, game):
    recipes = game.recipes
    if not recipes:
        game.message = "（没有可用配方）"; return

    # 收集所有配方并按分类分组
    all_names = [k for k, v in recipes.items() if isinstance(v, dict) and "ingredients" in v]
    categories = {}
    for name in all_names:
        cat = recipes[name].get("category", "未分类")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(name)
    
    cat_order = ["武器", "工具", "护甲", "建筑", "其他", "未分类"]
    ordered_cats = [c for c in cat_order if c in categories] + [c for c in categories if c not in cat_order]
    
    current_cat_idx = 0
    selected = 0
    h, w = 18, 50
    y, x = max(0,(curses.LINES-h)//2), max(0,(curses.COLS-w)//2)
    win = curses.newwin(h,w,y,x)
    win.keypad(True)
    status_msg = ""
    def redraw():
        win.erase(); win.box()
        cat_name = ordered_cats[current_cat_idx]
        names = categories[cat_name]
        win.addstr(0,2,f" 合成菜单 [{cat_name}] ")
        win.addstr(1,2,",切换分类 | ↑↓选择 | Enter合成 | c关闭")
        for i,name in enumerate(names):
            if i >= h - 5:
                win.addstr(3+i,2,f"  ... 还有 {len(names)-i} 项")
                break
            r = recipes[name]
            ing = " + ".join(f"{v}x{k}" for k,v in r.get("ingredients",{}).items())
            line = f" {name} ← {ing}"
            if r.get("desc"): line += f" ({r['desc']})"
            attr = curses.A_REVERSE if i==selected else curses.A_NORMAL
            win.addstr(3+i,2,line[:w-4],attr)
        if status_msg:
            win.addstr(h-2,2,status_msg[:w-4],curses.A_BOLD)
        win.refresh()
    while True:
        cat_name = ordered_cats[current_cat_idx]
        names = categories[cat_name]
        if selected >= len(names):
            selected = 0
        redraw()
        key = win.getch()
        if key in (ord('c'), ord('q')): status_msg = ""; break
        elif key == ord(','):  # Tab
            current_cat_idx = (current_cat_idx + 1) % len(ordered_cats)
            selected = 0; status_msg = ""
        elif key == curses.KEY_UP: selected = (selected-1) % len(names); status_msg = ""
        elif key == curses.KEY_DOWN: selected = (selected+1) % len(names); status_msg = ""
        elif key in (curses.KEY_ENTER, 10, 13):
            name = names[selected]; r = recipes[name]
            can = all(game._count_material(m) >= c for m,c in r.get("ingredients",{}).items())
            if not can:
                status_msg = "材料不足！按任意键继续。"
                redraw(); win.getch(); status_msg = ""; continue
            for m,c in r.get("ingredients",{}).items():
                game._remove_material(m, c)

            # 检查 result 类型
            result_def = r.get("result", {})
            result_type = result_def.get("type", "") if result_def else ""
            if result_type == "generated_equipment":
                from item_generator import get_generator
                gen = get_generator()
                arch = result_def.get("archetype")
                mat = result_def.get("material")
                # 矿石名自动映射到材质名
                mat = ORE_TO_MATERIAL.get(mat, mat)
                affix_chance = result_def.get("affix_chance", 0.0)
                if affix_chance > 0 and random.random() < affix_chance:
                    item_dict = gen.generate(archetype_name=arch, material_name=mat)
                else:
                    item_dict = gen.generate(archetype_name=arch, material_name=mat, affix_count=0)
                inst = EquipmentInstance(
                    name=item_dict["name"],
                    slot=item_dict.get("slot"),
                    attack_bonus=item_dict.get("attack_bonus", 0),
                    defense_bonus=item_dict.get("defense_bonus", 0),
                    tool_bonus=item_dict.get("tool_bonus", 0),
                    damage_min=item_dict.get("damage_min", 0),
                    damage_max=item_dict.get("damage_max", 0),
                    hit_bonus=item_dict.get("hit_bonus", 0),
                    affixes=item_dict.get("affixes", []),
                    on_attack=item_dict.get("on_attack", []),
                    lifesteal=item_dict.get("lifesteal", 0),
                    speed_bonus=item_dict.get("speed_bonus", 0),
                )
                game._add_equipment_instance(inst.name, inst)
                affix_str = ""
                if inst.affixes:
                    affix_str = " [" + "|".join(inst.affixes) + "]"
                status_msg = f"合成了 {inst.name}{affix_str}！(slot={inst.slot})"

            elif result_type == "material":
                # 材料类产物，存到材料背包
                mat_name = result_def.get("name", name)
                mat_count = result_def.get("count", 1)
                game._add_material(mat_name, mat_count)
                status_msg = f"合成了 {mat_name} x{mat_count}（共 {game._count_material(mat_name)}）"

            elif result_type == "placeable":
                # 可放置物，存到背包
                game._add_material(name, 1)
                status_msg = f"合成了 {name} x1（共 {game._count_material(name)}）。按 b 放置。"

            elif items_mod.is_placeable(game.items, name):
                if name == "木箱":
                    # 木箱不进建造模式，存进背包，玩家按 b 键随时选择放置
                    game._add_material(name, 1)
                    status_msg = f"合成了 {name}！按 b 从背包选择放置位置（共 {game._count_material(name)}）。"
                else:
                    game.place_mode = items_mod.get_place_tile(game.items, name)
                    game.place_item_name = None
                    game.last_place = game.place_mode
                    game.last_place_item_name = None
                    game.cursor_x, game.cursor_y = game.player_x, game.player_y
                    game.message = f"合成了 {name}！建造模式：方向键移动光标，回车放置，c 退出。"
                    break
            else:
                game._add_equipment_instance(name)
                status_msg = f"合成了 {name} x1（共 {game._count_equipment(name)}）"
    del win; game.stdscr.touchwin(); game.stdscr.refresh()
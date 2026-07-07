"""交互系统：统一处理"站旁边按按键"类操作。当前支持箱子存取，后续扩展门/开关/NPC对话。"""
import curses


def get_nearby_chest(game):
    """检查玩家四周是否有箱子，返回坐标或 None"""
    for dx, dy in [(0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,-1),(-1,1),(1,1)]:
        cx, cy = game.player_x + dx, game.player_y + dy
        if (cx, cy) in game.chests:
            return (cx, cy)
    return None


def open_chest_menu(game):
    """打开箱子界面"""
    chest_pos = get_nearby_chest(game)
    if chest_pos is None:
        game.message = "附近没有箱子。站到箱子旁边按 o 打开。"
        game.draw()
        return

    chest = game.chests[chest_pos]
    game.message = "箱子：,切换 | Enter取/存 | +全部转移 | o关闭"
    game.draw()

    viewing_chest = True
    chest_mats = list(chest["materials"].items())
    chest_equips = [(inst.name, inst) for inst in chest["equipment_instances"]]
    backpack_mats = list(game.inventory.get_materials().items())
    backpack_equips = [(inst.name, inst) for inst in game.inventory.get_equipment()]

    selected = 0
    while True:
        if viewing_chest:
            items = []
            for k, v in chest_mats:
                items.append(("material", k, v))
            for name, inst in chest_equips:
                affix = " [" + "|".join(inst.affixes) + "]" if inst.affixes else ""
                items.append(("equip", f"{name}{affix}", inst))
            title = "箱子内容"
        else:
            items = []
            for k, v in backpack_mats:
                items.append(("material", k, v))
            for name, inst in backpack_equips:
                affix = " [" + "|".join(inst.affixes) + "]" if inst.affixes else ""
                items.append(("equip", f"{name}{affix}", inst))
            title = "你的背包"

        h = max(len(items) + 5, 6)
        w = 45
        y, x = max(0, (curses.LINES - h) // 2), max(0, (curses.COLS - w) // 2)
        win = curses.newwin(h, w, y, x)
        win.keypad(True)

        if selected >= max(1, len(items)):
            selected = 0

        win.erase()
        win.box()
        win.addstr(0, 2, f" {title} ")
        win.addstr(1, 2, ",切换 | Enter取/存 | +全部转移 | o关闭")

        if not items:
            win.addstr(3, 2, "（空）")
        else:
            for i, item in enumerate(items):
                if item[0] == "material":
                    line = f"  {item[1]} x{item[2]}"
                else:
                    line = f"  {item[1]}"
                attr = curses.A_REVERSE if i == selected else curses.A_NORMAL
                win.addstr(3 + i, 2, line[:w-4], attr)

        win.refresh()

        key = win.getch()
        if key in (ord('o'), ord('q')):
            break
        elif key == ord(','):
            viewing_chest = not viewing_chest
            selected = 0
            chest_mats = list(chest["materials"].items())
            chest_equips = [(inst.name, inst) for inst in chest["equipment_instances"]]
            backpack_mats = list(game.inventory.get_materials().items())
            backpack_equips = [(inst.name, inst) for inst in game.inventory.get_equipment()]
        elif key == curses.KEY_UP:
            selected = (selected - 1) % max(1, len(items))
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % max(1, len(items))
        elif key == ord('+'):
            if viewing_chest:
                for item_id, item in list(game.inventory.all_items()):
                    if item.item_type in ("material", "placeable"):
                        chest["materials"][item_id] = chest["materials"].get(item_id, 0) + item.count
                        game.inventory.remove(item_id, item.count)
                    elif item.item_type == "equipment":
                        chest["equipment_instances"].append(item.instance)
                        game.inventory.remove(item_id)
                game.message = "所有物品已存入箱子。"
                backpack_mats = []
                backpack_equips = []
                chest_mats = list(chest["materials"].items())
                chest_equips = [(inst.name, inst) for inst in chest["equipment_instances"]]
            else:
                for k, v in list(chest["materials"].items()):
                    game._add_material(k, v)
                    del chest["materials"][k]
                for inst in list(chest["equipment_instances"]):
                    game._add_equipment_instance(inst.name, inst)
                    chest["equipment_instances"].remove(inst)
                game.message = "箱内所有物品已取出。"
                chest_mats = []
                chest_equips = []
            selected = 0
        elif items and key in (curses.KEY_ENTER, 10, 13, ord('\n'), ord('\r')):
            item = items[selected]
            if viewing_chest:
                if item[0] == "material":
                    mat_name, count = item[1], item[2]
                    game._add_material(mat_name, count)
                    del chest["materials"][mat_name]
                    chest_mats = list(chest["materials"].items())
                else:
                    inst = item[2]
                    game._add_equipment_instance(inst.name, inst)
                    chest["equipment_instances"].remove(inst)
                    chest_equips = [(i.name, i) for i in chest["equipment_instances"]]
                game.message = "已取出。"
            else:
                if item[0] == "material":
                    mat_name, count = item[1], item[2]
                    chest["materials"][mat_name] = chest["materials"].get(mat_name, 0) + count
                    game._remove_material(mat_name, count)
                    backpack_mats = list(game.inventory.get_materials().items())
                else:
                    inst = item[2]
                    chest["equipment_instances"].append(inst)
                    game.inventory.remove(inst.name)
                    backpack_equips = [(i.name, i) for i in game.inventory.get_equipment()]
                game.message = "已存入。"
            selected = 0

        game.draw()

    del win
    game.stdscr.touchwin()
    game.stdscr.refresh()

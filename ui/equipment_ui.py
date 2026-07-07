"""装备界面：查看装备槽位，选择候选装备，卸下/穿戴。"""
import curses


def equipment_menu(stdscr, game):
    slots = [("main_hand","主手"),("off_hand","副手"),("body","身体"),("accessory","饰品")]
    sel_slot = 0
    h, w = len(slots)+6, 50
    y, x = max(0,(curses.LINES-h)//2), max(0,(curses.COLS-w)//2)
    win = curses.newwin(h,w,y,x)
    win.keypad(True)
    status_msg = ""
    def redraw_eq():
        win.erase(); win.box()
        win.addstr(0,2," 装备菜单 ")
        win.addstr(1,2,"↑↓ 选槽位 Enter 换装 c 关闭")
        for i,(slot_id,slot_name) in enumerate(slots):
            equipped = game.equipment.get(slot_id, "（空）")
            line = f" {slot_name}: {equipped}"
            if equipped != "（空）":
                inst = game._get_equipment_instance(equipped)
                if inst:
                    if inst.affixes: line += " [" + "|".join(inst.affixes) + "]"
            attr = curses.A_REVERSE if i==sel_slot else curses.A_NORMAL
            win.addstr(3+i,2,line[:w-4],attr)
        if status_msg:
            win.addstr(h-2,2,status_msg[:w-4],curses.A_BOLD)
        win.refresh()
    while True:
        redraw_eq()
        key = win.getch()
        if key in (ord('c'), ord('q')): break
        elif key == curses.KEY_UP: sel_slot = (sel_slot-1) % len(slots); status_msg = ""
        elif key == curses.KEY_DOWN: sel_slot = (sel_slot+1) % len(slots); status_msg = ""
        elif key in (curses.KEY_ENTER, 10, 13):
            slot_id, slot_name = slots[sel_slot]
            candidates = []
            for inst in game.inventory.get_equipment():
                if inst and inst.slot == slot_id:
                    candidates.append(inst.name)
            if game.equipment.get(slot_id):
                candidates.insert(0, "__unequip__")
            if not candidates:
                status_msg = f"背包里没有能装备到{slot_name}的物品。按任意键继续。"
                redraw_eq(); win.getch(); status_msg = ""; continue
            sub_sel = 0; sub_h = len(candidates)+4; sub_w = 40
            sub_y = max(0, (curses.LINES-sub_h)//2); sub_x = max(0, (curses.COLS-sub_w)//2)
            sub = curses.newwin(sub_h, sub_w, sub_y, sub_x); sub.keypad(True)
            while True:
                sub.erase(); sub.box()
                sub.addstr(0,2,f" 选择{slot_name} 装备 ")
                for ci, cname in enumerate(candidates):
                    label = "（卸下）" if cname == "__unequip__" else cname
                    attr = curses.A_REVERSE if ci==sub_sel else curses.A_NORMAL
                    sub.addstr(2+ci,2,label[:sub_w-4],attr)
                sub.refresh()
                sk = sub.getch()
                if sk in (ord('c'), ord('q')): break
                elif sk == curses.KEY_UP: sub_sel = (sub_sel-1) % len(candidates)
                elif sk == curses.KEY_DOWN: sub_sel = (sub_sel+1) % len(candidates)
                elif sk in (curses.KEY_ENTER, 10, 13):
                    chosen = candidates[sub_sel]; old = game.equipment.get(slot_id)
                    if chosen == "__unequip__":
                        if old: game.equipment.pop(slot_id, None)
                        game.message = f"卸下了 {old}。"
                    else:
                        if old: game.equipment.pop(slot_id, None)
                        game.equipment[slot_id] = chosen
                        game.message = f"装备了 {chosen} 到{slot_name}。"
                    break
            del sub
    del win; game.stdscr.touchwin(); game.stdscr.refresh()

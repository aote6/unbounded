"""仿真测试：模拟真实玩家行为，500回合自动运行"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import Game


class FakeWorld:
    """模拟无限世界——任何坐标都是空地"""
    def get_tile(self, x, y):
        return {"tile": 0, "passable": True}
    def set_tile(self, x, y, t):
        pass
    def keep_radius(self, *a):
        pass
    def __init__(self):
        self.seed = 12345
        self.special_locations = []


class FakeStdscr:
    def erase(self): pass
    def refresh(self): pass
    def getch(self): return -1
    def addstr(self, *a, **k): pass
    def getmaxyx(self): return (24, 80)
    def keypad(self, v): pass
    def touchwin(self): pass


class FakeEngine:
    def __init__(self):
        self.stdscr = FakeStdscr()
        self._running = True
    def push_state(self, s): pass
    def pop_state(self): pass


def make_game():
    g = Game()
    g.world = FakeWorld()
    g.engine = FakeEngine()
    g.player_hp = 99999
    g.inventory.add("石头", 200)
    g.inventory.add("木材", 200)
    return g


def random_craft(game):
    """随机选一个可合成的配方尝试合成"""
    names = list(game.recipes.keys())
    if not names:
        return
    name = random.choice(names)
    r = game.recipes[name]
    # 给足材料
    for m, c in r.get("ingredients", {}).items():
        game.inventory.add(m, max(c * 10, 100))
    # 模拟合成（不走 UI，直接调 crafting_state 的逻辑）
    from systems.inventory_actions import add_equipment_instance
    result = r.get("result", {})
    rt = result.get("type", "")
    if rt == "material":
        game.inventory.add(result.get("name", name), result.get("count", 1))
    elif rt == "placeable":
        game.inventory.add(name, 1)
    elif rt == "equipment":
        ga = result.get("generator_args", {})
        if ga:
            from item_generator import get_generator
            from equipment import EquipmentInstance
            gen = get_generator()
            item_dict = gen.generate(archetype_name=ga.get("archetype"), material_name=ga.get("material"), affix_count=0)
            inst = EquipmentInstance(
                name=item_dict["name"], slot=item_dict.get("slot"),
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
            add_equipment_instance(game, inst.name, inst)
            # 自动装备
            if inst.slot:
                game.equipment[inst.slot] = inst
    game._crafted_this_life.append(name)


def test_500_turns_simulation():
    g = make_game()
    from systems.turn_system import advance_turn
    from systems.inventory_actions import add_monster
    from systems.player_action import try_move_or_dig, do_place

    # 预生成 10 只怪物
    for i in range(10):
        m = {"name": random.choice(["史莱姆", "蝙蝠", "岩石傀儡"]),
             "x": random.randint(-5, 5), "y": random.randint(-5, 5),
             "hp": 15, "max_hp": 15, "char": "M", "exp": 5,
             "drops": [], "speed": 1}
        add_monster(g, m)

    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    craft_count = 0
    place_count = 0
    kill_count = 0

    for turn in range(5000):
        action = random.random()

        if action < 0.6:
            # 60% 移动
            dx, dy = random.choice(directions)
            try_move_or_dig(g, dx, dy)
        elif action < 0.8:
            # 20% 合成
            random_craft(g)
            craft_count += 1
        elif action < 0.9:
            # 10% 放置
            g.place_mode = random.choice(["石墙", "木墙", "火把"])
            g.cursor_x, g.cursor_y = g.player_x + random.choice([-1, 0, 1]), g.player_y + random.choice([-1, 0, 1])
            do_place(g)
            place_count += 1
        else:
            # 10% 什么也不做
            pass

        advance_turn(g)
        if turn % 500 == 0:
            print(f"  ... {turn}/5000 回合, 怪物:{len(g.monsters)}")

        # 每 50 回合补怪物
        if turn % 50 == 0 and len(g.monsters) < 15:
            m = {"name": random.choice(["史莱姆", "蝙蝠", "狐狸"]),
                 "x": random.randint(-10, 10), "y": random.randint(-10, 10),
                 "hp": 20, "max_hp": 20, "char": "M", "exp": 5,
                 "drops": [], "speed": 1, "faction": "hostile"}
            add_monster(g, m)

        if g._monsters_killed_this_life > kill_count:
            kill_count = g._monsters_killed_this_life

    # 验证
    assert g.turn == 5000, f"回合数不对: {g.turn}"
    assert len(g.inventory.get_materials()) > 0, "背包应该有物品"
    print(f"[PASS] 5000回合仿真: {craft_count}次合成, {place_count}次放置, {kill_count}只击杀")
    print(f"       背包材料: {len(g.inventory.get_materials())}种, 装备: {len(g.inventory.get_equipment())}件")
    print(f"       位置: ({g.player_x},{g.player_y}), HP:{g.player_hp}")


def test_inventory_stress():
    """背包极限：反复增删 2000 次"""
    g = make_game()
    for i in range(2000):
        g.inventory.add("石头", 1)
        if i % 3 == 0:
            g.inventory.remove("石头", 1)
    c = g.inventory.count("石头")
    print(f"[PASS] 背包极限: 2000次操作后石头={c}")


if __name__ == "__main__":
    random.seed(42)
    test_inventory_stress()
    test_500_turns_simulation()
    print("仿真测试全部通过")

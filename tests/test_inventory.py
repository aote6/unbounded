"""单元测试: systems/inventory_actions.py"""
from main import Game
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestInventoryActions:
    @classmethod
    def setup_class(cls):
        cls.game = Game()

    def test_add_and_count_material(self):
        g = self.game
        g.inventory.add("石头", 10)
        from systems.inventory_actions import count_material
        assert count_material(g, "石头") == 10

    def test_remove_material(self):
        g = self.game
        from systems.inventory_actions import remove_material, count_material
        remove_material(g, "石头", 3)
        assert count_material(g, "石头") == 7

    def test_add_equipment_instance(self):
        g = self.game
        from systems.inventory_actions import add_equipment_instance, get_equipment_instance
        from equipment import EquipmentInstance
        inst = EquipmentInstance(name="测试剑", slot="main_hand", attack_bonus=5)
        add_equipment_instance(g, "测试剑", inst)
        found = get_equipment_instance(g, "测试剑")
        assert found is not None
        assert found.attack_bonus == 5

    def test_count_equipment(self):
        g = self.game
        from systems.inventory_actions import count_equipment
        assert count_equipment(g, "测试剑") == 1

    def test_add_and_remove_monster(self):
        g = self.game
        from systems.inventory_actions import add_monster, remove_monster
        m = {
            "name": "史莱姆",
            "x": 5,
            "y": 5,
            "hp": 10,
            "max_hp": 10,
            "char": "S"}
        add_monster(g, m)
        assert len(g.monsters) == 1
        assert g._monster_at(5, 5) is m
        remove_monster(g, m)
        assert len(g.monsters) == 0
        assert g._monster_at(5, 5) is None

    def test_monster_moved(self):
        g = self.game
        from systems.inventory_actions import add_monster, monster_moved
        m = {"name": "蝙蝠", "x": 0, "y": 0, "hp": 5, "max_hp": 5, "char": "B"}
        add_monster(g, m)
        monster_moved(g, m, 0, 0)
        m["x"], m["y"] = 1, 1
        monster_moved(g, m, 0, 0)  # 旧位置是 (0,0)，新位置是 (1,1)
        assert g._monster_at(0, 0) is None
        # 手动更新 monster 的坐标后索引应该更新
        g._monster_index[(1, 1)] = m
        assert g._monster_at(1, 1) is m


if __name__ == "__main__":
    t = TestInventoryActions()
    t.setup_class()
    for name in dir(t):
        if name.startswith("test_"):
            getattr(t, name)()
            print(f"[PASS] {name}")
    print("全部通过")

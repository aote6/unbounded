"""单元测试: systems/combat_system.py"""
from main import Game
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


class FakeWorld:
    def get_tile(self, x, y):
        return {"tile": 0}

    def set_tile(self, x, y, t):
        pass


def test_kill_monster_basic():
    g = Game()
    g.world = FakeWorld()
    from systems.entity.monster_index import add_monster
    from systems.combat.combat_system import kill_monster

    m = {"name": "史莱姆", "x": 3, "y": 3, "hp": 10, "max_hp": 10, "char": "S",
         "exp": 5, "drops": [], "corpse_tile": None}
    add_monster(g, m)
    assert len(g.monsters) == 1

    kill_monster(g, m, cause="attack")
    assert len(g.monsters) == 0
    assert g._monsters_killed_this_life == 1


def test_collect_attack_effects_empty():
    g = Game()
    from systems.combat.combat_system import collect_attack_effects
    effects = collect_attack_effects(g)
    assert effects == []


if __name__ == "__main__":
    test_kill_monster_basic()
    print("[PASS] test_kill_monster_basic")
    test_collect_attack_effects_empty()
    print("[PASS] test_collect_attack_effects_empty")
    print("全部通过")

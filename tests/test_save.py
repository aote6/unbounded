"""单元测试: systems/save_system.py"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import Game

def test_build_save_data():
    g = Game()
    from systems.save_system import build_save_data
    player, world = build_save_data(g)
    assert "player_x" in player
    assert "player_hp" in player
    assert player["player_hp"] == 100
    print("[PASS] build_save_data 结构正确")

def test_save_load_roundtrip():
    g = Game()
    from systems.save_system import build_save_data, apply_load_data

    g.player_x = 42
    g.player_y = 24
    g.player_hp = 80
    g.inventory.add("石头", 5)

    player, world = build_save_data(g)
    data = {"player": player, "world": world}

    g2 = Game()
    apply_load_data(g2, data)

    assert g2.player_x == 42
    assert g2.player_y == 24
    assert g2.player_hp == 80
    print("[PASS] save/load roundtrip 数据一致")

if __name__ == "__main__":
    test_build_save_data()
    test_save_load_roundtrip()
    print("全部通过")

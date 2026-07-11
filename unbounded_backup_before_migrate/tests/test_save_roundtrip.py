"""存档往返测试：new_game → save → load → 断言关键字段一致"""
import sys
import json
import tempfile
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_save_roundtrip():
    """核心：确保存档保存后再加载，关键字段完全一致"""
    from main import Game
    from systems.save_manager import new_game, save_game, load_game

    game = Game()
    new_game(game)
    # 记录关键字段
    before = {
        "x": game.player_x, "y": game.player_y,
        "hp": game.player_hp, "max_hp": game.player_max_hp,
        "turn": game.turn, "skills": dict(game.skills),
    }
    save_game(game)
    
    game2 = Game()
    load_result = load_game(game2)
    assert load_result is True, "读档失败"
    
    after = {
        "x": game2.player_x, "y": game2.player_y,
        "hp": game2.player_hp, "max_hp": game2.player_max_hp,
        "turn": game2.turn, "skills": dict(game2.skills),
    }
    assert before == after, f"存档不一致: {before} != {after}"
    print("✅ test_save_roundtrip 通过")


def test_world_determinism():
    """世界生成确定性：同种子同坐标 tile 必须一致"""
    from world_gen import generate_world
    
    w1 = generate_world(seed=42, decorate=False)
    w2 = generate_world(seed=42, decorate=False)
    
    test_coords = [(0,0), (100,50), (-30,-20), (16,16), (200,-100)]
    for x, y in test_coords:
        t1 = w1.get_tile(x, y)["tile"]
        t2 = w2.get_tile(x, y)["tile"]
        assert t1 == t2, f"({x},{y}): {t1} != {t2}"
    print("✅ test_world_determinism 通过")


if __name__ == "__main__":
    test_save_roundtrip()
    test_world_determinism()

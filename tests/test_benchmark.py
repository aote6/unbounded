"""性能基准测试"""
import time
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def bench_world_generation():
    from world_gen import generate_world
    start = time.perf_counter()
    w = generate_world(seed=42, decorate=True)
    for x in range(-160, 161, 32):
        for y in range(-160, 161, 32):
            w.get_tile(x, y)
    elapsed = time.perf_counter() - start
    print(f"世界生成(100 chunk): {elapsed:.3f}s")
    assert elapsed < 20.0


def bench_turn_advance():
    from main import Game
    from systems.core.save_manager import new_game
    game = Game()
    new_game(game)
    # 替换 show_death_screen 为无害函数
    import systems.gameplay.legacy_system as ls
    ls.show_death_screen = lambda g: None
    from systems.gameplay.turn_system import advance_turn
    start = time.perf_counter()
    for _ in range(1000):
        advance_turn(game)
        if game.player_hp <= 0:
            game.player_hp = game.player_max_hp
    elapsed = time.perf_counter() - start
    print(f"1000回合推进: {elapsed:.3f}s")
    assert elapsed < 30.0


def bench_save_load():
    from main import Game
    from systems.core.save_manager import new_game, save_game, load_game
    game = Game()
    new_game(game)
    start = time.perf_counter()
    save_game(game)
    elapsed_save = time.perf_counter() - start
    start = time.perf_counter()
    game2 = Game()
    load_game(game2)
    elapsed_load = time.perf_counter() - start
    print(f"存档写入: {elapsed_save:.3f}s, 读档: {elapsed_load:.3f}s")
    assert elapsed_save < 5.0
    assert elapsed_load < 8.0


if __name__ == "__main__":
    print("=== 性能基准测试 ===")
    bench_world_generation()
    bench_turn_advance()
    bench_save_load()
    print("=== 全部通过 ===")

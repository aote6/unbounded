def patch_file(path, replacements):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for old, new in replacements:
        if old not in content:
            print(f"[跳过] {path}: 片段未匹配")
            continue
        content = content.replace(old, new, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[完成] {path}")

repl = [(
'''        "seed": game.world.seed if hasattr(game.world, 'seed') else None,
    }''',
'''        "seed": game.world.seed if hasattr(game.world, 'seed') else None,
        "found_specials": [list(p) for p in getattr(game, '_found_specials', set())],
    }'''
)]

patch_file("systems/save_system.py", repl)
print("P0-4 完成")

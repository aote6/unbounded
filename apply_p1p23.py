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
'''    game.spawn_counter = data.get("spawn_counter", {"count": 5})
    game.modified_tiles = {}''',
'''    game.spawn_counter = data.get("spawn_counter", {"count": 5})
    game.modified_tiles = {}
    _found_raw = data.get("found_specials", [])
    game._found_specials = {
        tuple(item) if isinstance(item, list) and len(item) == 2 else item
        for item in _found_raw
    }'''
)]

patch_file("systems/save_system.py", repl)
print("P1-2/P1-3 完成")

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
'''    if monster_name:
        monster_data = load_monsters()
        monster = monster_data.get(monster_name, {})''',
'''    if monster_name:
        from main import StaticDataRegistry
        monster_data = StaticDataRegistry.instance().monster_data or load_monsters()
        monster = monster_data.get(monster_name, {})'''
)]

patch_file("monsters.py", repl)
print("P1-1 完成")

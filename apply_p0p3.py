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
'''        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(delta, f, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Chunk 保存失败 ({self.cx},{self.cy}): {e}", exc_info=True)''',
'''        import time as _time
        saved = False
        last_error = None
        for attempt in range(3):
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(delta, f, ensure_ascii=False)
                saved = True
                break
            except Exception as e:
                last_error = e
                if attempt < 2:
                    _time.sleep(0.1 * (2 ** attempt))
        if not saved:
            logger.error(
                f"Chunk 保存失败 ({self.cx},{self.cy})，重试3次均失败: {last_error}",
                exc_info=True,
            )
            # 写入失败队列，下次启动时尝试恢复
            try:
                with open("SAVE_FAILED.txt", "a", encoding="utf-8") as _sf:
                    _sf.write(f"chunk_{self.cx}_{self.cy}.json\\n")
            except Exception:
                pass'''
)]

patch_file("world_gen.py", repl)
print("P0-3 完成")

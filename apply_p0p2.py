import ast

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

# main.py: _setup_logging 替换为 RotatingFileHandler
main_repl = [(
'''def _setup_logging():
    logging.basicConfig(
        filename=str(BASE_DIR / "unbounded_debug.log"),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        encoding="utf-8",
    )''',
'''def _setup_logging():
    from logging.handlers import RotatingFileHandler
    log_path = BASE_DIR / "unbounded_debug.log"
    handler = RotatingFileHandler(
        str(log_path), maxBytes=5 * 1024 * 1024, backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    ))
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)'''
)]

# state_machine.py: 崩溃日志加轮转
sm_repl = [(
'''                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                with open(f"crash_{ts}.log", "w", encoding="utf-8") as f:''',
'''                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                # 保留最近 10 个崩溃日志，超出自动删除
                import glob as _glob
                _existing = sorted(_glob.glob("crash_*.log"))
                for _old in _existing[:-9]:
                    try:
                        __import__('os').remove(_old)
                    except OSError:
                        pass
                with open(f"crash_{ts}.log", "w", encoding="utf-8") as f:'''
)]

patch_file("main.py", main_repl)
patch_file("core/state_machine.py", sm_repl)
print("P0-2 完成")

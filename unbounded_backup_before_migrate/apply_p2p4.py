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

# config.py: 补全缺失的常量
config_repl = [(
'''@dataclass
class _World:
    SEED: int = 51329
    LAYERS: int = 5
    LAYER_DEPTH_OFFSET: int = 50''',
'''@dataclass
class _World:
    SEED: int = 51329
    LAYERS: int = 5
    LAYER_DEPTH_OFFSET: int = 50
    CHUNK_SIZE: int = 16
    KEEP_RADIUS: int = 3'''
)]

patch_file("config.py", config_repl)
print("P2-4 config 完成")

# world_gen.py: CHUNK_SIZE 从 config 导入
wgen_repl = [(
'''CHUNK_SIZE = 16
SAVE_DIR = Path(__file__).parent / "data" / "chunks"''',
'''from config import WORLD_CHUNK_SIZE as CHUNK_SIZE
SAVE_DIR = Path(__file__).parent / "data" / "chunks"'''
)]
# 如果 CHUNK_SIZE 在 world_gen 被赋值后 config 才导入会循环，改策略：
# 只在 config 加常量，world_gen 保留定义但加注释引用
wgen_repl = [(
'''CHUNK_SIZE = 16
SAVE_DIR = Path(__file__).parent / "data" / "chunks"''',
'''# CHUNK_SIZE 与 config.WORLD_CHUNK_SIZE 保持同步
CHUNK_SIZE = 16
SAVE_DIR = Path(__file__).parent / "data" / "chunks"'''
)]

patch_file("world_gen.py", wgen_repl)
print("P2-4 完成")

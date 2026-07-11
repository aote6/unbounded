#!/usr/bin/env python3
import os
import re
import shutil
from pathlib import Path

# --- 配置定义 ---
# 5个领域子包及其对应的模块映射关系（已补全遗漏的 age_system 和 interaction）
DOMAIN_MAP = {
    "core": ["event_bus", "keybind", "save_system", "save_manager"],
    "world": ["climate", "ecology", "noise_engine", "weather_system", "civilization", "room_system", "feature_engine", "scent_map"],
    "entity": ["entity", "entity_validator", "tag_system", "monster_index", "buff_system", "status_system"],
    "gameplay": ["player_action", "inventory_actions", "tile_interaction", "skill_system", "goal_system", "legacy_system", "turn_system", "time_system", "age_system", "interaction"],
    "combat": ["combat_system", "monster_ai"]
}

# 逆向映射：模块名 -> 子包名
MODULE_TO_DOMAIN = {}
for domain, modules in DOMAIN_MAP.items():
    for mod in modules:
        MODULE_TO_DOMAIN[mod] = domain

PROJECT_ROOT = Path(".").resolve()
SYSTEMS_DIR = PROJECT_ROOT / "systems"
BACKUP_DIR = PROJECT_ROOT / "unbounded_backup_before_migrate"

def setup_backup():
    """在脚本运行前对整个项目进行物理备份"""
    print("=== [1/5] 正在创建项目备份 ===")
    if BACKUP_DIR.exists():
        print(f"检测到历史备份目录 {BACKUP_DIR}，正在清理...")
        shutil.rmtree(BACKUP_DIR)
    
    # 排除备份目录自身
    def ignore_patterns(path, names):
        if Path(path).resolve() == BACKUP_DIR:
            return names
        return [n for n in names if n in [BACKUP_DIR.name, ".git", "__pycache__"]]

    shutil.copytree(PROJECT_ROOT, BACKUP_DIR, ignore=ignore_patterns)
    print(f"项目已成功备份至: {BACKUP_DIR}\n")

def move_modules_and_init():
    """创建子包并移动对应的物理文件（不处理 systems/__init__.py）"""
    print("=== [2/5] 正在创建子包并移动文件 ===")
    moved_files = []
    
    for domain, modules in DOMAIN_MAP.items():
        domain_path = SYSTEMS_DIR / domain
        domain_path.mkdir(exist_ok=True)
        
        # 确保新子包下存在 __init__.py
        init_file = domain_path / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            
        for mod in modules:
            src_file = SYSTEMS_DIR / f"{mod}.py"
            dest_file = domain_path / f"{mod}.py"
            if src_file.exists():
                shutil.move(str(src_file), str(dest_file))
                moved_files.append((mod, f"systems/{domain}/{mod}.py"))
            else:
                # 兼容处理：如果文件已经存在于目标位置，也算成功
                if dest_file.exists():
                    moved_files.append((mod, f"systems/{domain}/{mod}.py (已存在)"))
                else:
                    print(f"⚠️ 警告: 未找到预期模块文件 {src_file.name}")
                    
    print(f"成功移动了 {len(moved_files)} 个模块文件。\n")
    return moved_files

def build_regex_patterns():
    """构建用于精准匹配和替换 import 语句的正则表达式"""
    all_modules = list(MODULE_TO_DOMAIN.keys())
    if not all_modules:
        return [], []
        
    # 按照长度降序排列，防止短文件名被作为前缀错误匹配
    all_modules.sort(key=len, reverse=True)
    modules_alt = "|".join(all_modules)

    # 模式 1: from systems.xxx import ... 或 from systems.xxx.yyy import ...
    from_pattern = re.compile(
        rf"(\bfrom\s+systems\.)({modules_alt})(\b.*)"
    )

    # 模式 2: import systems.xxx 或 import systems.xxx as yyy
    import_pattern = re.compile(
        rf"(\bimport\s+systems\.)({modules_alt})(\b.*)"
    )

    return from_pattern, import_pattern

def update_imports():
    """全局扫描所有 .py 文件，重构导入路径"""
    print("=== [3/5] 正在全局扫描并更新 Import 导入语句 ===")
    from_pattern, import_pattern = build_regex_patterns()
    
    changed_records = {}
    
    # 遍历整个项目
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # 排除备份目录、git和pycache
        if any(p in Path(root).parts for p in [BACKUP_DIR.name, ".git", "__pycache__"]):
            continue
            
        for file in files:
            if not file.endswith(".py"):
                continue
                
            file_path = Path(root) / file
            relative_path = file_path.relative_to(PROJECT_ROOT)
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            modified_content = content
            file_changed = False
            file_changes_log = []

            # 1. 处理 from systems.xxx 类型的导入
            def from_repl(match):
                nonlocal file_changed
                prefix = match.group(1)
                mod_name = match.group(2)
                suffix = match.group(3)
                domain = MODULE_TO_DOMAIN[mod_name]
                new_statement = f"from systems.{domain}.{mod_name}{suffix}"
                file_changed = True
                file_changes_log.append(f"  [-] from systems.{mod_name} -> from systems.{domain}.{mod_name}")
                return new_statement

            modified_content = from_pattern.sub(from_repl, modified_content)

            # 2. 处理 import systems.xxx 类型的导入
            def import_repl(match):
                nonlocal file_changed
                prefix = match.group(1)
                mod_name = match.group(2)
                suffix = match.group(3)
                domain = MODULE_TO_DOMAIN[mod_name]
                new_statement = f"import systems.{domain}.{mod_name}{suffix}"
                file_changed = True
                file_changes_log.append(f"  [-] import systems.{mod_name} -> import systems.{domain}.{mod_name}")
                return new_statement

            modified_content = import_pattern.sub(import_repl, modified_content)

            # 如果内容发生变更，写回文件并记录
            if file_changed:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)
                changed_records[str(relative_path)] = file_changes_log

    print(f"代码重构完成，共修改了 {len(changed_records)} 个文件的代码。\n")
    return changed_records

def clean_empty_old_folders():
    """清理原 systems/ 根目录下残留的旧 __pycache__（如有）"""
    print("=== [4/5] 正在清理系统的旧缓存文件 ===")
    old_pycache = SYSTEMS_DIR / "__pycache__"
    if old_pycache.exists():
        shutil.rmtree(old_pycache)
        print("已清理原 systems/__pycache__")
    print("清理完毕。\n")

def print_summary(moved_files, changed_records):
    """打印最终的变更清单报告"""
    print("=== [5/5] 迁移任务完成！最终变更清单报告 ===")
    print("-" * 60)
    print("[物理文件移动清单]:")
    for mod, target in moved_files:
        print(f" 📦 模块 [{mod}.py] -> 已移至 -> {target}")
        
    print("\n[代码导入语句更新清单]:")
    if not changed_records:
        print("  (无代码变更或未匹配到受影响的 systems.xxx 导入语句)")
    for file_path, logs in changed_records.items():
        print(f" 📝 文件: {file_path}")
        for log in logs:
            print(log)
    print("-" * 60)
    print(f"💡 提示: 如果运行出现非预期错误，可直接通过备份目录恢复: {BACKUP_DIR.name}")

if __name__ == "__main__":
    if not SYSTEMS_DIR.exists() or not (PROJECT_ROOT / "main.py").exists():
        print("❌ 错误: 请确保在 unbounded 项目的根目录下执行此脚本（当前目录下未检测到 main.py 或 systems/ 目录）。")
        exit(1)
        
    setup_backup()
    moved = move_modules_and_init()
    changed = update_imports()
    clean_empty_old_folders()
    print_summary(moved, changed)


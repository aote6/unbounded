# Unbounded

> 终端俯视角 Roguelike 沙盒游戏。无尽世界，向下挖掘，与怪物战斗，锻造装备。

## 特性

- 🌍 **无限世界** — Perlin 噪声生成，x/y 轴无限延伸
- 👾 **怪物 AI** — 追逐、逃跑、分裂、瞬移、特殊行为
- ⚔️ **装备系统** — 原型 × 材质 × 词缀三层组装，生成千变万化的装备
- 🔨 **合成建造** — 采集材料，合成工具武器，放置墙壁火把
- 🌙 **昼夜循环** — 影响视野和怪物行为
- 📈 **技能升级** — 挖掘、战斗、防御三大技能随使用成长

## 快速开始

```bash
git clone https://github.com/aote6/unbounded.git
cd unbounded
python3 main.py
```

## 操作说明

| 按键 | 功能 |
|------|------|
| `hjkl` / 方向键 | 移动/攻击 |
| `d` | 挖掘方块 |
| `c` | 合成菜单 |
| `e` | 装备菜单 |
| `x` | 查看模式 |
| `.` | 重复上次建造 |
| `Enter` | 放置建造 |
| `S` | 存档 |
| `L` | 读档 |
| `q` | 退出 |

## 依赖

- Python 3.6+
- curses (内置)
- 无第三方依赖

## 存档位置

- `data/save.json` — 玩家状态
- `data/chunks/` — 地形修改数据

## 开发环境 (Termux 手机端)

### 已安装工具
| 工具 | 用途 | 命令示例 |
|------|------|---------|
| micro | 代码编辑器（语法高亮、行号、跳转） | `micro +200 main.py` |
| ripgrep (rg) | 超快代码搜索 | `rg -n "关键词" *.py` |
| fd | 超快文件查找 | `fd chunk_` |

### 项目路径
`~/unbounded`

### 常用操作
```bash
cd ~/unbounded
rg -n "搜索内容" *.py          # 搜索代码
micro +行号 文件名.py           # 打开文件跳转到指定行
python main.py                  # 运行游戏
python3 -c "import main"       # 语法检查
cat >> ~/unbounded/README.md << 'EOF'

## 开发环境 (Termux 手机端)

### 已安装工具
| 工具 | 用途 | 命令示例 |
|------|------|---------|
| micro | 代码编辑器（语法高亮、行号、跳转） | `micro +200 main.py` |
| ripgrep (rg) | 超快代码搜索 | `rg -n "关键词" *.py` |
| fd | 超快文件查找 | `fd chunk_` |

### 项目路径
`~/unbounded`

### 常用操作
```bash
cd ~/unbounded
rg -n "搜索内容" *.py          # 搜索代码
micro +行号 文件名.py           # 打开文件跳转到指定行
python main.py                  # 运行游戏
python3 -c "import main"       # 语法检查

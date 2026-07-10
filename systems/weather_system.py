"""天气系统 — 事件驱动，不持续模拟。

设计原则：
- 不是每回合计算全球天气
- 状态改变 → 触发事件 → 世界响应
- 基于 Seed 确定性选择天气类型
- 天气影响生物生成密度（通过 modifier 传递）
"""

import json
import random
from pathlib import Path
from systems.noise_engine import _hash_uniform
from systems.climate import get_biome

BASE_DIR = Path(__file__).parent.parent
WEATHER_FILE = BASE_DIR / "data" / "weather.json"

_WEATHER_CACHE = None
_ACTIVE_WEATHER: dict = {}  # {(cx,cy): {"type":..., "remaining":..., "modifiers":...}}


def _load_weather():
    global _WEATHER_CACHE
    if _WEATHER_CACHE is not None:
        return _WEATHER_CACHE
    if WEATHER_FILE.exists():
        with open(WEATHER_FILE, "r", encoding="utf-8") as f:
            _WEATHER_CACHE = json.load(f)
    else:
        _WEATHER_CACHE = []
    return _WEATHER_CACHE


def get_weather_at(x: int, y: int, seed: int = 12345, turn: int = 0) -> dict:
    """获取 (x,y) 位置的当前天气。
    使用大网格（同气候区），天气变化由 turn 驱动。
    返回 {"id": str, "name": str, "modifiers": dict}"""
    CELL = 200  # 与气候区大小一致
    cx, cy = x // CELL, y // CELL
    key = (cx, cy, seed)
    
    # 检查是否需要切换天气
    if key in _ACTIVE_WEATHER:
        active = _ACTIVE_WEATHER[key]
        if active["remaining"] > 0 and active["change_turn"] > turn:
            active["remaining"] -= 1
            return _pick_weather_info(active["type"])
    
    # 确定性选择天气
    weathers = _load_weather()
    if not weathers:
        return _pick_weather_info("clear")
    
    biome = get_biome(x, y, seed)
    rng = random.Random(seed + cx * 49999 + cy * 87719 + turn // 100)
    
    # 筛选该群系可用的天气
    candidates = [w for w in weathers if biome in w.get("biomes", [])]
    if not candidates:
        candidates = [w for w in weathers if w["id"] == "clear"]
    
    chosen = rng.choices(candidates, weights=[1.0/w.get("rarity", 0.5) for w in candidates], k=1)[0]
    duration = rng.randint(*chosen["duration"])
    
    _ACTIVE_WEATHER[key] = {
        "type": chosen["id"],
        "remaining": duration,
        "change_turn": turn + duration,
    }
    
    return _pick_weather_info(chosen["id"])


def _pick_weather_info(weather_id: str) -> dict:
    """从缓存查找天气的显示信息"""
    weathers = _load_weather()
    for w in weathers:
        if w["id"] == weather_id:
            return {
                "id": w["id"],
                "name": w["name"],
                "message": w["effects"]["message"],
                "modifiers": w.get("spawn_modifiers", {}),
            }
    return {"id": "clear", "name": "晴朗", "message": "", "modifiers": {}}


def get_weather_modifiers(x: int, y: int, seed: int = 12345, turn: int = 0) -> dict:
    """获取天气对生成密度的修正系数。"""
    weather = get_weather_at(x, y, seed, turn)
    return weather.get("modifiers", {})


def clear_weather_cache():
    global _WEATHER_CACHE
    _WEATHER_CACHE = None
    _ACTIVE_WEATHER.clear()

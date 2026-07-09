"""年龄系统——基于游戏天数，永不重置。"""
import json, os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
BIRTH_FILE = BASE_DIR / "data" / "birth.json"
DAYS_PER_AGE = 30
TURNS_PER_DAY = 1800


def _load():
    try:
        if BIRTH_FILE.exists() and os.path.getsize(BIRTH_FILE) > 0:
            with open(BIRTH_FILE) as f:
                return json.load(f)
    except:
        pass
    return {"total_turns": 0}


def _save(data):
    BIRTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BIRTH_FILE, "w") as f:
        json.dump(data, f)


def add_turns(turns):
    data = _load()
    data["total_turns"] = data.get("total_turns", 0) + turns
    _save(data)


def get_age():
    data = _load()
    days = data.get("total_turns", 0) // TURNS_PER_DAY
    return max(0, days // DAYS_PER_AGE)


def get_age_bonus():
    age = get_age()
    return {
        "evasion": min(30, age * 3),
        "craft": min(20, age * 2),
        "discovery": min(15, age),
        "wisdom": min(50, age * 5),
    }

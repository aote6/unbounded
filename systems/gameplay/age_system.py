"""年龄系统——基于游戏天数，永不重置。"""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
BIRTH_FILE = BASE_DIR / "data" / "birth.json"
DAYS_PER_AGE = 30
TURNS_PER_DAY = 1800


def _load():
    """Load the birth and turn data from the JSON storage file.

    Returns:
        dict: A dictionary containing total game turns.
    """
    try:
        if BIRTH_FILE.exists() and os.path.getsize(BIRTH_FILE) > 0:
            with open(BIRTH_FILE) as f:
                return json.load(f)
    except BaseException:
        pass
    return {"total_turns": 0}


def _save(data):
    """Save the turn data back to the JSON storage file.

    Args:
        data: A dictionary containing the updated game turn data.
    """
    BIRTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(BIRTH_FILE, "w") as f:
        json.dump(data, f)


def add_turns(turns):
    """Accumulate and save game turns to progress the absolute time.

    Args:
        turns: The number of elapsed game turns to add.
    """
    data = _load()
    data["total_turns"] = data.get("total_turns", 0) + turns
    _save(data)


def get_age():
    """Calculate the current persistent age based on total elapsed turns.

    Returns:
        int: The calculated age value.
    """
    data = _load()
    days = data.get("total_turns", 0) // TURNS_PER_DAY
    return max(0, days // DAYS_PER_AGE)


def get_age_bonus():
    """Get the specific attribute bonuses scaled and capped by the current age.

    Returns:
        dict: Bonuses for evasion, craft, discovery, and wisdom.
    """
    age = get_age()
    return {
        "evasion": min(30, age * 3),
        "craft": min(20, age * 2),
        "discovery": min(15, age),
        "wisdom": min(50, age * 5),
    }

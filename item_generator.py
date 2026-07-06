""" item_generator.py  三层物品组装引擎。原型 × 材质 × 词缀 → 具体物品。"""
import json, random
from pathlib import Path

BASE_DIR = Path(__file__).parent
ARCHETYPES_FILE = BASE_DIR / "data" / "archetypes.json"
MATERIALS_FILE = BASE_DIR / "data" / "materials.json"
AFFIXES_FILE = BASE_DIR / "data" / "affixes.json"

RARITY_WEIGHTS = {"common": 10, "rare": 3, "legendary": 1}


def load_json(path):
    if not path.exists():
        print(f"[generator] 文件不存在: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[generator] JSON 解析失败: {path} - {e}")
        return {}


class ItemGenerator:
    def __init__(self):
        self.archetypes = load_json(ARCHETYPES_FILE)
        self.materials = load_json(MATERIALS_FILE)
        self.affixes = load_json(AFFIXES_FILE)
        self._affix_pool = self._build_affix_pool()

    def _build_affix_pool(self):
        """按稀有度加权展开词缀池"""
        pool = []
        for name, data in self.affixes.items():
            weight = RARITY_WEIGHTS.get(data.get("rarity", "common"), 10)
            pool.extend([name] * weight)
        return pool

    def generate(self, archetype_name=None, material_name=None, affix_count=None):
        """
        生成一件物品。
        不指定参数则随机生成。
        """
        # 选原型
        if archetype_name and archetype_name in self.archetypes:
            arch = dict(self.archetypes[archetype_name])
        else:
            arch_name = random.choice(list(self.archetypes.keys()))
            arch = dict(self.archetypes[arch_name])
        arch["name"] = archetype_name or arch.get("name", "未知")

        # 选材质
        if material_name and material_name in self.materials:
            mat = dict(self.materials[material_name])
        else:
            mat_name = random.choice(list(self.materials.keys()))
            mat = dict(self.materials[mat_name])
        mat["name"] = material_name or mat.get("name", "未知")

        # 选词缀（0-3条，不重复）
        if affix_count is None:
            affix_count = random.choices([0, 1, 2, 3], weights=[2, 4, 3, 1])[0]
        selected_affixes = []
        available = list(self.affixes.keys())
        for _ in range(affix_count):
            if not available:
                break
            # 按稀有度加权选
            weights = [RARITY_WEIGHTS.get(self.affixes[a].get("rarity", "common"), 10) for a in available]
            chosen = random.choices(available, weights=weights, k=1)[0]
            selected_affixes.append(chosen)
            available.remove(chosen)

        # 组装最终物品
        item = self._assemble(arch, mat, selected_affixes)
        return item

    def _assemble(self, arch, mat, affix_names):
        """根据原型、材质、词缀计算最终数值"""
        item = {
            "name": f"{mat['name']}{arch.get('name', '')}",
            "archetype": arch.get("name", "未知"),
            "material": mat.get("name", "未知"),
            "slot": arch.get("slot"),
            "desc": arch.get("desc", ""),
            "affixes": affix_names,
            "tags": list(mat.get("tags", [])),
            "consumable": arch.get("consumable", False),
            "weight": mat.get("weight_per_unit", 3),
            "on_attack": [],
        }

        # 攻击力
        base_min = arch.get("base_damage_min", 0)
        base_max = arch.get("base_damage_max", 0)
        if base_max > 0:
            dmg_mult = mat.get("damage_mult", 1.0)
            item["damage_min"] = max(1, int(base_min * dmg_mult))
            item["damage_max"] = max(1, int(base_max * dmg_mult))
            item["attack_bonus"] = 0

        # 防御
        base_def = arch.get("base_defense", 0)
        if base_def > 0:
            def_mult = mat.get("defense_mult", 1.0)
            item["defense_bonus"] = max(1, int(base_def * def_mult))

        # 工具力
        base_tool = arch.get("base_tool_power", 0)
        if base_tool > 0:
            tool_mult = mat.get("tool_mult", 1.0)
            item["tool_bonus"] = max(1, int(base_tool * tool_mult))

        # 耐久
        base_dur = arch.get("base_durability", 50)
        dur_mult = mat.get("durability_mult", 1.0)
        item["durability"] = max(10, int(base_dur * dur_mult))
        item["durability_max"] = item["durability"]

        # 命中
        item["hit_bonus"] = arch.get("hit_bonus", 0)

        # 应用词缀
        for affix_name in affix_names:
            affix = self.affixes.get(affix_name, {})
            # 数值修正
            if "damage_bonus" in affix:
                item["attack_bonus"] = item.get("attack_bonus", 0) + affix["damage_bonus"]
            if "damage_penalty" in affix:
                item["attack_bonus"] = item.get("attack_bonus", 0) + affix["damage_penalty"]
            if "defense_bonus" in affix and "defense_bonus" in item:
                item["defense_bonus"] += affix["defense_bonus"]
            if "defense_penalty" in affix and "defense_bonus" in item:
                item["defense_bonus"] = max(0, item["defense_bonus"] + affix["defense_penalty"])
            if "durability_bonus" in affix:
                item["durability"] += affix["durability_bonus"]
                item["durability_max"] = item["durability"]
            if "durability_penalty" in affix:
                item["durability"] = max(5, item["durability"] + affix["durability_penalty"])
                item["durability_max"] = item["durability"]
            if "hit_bonus" in affix:
                item["hit_bonus"] = item.get("hit_bonus", 0) + affix["hit_bonus"]
            if "hit_penalty" in affix:
                item["hit_bonus"] = item.get("hit_bonus", 0) + affix["hit_penalty"]
            if "weight_bonus" in affix:
                item["weight"] += affix["weight_bonus"]
            if "weight_penalty" in affix:
                item["weight"] = max(1, item["weight"] + affix["weight_penalty"])
            if "speed_bonus" in affix:
                item["speed_bonus"] = item.get("speed_bonus", 0) + affix["speed_bonus"]
            if "speed_penalty" in affix:
                item["speed_bonus"] = item.get("speed_bonus", 0) - affix["speed_penalty"]
            # 特殊效果
            if "on_attack" in affix:
                item["on_attack"].extend(affix["on_attack"])
            if "lifesteal" in affix:
                item["lifesteal"] = affix["lifesteal"]
            # 标签
            if "tags" in affix:
                item["tags"].extend(affix["tags"])

        # 材质标签加入 on_attack（如燃烧的材质？未来扩展）
        # 去重 on_attack
        item["on_attack"] = list(set(item["on_attack"]))

        # 移除空字段
        if not item.get("attack_bonus") and "damage_min" in item:
            del item["attack_bonus"]
        if not item.get("on_attack"):
            del item["on_attack"]

        # 生成描述
        affix_descs = [self.affixes[a].get("desc", "") for a in affix_names if self.affixes.get(a, {}).get("desc")]
        desc_parts = [mat.get("desc", "")]
        if affix_descs:
            desc_parts.append(" | ".join(affix_descs))
        item["desc"] = "。".join(d for d in desc_parts if d)

        # 如果是消耗品，特殊处理
        if item.get("consumable"):
            item["name"] = f"{mat['name']}{arch.get('name', '药水')}"
            item.pop("durability", None)
            item.pop("durability_max", None)

        return item

    def generate_loot(self, depth=0):
        """
        生成掉落物品。depth 越深，材质和词缀越好。
        """
        # 深层更容易出好材质
        if depth < -30:
            mat_weights = {"石头": 3, "铁": 5, "钢": 2, "黑曜石": 3, "骨": 2, "皮": 1}
        elif depth < -10:
            mat_weights = {"石头": 5, "铁": 3, "钢": 1, "黑曜石": 1, "骨": 3, "皮": 2}
        else:
            mat_weights = {"石头": 6, "铁": 1, "骨": 3, "皮": 3}

        mat_names = list(mat_weights.keys())
        mat_w = [mat_weights[n] for n in mat_names]
        material = random.choices(mat_names, weights=mat_w, k=1)[0]

        # 排除消耗品用于掉落
        weapon_arches = [k for k, v in self.archetypes.items() if not v.get("consumable")]
        archetype = random.choice(weapon_arches)

        return self.generate(archetype_name=archetype, material_name=material)


# 全局单例
_generator = None


def get_generator():
    global _generator
    if _generator is None:
        _generator = ItemGenerator()
    return _generator


def generate_item(archetype=None, material=None, affix_count=None):
    return get_generator().generate(archetype, material, affix_count)


def generate_loot(depth=0):
    return get_generator().generate_loot(depth)

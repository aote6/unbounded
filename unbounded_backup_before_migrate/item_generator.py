""" item_generator.py  三层物品组装引擎。原型 × 材质 × 词缀 → 具体物品。"""
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).parent
ITEMS_FILE = BASE_DIR / "data" / "items.json"
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
        import logging
        logging.warning(f"item_generator 解析失败: {path} - {e}")
        return {}


class ItemGenerator:
    def __init__(self):
        # 从统一的 items.json 加载
        all_items = load_json(ITEMS_FILE)
        # 提取有 equippable 组件的作为原型
        self.archetypes = {}
        # 提取有 material 组件的作为材质
        self.materials = {}
        for item_id, data in all_items.items():
            comps = data.get("components", {})
            if "equippable" in comps:
                self.archetypes[item_id] = {
                    "name": data.get("name", item_id),
                    "slot": comps["equippable"].get("slot"),
                    "base_damage_min": comps["equippable"].get("base_damage_min"),
                    "base_damage_max": comps["equippable"].get("base_damage_max"),
                    "base_defense": comps["equippable"].get("base_defense"),
                    "base_durability": comps["equippable"].get("base_durability"),
                    "base_tool_power": comps["equippable"].get("base_tool_power"),
                    "hit_bonus": comps["equippable"].get("hit_bonus", 0),
                    "consumable": comps["equippable"].get("consumable", False),
                    "desc": data.get("desc", ""),
                }
                # 去掉 None
                self.archetypes[item_id] = {
                    k: v for k, v in self.archetypes[item_id].items() if v is not None}
            if "material" in comps:
                self.materials[item_id] = {
                    "name": data.get(
                        "name", item_id), "damage_mult": comps["material"].get(
                        "damage_mult", 1.0), "defense_mult": comps["material"].get(
                        "defense_mult", 1.0), "durability_mult": comps["material"].get(
                        "durability_mult", 1.0), "tool_mult": comps["material"].get(
                        "tool_mult", 1.0), "weight_per_unit": comps["material"].get(
                            "weight_per_unit", 1), "tags": data.get(
                                "tags", []), "desc": data.get(
                                    "desc", ""), }
        self.affixes = load_json(AFFIXES_FILE)
        self._affix_pool = self._build_affix_pool()

    def _build_affix_pool(self):
        """按稀有度加权展开词缀池"""
        pool = []
        for name, data in self.affixes.items():
            weight = RARITY_WEIGHTS.get(data.get("rarity", "common"), 10)
            pool.extend([name] * weight)
        return pool

    def generate(
            self,
            archetype_name=None,
            material_name=None,
            affix_count=None):
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
        arch["name"] = archetype_name if archetype_name else arch.get(
            "name", "未知原型")

        # 选材质
        if material_name and material_name in self.materials:
            mat = dict(self.materials[material_name])
        else:
            mat_name = random.choice(list(self.materials.keys()))
            mat = dict(self.materials[mat_name])
        mat["name"] = material_name if material_name else mat.get(
            "name", "未知材质")

        # 选词缀（0-3条，不重复）
        if affix_count is None:
            affix_count = random.choices([0, 1, 2, 3], weights=[2, 4, 3, 1])[0]
        selected_affixes = []
        available = list(self.affixes.keys())
        for _ in range(affix_count):
            if not available:
                break
            # 按稀有度加权选
            weights = [
                RARITY_WEIGHTS.get(
                    self.affixes[a].get(
                        "rarity",
                        "common"),
                    10) for a in available]
            chosen = random.choices(available, weights=weights, k=1)[0]
            selected_affixes.append(chosen)
            available.remove(chosen)

        # 组装最终物品
        item = self._assemble(arch, mat, selected_affixes)
        return item

    def _assemble(self, arch, mat, affix_names):
        """根据原型、材质、词缀计算最终数值（拆分为多个子步骤，逐一执行）"""
        item = self._init_item(arch, mat, affix_names)
        self._apply_base_stats(item, arch, mat)
        for affix_name in affix_names:
            affix = self.affixes.get(affix_name, {})
            self._apply_simple_additions(item, affix)
            self._apply_defense_modifiers(item, affix)
            self._apply_durability_modifiers(item, affix)
            self._apply_weight_modifiers(item, affix)
            self._apply_speed_modifiers(item, affix)
            self._apply_special_effects(item, affix)
        self._cleanup_item(item)
        self._apply_description(item, mat, affix_names)
        self._apply_consumable_override(item, arch, mat)
        return item

    def _init_item(self, arch, mat, affix_names):
        """组装物品的基础字段（不含数值）"""
        return {
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

    def _apply_base_stats(self, item, arch, mat):
        """原型 × 材质 → 四类基础数值（攻击/防御/工具/耐久）+ 命中"""
        base_min = arch.get("base_damage_min", 0)
        base_max = arch.get("base_damage_max", 0)
        if base_max > 0:
            dmg_mult = mat.get("damage_mult", 1.0)
            item["damage_min"] = max(1, int(base_min * dmg_mult))
            item["damage_max"] = max(1, int(base_max * dmg_mult))
            item["attack_bonus"] = 0

        base_def = arch.get("base_defense", 0)
        if base_def > 0:
            def_mult = mat.get("defense_mult", 1.0)
            item["defense_bonus"] = max(1, int(base_def * def_mult))

        base_tool = arch.get("base_tool_power", 0)
        if base_tool > 0:
            tool_mult = mat.get("tool_mult", 1.0)
            item["tool_bonus"] = max(1, int(base_tool * tool_mult))

        base_dur = arch.get("base_durability", 50)
        dur_mult = mat.get("durability_mult", 1.0)
        item["durability"] = max(10, int(base_dur * dur_mult))
        item["durability_max"] = item["durability"]

        item["hit_bonus"] = arch.get("hit_bonus", 0)

    # 词缀里"加成/惩罚都做同一件事(累加)"的字段，放进表里统一处理
    _SIMPLE_ADD_FIELDS = (
        ("damage_bonus", "attack_bonus"),
        ("damage_penalty", "attack_bonus"),
        ("hit_bonus", "hit_bonus"),
        ("hit_penalty", "hit_bonus"),
    )

    def _apply_simple_additions(self, item, affix):
        for affix_key, item_key in self._SIMPLE_ADD_FIELDS:
            if affix_key in affix:
                item[item_key] = item.get(item_key, 0) + affix[affix_key]

    def _apply_defense_modifiers(self, item, affix):
        if "defense_bonus" in affix and "defense_bonus" in item:
            item["defense_bonus"] += affix["defense_bonus"]
        if "defense_penalty" in affix and "defense_bonus" in item:
            item["defense_bonus"] = max(
                0, item["defense_bonus"] + affix["defense_penalty"])

    def _apply_durability_modifiers(self, item, affix):
        if "durability_bonus" in affix:
            item["durability"] += affix["durability_bonus"]
            item["durability_max"] = item["durability"]
        if "durability_penalty" in affix:
            item["durability"] = max(
                5, item["durability"] + affix["durability_penalty"])
            item["durability_max"] = item["durability"]

    def _apply_weight_modifiers(self, item, affix):
        if "weight_bonus" in affix:
            item["weight"] += affix["weight_bonus"]
        if "weight_penalty" in affix:
            item["weight"] = max(1, item["weight"] + affix["weight_penalty"])

    def _apply_speed_modifiers(self, item, affix):
        # 注意：speed_bonus 是加，speed_penalty 是减，两者不对称，保留原逻辑
        if "speed_bonus" in affix:
            item["speed_bonus"] = item.get(
                "speed_bonus", 0) + affix["speed_bonus"]
        if "speed_penalty" in affix:
            item["speed_bonus"] = item.get(
                "speed_bonus", 0) - affix["speed_penalty"]

    def _apply_special_effects(self, item, affix):
        if "on_attack" in affix:
            item["on_attack"].extend(affix["on_attack"])
        if "lifesteal" in affix:
            item["lifesteal"] = affix["lifesteal"]
        if "tags" in affix:
            item["tags"].extend(affix["tags"])

    def _cleanup_item(self, item):
        """去重 on_attack + 移除空字段"""
        item["on_attack"] = list(set(item["on_attack"]))
        if not item.get("attack_bonus") and "damage_min" in item:
            del item["attack_bonus"]
        if not item.get("on_attack"):
            del item["on_attack"]

    def _apply_description(self, item, mat, affix_names):
        affix_descs = [
            self.affixes[a].get(
                "desc",
                "") for a in affix_names if self.affixes.get(
                a,
                {}).get("desc")]
        desc_parts = [mat.get("desc", "")]
        if affix_descs:
            desc_parts.append(" | ".join(affix_descs))
        item["desc"] = "。".join(d for d in desc_parts if d)

    def _apply_consumable_override(self, item, arch, mat):
        if item.get("consumable"):
            item["name"] = f"{mat['name']}{arch.get('name', '药水')}"
            item.pop("durability", None)
            item.pop("durability_max", None)

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
        weapon_arches = [
            k for k,
            v in self.archetypes.items() if not v.get("consumable")]
        archetype = random.choice(weapon_arches)

        return self.generate(archetype_name=archetype, material_name=material)


# 全局单例
_generator = None


def get_generator():
    global _generator
    if _generator is None:
        _generator = ItemGenerator()
    return _generator


def generate_loot(depth=0):
    return get_generator().generate_loot(depth)

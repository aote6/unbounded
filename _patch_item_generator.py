import pathlib

path = pathlib.Path.home() / "unbounded" / "item_generator.py"
src = path.read_text(encoding="utf-8")

OLD = '''    def _assemble(self, arch, mat, affix_names):
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
                item["attack_bonus"] = item.get(
                    "attack_bonus", 0) + affix["damage_bonus"]
            if "damage_penalty" in affix:
                item["attack_bonus"] = item.get(
                    "attack_bonus", 0) + affix["damage_penalty"]
            if "defense_bonus" in affix and "defense_bonus" in item:
                item["defense_bonus"] += affix["defense_bonus"]
            if "defense_penalty" in affix and "defense_bonus" in item:
                item["defense_bonus"] = max(
                    0, item["defense_bonus"] + affix["defense_penalty"])
            if "durability_bonus" in affix:
                item["durability"] += affix["durability_bonus"]
                item["durability_max"] = item["durability"]
            if "durability_penalty" in affix:
                item["durability"] = max(
                    5, item["durability"] + affix["durability_penalty"])
                item["durability_max"] = item["durability"]
            if "hit_bonus" in affix:
                item["hit_bonus"] = item.get(
                    "hit_bonus", 0) + affix["hit_bonus"]
            if "hit_penalty" in affix:
                item["hit_bonus"] = item.get(
                    "hit_bonus", 0) + affix["hit_penalty"]
            if "weight_bonus" in affix:
                item["weight"] += affix["weight_bonus"]
            if "weight_penalty" in affix:
                item["weight"] = max(
                    1, item["weight"] + affix["weight_penalty"])
            if "speed_bonus" in affix:
                item["speed_bonus"] = item.get(
                    "speed_bonus", 0) + affix["speed_bonus"]
            if "speed_penalty" in affix:
                item["speed_bonus"] = item.get(
                    "speed_bonus", 0) - affix["speed_penalty"]
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

        # 如果是消耗品，特殊处理
        if item.get("consumable"):
            item["name"] = f"{mat['name']}{arch.get('name', '药水')}"
            item.pop("durability", None)
            item.pop("durability_max", None)

        return item'''

NEW = '''    def _assemble(self, arch, mat, affix_names):
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
            item.pop("durability_max", None)'''

count = src.count(OLD)
assert count == 1, f"匹配到 {count} 处，应为 1 处，中止！"

backup = path.with_suffix(".py.bak")
backup.write_text(src, encoding="utf-8")

path.write_text(src.replace(OLD, NEW), encoding="utf-8")
print("item_generator.py 已替换，备份在", backup)

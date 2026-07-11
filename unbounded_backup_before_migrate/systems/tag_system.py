"""标签系统：加载交互规则矩阵，提供标签匹配查询。"""
import json
import os

_rules = []


def load_rules(path="data/interaction_rules.json"):
    """加载交互规则矩阵。"""
    global _rules
    full_path = os.path.join(os.path.dirname(__file__), "..", path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _rules = data.get("rules", [])
    return _rules


def check_interaction(source_tags, target_tags):
    """检查 source 和 target 标签之间是否有匹配的交互规则。
    返回匹配的规则列表，每个规则是 dict。
    """
    matches = []
    source_set = set(source_tags) if source_tags else set()
    target_set = set(target_tags) if target_tags else set()
    for rule in _rules:
        req_source = set(rule.get("source_tags", []))
        req_target = set(rule.get("target_tags", []))
        if req_source & source_set and req_target & target_set:
            matches.append(rule)
    return matches

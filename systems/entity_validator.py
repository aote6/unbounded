"""中央实体验证器：启动时校验所有跨文件引用的一致性。"""
import json
from pathlib import Path
from inventory import ItemCategory

BASE_DIR = Path(__file__).parent.parent


def validate_all():
    """启动时调用。检查所有数据文件之间的引用是否一致。
    有问题直接抛异常，不再静默容错。
    """
    errors = []

    # 加载数据
    with open(BASE_DIR / "data" / "items.json", encoding="utf-8") as f:
        items = json.load(f)
    with open(BASE_DIR / "data" / "recipes.json", encoding="utf-8") as f:
        recipes = json.load(f)

    # 1. 检查 items.json 每个条目都有合法 type
    valid_types = set(e.value for e in ItemCategory)
    for name, data in items.items():
        t = data.get("type")
        if t not in valid_types:
            errors.append(
                f"items.json: '{name}' 的 type='{t}' 不合法，合法值: {valid_types}"
            )

    # 2. 检查每个配方的 result.name 在 items.json 中存在
    #    （装备类配方走 item_generator，但也需要原型在 items.json 中有定义）
    for recipe_name, r in recipes.items():
        if not isinstance(r, dict) or "result" not in r:
            errors.append(f"recipes.json: '{recipe_name}' 缺少 result 字段")
            continue

        result = r["result"]
        result_type = result.get("type")
        result_name = result.get("name", recipe_name)

        if result_type not in valid_types:
            errors.append(
                f"recipes.json: '{recipe_name}' 的 result.type='{result_type}' 不在 ItemCategory 枚举中"
            )

        # 材料/可放置物：result.name 必须在 items.json 中存在
        if result_type in (ItemCategory.MATERIAL, ItemCategory.PLACEABLE):
            if result_name not in items:
                errors.append(
                    f"recipes.json: '{recipe_name}' 产出 '{result_name}'，"
                    f"但 items.json 中不存在该物品"
                )
            else:
                item_type = items[result_name].get("type")
                if item_type != result_type:
                    errors.append(
                        f"recipes.json: '{recipe_name}' 声明 type={result_type}，"
                        f"但 items.json 中 '{result_name}' 的 type={item_type}，不一致"
                    )

        # 装备类：generator_args.archetype 必须在 items.json 中存在
        elif result_type == ItemCategory.EQUIPMENT:
            gen_args = result.get("generator_args", {})
            archetype = gen_args.get("archetype", "")
            if archetype and archetype not in items:
                errors.append(
                    f"recipes.json: '{recipe_name}' 引用原型 '{archetype}'，"
                    f"但 items.json 中不存在该原型"
                )

    if errors:
        msg = "实体验证失败，以下引用不一致:\n" + "\n".join(f"  - {e}" for e in errors)
        raise ValueError(msg)

    return True

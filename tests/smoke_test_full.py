"""
最小可玩闭环冒烟测试
覆盖：合成装备 → 装备 → 技能升级 → 存档/读档 → 数据一致性校验

在 unbounded 目录下运行：
    python3 tests/smoke_test_full.py
"""
import sys
import os
import inspect
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = []
FAIL = []


def check(name, fn):
    """运行一个测试用例，捕获异常，记录结果。"""
    try:
        fn()
        PASS.append(name)
        print(f"[PASS] {name}")
    except Exception as e:
        FAIL.append((name, e))
        print(f"[FAIL] {name}: {e}")
        traceback.print_exc()


def main():
    from main import Game

    # ── 用例1：创建游戏对象，静态数据加载 + entity_validator 应正常通过 ──
    game = Game()

    def test_create_game():
        assert game.player_hp > 0, "初始HP应大于0"
        assert game.recipes, "配方数据应已加载"
        assert game.items, "物品数据应已加载"

    check("创建游戏对象 & 静态数据加载", test_create_game)

    # ── 用例2：合成一把石头剑（走 item_generator，不走UI） ──
    equip_holder = {}

    def test_craft_equipment():
        from item_generator import get_generator
        from systems.inventory_actions import add_equipment_instance, get_equipment_instance
        from equipment import EquipmentInstance

        gen = get_generator()
        # 尝试常见的原型/材质参数名，具体archetype/material请按你实际数据调整
        item_dict = gen.generate(
            archetype_name="剑",
            material_name="石头",
            affix_count=0)
        inst = EquipmentInstance(
            name=item_dict["name"],
            slot=item_dict.get("slot"),
            attack_bonus=item_dict.get("attack_bonus", 0),
            defense_bonus=item_dict.get("defense_bonus", 0),
            tool_bonus=item_dict.get("tool_bonus", 0),
            damage_min=item_dict.get("damage_min", 0),
            damage_max=item_dict.get("damage_max", 0),
            hit_bonus=item_dict.get("hit_bonus", 0),
            affixes=item_dict.get("affixes", []),
            on_attack=item_dict.get("on_attack", []),
            lifesteal=item_dict.get("lifesteal", 0),
            speed_bonus=item_dict.get("speed_bonus", 0),
        )
        add_equipment_instance(game, inst.name, inst)
        found = get_equipment_instance(game, inst.name)
        assert found is not None, "合成后应能在背包中找到该装备实例"
        assert found.slot, "装备实例的slot字段不应为空"
        equip_holder["inst"] = found

    check("合成装备并写入背包", test_craft_equipment)

    # ── 用例3：装备到槽位，验证读取一致 ──
    def test_equip_item():
        inst = equip_holder.get("inst")
        assert inst is not None, "上一步未成功生成装备实例，无法测试装备"
        slot_id = inst.slot
        game.equipment[slot_id] = inst
        assert game.equipment.get(slot_id) is inst, "装备槽应正确写入实例"
        assert game.equipment.get(slot_id).name == inst.name, "装备名称应一致"

    check("装备到槽位", test_equip_item)

    # ── 用例4：技能升级判定 ──
    def test_skill_levelup():
        from systems.skill_system import gain_skill, SKILL_LEVEL_THRESHOLD
        game.skills["digging"] = 0
        game.skill_levels["digging"] = 1
        for _ in range(SKILL_LEVEL_THRESHOLD):
            gain_skill(game, "digging")
        assert game.skill_levels["digging"] == 2, (
            f"攒够{SKILL_LEVEL_THRESHOLD}点经验后应升到2级，实际为{game.skill_levels['digging']}"
        )

    check("技能升级判定", test_skill_levelup)

    # ── 用例5：存档/读档，装备应保持一致 ──
    def test_save_load_roundtrip():
        from systems import save_manager

        equipped_name = None
        for inst in game.equipment.values():
            if inst:
                equipped_name = inst.name
                break
        assert equipped_name is not None, "测试前应已装备至少一件物品"

        # 尝试常见的 save_game/load_game 签名：仅接受 game
        sig_save = inspect.signature(save_manager.save_game)
        if len(sig_save.parameters) == 1:
            save_manager.save_game(game)
        else:
            raise AssertionError(
                f"save_game 签名为 {sig_save}，与预期不符，请手动检查 systems/save_manager.py"
            )

        sig_load = inspect.signature(save_manager.load_game)
        if len(sig_load.parameters) == 1:
            save_manager.load_game(game)
        else:
            raise AssertionError(
                f"load_game 签名为 {sig_load}，与预期不符，请手动检查 systems/save_manager.py"
            )

        found_after_load = any(
            inst and inst.name == equipped_name for inst in game.equipment.values())
        assert found_after_load, "读档后装备应仍然存在于装备槽"

    check("存档/读档装备持久化", test_save_load_roundtrip)

    # ── 用例6：数据一致性校验器可独立运行 ──
    def test_entity_validator():
        from systems.entity_validator import validate_all
        validate_all()

    check("数据一致性校验(entity_validator)", test_entity_validator)

    # ── 汇总 ──
    print("\n" + "=" * 40)
    print(f"通过: {len(PASS)}  失败: {len(FAIL)}")
    if FAIL:
        print("失败用例:")
        for name, e in FAIL:
            print(f"  - {name}: {e}")
        sys.exit(1)
    else:
        print("全部通过。")
        sys.exit(0)


if __name__ == "__main__":
    main()

"""战斗系统：攻击、击杀、掉落——从 Game 类提取。"""
import random
from config import PLAYER_BASE_HIT_CHANCE, PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX
from world_gen import TILE_AIR
from systems.event_bus import EventBus, EventType, GameEvent
import monsters as monsters_mod


class CombatSystem:
    """战斗逻辑。接收 game 上下文，执行攻击/击杀流程。"""

    def __init__(self, game):
        self.game = game

    def attack_monster(self, monster):
        """玩家攻击怪物。"""
        game = self.game
        if random.random() > PLAYER_BASE_HIT_CHANCE:
            game.message = f"攻击 {monster['name']}，但未命中！"
            game.turn += 1
            return

        dmg = random.randint(PLAYER_BASE_DAMAGE_MIN, PLAYER_BASE_DAMAGE_MAX)
        dmg += game._equipment_bonus("attack_bonus")
        dmg += game._combat_damage_bonus()
        armor = monster.get("properties", {}).get("natural_armor", 0)
        dmg = max(1, dmg - armor)
        monster["hp"] -= dmg

        EventBus().emit(GameEvent(EventType.DAMAGE_DEALT,
            {"attacker": "player", "target": monster, "damage": dmg}), game)
        game._gain_skill("combat")

        if monster["hp"] <= 0:
            self.kill_monster(monster, cause="attack")
        else:
            hp_ratio = monster["hp"] / monster["max_hp"]
            if hp_ratio < 0.3:
                game.message = f"攻击 {monster['name']}，造成 {dmg} 点伤害。它快不行了！"
            else:
                game.message = f"攻击 {monster['name']}，造成 {dmg} 点伤害。"

    def kill_monster(self, monster, cause="attack"):
        """击杀怪物：计数、掉落、尸体、分裂。"""
        game = self.game
        game._monsters_killed_this_life += 1
        mx, my = monster["x"], monster["y"]
        mname = monster["name"]

        EventBus().emit(GameEvent(EventType.MONSTER_KILLED,
            {"monster": monster, "cause": cause}), game)

        corpse_tile = monster.get("corpse_tile")
        splits = monsters_mod.get_split_spawns(monster, game.monster_data)
        drop_name, drop_obj = monsters_mod.generate_loot_for(game.player_y, mname)

        if drop_name and drop_obj:
            if isinstance(drop_obj, dict) and "count" in drop_obj:
                game._add_material(drop_name, drop_obj.get("count", 1))
            else:
                game._add_equipment_instance(drop_name, drop_obj)

        game._remove_monster(monster)

        if corpse_tile and game.world.get_tile(mx, my)["tile"] == TILE_AIR:
            old_tile = game.world.get_tile(mx, my)["tile"]
            game.world.set_tile(mx, my, corpse_tile)
            EventBus().emit(GameEvent(EventType.TILE_CHANGED,
                {"x": mx, "y": my, "old": old_tile, "new": corpse_tile}), game)
            game.modified_tiles[(mx, my)] = corpse_tile
            game.corpses[(mx, my)] = 50  # CORPSE_DECAY_TURNS

        if splits:
            for s in splits:
                game._add_monster(s)

        cause_msg = {
            "attack": f"打倒了 {mname}！",
            "burn": f"{mname} 被烧死了！",
            "poison": f"{mname} 中毒身亡！",
            "predator": f"{mname} 被猎杀了！",
        }.get(cause, f"{mname} 死了。")

        if splits:
            cause_msg += f"它分裂成了 {len(splits)} 只小史莱姆！"
        elif drop_name:
            cause_msg += f"掉落了 {drop_name}。"
        game.message = cause_msg

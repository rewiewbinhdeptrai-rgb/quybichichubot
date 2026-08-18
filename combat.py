"""
Combat Engine — PvE tối thiểu (mục 23-27 trong spec).

Turn structure:
  Player action (Attack / Ability / Defend / Flee)
    -> nếu Monster còn sống: Monster phản đòn ngay trong cùng lượt
    -> Effect Engine tick (buff/debuff giảm duration)
    -> Kiểm tra thắng/thua

Mọi thay đổi HP/Tiền/EXP được ghi vào DB qua db.apply_combat_result() —
một transaction duy nhất (mục 49-50), không update rời rạc.
"""
import random

import database as db
import effects
import inventory
import achievements
import quest
import faction


class CombatError(Exception):
    """Lỗi nghiệp vụ (không có trận đang diễn ra, HP không đủ Spirituality...)."""


# ---------------------------------------------------------------------------
# Bắt đầu / truy vấn trận
# ---------------------------------------------------------------------------

def start_pve(character: dict, monster_id: str):
    if db.get_active_combat_session(character["character_id"]):
        raise CombatError("Đang có một trận đấu khác chưa kết thúc.")

    monster = db.get_monster(monster_id)
    if monster is None:
        raise CombatError("Không tìm thấy Quái vật này.")

    if character["hp"] <= 0:
        raise CombatError("HP hiện tại bằng 0 — cần hồi phục trước khi chiến đấu.")

    effects.clear_all(character["character_id"])  # bắt đầu trận sạch buff/debuff cũ
    session = db.create_combat_session(
        character["character_id"], monster_id, character["hp"], monster["hp"]
    )
    db.log_action(character["character_id"], "combat_start", monster["name_en"])
    return session, monster


def get_active_session(character_id: int):
    return db.get_active_combat_session(character_id)


# ---------------------------------------------------------------------------
# Nội bộ: đòn phản công của Monster + xử lý thắng/thua
# ---------------------------------------------------------------------------

def _monster_counter_attack(character_id: int, monster: dict, player_hp: int):
    raw_damage = monster["attack"]
    real_damage = effects.calculate_incoming_damage(character_id, raw_damage)
    new_player_hp = max(0, player_hp - real_damage)
    return new_player_hp, real_damage


def _finish(character: dict, session: dict, player_hp: int, monster_hp: int, monster: dict):
    """Quyết định trạng thái cuối cùng của lượt: ongoing / victory / defeat.
    Luôn ghi DB thật (mục 15, 49-51) — không có kết quả nào chỉ hiện trên UI."""
    character_id = character["character_id"]

    if monster_hp <= 0:
        db.update_combat_session(session["session_id"], player_hp, 0, session["turn"] + 1, "victory")
        db.apply_combat_result(character_id, player_hp, monster["reward_money"], monster["reward_exp"])
        db.log_action(character_id, "combat_victory", monster["name_en"])
        achievements.unlock(character_id, "first_kill")
        # mục 45: check_wealth_achievements() có sẵn trong achievements.py nhưng
        # trước đây chưa từng được gọi ở đâu -> Achievement giàu có (wealthy_1)
        # KHÔNG BAO GIỜ mở khoá được dù người chơi có bao nhiêu tiền. Gọi thật
        # ngay sau khi Tiền vừa được cộng ở dòng trên (mục 49: đồng bộ, không
        # cập nhật một nơi rồi quên nơi khác).
        achievements.check_wealth_achievements(character_id, db.get_character_by_id(character_id)["money"])
        # Hook Quest (mục 43): tiến độ Objective "kill_monster" đến từ đúng
        # sự kiện thắng trận thật, không phải player tự khai đã giết.
        quest.progress_objective(character_id, "kill_monster", monster["monster_id"], 1)

        # Hook Faction/Church Mission (mục 33-34): kill_progress chỉ tăng từ
        # chiến thắng thật ở đây — không có cách nào khác để "tự khai" đã giết.
        org_type, org_id, _rep = faction._current_org(character_id)
        if org_type is not None:
            db.progress_faction_mission_kill(character_id, monster["monster_id"], org_type, org_id, 1)

        dropped_item = None
        if monster["drop_item_id"] and random.random() < monster["drop_chance"]:
            db.add_inventory_item(character_id, monster["drop_item_id"], 1)
            dropped_item = db.get_item(monster["drop_item_id"])
            db.log_action(character_id, "item_drop", dropped_item["name_en"])
            quest.progress_objective(character_id, "collect_item", monster["drop_item_id"], 1)

        # Party (mục 36): đồng đội cùng địa điểm, còn sống, nhận % EXP/Tiền.
        # Không tạo damage/participation giả — đây là share thật qua DB.
        party_rewarded = db.apply_party_combat_share(
            character_id, monster["reward_money"], monster["reward_exp"]
        )

        result = {
            "status": "victory",
            "player_hp": player_hp,
            "monster_hp": 0,
            "reward_money": monster["reward_money"],
            "reward_exp": monster["reward_exp"],
            "dropped_item": dropped_item,
            "party_rewarded_count": len(party_rewarded),
        }
        if session.get("dungeon_run_id"):
            import dungeon  # import cục bộ để tránh circular import (dungeon.py import combat.py)
            result["dungeon_result"] = dungeon.on_combat_resolved(character_id, session["dungeon_run_id"], result)
        return result

    if player_hp <= 0:
        # Thua trận (mục 13 - hậu quả "nặng"): không chết hẳn, về 1 HP + mất 10% tiền
        penalty = -round(character["money"] * 0.10)
        db.update_combat_session(session["session_id"], 1, monster_hp, session["turn"] + 1, "defeat")
        db.apply_combat_result(character_id, 1, penalty, 0)
        db.log_action(character_id, "combat_defeat", monster["name_en"])
        result = {
            "status": "defeat",
            "player_hp": 1,
            "monster_hp": monster_hp,
            "money_penalty": penalty,
        }
        if session.get("dungeon_run_id"):
            import dungeon
            result["dungeon_result"] = dungeon.on_combat_resolved(character_id, session["dungeon_run_id"], result)
        return result

    db.update_combat_session(session["session_id"], player_hp, monster_hp, session["turn"] + 1, "active")
    return {"status": "ongoing", "player_hp": player_hp, "monster_hp": monster_hp}


# ---------------------------------------------------------------------------
# Hành động của Player
# ---------------------------------------------------------------------------

def perform_attack(character: dict, session: dict):
    monster = db.get_monster(session["monster_id"])
    base_damage = 10 + character["level"] * 2
    dealt = effects.calculate_damage(character["character_id"], base_damage)
    monster_hp = max(0, session["monster_hp"] - dealt)

    player_hp = session["player_hp"]
    counter_damage = 0
    if monster_hp > 0:
        player_hp, counter_damage = _monster_counter_attack(character["character_id"], monster, player_hp)

    effects.tick(character["character_id"])
    result = _finish(character, session, player_hp, monster_hp, monster)
    result["player_dealt"] = dealt
    result["counter_damage"] = counter_damage
    result["action_label"] = "⚔️ Tấn công"
    return result


def perform_ability(character: dict, session: dict, ability_id: str):
    ability = db.get_ability(ability_id)
    if ability is None or ability["pathway_id"] != character["pathway_id"]:
        raise CombatError("Ability này không thuộc Pathway hiện tại.")
    if ability["sequence_number"] < character["sequence_number"]:
        raise CombatError("Chưa đạt tới Sequence mở khóa Ability này.")
    if character["spirituality"] < ability["cost"]:
        raise CombatError(f"Không đủ Spirituality (cần {ability['cost']}).")

    monster = db.get_monster(session["monster_id"])
    base_damage = (10 + character["level"] * 2) * ability["damage_multiplier"]
    dealt = effects.calculate_damage(character["character_id"], base_damage)
    monster_hp = max(0, session["monster_hp"] - dealt)

    # Trừ Spirituality thật (mục 14)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE characters SET spirituality = spirituality - ? WHERE character_id = ?",
            (ability["cost"], character["character_id"]),
        )

    player_hp = session["player_hp"]
    counter_damage = 0
    if monster_hp > 0:
        player_hp, counter_damage = _monster_counter_attack(character["character_id"], monster, player_hp)

    effects.tick(character["character_id"])
    result = _finish(character, session, player_hp, monster_hp, monster)
    result["player_dealt"] = dealt
    result["counter_damage"] = counter_damage
    result["action_label"] = f"✨ {ability['name_en']}"
    return result


def perform_defend(character: dict, session: dict):
    monster = db.get_monster(session["monster_id"])
    effects.apply_effect(character["character_id"], "defending", source="combat_defend", duration=1)

    player_hp, counter_damage = _monster_counter_attack(character["character_id"], monster, session["player_hp"])

    effects.tick(character["character_id"])
    result = _finish(character, session, player_hp, session["monster_hp"], monster)
    result["player_dealt"] = 0
    result["counter_damage"] = counter_damage
    result["action_label"] = "🛡️ Phòng thủ"
    return result


def perform_flee(character: dict, session: dict):
    monster = db.get_monster(session["monster_id"])
    success = random.random() < 0.5

    if success:
        db.update_combat_session(
            session["session_id"], session["player_hp"], session["monster_hp"], session["turn"] + 1, "fled"
        )
        db.apply_combat_result(character["character_id"], session["player_hp"], 0, 0)
        db.log_action(character["character_id"], "combat_flee_success", monster["name_en"])
        result = {"status": "fled", "player_hp": session["player_hp"], "action_label": "🏃 Rút lui"}
        if session.get("dungeon_run_id"):
            import dungeon
            result["dungeon_result"] = dungeon.on_combat_resolved(
                character["character_id"], session["dungeon_run_id"], result
            )
        return result

    player_hp, counter_damage = _monster_counter_attack(character["character_id"], monster, session["player_hp"])
    effects.tick(character["character_id"])
    result = _finish(character, session, player_hp, session["monster_hp"], monster)
    result["player_dealt"] = 0
    result["counter_damage"] = counter_damage
    result["action_label"] = "🏃 Rút lui (thất bại)"
    return result

"""
PvP Engine (mục 24) — tái dùng EffectEngine/damage formula của combat.py
nhưng đối thủ là một Character thật thay vì Monster tĩnh.

Khác PvE: không auto-counter cùng lượt. Turn LUÂN PHIÊN — chỉ
character_id == session['turn_character_id'] mới được hành động; sau mỗi
hành động lượt chuyển sang đối thủ. Mọi thay đổi HP/Tiền đi qua
db.apply_pvp_result() — một transaction duy nhất (mục 49-50).
"""
import random

import database as db
import effects
import achievements

WAGER = 500  # Bảng cược mặc định mỗi trận (mục 24) — chuyển thật khi có người thua


class PvPError(Exception):
    """Lỗi nghiệp vụ (đã có trận khác, tự thách đấu chính mình, chưa tới lượt...)."""


# ---------------------------------------------------------------------------
# Thách đấu / chấp nhận / từ chối
# ---------------------------------------------------------------------------

def challenge(challenger: dict, opponent: dict):
    if challenger["character_id"] == opponent["character_id"]:
        raise PvPError("Không thể tự thách đấu chính mình.")
    if db.get_active_pvp_session(challenger["character_id"]) or db.get_active_pvp_session(opponent["character_id"]):
        raise PvPError("Một trong hai bên đang có trận PvP khác chưa kết thúc.")
    if db.get_outgoing_challenge(challenger["character_id"]):
        raise PvPError("Bạn đang có một lời thách đấu khác chưa được trả lời.")
    if challenger["hp"] <= 0 or opponent["hp"] <= 0:
        raise PvPError("HP hiện tại bằng 0 — cần hồi phục trước khi PvP.")
    session = db.create_pvp_challenge(challenger["character_id"], opponent["character_id"])
    db.log_action(challenger["character_id"], "pvp_challenge", str(opponent["character_id"]))
    return session


def get_incoming_challenge(character_id: int):
    return db.get_incoming_challenge(character_id)


def get_outgoing_challenge(character_id: int):
    return db.get_outgoing_challenge(character_id)


def accept(character: dict):
    session = db.get_incoming_challenge(character["character_id"])
    if session is None:
        raise PvPError("Không có lời thách đấu nào đang chờ bạn.")
    challenger = db.get_character_by_id(session["challenger_id"])
    if challenger["hp"] <= 0 or character["hp"] <= 0:
        raise PvPError("Một trong hai bên đã hết HP — cần hồi phục trước.")

    effects.clear_all(challenger["character_id"])
    effects.clear_all(character["character_id"])
    db.activate_pvp_session(
        session["session_id"], challenger["hp"], character["hp"], session["challenger_id"]
    )
    db.log_action(character["character_id"], "pvp_accept", str(challenger["character_id"]))
    return db.get_pvp_session(session["session_id"]), challenger


def decline(character: dict):
    session = db.get_incoming_challenge(character["character_id"])
    if session is None:
        raise PvPError("Không có lời thách đấu nào đang chờ bạn.")
    db.set_pvp_status(session["session_id"], "declined")
    db.log_action(character["character_id"], "pvp_decline", str(session["challenger_id"]))


def get_active_session(character_id: int):
    return db.get_active_pvp_session(character_id)


# ---------------------------------------------------------------------------
# Nội bộ: xác định vai trò trong session + xử lý thắng/thua
# ---------------------------------------------------------------------------

def _role(character_id: int, session: dict):
    """Trả về (self_hp, opponent_id, opponent_hp, is_challenger)."""
    if character_id == session["challenger_id"]:
        return session["challenger_hp"], session["opponent_id"], session["opponent_hp"], True
    return session["opponent_hp"], session["challenger_id"], session["challenger_hp"], False


def _assemble(is_challenger: bool, self_hp: int, opponent_hp: int):
    """Ghép lại đúng thứ tự (challenger_hp, opponent_hp) để ghi DB."""
    return (self_hp, opponent_hp) if is_challenger else (opponent_hp, self_hp)


def _finish(character: dict, session: dict, self_hp: int, opponent_id: int, opponent_hp: int, is_challenger: bool):
    character_id = character["character_id"]
    challenger_hp, opponent_col_hp = _assemble(is_challenger, self_hp, opponent_hp)

    if opponent_hp <= 0:
        status = "finished_challenger" if is_challenger else "finished_opponent"
        db.update_pvp_session(session["session_id"], challenger_hp, opponent_col_hp, None, status)
        db.apply_pvp_result(character_id, opponent_id, 1, WAGER)
        db.log_action(character_id, "pvp_victory", str(opponent_id))
        achievements.unlock(character_id, "first_pvp_win")
        _hook_guild_war_score(character_id, opponent_id)
        db.increment_season_stat(character_id, "pvp_wins")
        return {"status": "victory", "self_hp": self_hp, "opponent_hp": 0, "wager": WAGER}

    if self_hp <= 0:
        status = "finished_opponent" if is_challenger else "finished_challenger"
        db.update_pvp_session(session["session_id"], challenger_hp, opponent_col_hp, None, status)
        db.apply_pvp_result(opponent_id, character_id, 1, WAGER)
        db.log_action(character_id, "pvp_defeat", str(opponent_id))
        return {"status": "defeat", "self_hp": 1, "opponent_hp": opponent_hp, "wager": WAGER}

    db.update_pvp_session(session["session_id"], challenger_hp, opponent_col_hp, opponent_id, "active")
    return {"status": "ongoing", "self_hp": self_hp, "opponent_hp": opponent_hp}


def _require_turn(character_id: int, session: dict):
    if session["turn_character_id"] != character_id:
        raise PvPError("Chưa tới lượt của bạn.")


def _hook_guild_war_score(winner_character_id: int, loser_character_id: int):
    """Nếu winner và loser thuộc hai Guild đang có Guild War active (mục 34),
    thắng PvP cộng 1 điểm thật vào score cuộc chiến — KHÔNG chỉ hiển thị.
    Guild war không bắt buộc phải tồn tại; bỏ qua lặng lẽ nếu không có."""
    winner_guild = db.get_character_guild(winner_character_id)
    loser_guild = db.get_character_guild(loser_character_id)
    if not winner_guild or not loser_guild or winner_guild["guild_id"] == loser_guild["guild_id"]:
        return
    war = db.get_active_guild_war(winner_guild["guild_id"])
    if war is None:
        return
    if loser_guild["guild_id"] not in (war["attacker_guild_id"], war["defender_guild_id"]):
        return
    db.guild_war_contribute_transaction(winner_character_id, war["war_id"], 1)


# ---------------------------------------------------------------------------
# Hành động của Player
# ---------------------------------------------------------------------------

def perform_attack(character: dict, session: dict):
    character_id = character["character_id"]
    _require_turn(character_id, session)
    self_hp, opponent_id, opponent_hp, is_challenger = _role(character_id, session)

    base_damage = 10 + character["level"] * 2
    dealt = effects.calculate_damage(character_id, base_damage)
    dealt = effects.calculate_incoming_damage(opponent_id, dealt)
    opponent_hp = max(0, opponent_hp - dealt)

    effects.tick(character_id)
    result = _finish(character, session, self_hp, opponent_id, opponent_hp, is_challenger)
    result["dealt"] = dealt
    result["action_label"] = "⚔️ Tấn công"
    return result


def perform_ability(character: dict, session: dict, ability_id: str):
    character_id = character["character_id"]
    _require_turn(character_id, session)
    self_hp, opponent_id, opponent_hp, is_challenger = _role(character_id, session)

    ability = db.get_ability(ability_id)
    if ability is None or ability["pathway_id"] != character["pathway_id"]:
        raise PvPError("Ability này không thuộc Pathway hiện tại.")
    if ability["sequence_number"] < character["sequence_number"]:
        raise PvPError("Chưa đạt tới Sequence mở khóa Ability này.")
    if character["spirituality"] < ability["cost"]:
        raise PvPError(f"Không đủ Spirituality (cần {ability['cost']}).")

    base_damage = (10 + character["level"] * 2) * ability["damage_multiplier"]
    dealt = effects.calculate_damage(character_id, base_damage)
    dealt = effects.calculate_incoming_damage(opponent_id, dealt)
    opponent_hp = max(0, opponent_hp - dealt)

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE characters SET spirituality = spirituality - ? WHERE character_id = ?",
            (ability["cost"], character_id),
        )

    effects.tick(character_id)
    result = _finish(character, session, self_hp, opponent_id, opponent_hp, is_challenger)
    result["dealt"] = dealt
    result["action_label"] = f"✨ {ability['name_en']}"
    return result


def perform_defend(character: dict, session: dict):
    character_id = character["character_id"]
    _require_turn(character_id, session)
    self_hp, opponent_id, opponent_hp, is_challenger = _role(character_id, session)

    effects.apply_effect(character_id, "defending", source="pvp_defend", duration=2)
    effects.tick(character_id)

    result = _finish(character, session, self_hp, opponent_id, opponent_hp, is_challenger)
    result["dealt"] = 0
    result["action_label"] = "🛡️ Phòng thủ"
    return result


def perform_flee(character: dict, session: dict):
    """Rút lui khỏi PvP luôn thành công nhưng xử thua ngay (mục 24) — không
    có việc rút lui 50% như PvE vì đối thủ là người thật, không "để nguyên"
    trận treo lại được."""
    character_id = character["character_id"]
    _require_turn(character_id, session)
    self_hp, opponent_id, opponent_hp, is_challenger = _role(character_id, session)

    status = "fled_challenger" if is_challenger else "fled_opponent"
    challenger_hp, opponent_col_hp = _assemble(is_challenger, 1, opponent_hp)
    db.update_pvp_session(session["session_id"], challenger_hp, opponent_col_hp, None, status)
    db.apply_pvp_result(opponent_id, character_id, 1, WAGER)
    db.log_action(character_id, "pvp_flee", str(opponent_id))
    return {"status": "fled", "self_hp": 1, "opponent_hp": opponent_hp, "wager": WAGER,
            "action_label": "🏃 Rút lui (xử thua)"}

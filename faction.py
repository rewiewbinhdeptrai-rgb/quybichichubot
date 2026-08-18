"""
Church / Faction Engine (mục 33-34 trong spec).

Một Character chỉ thuộc tối đa MỘT Church và MỘT Faction cùng lúc — gia
nhập cái mới sẽ tự động rời cái cũ (database.join_church/join_faction đã
xử lý atomic). Reputation là số thật lưu trong DB, không phải chỉ hiển thị.
"""
import database as db
import achievements

JOIN_REPUTATION_BONUS = 0
LEAVE_PENALTY = -10

# Rank thật gate Mission bậc cao (min_reputation trong faction_missions) —
# đây không phải danh hiệu suông, get_rank() là hàm DUY NHẤT mọi UI/Engine
# phải gọi để biết Rank hiện tại, không tự suy luận từ reputation riêng lẻ.
RANK_THRESHOLDS = [
    (-100, "Bị nghi ngờ"),
    (0, "Tân binh"),
    (30, "Thành viên"),
    (60, "Cốt cán"),
    (90, "Trưởng lão"),
]

# Số Reputation nhận được trên mỗi 1 Bảng quyên góp — cố ý rất nhỏ để
# donate không thể thay thế hoàn toàn Mission (mục 33-34: Reputation phải
# đến từ nhiều nguồn gameplay thật, không chỉ trả tiền).
DONATE_RATE = 0.002


class FactionError(Exception):
    """Lỗi nghiệp vụ — hiển thị thẳng cho người chơi, không phải bug hệ thống."""


def get_rank(reputation: int) -> str:
    rank = RANK_THRESHOLDS[0][1]
    for threshold, name in RANK_THRESHOLDS:
        if reputation >= threshold:
            rank = name
    return rank


def list_churches():
    return db.list_churches()


def list_factions():
    return db.list_factions()


def get_membership(character_id: int):
    church = db.get_character_church(character_id)
    faction = db.get_character_faction(character_id)
    return {
        "church": church,
        "church_rank": get_rank(church["reputation"]) if church else None,
        "faction": faction,
        "faction_rank": get_rank(faction["reputation"]) if faction else None,
    }


def join_church(character_id: int, church_id: str):
    church = db.get_church(church_id)
    if church is None:
        raise FactionError("Nhà Thờ này không tồn tại.")
    db.join_church(character_id, church_id)
    achievements.unlock(character_id, "join_church")
    return church


def leave_church(character_id: int):
    current = db.get_character_church(character_id)
    if current is None:
        raise FactionError("Bạn hiện chưa thuộc về Nhà Thờ nào.")
    db.leave_church(character_id, penalty=LEAVE_PENALTY)
    return current


def join_faction(character_id: int, faction_id: str):
    faction = db.get_faction(faction_id)
    if faction is None:
        raise FactionError("Faction này không tồn tại.")
    db.join_faction(character_id, faction_id)
    achievements.unlock(character_id, "join_faction")
    return faction


def leave_faction(character_id: int):
    current = db.get_character_faction(character_id)
    if current is None:
        raise FactionError("Bạn hiện chưa thuộc về Faction nào.")
    db.leave_faction(character_id, penalty=LEAVE_PENALTY)
    return current


def donate(character_id: int, money_amount: int):
    """Quyên góp Tiền -> Reputation thật, atomic (mục 50). Ưu tiên Church nếu
    Character đang thuộc cả hai (không nên xảy ra vì chỉ được 1 trong 2 lúc
    này, nhưng giữ rõ ràng)."""
    if money_amount <= 0:
        raise FactionError("Số tiền quyên góp phải lớn hơn 0.")
    church = db.get_character_church(character_id)
    faction = db.get_character_faction(character_id)
    if church is None and faction is None:
        raise FactionError("Bạn chưa thuộc về Nhà Thờ hay Faction nào để quyên góp.")
    is_church = church is not None
    try:
        gained, new_rep = db.donate_to_org(character_id, is_church, money_amount, DONATE_RATE)
    except ValueError as exc:
        raise FactionError(str(exc)) from exc
    return {"gained": gained, "reputation": new_rep, "rank": get_rank(new_rep), "is_church": is_church}


# ---------------------------------------------------------------------------
# Mission (mục 33-34): kill-tracking thật đến từ combat.py._finish(), min_
# reputation gate Mission bậc cao bằng Reputation THẬT đang có, claim atomic
# chặn double-claim ở tầng database.py.
# ---------------------------------------------------------------------------

def _current_org(character_id: int):
    church = db.get_character_church(character_id)
    if church:
        return "church", church["church_id"], church["reputation"]
    faction = db.get_character_faction(character_id)
    if faction:
        return "faction", faction["faction_id"], faction["reputation"]
    return None, None, None


def list_missions(character_id: int):
    org_type, org_id, reputation = _current_org(character_id)
    if org_type is None:
        raise FactionError("Bạn chưa thuộc về Nhà Thờ hay Faction nào.")
    missions = db.list_faction_missions(org_type, org_id)
    result = []
    for m in missions:
        progress = db.get_character_faction_mission(character_id, m["mission_id"])
        result.append({
            **m,
            "unlocked": reputation >= m["min_reputation"],
            "accepted": progress is not None,
            "kill_progress": progress["kill_progress"] if progress else 0,
            "claimed": bool(progress and progress["claimed_at"]),
        })
    return result


def accept_mission(character_id: int, mission_id: str):
    mission = db.get_faction_mission(mission_id)
    if mission is None:
        raise FactionError("Mission này không tồn tại.")
    org_type, org_id, reputation = _current_org(character_id)
    if org_type != mission["org_type"] or org_id != mission["org_id"]:
        raise FactionError("Mission này không thuộc tổ chức bạn đang tham gia.")
    if reputation < mission["min_reputation"]:
        raise FactionError(
            f"Cần Reputation >= {mission['min_reputation']} (hiện {reputation}) để nhận Mission này."
        )
    if db.get_character_faction_mission(character_id, mission_id):
        raise FactionError("Bạn đã nhận Mission này rồi.")
    db.accept_faction_mission(character_id, mission_id)
    return mission


def claim_mission(character_id: int, mission_id: str):
    progress = db.get_character_faction_mission(character_id, mission_id)
    if progress is None:
        raise FactionError("Bạn chưa nhận Mission này.")
    if progress["claimed_at"]:
        raise FactionError("Mission này đã được nhận thưởng rồi.")
    mission = db.get_faction_mission(mission_id)
    if progress["kill_progress"] < mission["required_kills"]:
        raise FactionError(
            f"Chưa đủ tiến độ ({progress['kill_progress']}/{mission['required_kills']})."
        )
    try:
        return db.claim_faction_mission(character_id, mission_id)
    except ValueError as exc:
        raise FactionError(str(exc)) from exc

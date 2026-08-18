"""
Quest Engine (mục 43 trong spec).

KHÁC Investigation (mục 27 — không tuyến tính, dùng Clue + xác suất) và
KHÁC Contract/Bounty (mục 39-40 — giao dịch Player-Player). Quest ở đây là
nội dung World đưa sẵn (Main/Side/Church/Hidden), có nhiều Objective, và
Objective CHỈ tiến triển khi Engine khác (combat.py, world.py, inventory.py)
gọi progress_objective() sau một hành động gameplay thật đã xảy ra — không
có lệnh "?quest-complete" nào tự ý đánh dấu xong.

State: LOCKED -> AVAILABLE -> ACTIVE -> (OBJECTIVE_PROGRESS ngầm định qua
character_quest_objectives) -> COMPLETED. FAILED/EXPIRED chưa có trigger
trong bản này (chưa có Quest nào có deadline) — để mở rộng sau.
"""
import database as db
import achievements


class QuestError(Exception):
    """Lỗi nghiệp vụ (chưa đủ điều kiện, đã nhận, chưa đủ Objective...) —
    hiển thị thẳng cho người chơi, không phải bug."""


def _is_unlocked(character: dict, quest: dict) -> bool:
    if character["level"] < quest["min_level"]:
        return False
    if quest["prerequisite_quest_id"]:
        prereq = db.get_character_quest(character["character_id"], quest["prerequisite_quest_id"])
        if prereq is None or prereq["status"] != "COMPLETED":
            return False
    return True


def list_quests(character: dict):
    """Trả về toàn bộ Quest kèm status suy ra cho Character này:
    LOCKED (chưa đủ điều kiện) / AVAILABLE (đủ điều kiện, chưa nhận) /
    ACTIVE / COMPLETED — không sửa DB, chỉ đọc."""
    result = []
    for quest in db.list_all_quests():
        cq = db.get_character_quest(character["character_id"], quest["quest_id"])
        if cq is not None:
            status = cq["status"]
        elif _is_unlocked(character, quest):
            status = "AVAILABLE"
        else:
            status = "LOCKED"
        result.append({**quest, "status": status})
    return result


def get_progress(character_id: int, quest_id: str):
    quest = db.get_quest(quest_id)
    if quest is None:
        raise QuestError("Nhiệm vụ này không tồn tại.")
    cq = db.get_character_quest(character_id, quest_id)
    objectives = db.list_character_quest_objectives(character_id, quest_id) if cq else db.list_quest_objectives(quest_id)
    return {
        "quest": quest,
        "status": cq["status"] if cq else None,
        "objectives": objectives,
    }


def start(character: dict, quest_id: str):
    quest = db.get_quest(quest_id)
    if quest is None:
        raise QuestError("Nhiệm vụ này không tồn tại.")

    existing = db.get_character_quest(character["character_id"], quest_id)
    if existing is not None and not (existing["status"] == "COMPLETED" and quest["repeatable"]):
        raise QuestError("Bạn đã nhận nhiệm vụ này rồi (hoặc nó không thể lặp lại).")

    if not _is_unlocked(character, quest):
        if quest["prerequisite_quest_id"]:
            raise QuestError("Bạn cần hoàn thành nhiệm vụ trước đó để mở khóa nhiệm vụ này.")
        raise QuestError(f"Bạn cần đạt Level {quest['min_level']} để nhận nhiệm vụ này.")

    ok = db.start_character_quest(character["character_id"], quest_id)
    if not ok:
        raise QuestError("Không thể nhận nhiệm vụ này lúc này.")
    db.log_action(character["character_id"], "quest_start", quest_id)
    return quest


def progress_objective(character_id: int, objective_type: str, target_id: str, amount: int = 1):
    """HOOK — gọi từ Engine khác (combat._finish khi thắng PvE, world.travel
    khi tới Location, inventory khi nhặt/thu Item...) ngay sau khi hành động
    gameplay thật đã xảy ra. Không được gọi trực tiếp từ lệnh người chơi.
    Trả về danh sách objective_id vừa hoàn thành (để UI có thể thông báo),
    không raise nếu không có Quest nào khớp — im lặng bỏ qua là hành vi
    đúng (không phải mọi hành động đều thuộc về một Quest đang ACTIVE)."""
    return db.advance_quest_objectives(character_id, objective_type, target_id, amount)


def complete(character: dict, quest_id: str):
    quest = db.get_quest(quest_id)
    if quest is None:
        raise QuestError("Nhiệm vụ này không tồn tại.")

    ok = db.complete_character_quest_transaction(character["character_id"], quest_id, character["hp"])
    if not ok:
        raise QuestError("Bạn chưa hoàn thành đủ mục tiêu của nhiệm vụ này.")

    db.log_action(character["character_id"], "quest_complete", quest_id)
    achievements.unlock(character["character_id"], "first_quest")
    return quest

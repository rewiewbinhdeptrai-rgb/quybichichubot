"""Party Engine (mục 36 trong spec). 1-5 người, một Character chỉ ở một
Party active tại một thời điểm — database.py đã enforce atomic."""
import database as db


class PartyError(Exception):
    """Lỗi nghiệp vụ hiển thị thẳng cho người chơi."""


def get_party(character_id: int):
    party = db.get_character_party(character_id)
    if party is None:
        return None
    party["members"] = db.list_party_members(party["party_id"])
    return party


def create_party(character_id: int):
    party_id = db.create_party(character_id)
    if party_id is None:
        raise PartyError("Bạn đã ở trong một Đội nhóm khác — hãy rời đội hiện tại trước.")
    return get_party(character_id)


def join_party(character_id: int, party_id: int):
    ok = db.join_party(party_id, character_id)
    if not ok:
        raise PartyError("Không thể gia nhập Đội nhóm này (đã đầy hoặc bạn đã ở đội khác).")
    return get_party(character_id)


def leave_party(character_id: int):
    party = db.get_character_party(character_id)
    if party is None:
        raise PartyError("Bạn hiện không ở trong Đội nhóm nào.")
    db.leave_party(character_id)

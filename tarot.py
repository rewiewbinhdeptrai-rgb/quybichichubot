"""
Tarot Club Engine (mục 35 trong spec).

Nguyên tắc bắt buộc: Character Identity != Tarot Identity. Mọi hiển thị
trong phạm vi Tarot Club (danh sách hội viên, hội nghị, tin nhắn) chỉ được
lộ ra tarot_seat — KHÔNG BAO GIỜ hiện tên Character thật, kể cả trong log.
"""
import random

import database as db
from data.factions_seed import TAROT_SEATS, TAROT_DESCRIPTION_VI
import achievements


class TarotError(Exception):
    """Lỗi nghiệp vụ hiển thị thẳng cho người chơi."""


def description() -> str:
    return TAROT_DESCRIPTION_VI


def get_membership(character_id: int):
    return db.get_tarot_membership(character_id)


def available_seats() -> list:
    taken = db.list_taken_seats()
    return [s for s in TAROT_SEATS if s not in taken]


def request_join(character_id: int, preferred_seat: str = None) -> str:
    """Trả về mật danh (tarot_seat) được cấp. Nếu preferred_seat còn trống
    thì cấp đúng ghế đó, ngược lại tự chọn ngẫu nhiên trong các ghế còn
    trống — không bao giờ để hai Character trùng mật danh."""
    if db.get_tarot_membership(character_id):
        raise TarotError("Bạn đã là thành viên Tarot Club — không thể gia nhập lần nữa.")

    seats = available_seats()
    if not seats:
        raise TarotError("Mọi ghế Tarot hiện đã có chủ. Hãy quay lại sau.")

    seat = preferred_seat if preferred_seat in seats else random.choice(seats)
    ok = db.join_tarot_club(character_id, seat)
    if not ok:
        # Ai đó vừa lấy mất ghế cùng lúc — thử lại với ghế bất kỳ còn trống.
        seats = available_seats()
        if not seats:
            raise TarotError("Mọi ghế Tarot hiện đã có chủ. Hãy quay lại sau.")
        seat = random.choice(seats)
        db.join_tarot_club(character_id, seat)
    achievements.unlock(character_id, "join_tarot")
    return seat


def leave(character_id: int):
    membership = db.get_tarot_membership(character_id)
    if membership is None:
        raise TarotError("Bạn hiện không phải thành viên Tarot Club.")
    db.leave_tarot_club(character_id)
    return membership


def list_meetings():
    return db.list_tarot_meetings()


def call_meeting(character_id: int, topic_vi: str) -> int:
    membership = db.get_tarot_membership(character_id)
    if membership is None:
        raise TarotError("Chỉ thành viên Tarot Club mới có thể triệu tập hội nghị.")
    return db.create_tarot_meeting(topic_vi, membership["tarot_seat"])


def post_message(character_id: int, meeting_id: int, content_vi: str):
    membership = db.get_tarot_membership(character_id)
    if membership is None:
        raise TarotError("Chỉ thành viên Tarot Club mới có thể gửi thông điệp ở đây.")
    db.post_tarot_message(meeting_id, membership["tarot_seat"], content_vi)


def list_messages(meeting_id: int):
    return db.list_tarot_messages(meeting_id)

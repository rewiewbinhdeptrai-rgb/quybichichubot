"""
Achievement / Ranking Engine (mục 45-46 trong spec).

Achievement được Engine tự kiểm tra và mở khoá ngay sau các hành động liên
quan (không có nút "claim" thủ công cho player bấm bậy) — gọi check_and_unlock()
ở cuối các luồng gameplay liên quan (combat, investigation, faction, trade...).
Ranking luôn tính trực tiếp từ dữ liệu Character sống, không dùng snapshot
có thể lệch (đúng mục 49: đồng bộ dữ liệu toàn hệ thống).
"""
import database as db


def list_all():
    return db.list_achievements()


def list_unlocked(character_id: int):
    unlocked_ids = db.list_character_achievement_ids(character_id)
    return [a for a in db.list_achievements() if a["achievement_id"] in unlocked_ids]


def list_locked(character_id: int):
    unlocked_ids = db.list_character_achievement_ids(character_id)
    return [a for a in db.list_achievements() if a["achievement_id"] not in unlocked_ids]


def unlock(character_id: int, achievement_id: str) -> bool:
    """Trả True nếu vừa mở khoá THẬT (để UI có thể thông báo), False nếu đã
    có từ trước hoặc achievement_id không tồn tại — không bao giờ raise,
    vì đây được gọi âm thầm từ nhiều luồng gameplay khác nhau."""
    return db.unlock_achievement_transaction(character_id, achievement_id)


def check_wealth_achievements(character_id: int, money: int):
    if money >= 50_000:
        unlock(character_id, "wealthy_1")


def get_ranking(field: str = "level", limit: int = 10):
    return db.get_ranking(field, limit)

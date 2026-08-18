"""
Guild Engine (mục 34 mở rộng trong spec) — KHÁC Church/Faction (tổ chức thế
giới cố định, seed sẵn): Guild do Player tự lập, có Treasury thật tách khỏi
characters.money, và Guild War có score thật (không phải chỉ hiển thị).

Một Character chỉ thuộc TỐI ĐA một Guild cùng lúc — giống nguyên tắc
Church/Faction (mục 4 profile: "Faction: None" là trạng thái hợp lệ).
"""
import database as db

GUILD_FOUNDING_COST = db.GUILD_FOUNDING_COST


class GuildError(Exception):
    """Lỗi nghiệp vụ — hiển thị thẳng cho người chơi, không phải bug hệ thống."""


def list_guilds():
    return db.list_guilds()


def get_my_guild(character_id: int):
    return db.get_character_guild(character_id)


def get_members(guild_id: int):
    return db.list_guild_members(guild_id)


def create_guild(character_id: int, name: str, description_vi: str = ""):
    name = name.strip()
    if not name or len(name) > 40:
        raise GuildError("Tên Guild phải từ 1 đến 40 ký tự.")
    guild_id = db.create_guild_transaction(character_id, name, description_vi)
    if guild_id is None:
        raise GuildError(
            f"Không thể lập Guild — bạn đã có Guild, tên đã bị trùng, "
            f"hoặc không đủ {GUILD_FOUNDING_COST} Bảng phí thành lập."
        )
    return db.get_guild(guild_id)


def disband_guild(character_id: int):
    if not db.disband_guild_transaction(character_id):
        raise GuildError("Chỉ Leader mới có thể giải tán Guild.")


def recruit_member(inviter_character_id: int, target_character_id: int):
    reason = db.recruit_guild_member_transaction(inviter_character_id, target_character_id)
    if reason == "no_permission":
        raise GuildError("Chỉ Leader hoặc Officer mới có thể tuyển thành viên.")
    if reason == "already_in_guild":
        raise GuildError("Người chơi này đã thuộc về một Guild khác.")


def leave_guild(character_id: int):
    if not db.leave_guild_transaction(character_id):
        raise GuildError(
            "Không thể rời Guild — bạn chưa có Guild, hoặc bạn là Leader và "
            "còn thành viên khác (hãy kick hết hoặc chuyển giao Guild trước)."
        )


def kick_member(kicker_character_id: int, target_character_id: int):
    if not db.kick_guild_member_transaction(kicker_character_id, target_character_id):
        raise GuildError("Không thể kick — bạn không có quyền, hoặc mục tiêu không hợp lệ.")


def deposit(character_id: int, amount: int):
    if amount <= 0:
        raise GuildError("Số tiền nộp quỹ phải lớn hơn 0.")
    if not db.deposit_guild_treasury_transaction(character_id, amount):
        raise GuildError("Không thể nộp quỹ — bạn chưa có Guild hoặc không đủ Bảng.")


def withdraw(character_id: int, amount: int):
    if amount <= 0:
        raise GuildError("Số tiền rút quỹ phải lớn hơn 0.")
    if not db.withdraw_guild_treasury_transaction(character_id, amount):
        raise GuildError("Không thể rút quỹ — chỉ Leader/Officer mới rút được, và quỹ phải đủ.")


def get_active_war(guild_id: int):
    return db.get_active_guild_war(guild_id)


def declare_war(character_id: int, defender_guild_id: int):
    war_id = db.declare_guild_war_transaction(character_id, defender_guild_id)
    if war_id is None:
        raise GuildError(
            "Không thể tuyên chiến — chỉ Leader mới tuyên chiến được, và một "
            "trong hai Guild có thể đang có chiến tranh khác."
        )
    return db.get_active_guild_war(defender_guild_id)


def contribute_war_score(character_id: int, war_id: int, points: int = 1):
    """Gọi từ pvp.py khi thắng một trận PvP nhắm vào thành viên Guild địch
    đang trong chiến tranh (mục 34 Wars — score thật, không phải hiển thị)."""
    return db.guild_war_contribute_transaction(character_id, war_id, points)

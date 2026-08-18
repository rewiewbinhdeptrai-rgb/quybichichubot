"""
World Event Engine (mục 47 trong spec).

Trigger -> World State (cities.economy/crime/mystical_activity thay đổi
THẬT ngay khi trigger, không chỉ hiển thị) -> Player có thể can thiệp
(contribute) bằng cách bỏ ra tài nguyên thật -> đủ ngưỡng thì Resolve (hoàn
tác đúng phần delta đã áp, city trở lại trạng thái trước Event) -> History
(ghi qua log_action + bảng world_events tự thân là History).

Event được Trigger từ chính luồng gameplay hiện có (world.travel()) — không
cần thêm scheduler/cron mới vào bot, đúng tinh thần "Event phải gắn với
World State thật", không phải job nền tách rời khỏi Engine.
"""
import random

import database as db
import ai_narrative
from data.world_events_seed import (
    WORLD_EVENT_TEMPLATES,
    TRAVEL_TRIGGER_CHANCE,
    CONTRIBUTION_PER_ACTION,
    CONTRIBUTION_COST_MONEY,
)

_THRESHOLD_BY_KEY = {t[0]: t[6] for t in WORLD_EVENT_TEMPLATES}


class WorldEventError(Exception):
    """Lỗi nghiệp vụ hiển thị thẳng cho người chơi."""


def list_active():
    return db.list_active_world_events()


def get_event(event_id: int):
    return db.get_world_event(event_id)


def get_active_event_for_city(city_id: str):
    for e in db.list_active_world_events():
        if e["city_id"] == city_id:
            return e
    return None


def maybe_trigger_on_travel(city_id: str):
    """Gọi từ world.travel() sau khi Character đặt chân tới city_id. Chỉ
    trigger nếu City chưa có Event active — tránh chồng nhiều Event cùng
    lúc một nơi, khiến delta cộng dồn không kiểm soát được."""
    if get_active_event_for_city(city_id):
        return None
    if random.random() >= TRAVEL_TRIGGER_CHANCE:
        return None
    return trigger_random(city_id)


def trigger_random(city_id: str):
    template = random.choice(WORLD_EVENT_TEMPLATES)
    event_key, name_vi, description_vi, economy_delta, crime_delta, mystical_delta, _threshold = template
    event_id = db.trigger_world_event_transaction(
        event_key, name_vi, description_vi, city_id, economy_delta, crime_delta, mystical_delta
    )
    event = db.get_world_event(event_id)
    event["narrative"] = _event_narrative(name_vi, description_vi, city_id)
    return event


def _event_narrative(name_vi: str, description_vi: str, city_id: str) -> str:
    """Diễn đạt lại mô tả Event tĩnh cho sống động hơn (mục 29-30) — KHÔNG
    đổi economy/crime/mystical delta đã áp thật lên City ở trigger_world_event_transaction().
    description_vi gốc trong DB (world_events.description_vi) không bị sửa,
    chỉ dòng hiển thị tức thời này được viết lại."""
    prompt = (
        f"Viết lại đoạn mô tả sự kiện thế giới sau cho sống động hơn, giữ "
        f"nguyên ý nghĩa, không quá 2 câu, không thêm số liệu mới. "
        f"Sự kiện: '{name_vi}' tại {city_id}. Mô tả gốc: \"{description_vi}\""
    )
    return ai_narrative.generate_line(prompt, fallback=description_vi)


def contribute(character_id: int, event_id: int):
    """Player bỏ CONTRIBUTION_COST_MONEY Bảng thật để góp CONTRIBUTION_PER_ACTION
    vào việc dẹp Event. Đủ ngưỡng resolve_threshold của template thì tự động
    Resolve — hoàn tác đúng phần delta đã áp lên City (mục 47)."""
    event = db.get_world_event(event_id)
    if event is None or event["stage"] != "active":
        raise WorldEventError("Sự kiện này không còn hoạt động.")

    character = db.get_character_by_id(character_id)
    if character is None or character["money"] < CONTRIBUTION_COST_MONEY:
        raise WorldEventError(f"Bạn không đủ {CONTRIBUTION_COST_MONEY} Bảng để can thiệp.")

    with db.get_conn() as conn:
        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?",
            (CONTRIBUTION_COST_MONEY, character_id),
        )
    db.contribute_to_world_event(event_id, character_id, CONTRIBUTION_PER_ACTION)
    db.log_action(character_id, "world_event_contribute", event["name_vi"])

    with db.get_conn() as conn:
        total = conn.execute(
            "SELECT COALESCE(SUM(contribution), 0) AS total FROM world_event_participants WHERE event_id = ?",
            (event_id,),
        ).fetchone()["total"]

    threshold = _THRESHOLD_BY_KEY.get(event["event_key"], 300)
    resolved = False
    if total >= threshold:
        resolved = db.resolve_world_event_transaction(event_id)
        if resolved:
            db.log_action(character_id, "world_event_resolved", event["name_vi"])

    return {"total_contribution": total, "threshold": threshold, "resolved": resolved}

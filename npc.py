"""
NPC Engine (mục 28 trong spec).

NPC đứng thật ở 1 Location (mục 31-32) và có Trust thật riêng cho từng
Character — không phải một biến toàn cục. Mọi tương tác đều được log vào
npc_memory (mục 28: "NPC phải nhớ hành động của người chơi"), không chỉ
lưu con số Trust cuối cùng.

Có AI Narrative layer tuỳ chọn (mục 29, qua ai_narrative.py): câu thoại
gốc luôn được Engine chọn tĩnh từ trust_tier trước — nếu có GEMINI_API_KEY,
câu đó được gửi qua Gemini để viết lại cho tự nhiên hơn; nếu không có key
hoặc Gemini lỗi, người chơi nhận lại đúng câu thoại tĩnh gốc, không có gì
thay đổi về gameplay. AI không có quyền chọn nội dung, chỉ diễn đạt lại.
"""
import random

import database as db
import ai_narrative
import world_event

TRUST_TIERS = [
    (60, "trusted"),
    (20, "acquaintance"),
    (0, "stranger"),
]

TALK_TRUST_GAIN = 1
GIFT_FAVORITE_TRUST_GAIN = 5
GIFT_NORMAL_TRUST_GAIN = 1

# mục 47 mở rộng: World Event phải lan xuống các hệ thống khác, không chỉ
# dừng ở City. Khi một Event làm crime_delta > 0 (bất ổn/nguy hiểm) đang
# active tại City của NPC, NPC cảnh giác hơn thật sự — Trust tăng chậm hơn,
# không chỉ là dòng text "thành phố đang bất ổn" vô nghĩa.
EVENT_DAMPENED_TRUST_FACTOR = 0.5


class NPCError(Exception):
    """Lỗi nghiệp vụ (NPC không ở đây, không đủ item...) — hiển thị thẳng
    cho người chơi, không phải bug."""


def trust_tier(trust: int) -> str:
    for threshold, tier in TRUST_TIERS:
        if trust >= threshold:
            return tier
    return "stranger"


def list_npcs_here(character: dict):
    """NPC thật đang đứng ở Location hiện tại của Character (mục 28+31-32
    liên kết thật, không phải danh sách tĩnh không phụ thuộc World)."""
    if not character or not character.get("location_id"):
        return []
    return db.list_npcs_at_location(character["location_id"])


def get_relationship(character_id: int, npc_id: str) -> dict:
    rel = db.get_character_npc(character_id, npc_id)
    rel["tier"] = trust_tier(rel["trust"])
    return rel


def _ensure_npc_here(character: dict, npc_id: str) -> dict:
    npc = db.get_npc(npc_id)
    if npc is None:
        raise NPCError("NPC này không tồn tại.")
    if npc["location_id"] != character.get("location_id"):
        raise NPCError(f"{npc['name_en']} không có ở đây — bạn cần tới đúng Location của họ.")
    return npc


def _dangerous_event_for_npc(npc: dict):
    """Trả về World Event đang active tại City của NPC nếu nó làm mất an
    ninh (crime_delta > 0 khi trigger) — dùng để dampen Trust gain thật
    (mục 47: Event phải ảnh hưởng NPC, không chỉ City)."""
    location = db.get_location(npc["location_id"])
    if location is None:
        return None
    event = world_event.get_active_event_for_city(location["city_id"])
    if event and event.get("crime_delta", 0) > 0:
        return event
    return None


def talk(character_id: int, character: dict, npc_id: str) -> dict:
    """Trò chuyện — miễn phí, +1 Trust thật, trả về 1 câu thoại tĩnh chọn
    ngẫu nhiên trong đúng trust_tier hiện tại (mục 28)."""
    npc = _ensure_npc_here(character, npc_id)

    rel = db.get_character_npc(character_id, npc_id)
    tier = trust_tier(rel["trust"])
    lines = db.get_npc_dialogue(npc_id, tier)
    base_line = random.choice(lines) if lines else "..."

    prompt = (
        f"Viết lại câu thoại sau bằng giọng văn tự nhiên hơn, giữ nguyên "
        f"ý nghĩa, không quá 2 câu, không thêm thông tin mới. "
        f"NPC: {npc['name_en']}. Mức độ thân thiết: {tier}. "
        f"Câu gốc: \"{base_line}\""
    )
    line = ai_narrative.generate_line(prompt, fallback=base_line)

    dangerous_event = _dangerous_event_for_npc(npc)
    trust_gain = TALK_TRUST_GAIN
    if dangerous_event:
        trust_gain = max(0, round(trust_gain * EVENT_DAMPENED_TRUST_FACTOR))

    new_trust = db.adjust_npc_trust(character_id, npc_id, trust_gain, "talk", detail=base_line)
    db.log_action(character_id, "npc_talk", npc["name_en"])
    return {
        "npc": npc,
        "line": line,
        "tier": tier,
        "trust": new_trust,
        "dangerous_event": dangerous_event["name_vi"] if dangerous_event else None,
    }


def give_gift(character_id: int, character: dict, npc_id: str, item_id: str) -> dict:
    """Tặng quà — trừ đúng 1 item khỏi Túi đồ thật (mục 22 Inventory), Trust
    tăng +5 nếu đúng món NPC thích, ngược lại +1 (mục 28: Relationship có
    thật, không phải phím tắt tăng số vô hạn)."""
    npc = _ensure_npc_here(character, npc_id)

    item = db.get_item(item_id)
    if item is None:
        raise NPCError("Vật phẩm này không tồn tại.")
    if not db.remove_inventory_item(character_id, item_id, 1):
        raise NPCError(f"Bạn không có {item['name_en']} trong Túi đồ.")

    is_favorite = npc["favorite_item_id"] == item_id
    gain = GIFT_FAVORITE_TRUST_GAIN if is_favorite else GIFT_NORMAL_TRUST_GAIN
    dangerous_event = _dangerous_event_for_npc(npc)
    if dangerous_event:
        gain = max(0, round(gain * EVENT_DAMPENED_TRUST_FACTOR))

    new_trust = db.adjust_npc_trust(character_id, npc_id, gain, "gift", detail=item["name_en"])
    db.log_action(character_id, "npc_gift", f"{npc['name_en']} <- {item['name_en']}")
    return {
        "npc": npc,
        "item": item,
        "is_favorite": is_favorite,
        "trust_gain": gain,
        "trust": new_trust,
        "dangerous_event": dangerous_event["name_vi"] if dangerous_event else None,
    }

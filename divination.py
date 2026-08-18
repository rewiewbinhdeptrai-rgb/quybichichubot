"""
Divination Engine (mục 19 trong spec).

Kết quả PHẢI do Engine tạo trước bằng roll thật (accuracy trừ Loss of Control
Risk hiện tại của Character) — AI (nếu gắn vào sau) chỉ được diễn đạt lại
tier đã có sẵn, không được tự quyết định kết quả (mục 19, 30).
"""
import random

import database as db
import effects
import ai_narrative
import loss_of_control

TIERS = ("clear", "vague", "failed", "ominous")

# Câu tĩnh dự phòng (mục 30: "Nếu API chết -> Fallback Content -> Game vẫn
# chạy") — AI (nếu khả dụng) chỉ VIẾT LẠI cho mượt hơn, không đổi ý nghĩa
# tier đã roll xong ở dưới.
_TIER_FALLBACK = {
    "clear": "Hình ảnh hiện lên rõ ràng, không chút mơ hồ.",
    "vague": "Có gì đó thấp thoáng, nhưng không đủ rõ để chắc chắn.",
    "failed": "Không có gì hiện lên cả — lần này vô hiệu.",
    "ominous": "Một cảm giác lạnh buốt lan qua người ngay khi hình ảnh vừa hiện lên.",
}


class DivinationError(Exception):
    """Lỗi nghiệp vụ (không đủ Spirituality, method không tồn tại...) —
    hiển thị thẳng cho người chơi, không phải bug."""


def list_methods():
    return db.list_divination_methods()


def perform(character: dict, method_id: str) -> dict:
    method = db.get_divination_method(method_id)
    if method is None:
        raise DivinationError("Phương pháp Bói toán này chưa khả dụng.")

    if character["spirituality"] < method["spirituality_cost"]:
        raise DivinationError(
            f"Không đủ Spirituality (cần {method['spirituality_cost']}, "
            f"hiện có {character['spirituality']})."
        )

    character_id = character["character_id"]
    new_spirituality = character["spirituality"] - method["spirituality_cost"]
    db.set_character_hp_spirituality(character_id, character["hp"], new_spirituality)

    risk_penalty = character.get("loss_of_control_risk", 0) or 0
    accuracy = max(5, min(95, method["base_accuracy"] - risk_penalty))
    roll = random.randint(1, 100)

    if roll <= accuracy - 40:
        tier = "clear"
    elif roll <= accuracy:
        tier = "vague"
    elif roll <= accuracy + 25:
        tier = "failed"
    else:
        tier = "ominous"

    incident = None
    if tier == "ominous":
        # mục 13: chạm phải điều không nên biết -> phản chấn tinh thần thật,
        # không chỉ là dòng chữ "điềm xấu" trên Embed.
        effects.apply_effect(character_id, "divination_backlash", source=f"divination:{method_id}")
        # Trước đây chỉ apply_effect (debuff), Risk được compute_risk() TÍNH ra
        # nhưng resolve_incident() (hàm áp hậu quả thật theo 4 tier mục 13)
        # không bao giờ được GỌI ở đây -> Loss of Control chỉ là con số trang
        # trí. "ominous" là đúng mốc rủi ro cao mà loss_of_control.py tự mô tả
        # là nơi nên gọi resolve_incident() -> giờ gọi thật.
        loss_of_control.compute_risk(character_id)
        incident = loss_of_control.resolve_incident(character_id)

    db.log_divination(character_id, method_id, tier, roll, accuracy)
    db.log_action(character_id, "divination", f"{method['name_en']} -> {tier}")

    fallback = _TIER_FALLBACK[tier]
    prompt = (
        f"Viết 1 câu tường thuật ngắn (không quá 2 câu) mô tả kết quả một "
        f"buổi {method['name_en']}, không tiết lộ thông tin cụ thể nào (vì "
        f"Engine chưa sinh nội dung tiên tri cụ thể), chỉ mô tả KHÔNG KHÍ "
        f"của kết quả mức độ '{tier}'. Câu gốc tham khảo: \"{fallback}\""
    )
    narrative = ai_narrative.generate_line(prompt, fallback=fallback)

    return {
        "method": method, "tier": tier, "roll": roll, "accuracy": accuracy,
        "spirituality": new_spirituality, "narrative": narrative, "incident": incident,
    }

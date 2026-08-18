"""
Loss of Control Risk Engine (mục 13 trong spec).

Trước bản này, characters.loss_of_control_risk là một con số tĩnh do nơi khác
tự set — không có Engine nào thật sự TÍNH nó. File này thay thế bằng công thức
đa yếu tố đúng như spec yêu cầu:

    Spirituality + Mental State + Potion Stability + Digestion status
    + Beyonder Characteristic (instability) + Artifact/Effect (loss_of_control_risk_flat)
    + Sequence (càng sâu càng nguy hiểm)
    ↓
    compute_risk() -> % Risk 0-100, LƯU THẬT vào characters.loss_of_control_risk

resolve_incident() roll ngẫu nhiên dựa trên % đó; nếu trúng, áp hậu quả THẬT
(trừ HP/Spirituality/Mental State, áp debuff qua EffectEngine, có thể làm gián
đoạn Digestion) theo đúng 4 tier Nhẹ/Trung bình/Nặng/Cực nặng của spec — không
chỉ là dòng text mô tả suông.

Nơi gọi: sau bất kỳ hành động đáng kể nào (Acting action, Ritual, Divination,
Mysticism, Combat, Black Market...) service layer nên gọi compute_risk() để
cập nhật số hiển thị, và có thể gọi resolve_incident() ở các mốc rủi ro cao
(sau Ritual thất bại, sau Divination "ominous", v.v.) — quyết định GỌI hay
KHÔNG vẫn nằm ở gameplay layer, engine này chỉ chịu trách nhiệm tính toán.
"""
import random

import database as db
import effects


# Trọng số từng yếu tố — điều chỉnh tại đây khi cần cân bằng lại, không rải
# rác magic number khắp nơi khác.
WEIGHT_SPIRITUALITY_DEFICIT = 15   # % Risk tối đa đến từ Spirituality cạn kiệt
WEIGHT_MENTAL_STATE_DEFICIT = 20   # % Risk tối đa đến từ Mental State thấp
WEIGHT_INJURY_DEFICIT = 10         # % Risk tối đa đến từ HP thấp (Injury)
WEIGHT_SEQUENCE_DEPTH = 2          # % Risk / bậc Sequence dưới 9 (càng sâu càng nguy hiểm)
POTION_INSTABILITY_FACTOR = 0.2    # % Risk / điểm (100 - potion.stability), chỉ khi đang digesting
CHARACTERISTIC_INSTABILITY_FACTOR = 0.1  # % Risk / điểm (100 - stability) mỗi Characteristic đang lưu, cộng dồn
CHARACTERISTIC_INSTABILITY_CAP = 20      # trần cộng dồn từ Characteristic, tránh 1 Character sở hữu nhiều items làm risk vọt phi lý


def compute_risk(character_id: int) -> dict:
    """Tính lại Risk đa yếu tố, LƯU vào DB, và trả breakdown để UI hiển thị
    minh bạch từng thành phần (đúng tinh thần mục 13: Engine tính, không phải
    một con số bí ẩn)."""
    inputs = db.get_risk_inputs(character_id)
    if inputs is None:
        raise ValueError(f"Character {character_id} không tồn tại.")

    character = inputs["character"]
    breakdown = {}

    spirituality_ratio = character["spirituality"] / max(1, character["spirituality_max"])
    breakdown["spirituality"] = round((1 - spirituality_ratio) * WEIGHT_SPIRITUALITY_DEFICIT, 1)

    mental_state = character.get("mental_state", 100) or 100
    breakdown["mental_state"] = round((1 - mental_state / 100) * WEIGHT_MENTAL_STATE_DEFICIT, 1)

    hp_ratio = character["hp"] / max(1, character["hp_max"])
    breakdown["injury"] = round((1 - hp_ratio) * WEIGHT_INJURY_DEFICIT, 1)

    sequence_number = character.get("sequence_number", 9) if character.get("pathway_id") else 9
    breakdown["sequence_depth"] = round(max(0, 9 - sequence_number) * WEIGHT_SEQUENCE_DEPTH, 1)

    potion_stability = inputs["potion_stability"]
    if inputs["digestion_status"] == "digesting" and potion_stability is not None:
        breakdown["potion_instability"] = round((100 - potion_stability) * POTION_INSTABILITY_FACTOR, 1)
    else:
        breakdown["potion_instability"] = 0.0

    char_instability = sum((100 - s) * CHARACTERISTIC_INSTABILITY_FACTOR for s in inputs["characteristic_stabilities"])
    breakdown["characteristic_instability"] = round(min(CHARACTERISTIC_INSTABILITY_CAP, char_instability), 1)

    # Artifact/Ritual backlash/Divination backlash... mọi effect_flat đang active
    # cộng dồn qua EffectEngine — engine này không tự biết nguồn gốc từng effect,
    # chỉ đọc modifier_key chung (đúng nguyên tắc EffectEngine dùng chung, mục 16).
    breakdown["active_effects"] = round(effects.get_modifier_sum(character_id, "loss_of_control_risk_flat"), 1)

    total = sum(breakdown.values())
    total = max(0, min(100, round(total)))

    db.update_character_risk(character_id, total)

    return {"total": total, "breakdown": breakdown}


def _severity_for(risk: int) -> str:
    if risk < 30:
        return "light"
    if risk < 60:
        return "moderate"
    if risk < 85:
        return "severe"
    return "critical"


SEVERITY_LABEL_VI = {
    "light": "Nhẹ",
    "moderate": "Trung bình",
    "severe": "Nặng",
    "critical": "Cực nặng",
}


def resolve_incident(character_id: int, force: bool = False) -> dict | None:
    """Roll 1 lần dựa trên Risk hiện tại (đã compute_risk() trước đó). Nếu
    không trúng, trả None (không có gì xảy ra — không giả vờ có sự cố).
    Nếu trúng, áp hậu quả THẬT theo đúng 4 tier của mục 13 và trả breakdown
    cho UI/AI Narrative mô tả lại (AI chỉ diễn đạt, không quyết định — mục 13,
    29)."""
    character = db.get_character_by_id(character_id)
    if character is None:
        return None

    risk = character["loss_of_control_risk"]
    roll = random.randint(1, 100)
    if not force and roll > risk:
        return None

    severity = _severity_for(risk)
    result = {"severity": severity, "severity_label_vi": SEVERITY_LABEL_VI[severity], "risk_at_trigger": risk}

    if severity == "light":
        new_spirituality = max(0, round(character["spirituality"] * 0.9))
        db.set_character_hp_spirituality(character_id, character["hp"], new_spirituality)
        db.adjust_mental_state(character_id, -10)
        effects.apply_effect(character_id, "mental_disturbance", source="loss_of_control")
        result["effects"] = ["-10% Spirituality", "-10 Mental State", "Debuff: Mental Disturbance"]

    elif severity == "moderate":
        new_spirituality = max(0, round(character["spirituality"] * 0.75))
        db.set_character_hp_spirituality(character_id, character["hp"], new_spirituality)
        db.adjust_mental_state(character_id, -20)
        effects.apply_effect(character_id, "confused_state", source="loss_of_control")
        result["effects"] = ["-25% Spirituality", "-20 Mental State", "Debuff: Confused"]

    elif severity == "severe":
        new_hp = max(1, round(character["hp"] * 0.85))
        new_spirituality = max(0, round(character["spirituality"] * 0.6))
        db.set_character_hp_spirituality(character_id, new_hp, new_spirituality)
        db.adjust_mental_state(character_id, -35)
        effects.apply_effect(character_id, "control_lost_temp", source="loss_of_control")
        db.interrupt_digestion(character_id, digestion_loss_pct=15)
        result["effects"] = [
            "-15% HP", "-40% Spirituality", "-35 Mental State",
            "Debuff: Temporary Loss of Control", "Digestion -15% (gián đoạn)",
        ]

    else:  # critical
        new_hp = max(1, round(character["hp"] * 0.6))
        new_spirituality = max(0, round(character["spirituality"] * 0.5))
        db.set_character_hp_spirituality(character_id, new_hp, new_spirituality)
        db.adjust_mental_state(character_id, -60)
        effects.apply_effect(character_id, "post_incident_trauma", source="loss_of_control")
        db.interrupt_digestion(character_id, digestion_loss_pct=50)
        result["effects"] = [
            "-40% HP", "-50% Spirituality", "-60 Mental State",
            "Debuff: Post-Incident Trauma", "Digestion -50% (gián đoạn nặng)",
        ]

    # Sau sự cố, tính lại Risk (Mental State/HP/Spirituality vừa thay đổi thật)
    compute_risk(character_id)
    return result

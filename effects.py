"""
EffectEngine — module trung tâm xử lý Buff/Debuff (mục 15-16 spec).

QUY TẮC BẮT BUỘC (mục 15, 51): nếu UI hiển thị một buff, nó phải thực sự
làm thay đổi số liệu Engine tính ra — không có buff nào chỉ tồn tại trên
Embed. Mọi hệ thống khác (Combat, Potion/Digestion, Artifact...) đều phải
đọc modifier qua get_modifier_sum() ở đây, KHÔNG tự cộng trừ riêng.
"""
import database as db


def apply_effect(character_id: int, effect_id: str, source: str, duration: int = None, stacks: int = 1):
    """Áp effect lên Character. Trả về effect definition đã áp dụng."""
    definition = db.get_effect_definition(effect_id)
    if definition is None:
        raise ValueError(f"Effect '{effect_id}' chưa được định nghĩa trong effect_definitions.")

    final_duration = duration if duration is not None else definition["default_duration"]
    db.add_character_effect(character_id, effect_id, source, final_duration, stacks)
    return definition


def list_active_effects(character_id: int):
    return db.list_character_effects(character_id)


def get_modifier_sum(character_id: int, modifier_key: str) -> float:
    """Cộng dồn giá trị modifier (theo stacks) từ mọi effect đang active có
    cùng modifier_key. Đây là hàm mà mọi công thức tính toán (damage,
    digestion, risk...) phải gọi thay vì đọc trực tiếp text buff."""
    total = 0.0
    for effect in db.list_character_effects(character_id):
        if effect["modifier_key"] == modifier_key:
            total += effect["modifier_value"] * effect["stacks"]
    return total


def tick(character_id: int):
    """Giảm duration của mọi effect đi 1 lượt — gọi sau mỗi hành động đáng kể
    (Acting action, đòn combat, ...) để buff/debuff thực sự hết hạn theo thời gian."""
    db.tick_character_effects(character_id)


def clear_all(character_id: int):
    db.clear_character_effects(character_id)


# ---------------------------------------------------------------------------
# Ví dụ áp dụng thật — mục 15 yêu cầu: "Base Damage -> Buff Modifier -> Final Damage"
# ---------------------------------------------------------------------------

def calculate_damage(character_id: int, base_damage: float) -> int:
    """Damage cuối cùng SAU khi cộng % từ mọi buff/debuff physical_damage_pct
    đang active. Dùng hàm này (thay vì base_damage thẳng) ở bất kỳ đâu tính
    sát thương, để buff luôn có hiệu lực thật thay vì chỉ hiện trên UI."""
    pct = get_modifier_sum(character_id, "physical_damage_pct")
    final_damage = base_damage * (1 + pct / 100)
    return max(0, round(final_damage))


def get_loss_of_control_risk(character_id: int, base_risk: int) -> int:
    """Risk % cuối cùng = base_risk (do Spirituality/Sequence/... quyết định
    ở nơi khác) + tổng modifier loss_of_control_risk_flat từ effect đang active."""
    flat = get_modifier_sum(character_id, "loss_of_control_risk_flat")
    return max(0, min(100, round(base_risk + flat)))


def calculate_incoming_damage(character_id: int, base_damage: float) -> int:
    """Sát thương THỰC nhận vào sau khi cộng % từ buff/debuff damage_taken_pct
    (vd hành động Phòng thủ). Dùng trong combat.py thay vì trừ HP trực tiếp."""
    pct = get_modifier_sum(character_id, "damage_taken_pct")
    final_damage = base_damage * (1 + pct / 100)
    return max(0, round(final_damage))

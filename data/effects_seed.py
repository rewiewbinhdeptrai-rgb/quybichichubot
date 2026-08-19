"""
Định nghĩa tĩnh cho Effect (buff/debuff) — mục 15-16 trong spec.

modifier_key là "chìa khóa" mà các hệ thống khác (combat, digestion, ...)
đọc ra để tính toán thật, KHÔNG chỉ hiển thị text suông.

Các modifier_key đang được EffectEngine/progression.py thực sự sử dụng:
- physical_damage_pct      : cộng dồn %, dùng trong effects.calculate_damage()
- loss_of_control_risk_flat: cộng dồn thẳng vào % Loss of Control Risk
- spirituality_regen_flat  : cộng dồn vào lượng Spirituality hồi mỗi lần tick
"""

EFFECT_DEFINITIONS = [
    # (effect_id, name_en, type, description, default_duration, modifier_key, modifier_value)
    (
        "strengthened_body", "Cường Hóa Thân Thể", "buff",
        "Physical Damage +15%", 3, "physical_damage_pct", 15,
    ),
    (
        "weakened", "Suy Yếu", "debuff",
        "Physical Damage -20%", 2, "physical_damage_pct", -20,
    ),
    (
        "potion_instability", "Dược Tính Bất Ổn", "debuff",
        "Vừa uống Potion — cơ thể chưa thích nghi, tăng nguy cơ mất kiểm soát.",
        5, "loss_of_control_risk_flat", 5,
    ),
    (
        "newly_advanced", "Vừa Thăng Cấp", "buff",
        "Vừa tiến cấp thành công — tinh thần ổn định hơn, hồi Spirituality nhanh hơn.",
        5, "spirituality_regen_flat", 5,
    ),
    (
        "ritual_backlash", "Phản Phệ Nghi Thức", "debuff",
        "Nghi thức tiến cấp thất bại — phản chấn tinh thần.",
        4, "loss_of_control_risk_flat", 15,
    ),
    (
        "defending", "Phòng thủ", "buff",
        "Đang thủ thế — giảm 30% sát thương nhận vào ở lượt kế tiếp.",
        1, "damage_taken_pct", -30,
    ),
    # --- Divination (mục 19) ---
    (
        "divination_backlash", "Phản Phệ Bói Toán", "debuff",
        "Một lần Bói toán \"ominous\" — chạm vào điều không nên biết.",
        3, "loss_of_control_risk_flat", 8,
    ),
    # --- Mysticism Knowledge (mục 18) ---
    (
        "mysticism_overreach", "Bí Thuật Quá Giới Hạn", "debuff",
        "Thấu hiểu kiến thức Huyền bí quá sâu — tâm trí quá tải tạm thời.",
        4, "loss_of_control_risk_flat", 10,
    ),
    (
        "mystic_insight", "Linh Cảm Huyền Bí", "buff",
        "Đã Thấu hiểu kỹ thuật ổn định tinh thần — Loss of Control Risk -5 (vĩnh viễn trong phiên chơi).",
        999999, "loss_of_control_risk_flat", -5,
    ),
    # --- Loss of Control incident outcomes (mục 13) — mỗi tier phải có hiệu lực
    # thật qua modifier_key đã được EffectEngine/combat/digestion tiêu thụ, không
    # chỉ là debuff hiển thị suông. ---
    (
        "mental_disturbance", "Tinh Thần Nhiễu Loạn", "debuff",
        "Sự cố mất kiểm soát mức Nhẹ — tinh thần dao động, dễ mất kiểm soát hơn nữa.",
        3, "loss_of_control_risk_flat", 6,
    ),
    (
        "confused_state", "Hoang Mang", "debuff",
        "Sự cố mất kiểm soát mức Trung bình — ảo giác thoáng qua khiến đòn đánh thiếu chính xác.",
        3, "physical_damage_pct", -20,
    ),
    (
        "control_lost_temp", "Mất Kiểm Soát Tạm Thời", "debuff",
        "Sự cố mất kiểm soát mức Nặng — cơ thể phản ứng chậm, dễ trúng đòn hơn hẳn.",
        3, "damage_taken_pct", 25,
    ),
    (
        "post_incident_trauma", "Chấn Thương Tâm Lý Hậu Sự Cố", "debuff",
        "Vừa trải qua một sự cố mất kiểm soát Cực nặng — dư chấn còn kéo dài, nguy cơ tái phát cao.",
        5, "loss_of_control_risk_flat", 12,
    ),
    # --- Black Market trap outcome (mục 41) ---
    (
        "black_market_trap", "Hàng Hóa Bị Phá Hoại", "debuff",
        "Vừa dính bẫy khi mua hàng ở Chợ đen — cơ thể phản ứng xấu với món hàng lậu.",
        4, "physical_damage_pct", -15,
    ),
]

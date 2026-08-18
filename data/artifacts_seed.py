"""
Sealed Artifact tĩnh (mục 22 trong spec).

Artifact KHÔNG phải "ATK +500" — mỗi Artifact có Effect + Rule + Side Effect +
Risk + Sealing Method + Usage Limit thật, và Effect/Side Effect đi thẳng qua
EffectEngine (effects.py) như mọi buff/debuff khác trong hệ thống — không
phải text hiển thị suông (mục 15, 51).

ARTIFACT_EFFECT_DEFINITIONS: định nghĩa modifier thật cho từng Effect/Side
Effect riêng của từng Artifact — được database.init_db() gộp chung vào bảng
effect_definitions cùng với EFFECT_DEFINITIONS ở effects_seed.py.

ARTIFACTS: (artifact_id, name_en, grade, origin, sealing_method, risk_stars,
            effect_id, side_effect_id, side_effect_chance, usage_limit, inspect_hint)
- usage_limit = -1 nghĩa là không giới hạn số lần Experiment.
- side_effect_chance: % (0-100) Side Effect kích hoạt mỗi lần Experiment.

ARTIFACT_RULES: (artifact_id, stage, text_vi) — nội dung tiết lộ dần theo
Inspect (mục 22: Unknown -> Inspect -> Research -> Experiment -> Discover Rule).
stage thuộc {"effect", "rule", "side_effect"}.

Trạng thái dữ liệu: 4 Artifact demo, đủ để chạy full flow Inspect/Experiment/
Discovery thật — CHƯA phải kho Artifact đầy đủ theo lore Quỷ Bí (cần mở rộng
sau, giống tình trạng ingredient/ritual material hiện tại).
"""

ARTIFACT_EFFECT_DEFINITIONS = [
    # (effect_id, name_en, type, description, default_duration, modifier_key, modifier_value)
    (
        "artifact_pocket_watch_effect", "Reversed Ticking", "buff",
        "Đồng hồ chạy ngược tích tắc — hồi Spirituality nhanh hơn.",
        4, "spirituality_regen_flat", 8,
    ),
    (
        "artifact_pocket_watch_side", "Temporal Disorientation", "debuff",
        "Cảm giác lệch thời gian sau khi dùng đồng hồ — tăng nguy cơ mất kiểm soát.",
        3, "loss_of_control_risk_flat", 5,
    ),
    (
        "artifact_widows_veil_effect", "Veiled Strike", "buff",
        "Tấm màn che giấu sát khí thật — Physical Damage +25%.",
        3, "physical_damage_pct", 25,
    ),
    (
        "artifact_widows_veil_side", "Exposed", "debuff",
        "Sơ hở sau đòn đánh dưới màn che — Damage nhận vào +15%.",
        3, "damage_taken_pct", 15,
    ),
    (
        "artifact_seal_fragment_effect", "Stabilized Will", "buff",
        "Mảnh ấn tín ổn định ý chí — Loss of Control Risk -10.",
        5, "loss_of_control_risk_flat", -10,
    ),
    (
        "artifact_seal_fragment_side", "Will Drain", "debuff",
        "Cái giá của sự ổn định — hao hụt hồi phục Spirituality.",
        5, "spirituality_regen_flat", -5,
    ),
    (
        "artifact_unknown_vial_effect", "Unknown Ward", "buff",
        "Chất lỏng trong lọ tạo một lớp bảo vệ mơ hồ — Damage nhận vào -10%.",
        3, "damage_taken_pct", -10,
    ),
    (
        "artifact_unknown_vial_side", "Numbness", "debuff",
        "Tay chân tê dại sau khi tiếp xúc — Physical Damage -10%.",
        3, "physical_damage_pct", -10,
    ),
]

ARTIFACTS = [
    (
        "tarnished_pocket_watch", "Tarnished Pocket Watch", "minor",
        "Cửa hàng đồ cổ không tên ở Backlund", "Hộp kính niêm sáp",
        2, "artifact_pocket_watch_effect", "artifact_pocket_watch_side", 20, 5,
        "Kim đồng hồ đôi khi chạy ngược trong tích tắc, dù mặt kính vẫn nguyên vẹn.",
    ),
    (
        "widows_veil_ring", "Widow's Veil Ring", "moderate",
        "Di vật của một góa phụ mất tích", "Khắc ký hiệu bên trong nhẫn, không thể tháo bằng lực thường",
        3, "artifact_widows_veil_effect", "artifact_widows_veil_side", 35, 3,
        "Chiếc nhẫn ấm lên bất thường khi ở gần xung đột.",
    ),
    (
        "black_emperor_seal_fragment", "Black Emperor Seal Fragment", "major",
        "Vỡ ra từ một Sealed Artifact lớn hơn, nguồn gốc không rõ", "Bọc trong vải đen tẩm nghi thức",
        4, "artifact_seal_fragment_effect", "artifact_seal_fragment_side", 40, 2,
        "Mảnh ấn phát ra một áp lực tinh thần trầm ổn, như đang quan sát ngược lại người cầm.",
    ),
    (
        "unlabeled_glass_vial", "Unlabeled Glass Vial", "unknown",
        "Không rõ — tìm thấy trong hành trang khởi đầu", "Nút chai niêm chì, chưa từng bị mở",
        5, "artifact_unknown_vial_effect", "artifact_unknown_vial_side", 30, 4,
        "Chất lỏng bên trong không có màu, không có mùi, và không đứng yên.",
    ),
]

ARTIFACT_RULES = [
    ("tarnished_pocket_watch", "effect", "Effect: Hồi thêm Spirituality khi kích hoạt (Reversed Ticking)."),
    ("tarnished_pocket_watch", "rule", "Rule: Chỉ kích hoạt được khi tự tay lên dây cót — không thể dùng qua trung gian."),
    ("tarnished_pocket_watch", "side_effect", "Side Effect: Có thể gây Temporal Disorientation, tăng Loss of Control Risk."),
    ("widows_veil_ring", "effect", "Effect: Tăng mạnh Physical Damage trong thời gian ngắn (Veiled Strike)."),
    ("widows_veil_ring", "rule", "Rule: Chỉ có hiệu lực khi đeo trực tiếp lên ngón tay, không thể dùng qua túi đồ."),
    ("widows_veil_ring", "side_effect", "Side Effect: Exposed — sát thương nhận vào tăng ngay sau đòn đánh."),
    ("black_emperor_seal_fragment", "effect", "Effect: Ổn định ý chí, giảm mạnh Loss of Control Risk tạm thời."),
    ("black_emperor_seal_fragment", "rule", "Rule: Chỉ phát huy hiệu lực khi Character đang mang một Beyonder Characteristic đang giữ (chưa được Engine ràng buộc cứng — ghi nhận lore, chưa validate)."),
    ("black_emperor_seal_fragment", "side_effect", "Side Effect: Will Drain — làm chậm hồi phục Spirituality."),
    ("unlabeled_glass_vial", "effect", "Effect: Tạo lớp bảo vệ mơ hồ, giảm sát thương nhận vào (Unknown Ward)."),
    ("unlabeled_glass_vial", "rule", "Rule: Không rõ cơ chế kích hoạt chính xác — chỉ biết được là có tác dụng khi tiếp xúc trực tiếp."),
    ("unlabeled_glass_vial", "side_effect", "Side Effect: Numbness — giảm tạm thời Physical Damage sau khi dùng."),
]

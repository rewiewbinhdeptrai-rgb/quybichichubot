"""
Mysticism Knowledge tĩnh (mục 18 trong spec).

Flow bắt buộc: Unknown -> Discovered -> Studied -> Understood.
Character KHÔNG có row trong character_knowledge nghĩa là "Unknown" (ngầm
định, không cần lưu). Mỗi bước tốn Spirituality thật (mysticism.py), và
"Understood" có % Risk thật gây Loss of Control (mục 13, 18).

(knowledge_id, name_en, category, description_vi, discover_cost, study_cost,
 understand_cost, understand_risk, unlock_effect_id)

unlock_effect_id: effect_id trong effect_definitions được áp VĨNH VIỄN
(duration cực lớn) khi Understood — None nếu kiến thức chỉ mang tính lore/
mở khóa Divination/Investigation sau này, chưa có phần thưởng cơ chế.
"""

KNOWLEDGE_DEFINITIONS = [
    (
        "ritual_symbols_101", "Basic Ritual Symbols", "symbol",
        "Ký hiệu nghi thức cơ bản dùng để khoanh vùng năng lượng huyền bí.",
        5, 10, 15, 5, None,
    ),
    (
        "astral_pattern_reading", "Astral Pattern Reading", "symbol",
        "Cách đọc quỹ đạo sao trời liên hệ tới vận mệnh cá nhân.",
        5, 10, 15, 8, None,
    ),
    (
        "spirit_world_glimpse", "Glimpse of the Spirit World", "spirit_world",
        "Một cái nhìn thoáng qua vào thế giới linh hồn song song với thực tại.",
        8, 15, 20, 15, None,
    ),
    (
        "mystic_stabilization_technique", "Mystic Stabilization Technique", "ritual_knowledge",
        "Kỹ thuật hít thở và tập trung giúp ổn định tinh thần khi tiếp xúc Huyền bí.",
        6, 12, 18, 10, "mystic_insight",
    ),
    (
        "forbidden_grimoire_fragment", "Forbidden Grimoire Fragment", "secret",
        "Một đoạn trích từ cuốn sách cấm — nội dung không được phép sao chép lại ở đây.",
        10, 20, 25, 25, None,
    ),
]

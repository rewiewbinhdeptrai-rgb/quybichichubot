"""
Divination Method tĩnh (mục 19 trong spec).

Kết quả Divination phải do Engine tạo trước (roll thật dựa trên accuracy +
Loss of Control Risk hiện tại của Character), AI (nếu có sau này) chỉ được
diễn đạt lại — không được tự quyết định tier (mục 19, 30).

(method_id, name_en, spirituality_cost, base_accuracy, risk_stars)

Trạng thái dữ liệu: 5/8 phương pháp trong spec mục 19 đã có Engine thật chạy
được (Tarot, Crystal Ball, Astrology, Dream, Spiritual Perception). Item/
Location/Person Divination (soi vật phẩm/địa điểm/nhân vật cụ thể) CHƯA làm —
cần World/NPC Engine (mục 27-28) tồn tại trước để có mục tiêu thật để soi.
"""

DIVINATION_METHODS = [
    ("tarot", "Tarot Reading", 10, 70, 2),
    ("crystal_ball", "Crystal Ball", 15, 65, 2),
    ("astrology", "Astrology Chart", 12, 60, 1),
    ("dream", "Dream Divination", 8, 55, 3),
    ("spiritual_perception", "Spiritual Perception", 20, 75, 3),
]

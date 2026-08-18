"""
Seed templates cho World Event (mục 47). Mỗi lần trigger, Engine chọn ngẫu
nhiên 1 template rồi áp dụng THẬT lên City (economy/crime/mystical_activity)
qua database.trigger_world_event_transaction() — không phải chỉ hiển thị.

resolve_threshold: tổng contribution (từ contribute_to_world_event, do Player
bỏ công sức xử lý) cần đạt để Event tự động Resolve sớm (hoàn tác delta).
Nếu không ai can thiệp, Event vẫn tồn tại ở stage='active' cho tới khi được
resolve thủ công hoặc bởi Event tiếp theo cùng City ghi đè.
"""

# (event_key, name_vi, description_vi, economy_delta, crime_delta, mystical_delta, resolve_threshold)
WORLD_EVENT_TEMPLATES = [
    (
        "cult_uprising",
        "Giáo phái nổi dậy",
        "Một giáo phái bí mật vừa tiến hành nghi thức lớn giữa đêm, khiến an ninh "
        "thành phố hỗn loạn và mức độ huyền bí tăng vọt.",
        -8, 15, 20, 300,
    ),
    (
        "market_boom",
        "Bùng nổ thương mại",
        "Một đoàn tàu buôn khổng lồ vừa cập cảng, mang theo hàng hóa dồi dào và "
        "thúc đẩy kinh tế thành phố.",
        15, 3, -2, 200,
    ),
    (
        "serial_disappearances",
        "Hàng loạt vụ mất tích bí ẩn",
        "Nhiều cư dân đã biến mất không dấu vết trong tuần qua, gieo rắc hoang mang "
        "và thu hút sự chú ý của những kẻ ưa thích điều tra huyền bí.",
        -5, 10, 12, 250,
    ),
    (
        "church_pilgrimage",
        "Đoàn hành hương Nhà Thờ",
        "Một đoàn hành hương lớn đổ về thành phố, mang theo cả lòng sùng kính lẫn "
        "những kẻ trà trộn mưu đồ riêng.",
        5, -3, 10, 200,
    ),
    (
        "gang_war",
        "Chiến tranh băng đảng",
        "Xung đột giữa các băng nhóm tội phạm bùng nổ trên đường phố, an ninh thành "
        "phố xuống cấp nghiêm trọng.",
        -12, 25, 0, 350,
    ),
    (
        "mystical_convergence",
        "Hội tụ huyền bí",
        "Một hiện tượng thiên văn hiếm gặp khiến ranh giới giữa thực tại và những gì "
        "ẩn giấu trở nên mong manh hơn bao giờ hết.",
        0, 5, 30, 400,
    ),
]

# Xác suất (0-1) một Event mới được Trigger mỗi khi Player Travel tới một
# City hiện KHÔNG có Event active — đây là "Trigger" thật của mục 47, không
# phải cron job giả lập.
TRAVEL_TRIGGER_CHANCE = 0.12

# Player bỏ công (mất tiền thật) để đóng góp dẹp Event — mỗi lần góp bao
# nhiêu contribution và tốn bao nhiêu Bảng.
CONTRIBUTION_PER_ACTION = 40
CONTRIBUTION_COST_MONEY = 100

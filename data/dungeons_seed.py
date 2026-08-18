"""
Seed dữ liệu Dungeon (mục 26 trong spec).

monster_pool: chuỗi các monster_id cách nhau bởi dấu phẩy — Room thường (không
phải Boss) chọn ngẫu nhiên 1 con trong pool này theo seed của run.
"""

# (dungeon_id, name_en, name_vi, description_vi, location_id, room_count,
#  monster_pool, boss_monster_id, reward_money, reward_exp, reward_item_id)
DUNGEONS = [
    (
        "backlund_slums_hideout",
        "The Slums Hideout",
        "Sào Huyệt Khu Ổ Chuột",
        "Một mạng lưới hầm trú ẩn dưới Khu ổ chuột Backlund, nơi một giáo phái "
        "bí mật đang tiến hành các nghi thức cấm kỵ. Đồn rằng có một Thực Thể "
        "bị bỏ rơi đang ẩn mình ở phòng sâu nhất.",
        "backlund_slums",
        5,
        "street_thug,cult_fanatic,slum_grave_robber,ghoul",
        "forsaken_dockworker_horror",
        800,
        400,
        "ing_miracle_dust",
    ),
    (
        "migas_sunken_ruins",
        "The Sunken Ruins of Migas",
        "Phế Tích Chìm Migas",
        "Tàn tích của một nền văn minh tiền-Cách-Mạng-Công-Nghiệp bị cát sa mạc "
        "chôn vùi. Những cạm bẫy cổ xưa vẫn còn hoạt động, và thứ gì đó vẫn còn "
        "canh giữ căn phòng trung tâm.",
        "migas_ruins",
        6,
        "sand_wraith,hound_of_bones,cult_fanatic",
        "sand_pharaoh_remnant",
        1200,
        650,
        "ing_old_tome_page",
    ),
]

# Các sự kiện phòng không-chiến-đấu (mục 26: Treasure / Trap / Secret).
# roll_weight dùng để random.choices weighted theo tổng của TRAP_TREASURE_EVENTS.
# (event_type, name_vi, roll_weight, money_delta_min, money_delta_max, hp_delta_min, hp_delta_max)
ROOM_EVENTS = [
    ("treasure", "🎁 Rương kho báu", 3, 50, 300, 0, 0),
    ("trap", "⚠️ Cạm bẫy cổ xưa", 3, -100, -20, -25, -5),
    ("secret", "🔍 Lối đi bí mật", 2, 20, 150, 0, 0),
]

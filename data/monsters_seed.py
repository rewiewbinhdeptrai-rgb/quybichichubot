"""
Dữ liệu Monster tĩnh cho PvE (mục 25).

Bản demo — 3 Monster độ khó tăng dần. Mở rộng thêm rank/location/weakness/
resistance/drop table theo mục 25 khi cần.
"""

MONSTERS = [
    # (monster_id, name_en, hp, attack, reward_money, reward_exp, drop_item_id, drop_chance)
    ("street_thug", "Kẻ Côn Đồ Đường Phố", 40, 6, 30, 15, "rusty_dagger", 0.20),
    ("ghoul", "Ghoul", 70, 10, 60, 30, "spirit_incense", 0.25),
    ("hound_of_bones", "Khuyển Cốt", 110, 14, 120, 60, "leather_vest", 0.15),
    ("cult_fanatic", "Tín Đồ Cuồng Nhiệt", 85, 12, 80, 40, "ing_bizarre_powder", 0.20),
    ("slum_grave_robber", "Kẻ Đào Mộ Khu Ổ Chuột", 60, 9, 50, 25, "ing_sealed_letter", 0.20),
    ("sand_wraith", "U Hồn Sa Mạc", 95, 13, 90, 45, "raw_mystical_essence", 0.20),
    # Boss — HP/Attack cao hơn hẳn, dùng làm phòng cuối Dungeon (mục 26).
    ("forsaken_dockworker_horror", "Quái Vật Bến Cảng Bị Lãng Quên", 260, 22, 400, 220, "ing_miracle_dust", 0.60),
    ("sand_pharaoh_remnant", "Tàn Hồn Pharaoh Cát", 300, 25, 500, 260, "ing_old_tome_page", 0.60),
]


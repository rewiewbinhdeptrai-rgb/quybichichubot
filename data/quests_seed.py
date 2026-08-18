"""
Quest tuyến tính có mốc tiến độ (mục 43 trong spec) — KHÁC với Investigation
(mục 27, không tuyến tính, dùng Clue) và KHÁC với Contract/Bounty (giao dịch
Player-Player, mục 39-40). Đây là nội dung do World đưa ra sẵn, có nhiều
Objective phải hoàn thành theo tiến độ thật từ gameplay (giết Monster, thu
thập Item, di chuyển tới Location) — không phải một nút "Nhận thưởng" đơn.

State machine (đúng mục 43):
    LOCKED -> AVAILABLE -> ACTIVE -> OBJECTIVE_PROGRESS -> COMPLETED
                                                          -> FAILED / EXPIRED
Engine (quest.py) quản lý transition này; file này chỉ chứa dữ liệu tĩnh.

Mỗi quest: (quest_id, category, name_vi, name_en, description_vi,
            min_level, prerequisite_quest_id, repeatable,
            reward_money, reward_exp, reward_item_id)

Mỗi objective: (quest_id, order_index, objective_type, target_id,
                 target_count, description_vi)

objective_type hiện engine hỗ trợ (mở rộng thêm khi có hook mới):
    kill_monster   -> target_id = monster_id (data/monsters_seed.py)
    collect_item   -> target_id = item_id (data/items_seed.py)
    visit_location -> target_id = location_id (data/world_seed.py)

Toàn bộ monster_id / item_id / location_id dưới đây lấy từ seed đã tồn tại
sẵn trong game (monsters_seed.py, items_seed.py, world_seed.py) — không bịa
ID mới để tránh FK trỏ vào chỗ không tồn tại.
"""

QUESTS = [
    (
        "slums_cleanup", "side", "Dọn dẹp khu ổ chuột", "Slums Cleanup",
        "Cảnh sát Backlund treo thưởng cho ai dẹp bớt đám côn đồ đang lộng hành "
        "ở khu ổ chuột.",
        1, None, True, 200, 80, None,
    ),
    (
        "docks_investigation_backup", "side", "Chi viện bến cảng", "Docks Backup",
        "Bến cảng Backlund gần đây xuất hiện Ghoul lang thang ban đêm — thương "
        "nhân địa phương cần người dẹp loạn trước khi hàng hóa bị phá hỏng.",
        3, "slums_cleanup", True, 350, 150, "spirit_incense",
    ),
    (
        "collector_first_ledger", "main", "Cuốn sổ đầu tiên", "The First Ledger",
        "Một cuốn Obscure Journal bị thất lạc quanh Backlund chứa manh mối về "
        "một Beyonder mất tích. Hãy tìm lại nó.",
        2, None, False, 250, 100, None,
    ),
    (
        "church_district_errand", "church", "Việc vặt cho Giáo hội", "Church Errand",
        "Nhà thờ Đêm Vĩnh Hằng chi nhánh Backlund cần một người ngoài đưa tin "
        "tới khu Giáo hội mà không gây chú ý.",
        1, None, True, 120, 60, None,
    ),
    (
        "tingen_old_town_secret", "hidden", "Bí mật phố cổ Tingen", "Old Town Secret",
        "Có tin đồn về một cánh cửa không nên mở nằm sâu trong phố cổ Tingen. "
        "Không ai treo thưởng chính thức cho việc này.",
        5, "collector_first_ledger", False, 500, 300, "raw_mystical_essence",
    ),
    (
        "dockworker_horror_bounty", "main", "Nỗi kinh hoàng bến tàu", "The Dockworker Horror",
        "Thứ gì đó ẩn trong bóng tối bến cảng Backlund đã giết ba công nhân. "
        "Đây không phải Ghoul thường — cần chuẩn bị kỹ trước khi đối mặt.",
        8, "docks_investigation_backup", False, 800, 400, "leather_vest",
    ),
]

QUEST_OBJECTIVES = [
    # slums_cleanup — giết 3 Street Thug tại khu ổ chuột
    ("slums_cleanup", 1, "kill_monster", "street_thug", 3,
     "Đánh bại 3 Street Thug"),

    # docks_investigation_backup — giết 2 Ghoul, sau đó ghé bến cảng báo cáo
    ("docks_investigation_backup", 1, "kill_monster", "ghoul", 2,
     "Đánh bại 2 Ghoul"),
    ("docks_investigation_backup", 2, "visit_location", "backlund_docks", 1,
     "Có mặt tại Bến cảng Backlund để báo cáo"),

    # collector_first_ledger — thu thập 1 Obscure Journal
    ("collector_first_ledger", 1, "collect_item", "obscure_journal", 1,
     "Thu thập 1 Obscure Journal"),

    # church_district_errand — di chuyển tới khu Giáo hội
    ("church_district_errand", 1, "visit_location", "backlund_church_district", 1,
     "Đến Khu Nhà thờ Backlund"),

    # tingen_old_town_secret — tới phố cổ Tingen, thu thập 1 nguyên liệu huyền bí thô
    ("tingen_old_town_secret", 1, "visit_location", "tingen_old_town", 1,
     "Đến Phố cổ Tingen"),
    ("tingen_old_town_secret", 2, "collect_item", "raw_mystical_essence", 1,
     "Thu thập 1 Raw Mystical Essence"),

    # dockworker_horror_bounty — hạ Boss Forsaken Dockworker Horror
    ("dockworker_horror_bounty", 1, "kill_monster", "forsaken_dockworker_horror", 1,
     "Đánh bại Forsaken Dockworker Horror"),
]

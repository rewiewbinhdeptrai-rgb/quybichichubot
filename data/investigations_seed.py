"""
Seed dữ liệu Investigation — Event -> Observe -> Clue -> Analyze ->
Hypothesis -> Investigate -> Resolution (mục 27 trong spec).

Không phải quest tuyến tính "bấm nút nhận thưởng": mỗi Investigation có
nhiều Clue theo order_index, mỗi lần Quan sát chỉ có find_chance% tìm được
Clue tiếp theo (đúng "người chơi có thể bỏ sót clue"). Resolution chỉ mở khi
đã tìm đủ min_clue_ratio% số Clue, và tỉ lệ "Hiểu đúng" tăng theo số Clue
(đặc biệt Key Clue) đã tìm được — không phải hằng số.

INVESTIGATIONS: (investigation_id, location_id, name_en, description_vi,
                  min_clue_ratio, reward_money, reward_exp, reward_item_id)

INVESTIGATION_CLUES: (clue_id, investigation_id, order_index, text_vi,
                       find_chance, is_key_clue)
- is_key_clue: 1 nếu Clue này bắt buộc phải có để "Hiểu đúng" (ảnh hưởng
  success chance nặng hơn Clue thường trong investigation.resolve()).

Trạng thái dữ liệu: 3 Investigation demo trải trên 3 Location khác nhau, đủ
để chạy full flow Observe/Resolve thật — CHƯA phải kho vụ án đầy đủ theo lore
Quỷ Bí (mở rộng sau, giống tình trạng Artifact/Monster hiện tại).
"""

INVESTIGATIONS = [
    (
        "backlund_docks_disappearance", "backlund_docks",
        "Vụ mất tích ở Bến cảng",
        "Một công nhân bốc vác mất tích không dấu vết ba đêm trước. Đồng "
        "nghiệp của anh ta thì thầm về một con tàu không treo cờ cập bến "
        "đúng đêm đó.",
        60, 800, 150, None,
    ),
    (
        "tingen_old_town_symbol", "tingen_old_town",
        "Ký hiệu trên tường Phố cổ",
        "Những ký hiệu lạ xuất hiện trên tường một con hẻm ở Phố cổ Tingen "
        "sau mỗi đêm trăng non. Người dân địa phương tránh đi qua đó sau "
        "hoàng hôn.",
        60, 600, 180, "raw_mystical_essence",
    ),
    (
        "skruvi_library_missing_page", "skruvi_library",
        "Trang sách bị xé",
        "Một cuốn sách cổ trong Thư viện Skruvi bị xé mất đúng một trang — "
        "và người thủ thư phụ trách khu vực đó đã không đến làm việc kể từ "
        "hôm sau.",
        70, 900, 220, "spirit_ash",
    ),
]

INVESTIGATION_CLUES = [
    # --- Vụ mất tích ở Bến cảng ---
    ("docks_clue_1", "backlund_docks_disappearance", 1,
     "Dấu giày dẫn từ kho hàng ra mép cầu tàu rồi biến mất.", 80, 0),
    ("docks_clue_2", "backlund_docks_disappearance", 2,
     "Một mảnh vải rách mắc trên đinh cầu tàu, cùng màu áo công nhân mất tích.", 70, 0),
    ("docks_clue_3", "backlund_docks_disappearance", 3,
     "Sổ ghi tàu cập bến đêm đó bị xé mất một trang.", 55, 1),
    ("docks_clue_4", "backlund_docks_disappearance", 4,
     "Một thủy thủ say rượu nhắc tới cái tên \"Bà góa áo xám\" rồi im bặt.", 40, 1),

    # --- Ký hiệu trên tường Phố cổ ---
    ("tingen_clue_1", "tingen_old_town_symbol", 1,
     "Ký hiệu được vẽ bằng thứ gì đó không phải sơn thường — có mùi tanh nhẹ.", 75, 0),
    ("tingen_clue_2", "tingen_old_town_symbol", 2,
     "Vị trí các ký hiệu, nếu nối lại, tạo thành một hình ngũ giác quanh một căn nhà bỏ hoang.", 60, 1),
    ("tingen_clue_3", "tingen_old_town_symbol", 3,
     "Một tu sĩ trẻ của Nhà thờ Đêm Vĩnh Hằng từng cảnh báo dân khu này về \"nghi thức chưa hoàn tất\".", 45, 1),

    # --- Trang sách bị xé ---
    ("skruvi_clue_1", "skruvi_library_missing_page", 1,
     "Trang bị xé nằm ngay chương nói về nghi thức triệu hồi cổ.", 75, 0),
    ("skruvi_clue_2", "skruvi_library_missing_page", 2,
     "Người thủ thư gần đây mượn rất nhiều sách về cùng chủ đề trước khi biến mất.", 65, 0),
    ("skruvi_clue_3", "skruvi_library_missing_page", 3,
     "Trong ngăn bàn của thủ thư có một mẩu giấy ghi vội tọa độ một địa điểm ở ngoại ô.", 50, 1),
    ("skruvi_clue_4", "skruvi_library_missing_page", 4,
     "Mùi mực trên mẩu giấy trùng với mùi ký hiệu từng ghi nhận ở một vụ việc khác.", 35, 1),
]

"""
Black Market — Chợ đen (mục 41 trong spec).

Nguồn tham khảo (không sao chép nguyên văn — chỉ dùng làm cảm hứng đặt tên/lore,
mọi mô tả trong file này là tự viết): hệ thống Sealed Artifact được các Giáo hội
chính thống phân cấp Grade 0-3 theo mức nguy hiểm (Grade 0 = tối nguy hiểm, chỉ
lưu trong hầm Nhà thờ chính; Grade 3 = có thể mượn cho nhiệm vụ thường), và các
Beyonder Characteristic/Potion nguyên liệu bị cấm lưu hành công khai. Chợ đen
trong game giả định đây là hàng "rò rỉ" khỏi kho lưu trữ đó — nên rủi ro cao.

Không dùng lại tên nhân vật/artifact cụ thể từ nguyên tác (Quill of Alzuhod,
Blood Vessel Thief...) làm vật phẩm mua bán được — chỉ tham khảo PHONG CÁCH đặt
mã danh (số Grade + số hiệu, vd "0-13") cho item gốc riêng của game.

category: forbidden_material | illegal_potion | mystical_item | information | rare_characteristic | secret_contract
risk_type: none | scam | trap | wanted
  - none : luôn thành công, chỉ đắt hơn giá chợ thường vì là hàng hiếm/cấm.
  - scam : % bị lừa — mất tiền, không nhận được gì (mục 41: Scam).
  - trap : % dính bẫy — mất tiền + nhận debuff thật qua EffectEngine + mất HP (mục 41: Trap).
  - wanted: % bị lộ khi giao dịch — tạo một Bounty (mục 40) thật nhắm vào chính người mua,
            người chơi khác có thể nhận và truy nã (mục 41: Wanted/Tracking).
currency: tất cả định giá bằng "Bảng" — đơn vị tiền tệ duy nhất đã có trong file
(characters.money), không thêm loại tiền tệ mới để tránh phá vỡ đồng bộ Economy hiện tại.
"""

# Item mới cần có trong bảng items trước khi black_market_listings có thể trỏ tới.
# Định dạng giống hệt data/items_seed.py: (item_id, name_en, name_vi, type,
# description, heal_hp, heal_spirituality, equip_slot, modifier_key, modifier_value)
BLACK_MARKET_ITEMS = [
    (
        "grey_fog_essence", "Grey Fog Essence", "Tinh Chất Sương Xám", "material",
        "Tinh chất sương xám thu được từ khu vực có hoạt động Huyền bí bất thường. "
        "Nguyên liệu cấm cho một số công thức Potion cao cấp.", 0, 0, None, None, None,
    ),
    (
        "unlicensed_beyonder_blood", "Unlicensed Beyonder Blood Sample", "Mẫu Máu Beyonder Không Giấy Phép", "material",
        "Mẫu máu Beyonder không rõ nguồn gốc, không qua kiểm định của Giáo hội. "
        "Sở hữu trái phép loại này là tội danh nghiêm trọng ở hầu hết các quốc gia.",
        0, 0, None, None, None,
    ),
    (
        "black_fog_potion_vial", "Unlabeled Potion Vial (Black Fog)", "Lọ Ma Dược Không Nhãn (Sương Đen)", "consumable",
        "Ma dược chế lậu, không rõ Pathway gốc, nhãn bị cố tình xoá. Hồi 15 Spirituality "
        "nhưng để lại dư chấn bất ổn trong cơ thể.", 0, 15, None, None, None,
    ),
    (
        "0-13_music_box", "Sealed Item 0-13 (Music Box)", "Vật Phẩm Niêm Phong 0-13 (Hộp Nhạc)", "equipment",
        "Hộp nhạc bọc kín trong vải đen, mã hiệu chợ đen tự đặt \"0-13\" theo phong cách "
        "phân cấp của Nghị hội. Physical Damage +30% khi trang bị — nhưng thứ gì đó "
        "trong hộp vẫn còn thức.", 0, 0, "weapon", "physical_damage_pct", 30,
    ),
    (
        "informant_dossier", "Informant Dossier", "Hồ Sơ Chỉ Điểm", "material",
        "Tập hồ sơ chép tay về hoạt động của một Giáo hội hoặc Thế lực địa phương. "
        "Thông tin có thể đúng, có thể là mồi nhử.", 0, 0, None, None, None,
    ),
    (
        "warped_tarot_deck", "Warped Tarot Deck", "Bộ Bài Tarot Dị Dạng", "material",
        "Một bộ bài Tarot lạ, hoa văn không khớp với bất kỳ Tarot Club chính thức "
        "nào được ghi nhận.", 0, 0, None, None, None,
    ),
]

# (listing_id, category, item_id, quantity, price, risk_type, risk_chance_pct, description_vi)
BLACK_MARKET_LISTINGS = [
    (
        "bm_grey_fog_essence", "forbidden_material", "grey_fog_essence", 1, 850,
        "none", 0,
        "Nguyên liệu cấm nhưng người bán này đáng tin — không có rủi ro thêm ngoài giá cắt cổ.",
    ),
    (
        "bm_beyonder_blood", "forbidden_material", "unlicensed_beyonder_blood", 1, 2200,
        "wanted", 20,
        "Hàng cực nóng. 20% khả năng có tai mắt Nighthawks trà trộn trong phiên giao dịch — "
        "bị phát hiện sẽ có Truy nã treo lên chính bạn.",
    ),
    (
        "bm_black_fog_potion", "illegal_potion", "black_fog_potion_vial", 1, 600,
        "trap", 25,
        "Ma dược không nhãn, không kiểm định. 25% khả năng công thức bị pha lỗi, gây phản ứng "
        "ngược thay vì hồi phục.",
    ),
    (
        "bm_0-13_music_box", "mystical_item", "0-13_music_box", 1, 5400,
        "trap", 35,
        "Vật phẩm mã hiệu 0-13, rò rỉ từ đâu đó không ai dám hỏi. 35% khả năng thứ bên trong "
        "phản ứng ngay khi bạn vừa nhận hàng.",
    ),
    (
        "bm_informant_dossier", "information", "informant_dossier", 1, 400,
        "scam", 30,
        "Thông tin tình báo giá rẻ — đúng nghĩa \"tiền nào của nấy\". 30% khả năng đây chỉ là "
        "giấy trắng đóng dấu giả.",
    ),
    (
        "bm_warped_tarot_deck", "mystical_item", "warped_tarot_deck", 1, 1500,
        "scam", 15,
        "Được đồn là có thể dùng để liên lạc với một Tarot Club không chính thức. 15% khả năng "
        "chỉ là bộ bài in lỗi bình thường.",
    ),
    (
        "bm_secret_contract_silence", "secret_contract", None, 1, 3000,
        "wanted", 15,
        "Một Khế ước bí mật: bên bán đồng ý \"giữ im lặng\" về một việc bạn từng làm. Không có "
        "vật phẩm nào được giao — chỉ là lời hứa miệng. 15% khả năng chính bên bán tố giác bạn "
        "để lấy thêm tiền thưởng.",
    ),
]

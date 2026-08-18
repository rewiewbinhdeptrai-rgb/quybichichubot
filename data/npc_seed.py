"""
Seed dữ liệu NPC (mục 28 trong spec).

NPC không phải bảng chat vô tri — mỗi NPC đứng thật ở 1 Location (mục 31-32,
`world.py`), có Trust thật với từng Character (không dùng chung một biến
toàn cục), và NHỚ hành động của người chơi qua `npc_memory` (log thật, không
phải state ẩn). Dialogue là ngân hàng câu thoại tĩnh chọn theo `trust_tier`
hiện tại — CHƯA có AI Narrative layer (mục 29, cần Gemini/Groq + Context
Builder, việc riêng và lớn hơn nhiều) nên không có câu thoại động/tùy biến.

(npc_id, name_en, location_id, role, description_vi, favorite_item_id)
favorite_item_id: None nếu NPC không đặc biệt thích quà nào (Tặng quà vẫn
được nhưng chỉ +1 Trust thay vì +5).
"""

NPCS = [
    ("docks_merchant", "Harold the Merchant", "backlund_docks", "merchant",
     "Thương nhân buôn bán tại bến cảng Backlund — tin tức về hàng hóa lẫn "
     "tin đồn đều qua tay ông ta.", "obscure_journal"),
    ("church_clergyman", "Father Elias", "backlund_church_district", "clergy",
     "Giáo sĩ tại chi nhánh Nhà thờ Đêm Vĩnh Hằng ở Backlund — kín tiếng "
     "nhưng am hiểu Huyền bí hơn vẻ ngoài cho thấy.", "spirit_incense"),
    ("slum_informant", "Nell the Informant", "backlund_slums", "informant",
     "Một kẻ chạy tin ở khu ổ chuột Backlund — biết nhiều thứ hơn hầu hết "
     "quý tộc trong thành phố.", None),
    ("skruvi_librarian", "Old Ambrose", "skruvi_library", "scholar",
     "Thủ thư già của Thư viện cổ Skruvi, dành cả đời nghiên cứu văn tự "
     "huyền bí thất truyền.", "obscure_journal"),
    ("tingen_priestess", "Sister Odette", "tingen_cathedral", "clergy",
     "Nữ tu tại Đại giáo đường Tingen — đại diện cho quyền lực của Giáo hội "
     "tại đây.", "spirit_incense"),
    ("trier_dockmaster", "Captain Reyes", "trier_harbor", "sailor",
     "Thuyền trưởng kỳ cựu quản lý bến cảng Trier, biết rõ mọi tuyến hàng "
     "hải và cả những chuyến hàng không muốn ai biết tới.", "healing_draught"),
]

# (npc_id, trust_tier, line_vi) — trust_tier: stranger (<20) | acquaintance (20-59) | trusted (>=60)
NPC_DIALOGUE = [
    ("docks_merchant", "stranger", "\"Mua bán gì thì nói nhanh, tôi không rảnh tán gẫu với người lạ.\""),
    ("docks_merchant", "acquaintance", "\"À, lại là cậu. Dạo này hàng về chậm, chắc do thời tiết... hoặc không phải.\""),
    ("docks_merchant", "trusted", "\"Nói thật với cậu — có vài kiện hàng gần đây tôi không dám hỏi nguồn gốc.\""),

    ("church_clergyman", "stranger", "\"Chúa phù hộ con. Con tìm gì ở đây?\""),
    ("church_clergyman", "acquaintance", "\"Con lại tới rồi. Có điều gì đang làm con bận tâm sao?\""),
    ("church_clergyman", "trusted", "\"Có những chuyện trong Nhà thờ này ta chỉ dám nói với người ta tin tưởng.\""),

    ("slum_informant", "stranger", "\"Tin tức không miễn phí đâu, bạn ơi.\""),
    ("slum_informant", "acquaintance", "\"Lần này tôi nghe được vài chuyện thú vị ở khu cảng đấy.\""),
    ("slum_informant", "trusted", "\"Chỉ nói riêng với cậu thôi — có người đang hỏi thăm về cậu đấy.\""),

    ("skruvi_librarian", "stranger", "\"Thư viện đóng cửa sau 6 giờ. Cậu tìm sách gì?\""),
    ("skruvi_librarian", "acquaintance", "\"Cậu lại đến nghiên cứu à? Ta có vài ghi chép có thể cậu sẽ thích.\""),
    ("skruvi_librarian", "trusted", "\"Có một cuốn ta cất kỹ, không đưa ai xem — trừ khi ta tin họ.\""),

    ("tingen_priestess", "stranger", "\"Bình an cho con. Con đến để cầu nguyện hay để tìm hiểu điều gì khác?\""),
    ("tingen_priestess", "acquaintance", "\"Ta nhớ con. Dạo này con đi Con đường của mình tới đâu rồi?\""),
    ("tingen_priestess", "trusted", "\"Giáo hội không phải lúc nào cũng đúng. Ta tin con đủ để nói vậy.\""),

    ("trier_dockmaster", "stranger", "\"Cảng này không phải chỗ cho khách du lịch, nhóc.\""),
    ("trier_dockmaster", "acquaintance", "\"Cậu lại quay lại bến cảng này rồi. Cần đi đâu à?\""),
    ("trier_dockmaster", "trusted", "\"Nếu cậu cần một chuyến đi kín tiếng, tìm tôi. Tôi nợ cậu một ân tình.\""),
]

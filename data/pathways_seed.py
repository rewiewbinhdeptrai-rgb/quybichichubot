"""
Dữ liệu tĩnh cho 22 Pathway (mục 6 & 55 trong spec).
Đây là dữ liệu "canonical" — không được AI runtime chỉnh sửa (mục 67).

Mỗi pathway: (pathway_id, icon, name_en, title_en)
name_en giữ nguyên bản canonical để không dịch sai lore.

sequences: cả 22/22 Pathway đã có tên Sequence 9->0 thật — xem SOURCE NOTE
bên dưới. Không còn placeholder "Sequence N".

SOURCE NOTE (quan trọng — đọc trước khi thêm Pathway khác):
Các tên Sequence dưới đây được đối chiếu từ lordofthemysteries.fandom.com
(wiki có trích dẫn WeChat QnA gốc của tác giả Cuttlefish That Loves Diving),
chéo kiểm với lord-of-the-mysteries-craft.fandom.com và ít nhất 1 nguồn thứ 3.
KHÔNG dùng trang "lord-of-the-mysteries.shop" — trang này bịa dữ liệu (đã bắt
gặp nó gán sai tên Sequence của Red Priest cho Sailor, và tên Sequence của
một pathway khác hẳn cho Reader). Nếu điền tiếp 15 Pathway còn lại, luôn đối
chiếu tối thiểu 2 nguồn độc lập trước khi coi là canonical.
"""

PATHWAYS = [
    {"id": "seer", "icon": "🃏", "name_en": "Seer", "name_vi": "Nhà Tiên Tri", "title_en": "Fool", "title_vi": "Kẻ Khờ"},
    {"id": "apprentice", "icon": "🚪", "name_en": "Apprentice", "name_vi": "Học Đồ", "title_en": "Door", "title_vi": "Cánh Cửa"},
    {"id": "marauder", "icon": "🕵️", "name_en": "Marauder", "name_vi": "Kẻ Cướp Đoạt", "title_en": "Error", "title_vi": "Lỗi"},
    {"id": "spectator", "icon": "🎭", "name_en": "Spectator", "name_vi": "Khán Giả", "title_en": "Visionary", "title_vi": "Người Tưởng Tượng"},
    {"id": "bard", "icon": "☀️", "name_en": "Bard", "name_vi": "Thi Ca Sư", "title_en": "Sun", "title_vi": "Mặt Trời"},
    {"id": "sailor", "icon": "⚡", "name_en": "Sailor", "name_vi": "Thủy Thủ", "title_en": "Tyrant", "title_vi": "Bạo Quân"},
    {"id": "secrets_suppliant", "icon": "🪞", "name_en": "Secrets Suppliant", "name_vi": "Kẻ Khẩn Cầu Bí Ẩn", "title_en": "Hanged Man", "title_vi": "Người Treo Ngược"},
    {"id": "reader", "icon": "📖", "name_en": "Reader", "name_vi": "Độc Giả", "title_en": "White Tower", "title_vi": "Bạch Tháp"},
    {"id": "corpse_collector", "icon": "💀", "name_en": "Corpse Collector", "name_vi": "Người Thu Thập Thi Thể", "title_en": "Death", "title_vi": "Tử Thần"},
    {"id": "sleepless", "icon": "🌙", "name_en": "Sleepless", "name_vi": "Người Không Ngủ", "title_en": "Darkness", "title_vi": "Hắc Dạ"},
    {"id": "warrior", "icon": "⚔️", "name_en": "Warrior", "name_vi": "Chiến Binh", "title_en": "Twilight Giant", "title_vi": "Cự Nhân Hoàng Hôn"},
    {"id": "lawyer", "icon": "⚖️", "name_en": "Lawyer", "name_vi": "Luật Sư", "title_en": "Black Emperor", "title_vi": "Hắc Hoàng Đế"},
    {"id": "arbiter", "icon": "📜", "name_en": "Arbiter", "name_vi": "Thẩm Phán", "title_en": "Justiciar", "title_vi": "Chấp Chính Quan"},
    {"id": "hunter", "icon": "🏹", "name_en": "Hunter", "name_vi": "Thợ Săn", "title_en": "Red Priest", "title_vi": "Hồng Tế Tự"},
    {"id": "assassin", "icon": "🩸", "name_en": "Assassin", "name_vi": "Thích Khách", "title_en": "Demoness", "title_vi": "Ma Nữ"},
    {"id": "criminal", "icon": "🔥", "name_en": "Criminal", "name_vi": "Tội Phạm", "title_en": "Abyss", "title_vi": "Vực Sâu"},
    {"id": "prisoner", "icon": "⛓️", "name_en": "Prisoner", "name_vi": "Tù Nhân", "title_en": "Chained", "title_vi": "Người Bị Trói Buộc"},
    {"id": "mystery_pryer", "icon": "🔮", "name_en": "Mystery Pryer", "name_vi": "Kẻ Khẩn Cầu Huyền Bí", "title_en": "Hermit", "title_vi": "Ẩn Sĩ"},
    {"id": "savant", "icon": "⚙️", "name_en": "Savant", "name_vi": "Học Giả", "title_en": "Paragon", "title_vi": "Thợ Thủ Công"},
    {"id": "planter", "icon": "🌿", "name_en": "Planter", "name_vi": "Người Trồng Trọt", "title_en": "Mother", "title_vi": "Mẫu Thần"},
    {"id": "apothecary", "icon": "🧪", "name_en": "Apothecary", "name_vi": "Dược Sư", "title_en": "Moon", "title_vi": "Mặt Trăng"},
    {"id": "monster", "icon": "🎡", "name_en": "Monster", "name_vi": "Quái Vật", "title_en": "Wheel of Fortune", "title_vi": "Bánh Xe Vận Mệnh"},
]

# Sequence 9 -> 0 mẫu đầy đủ cho Seer (mục 54 tài liệu đầu)
SEER_SEQUENCES = [
    (9, "Seer", "Nhà Tiên Tri"),
    (8, "Clown", "Hề"),
    (7, "Magician", "Ma Thuật Sư"),
    (6, "Faceless", "Vô Diện Nhân"),
    (5, "Marionettist", "Thao Ngẫu Sư"),
    (4, "Bizarro Sorcerer", "Ma Thuật Sư Bizarro"),
    (3, "Scholar of Yore", "Học Giả Cổ Đại"),
    (2, "Miracle Invoker", "Kẻ Gọi Phép Màu"),
    (1, "Attendant of Mysteries", "Thị Giả Huyền Bí"),
    (0, "The Fool", "Kẻ Khờ"),
]

# Sequence 9 -> 0 cho Apprentice / Door Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Door_Pathway/Advancement
# (trích dẫn Cuttlefish's WeChat Post "Apprentice Pathway Abilities"),
# đối chiếu craft wiki + webnovel reprint + Friends & Fables TTRPG guide.
APPRENTICE_SEQUENCES = [
    (9, "Apprentice", "Học Đồ"),
    (8, "Trickmaster", "Bậc Thầy Mánh Khóe"),
    (7, "Astrologer", "Chiêm Tinh Gia"),
    (6, "Scribe", "Người Ghi Chép"),
    (5, "Traveler", "Lữ Hành Giả"),
    (4, "Secrets Sorcerer", "Ma Thuật Sư Bí Ẩn"),
    (3, "Wanderer", "Kẻ Lang Thang"),
    (2, "Planeswalker", "Người Du Hành Không Gian"),
    (1, "Key of Stars", "Chìa Khóa Các Vì Sao"),
    (0, "Door", "Cánh Cửa"),
]

# Sequence 9 -> 0 cho Sailor / Tyrant Pathway.
# Nguồn: lord-of-the-mysteries-craft.fandom.com/wiki/Sailor_Pathway.
# LƯU Ý: tên Sequence 4 "Cataclysmic Interrer" nghe như lỗi đánh máy của
# wiki gốc (có thể là "Cataclysmic Interpreter") — cần đối chiếu lại khi
# có bản dịch chính thức, đừng coi là chắc chắn 100%.
SAILOR_SEQUENCES = [
    (9, "Sailor", "Thủy Thủ"),
    (8, "Folk of Rage", "Kẻ Cuồng Nộ"),
    (7, "Storm Priest", "Tư Tế Bão Tố"),
    (6, "Wind Blessed", "Kẻ Được Gió Ban Phúc"),
    (5, "Ocean Songster", "Ca Sĩ Đại Dương"),
    (4, "Cataclysmic Interrer", "Kẻ Mai Táng Đại Tai Biến"),
    (3, "Sea King", "Hải Vương"),
    (2, "Calamity", "Tai Họa"),
    (1, "Thunder God", "Lôi Thần"),
    (0, "Tyrant", "Bạo Quân"),
]

# Sequence 9 -> 0 cho Reader / White Tower Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/White_Tower_Pathway/Abilities
# và /Advancement (không dùng bản "shop" — bản đó bịa hẳn 1 bộ tên khác).
READER_SEQUENCES = [
    (9, "Reader", "Độc Giả"),
    (8, "Student of Ratiocination", "Học Sinh Suy Luận"),
    (7, "Detective", "Thám Tử"),
    (6, "Polymath", "Bác Học Đa Tài"),
    (5, "Mysticism Magister", "Đại Sư Huyền Bí Học"),
    (4, "Prophet", "Tiên Tri"),
    (3, "Cognizer", "Người Nhận Thức"),
    (2, "Wisdom Angel", "Thiên Sứ Trí Tuệ"),
    (1, "Omniscient Eye", "Con Mắt Toàn Tri"),
    (0, "White Tower", "Bạch Tháp"),
]

# Sequence 9 -> 0 cho Warrior / Twilight Giant Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Twilight_Giant_Pathway/Abilities.
# Tên thay thế trong ngoặc trên wiki gốc: Pugilist (Gladiator),
# Demon Hunter (Witcher), Glory, Twilight Giant (Twilight/Giant) — đã chọn
# tên chính, các biến thể có thể dùng làm alias hiển thị.
WARRIOR_SEQUENCES = [
    (9, "Warrior", "Chiến Binh"),
    (8, "Pugilist", "Võ Sĩ"),
    (7, "Weapon Master", "Võ Khí Đại Sư"),
    (6, "Dawn Paladin", "Kỵ Sĩ Bình Minh"),
    (5, "Guardian", "Hộ Vệ"),
    (4, "Demon Hunter", "Kẻ Săn Quỷ"),
    (3, "Silver Knight", "Kỵ Sĩ Bạc"),
    (2, "Glory", "Vinh Quang"),
    (1, "Hand of God", "Bàn Tay Của Thần"),
    (0, "Twilight Giant", "Cự Nhân Hoàng Hôn"),
]

# Sequence 9 -> 0 cho Hunter / Red Priest Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Red_Priest_Pathway/Abilities
# và /Advancement (trích Cuttlefish's WeChat Post "Formulas and Abilities
# of the Red Priest Pathway").
HUNTER_SEQUENCES = [
    (9, "Hunter", "Thợ Săn"),
    (8, "Provoker", "Kẻ Khiêu Khích"),
    (7, "Pyromaniac", "Kẻ Cuồng Lửa"),
    (6, "Conspirer", "Kẻ Mưu Đồ"),
    (5, "Reaper", "Tử Thần Thu Hoạch"),
    (4, "Iron-blooded Knight", "Kỵ Sĩ Thiết Huyết"),
    (3, "War Bishop", "Giám Mục Chiến Tranh"),
    (2, "Weather Warlock", "Vu Sư Thời Tiết"),
    (1, "Conqueror", "Kẻ Chinh Phục"),
    (0, "Red Priest", "Hồng Tế Tự"),
]

# Sequence 9 -> 0 cho Apothecary / Moon Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Moon_Pathway/Advancement,
# đối chiếu Heroes Wiki (liệt kê đầy đủ Sequence 9->0 của Evernight Goddess).
# Sanguine (dòng máu ma cà rồng) dùng tên tước hiệu song song sau Sequence 7:
# Baron(6) Viscount(5) Earl(4) Marquis(3) Duke(2) Queen(1) — có thể dùng làm
# tên hiển thị thay thế cho nhân vật thuộc chủng Sanguine.
APOTHECARY_SEQUENCES = [
    (9, "Apothecary", "Dược Sư"),
    (8, "Beast Tamer", "Kẻ Thuần Thú"),
    (7, "Vampire", "Huyết Tộc"),
    (6, "Potions Professor", "Giáo Sư Ma Dược"),
    (5, "Scarlet Scholar", "Học Giả Đỏ Thẫm"),
    (4, "Shaman King", "Vu Vương"),
    (3, "High Summoner", "Đại Triệu Hoán Sư"),
    (2, "Life-Giver", "Người Ban Sinh Mệnh"),
    (1, "Beauty Goddess", "Nữ Thần Mỹ Lệ"),
    (0, "Moon", "Mặt Trăng"),
]

# Sequence 9 -> 0 cho Marauder / Error Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Error_Pathway (+ /Abilities,
# /Advancement, trích Cuttlefish's WeChat Post "Marauder Pathway Abilities"),
# đối chiếu NamuWiki (bản dịch Hàn) và webnovel reprint.
MARAUDER_SEQUENCES = [
    (9, "Marauder", "Kẻ Cướp Đoạt"),
    (8, "Swindler", "Kẻ Lừa Đảo"),
    (7, "Cryptologist", "Nhà Mật Mã Học"),
    (6, "Prometheus", "Prometheus"),
    (5, "Dream Stealer", "Kẻ Đánh Cắp Giấc Mơ"),
    (4, "Parasite", "Ký Sinh Trùng"),
    (3, "Mentor of Deceit", "Bậc Thầy Lừa Dối"),
    (2, "Trojan Horse of Fate", "Ngựa Thành Troy Của Vận Mệnh"),
    (1, "Worm of Time", "Trùng Thời Gian"),
    (0, "Error", "Lỗi"),
]

# Sequence 9 -> 0 cho Spectator / Visionary Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Visionary_Pathway/Advancement
# (mục lục đầy đủ), đối chiếu webnovel reprint.
SPECTATOR_SEQUENCES = [
    (9, "Spectator", "Khán Giả"),
    (8, "Telepathist", "Nhà Đọc Tâm"),
    (7, "Psychiatrist", "Bác Sĩ Tâm Thần"),
    (6, "Hypnotist", "Nhà Thôi Miên"),
    (5, "Dreamwalker", "Kẻ Du Hành Giấc Mơ"),
    (4, "Manipulator", "Người Thao Túng"),
    (3, "Dream Weaver", "Kẻ Dệt Mộng"),
    (2, "Discerner", "Người Phân Biệt"),
    (1, "Author", "Tác Giả"),
    (0, "Visionary", "Người Tưởng Tượng"),
]

# Sequence 9 -> 0 cho Bard / Sun Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Sun_Pathway/Abilities (mục lục
# đầy đủ), đối chiếu Friends & Fables TTRPG guide.
BARD_SEQUENCES = [
    (9, "Bard", "Thi Ca Sư"),
    (8, "Light Suppliant", "Kẻ Khẩn Cầu Ánh Sáng"),
    (7, "Solar High Priest", "Đại Tế Tư Mặt Trời"),
    (6, "Notary", "Công Chứng Viên"),
    (5, "Priest of Light", "Tư Tế Ánh Sáng"),
    (4, "Unshadowed", "Kẻ Không Bóng"),
    (3, "Justice Mentor", "Cố Vấn Công Lý"),
    (2, "Lightseeker", "Kẻ Tầm Cầu Ánh Sáng"),
    (1, "White Angel", "Thiên Sứ Trắng"),
    (0, "Sun", "Mặt Trời"),
]

# Sequence 9 -> 0 cho Secrets Suppliant / Hanged Man Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Hanged_Man_Pathway/Advancement,
# đối chiếu Friends & Fables (khớp từng tên).
SECRETS_SUPPLIANT_SEQUENCES = [
    (9, "Secrets Suppliant", "Kẻ Khẩn Cầu Bí Ẩn"),
    (8, "Listener", "Người Lắng Nghe"),
    (7, "Shadow Ascetic", "Khổ Tu Sĩ Bóng Tối"),
    (6, "Rose Bishop", "Giám Mục Hoa Hồng"),
    (5, "Shepherd", "Mục Sư"),
    (4, "Black Knight", "Kỵ Sĩ Đen"),
    (3, "Trinity Templar", "Thánh Kỵ Sĩ Tam Vị"),
    (2, "Profane Presbyter", "Trưởng Lão Tà Dị"),
    (1, "Dark Angel", "Thiên Sứ Bóng Tối"),
    (0, "Hanged Man", "Người Treo Ngược"),
]

# Sequence 9 -> 0 cho Corpse Collector / Death Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Death_Pathway (+/Advancement),
# đối chiếu Friends & Fables. LƯU Ý: trang "shop" (không đáng tin) đảo
# ngược thứ tự Ferryman/Gatekeeper — bản dưới đây theo 2 nguồn đối chiếu.
CORPSE_COLLECTOR_SEQUENCES = [
    (9, "Corpse Collector", "Người Thu Thập Thi Thể"),
    (8, "Gravedigger", "Người Đào Mộ"),
    (7, "Spirit Medium", "Linh Môi"),
    (6, "Spirit Guide", "Người Dẫn Linh"),
    (5, "Gatekeeper", "Người Gác Cổng"),
    (4, "Undying", "Bất Tử Giả"),
    (3, "Ferryman", "Người Đưa Đò"),
    (2, "Death Consul", "Tử Thần Chiêu Hồn"),
    (1, "Pale Emperor", "Hoàng Đế Nhợt Nhạt"),
    (0, "Death", "Tử Thần"),
]

# Sequence 9 -> 0 cho Sleepless / Darkness Pathway.
# Nguồn: TikTok tóm tắt chi tiết đối chiếu với lordofthemysteries.fandom.com
# (xác nhận riêng lẻ Sleepless/Midnight Poet/Nightmare/Nightwatcher) và
# fandomwire.com (xác nhận Sleepless/Midnight Poet/Nightmare).
SLEEPLESS_SEQUENCES = [
    (9, "Sleepless", "Người Không Ngủ"),
    (8, "Midnight Poet", "Thi Nhân Nửa Đêm"),
    (7, "Nightmare", "Ác Mộng"),
    (6, "Soul Assurer", "Người Trấn An Linh Hồn"),
    (5, "Spirit Warlock", "Vu Sư Linh Hồn"),
    (4, "Nightwatcher", "Người Gác Đêm"),
    (3, "Horror Bishop", "Giám Mục Kinh Hoàng"),
    (2, "Servant of Concealment", "Người Hầu Của Che Giấu"),
    (1, "Knight of Misfortune", "Kỵ Sĩ Bất Hạnh"),
    (0, "Darkness", "Hắc Dạ"),
]

# Sequence 9 -> 0 cho Lawyer / Black Emperor Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Black_Emperor_Pathway/Advancement,
# đối chiếu Friends & Fables (khớp từng tên).
LAWYER_SEQUENCES = [
    (9, "Lawyer", "Luật Sư"),
    (8, "Barbarian", "Dã Man Nhân"),
    (7, "Briber", "Kẻ Hối Lộ"),
    (6, "Baron of Corruption", "Bá Tước Hủ Bại"),
    (5, "Mentor of Disorder", "Cố Vấn Hỗn Loạn"),
    (4, "Earl of the Fallen", "Bá Tước Sa Đọa"),
    (3, "Frenzied Mage", "Pháp Sư Cuồng Loạn"),
    (2, "Duke of Entropy", "Công Tước Hỗn Độn"),
    (1, "Prince of Abolition", "Vương Tử Hủy Diệt"),
    (0, "Black Emperor", "Hắc Hoàng Đế"),
]

# Sequence 9 -> 0 cho Arbiter / Justiciar Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Justiciar_Pathway/Abilities
# (mục lục đầy đủ), đối chiếu Friends & Fables (khớp từng tên).
ARBITER_SEQUENCES = [
    (9, "Arbiter", "Thẩm Phán"),
    (8, "Sheriff", "Cảnh Trưởng"),
    (7, "Interrogator", "Thẩm Vấn Quan"),
    (6, "Judge", "Phán Quan"),
    (5, "Disciplinary Paladin", "Kỵ Sĩ Kỷ Luật"),
    (4, "Imperative Mage", "Pháp Sư Mệnh Lệnh"),
    (3, "Chaos Hunter", "Thợ Săn Hỗn Loạn"),
    (2, "Balancer", "Kẻ Cân Bằng"),
    (1, "Hand of Order", "Bàn Tay Trật Tự"),
    (0, "Justiciar", "Chấp Chính Quan"),
]

# Sequence 9 -> 0 cho Assassin / Demoness Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Demoness_Pathway (+/Abilities,
# /Advancement), đối chiếu Friends & Fables (khớp từng tên). Sequence 0 đôi
# khi được ghi là "Primordial Demoness" trên Card of Blasphemy — dùng
# "Demoness" làm tên chính theo quy ước phổ biến hơn.
ASSASSIN_SEQUENCES = [
    (9, "Assassin", "Thích Khách"),
    (8, "Instigator", "Kẻ Xúi Giục"),
    (7, "Witch", "Phù Thủy"),
    (6, "Pleasure", "Hoan Du"),
    (5, "Affliction", "Khổ Nạn"),
    (4, "Despair", "Tuyệt Vọng"),
    (3, "Unaging", "Bất Lão"),
    (2, "Catastrophe", "Đại Tai Biến"),
    (1, "Apocalypse", "Tận Thế"),
    (0, "Demoness", "Ma Nữ"),
]

# Sequence 9 -> 0 cho Criminal / Abyss Pathway.
# Nguồn: TikTok tóm tắt đối chiếu với lordofthemysteries.fandom.com/wiki/
# Abyss_Pathway/Abilities (xác nhận riêng lẻ Criminal/Unwinged Angel/Serial
# Killer/Demon qua mô tả ability). LƯU Ý: Friends & Fables ghi tên khác cho
# Sequence 8 ("Coldblooded" thay vì "Unwinged Angel") — ưu tiên bản Fandom
# vì có mô tả ability chi tiết khớp với "Unwinged Angel", nhưng cần xác
# minh thêm nếu có bản dịch chính thức.
CRIMINAL_SEQUENCES = [
    (9, "Criminal", "Tội Phạm"),
    (8, "Unwinged Angel", "Thiên Sứ Không Cánh"),
    (7, "Serial Killer", "Kẻ Giết Người Hàng Loạt"),
    (6, "Devil", "Ác Ma"),
    (5, "Desire Apostle", "Sứ Đồ Dục Vọng"),
    (4, "Demon", "Ma Quỷ"),
    (3, "Blatherer", "Kẻ Nói Nhảm"),
    (2, "Bloody Archduke", "Đại Công Tước Đẫm Máu"),
    (1, "Filthy Monarch", "Quân Vương Ô Uế"),
    (0, "Abyss", "Vực Sâu"),
]

# Sequence 9 -> 0 cho Prisoner / Chained Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Chained_Pathway/Advancement
# (mục lục đầy đủ), đối chiếu Friends & Fables (khớp từng tên) và TikTok.
PRISONER_SEQUENCES = [
    (9, "Prisoner", "Tù Nhân"),
    (8, "Lunatic", "Kẻ Điên"),
    (7, "Werewolf", "Người Sói"),
    (6, "Zombie", "Cương Thi"),
    (5, "Wraith", "Oán Linh"),
    (4, "Puppet", "Con Rối"),
    (3, "Disciple of Silence", "Đệ Tử Im Lặng"),
    (2, "Ancient Bane", "Tai Họa Cổ Đại"),
    (1, "Abomination", "Quái Vật Dị Hình"),
    (0, "Chained", "Người Bị Trói Buộc"),
]

# Sequence 9 -> 0 cho Mystery Pryer / Hermit Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Hermit_Pathway/Advancement +
# /Abilities (Sequence 9-6, 4), Hunting Hidden Sage + Moses Ascetic Order
# (Sequence 3 Clairvoyant, 2 Sage, 1 Knowledge Emperor), /wiki/Hermit_Pathway
# (Sequence 0). Baidu Baike ghi tên khác cho một số Sequence giữa (vd.
# "Combat Scholar" thay vì "Melee Scholar") — có thể là biến thể dịch.
MYSTERY_PRYER_SEQUENCES = [
    (9, "Mystery Pryer", "Kẻ Khẩn Cầu Huyền Bí"),
    (8, "Melee Scholar", "Học Giả Cận Chiến"),
    (7, "Warlock", "Vu Sư"),
    (6, "Scrolls Professor", "Giáo Sư Kinh Thư"),
    (5, "Constellations Master", "Đại Sư Tinh Tọa"),
    (4, "Mysticologist", "Huyền Bí Học Gia"),
    (3, "Clairvoyant", "Nhà Tiên Tri"),
    (2, "Sage", "Hiền Giả"),
    (1, "Knowledge Emperor", "Hoàng Đế Tri Thức"),
    (0, "Hermit", "Ẩn Sĩ"),
]

# Sequence 9 -> 0 cho Savant / Paragon Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Paragon_Pathway/Advancement
# (mục lục đầy đủ), đối chiếu TikTok và Friends & Fables (khớp từng tên —
# 3 nguồn đồng nhất hoàn toàn, độ tin cậy cao).
SAVANT_SEQUENCES = [
    (9, "Savant", "Học Giả"),
    (8, "Archaeologist", "Nhà Khảo Cổ Học"),
    (7, "Appraiser", "Giám Định Sư"),
    (6, "Artisan", "Nghệ Nhân"),
    (5, "Astronomer", "Nhà Thiên Văn Học"),
    (4, "Alchemist", "Luyện Kim Thuật Sư"),
    (3, "Arcane Scholar", "Học Giả Huyền Thuật"),
    (2, "Knowledge Magister", "Đại Sư Tri Thức"),
    (1, "Illuminator", "Người Khai Sáng"),
    (0, "Paragon", "Thợ Thủ Công"),
]

# Sequence 9 -> 0 cho Planter / Mother Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Mother_Pathway/Advancement
# (Sequence 9-3), /wiki/Mother_Pathway (Sequence 2 "Desolate Matriarch",
# Sequence 1 "Naturewalker", Sequence 0 "Mother" — xác nhận trực tiếp
# trong văn bản, có trích dẫn WeChat QnA của tác giả).
PLANTER_SEQUENCES = [
    (9, "Planter", "Người Trồng Trọt"),
    (8, "Doctor", "Bác Sĩ"),
    (7, "Harvest Priest", "Tư Tế Thu Hoạch"),
    (6, "Biologist", "Nhà Sinh Vật Học"),
    (5, "Druid", "Tu Sĩ Druid"),
    (4, "Ancient Alchemist", "Luyện Kim Thuật Sư Cổ Đại"),
    (3, "Pallbearer", "Người Khiêng Quan Tài"),
    (2, "Desolate Matriarch", "Mẫu Thần Hoang Vu"),
    (1, "Naturewalker", "Kẻ Du Hành Tự Nhiên"),
    (0, "Mother", "Mẫu Thần"),
]

# Sequence 9 -> 0 cho Monster / Wheel of Fortune Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Wheel_of_Fortune_Pathway/
# Advancement (Sequence 9-6, và Chaoswalker/Soothsayer), đối chiếu Friends
# & Fables (khớp từng tên) và Baidu Baike (khớp phần lớn, riêng Sequence 2
# Baidu ghi "Prophet" thay vì "Soothsayer" — dùng "Soothsayer" vì có xác
# nhận trực tiếp từ trang Advancement của Fandom).
MONSTER_SEQUENCES = [
    (9, "Monster", "Quái Vật"),
    (8, "Robot", "Người Máy"),
    (7, "Lucky One", "Kẻ May Mắn"),
    (6, "Calamity Priest", "Tư Tế Tai Họa"),
    (5, "Winner", "Người Chiến Thắng"),
    (4, "Misfortune Mage", "Pháp Sư Bất Hạnh"),
    (3, "Chaoswalker", "Kẻ Du Hành Hỗn Loạn"),
    (2, "Soothsayer", "Nhà Tiên Tri"),
    (1, "Snake of Mercury", "Xà Thủy Ngân"),
    (0, "Wheel of Fortune", "Bánh Xe Vận Mệnh"),
]

_SOURCED_SEQUENCES = {
    "seer": SEER_SEQUENCES,
    "apprentice": APPRENTICE_SEQUENCES,
    "sailor": SAILOR_SEQUENCES,
    "reader": READER_SEQUENCES,
    "warrior": WARRIOR_SEQUENCES,
    "hunter": HUNTER_SEQUENCES,
    "apothecary": APOTHECARY_SEQUENCES,
    "marauder": MARAUDER_SEQUENCES,
    "spectator": SPECTATOR_SEQUENCES,
    "bard": BARD_SEQUENCES,
    "secrets_suppliant": SECRETS_SUPPLIANT_SEQUENCES,
    "corpse_collector": CORPSE_COLLECTOR_SEQUENCES,
    "sleepless": SLEEPLESS_SEQUENCES,
    "lawyer": LAWYER_SEQUENCES,
    "arbiter": ARBITER_SEQUENCES,
    "assassin": ASSASSIN_SEQUENCES,
    "criminal": CRIMINAL_SEQUENCES,
    "prisoner": PRISONER_SEQUENCES,
    "mystery_pryer": MYSTERY_PRYER_SEQUENCES,
    "savant": SAVANT_SEQUENCES,
    "planter": PLANTER_SEQUENCES,
    "monster": MONSTER_SEQUENCES,
}


def build_sequence_rows():
    """Trả về list các dòng (pathway_id, sequence_number, name_en, name_vi) để insert vào DB."""
    rows = []
    for pathway in PATHWAYS:
        pid = pathway["id"]
        if pid in _SOURCED_SEQUENCES:
            for num, name, name_vi in _SOURCED_SEQUENCES[pid]:
                rows.append((pid, num, name, name_vi))
        else:
            # Placeholder — điền tên thật theo tài liệu gốc khi có
            for num in range(9, -1, -1):
                rows.append((pid, num, f"Sequence {num}", f"Sequence {num}"))
    return rows

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
    {"id": "seer", "icon": "🃏", "name_en": "Seer", "title_en": "Fool"},
    {"id": "apprentice", "icon": "🚪", "name_en": "Apprentice", "title_en": "Door"},
    {"id": "marauder", "icon": "🕵️", "name_en": "Marauder", "title_en": "Error"},
    {"id": "spectator", "icon": "🎭", "name_en": "Spectator", "title_en": "Visionary"},
    {"id": "bard", "icon": "☀️", "name_en": "Bard", "title_en": "Sun"},
    {"id": "sailor", "icon": "⚡", "name_en": "Sailor", "title_en": "Tyrant"},
    {"id": "secrets_suppliant", "icon": "🪞", "name_en": "Secrets Suppliant", "title_en": "Hanged Man"},
    {"id": "reader", "icon": "📖", "name_en": "Reader", "title_en": "White Tower"},
    {"id": "corpse_collector", "icon": "💀", "name_en": "Corpse Collector", "title_en": "Death"},
    {"id": "sleepless", "icon": "🌙", "name_en": "Sleepless", "title_en": "Darkness"},
    {"id": "warrior", "icon": "⚔️", "name_en": "Warrior", "title_en": "Twilight Giant"},
    {"id": "lawyer", "icon": "⚖️", "name_en": "Lawyer", "title_en": "Black Emperor"},
    {"id": "arbiter", "icon": "📜", "name_en": "Arbiter", "title_en": "Justiciar"},
    {"id": "hunter", "icon": "🏹", "name_en": "Hunter", "title_en": "Red Priest"},
    {"id": "assassin", "icon": "🩸", "name_en": "Assassin", "title_en": "Demoness"},
    {"id": "criminal", "icon": "🔥", "name_en": "Criminal", "title_en": "Abyss"},
    {"id": "prisoner", "icon": "⛓️", "name_en": "Prisoner", "title_en": "Chained"},
    {"id": "mystery_pryer", "icon": "🔮", "name_en": "Mystery Pryer", "title_en": "Hermit"},
    {"id": "savant", "icon": "⚙️", "name_en": "Savant", "title_en": "Paragon"},
    {"id": "planter", "icon": "🌿", "name_en": "Planter", "title_en": "Mother"},
    {"id": "apothecary", "icon": "🧪", "name_en": "Apothecary", "title_en": "Moon"},
    {"id": "monster", "icon": "🎡", "name_en": "Monster", "title_en": "Wheel of Fortune"},
]

# Sequence 9 -> 0 mẫu đầy đủ cho Seer (mục 54 tài liệu đầu)
SEER_SEQUENCES = [
    (9, "Seer"),
    (8, "Clown"),
    (7, "Magician"),
    (6, "Faceless"),
    (5, "Marionettist"),
    (4, "Bizarro Sorcerer"),
    (3, "Scholar of Yore"),
    (2, "Miracle Invoker"),
    (1, "Attendant of Mysteries"),
    (0, "The Fool"),
]

# Sequence 9 -> 0 cho Apprentice / Door Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Door_Pathway/Advancement
# (trích dẫn Cuttlefish's WeChat Post "Apprentice Pathway Abilities"),
# đối chiếu craft wiki + webnovel reprint + Friends & Fables TTRPG guide.
APPRENTICE_SEQUENCES = [
    (9, "Apprentice"),
    (8, "Trickmaster"),
    (7, "Astrologer"),
    (6, "Scribe"),
    (5, "Traveler"),
    (4, "Secrets Sorcerer"),
    (3, "Wanderer"),
    (2, "Planeswalker"),
    (1, "Key of Stars"),
    (0, "Door"),
]

# Sequence 9 -> 0 cho Sailor / Tyrant Pathway.
# Nguồn: lord-of-the-mysteries-craft.fandom.com/wiki/Sailor_Pathway.
# LƯU Ý: tên Sequence 4 "Cataclysmic Interrer" nghe như lỗi đánh máy của
# wiki gốc (có thể là "Cataclysmic Interpreter") — cần đối chiếu lại khi
# có bản dịch chính thức, đừng coi là chắc chắn 100%.
SAILOR_SEQUENCES = [
    (9, "Sailor"),
    (8, "Folk of Rage"),
    (7, "Storm Priest"),
    (6, "Wind Blessed"),
    (5, "Ocean Songster"),
    (4, "Cataclysmic Interrer"),
    (3, "Sea King"),
    (2, "Calamity"),
    (1, "Thunder God"),
    (0, "Tyrant"),
]

# Sequence 9 -> 0 cho Reader / White Tower Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/White_Tower_Pathway/Abilities
# và /Advancement (không dùng bản "shop" — bản đó bịa hẳn 1 bộ tên khác).
READER_SEQUENCES = [
    (9, "Reader"),
    (8, "Student of Ratiocination"),
    (7, "Detective"),
    (6, "Polymath"),
    (5, "Mysticism Magister"),
    (4, "Prophet"),
    (3, "Cognizer"),
    (2, "Wisdom Angel"),
    (1, "Omniscient Eye"),
    (0, "White Tower"),
]

# Sequence 9 -> 0 cho Warrior / Twilight Giant Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Twilight_Giant_Pathway/Abilities.
# Tên thay thế trong ngoặc trên wiki gốc: Pugilist (Gladiator),
# Demon Hunter (Witcher), Glory, Twilight Giant (Twilight/Giant) — đã chọn
# tên chính, các biến thể có thể dùng làm alias hiển thị.
WARRIOR_SEQUENCES = [
    (9, "Warrior"),
    (8, "Pugilist"),
    (7, "Weapon Master"),
    (6, "Dawn Paladin"),
    (5, "Guardian"),
    (4, "Demon Hunter"),
    (3, "Silver Knight"),
    (2, "Glory"),
    (1, "Hand of God"),
    (0, "Twilight Giant"),
]

# Sequence 9 -> 0 cho Hunter / Red Priest Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Red_Priest_Pathway/Abilities
# và /Advancement (trích Cuttlefish's WeChat Post "Formulas and Abilities
# of the Red Priest Pathway").
HUNTER_SEQUENCES = [
    (9, "Hunter"),
    (8, "Provoker"),
    (7, "Pyromaniac"),
    (6, "Conspirer"),
    (5, "Reaper"),
    (4, "Iron-blooded Knight"),
    (3, "War Bishop"),
    (2, "Weather Warlock"),
    (1, "Conqueror"),
    (0, "Red Priest"),
]

# Sequence 9 -> 0 cho Apothecary / Moon Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Moon_Pathway/Advancement,
# đối chiếu Heroes Wiki (liệt kê đầy đủ Sequence 9->0 của Evernight Goddess).
# Sanguine (dòng máu ma cà rồng) dùng tên tước hiệu song song sau Sequence 7:
# Baron(6) Viscount(5) Earl(4) Marquis(3) Duke(2) Queen(1) — có thể dùng làm
# tên hiển thị thay thế cho nhân vật thuộc chủng Sanguine.
APOTHECARY_SEQUENCES = [
    (9, "Apothecary"),
    (8, "Beast Tamer"),
    (7, "Vampire"),
    (6, "Potions Professor"),
    (5, "Scarlet Scholar"),
    (4, "Shaman King"),
    (3, "High Summoner"),
    (2, "Life-Giver"),
    (1, "Beauty Goddess"),
    (0, "Moon"),
]

# Sequence 9 -> 0 cho Marauder / Error Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Error_Pathway (+ /Abilities,
# /Advancement, trích Cuttlefish's WeChat Post "Marauder Pathway Abilities"),
# đối chiếu NamuWiki (bản dịch Hàn) và webnovel reprint.
MARAUDER_SEQUENCES = [
    (9, "Marauder"),
    (8, "Swindler"),
    (7, "Cryptologist"),
    (6, "Prometheus"),
    (5, "Dream Stealer"),
    (4, "Parasite"),
    (3, "Mentor of Deceit"),
    (2, "Trojan Horse of Fate"),
    (1, "Worm of Time"),
    (0, "Error"),
]

# Sequence 9 -> 0 cho Spectator / Visionary Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Visionary_Pathway/Advancement
# (mục lục đầy đủ), đối chiếu webnovel reprint.
SPECTATOR_SEQUENCES = [
    (9, "Spectator"),
    (8, "Telepathist"),
    (7, "Psychiatrist"),
    (6, "Hypnotist"),
    (5, "Dreamwalker"),
    (4, "Manipulator"),
    (3, "Dream Weaver"),
    (2, "Discerner"),
    (1, "Author"),
    (0, "Visionary"),
]

# Sequence 9 -> 0 cho Bard / Sun Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Sun_Pathway/Abilities (mục lục
# đầy đủ), đối chiếu Friends & Fables TTRPG guide.
BARD_SEQUENCES = [
    (9, "Bard"),
    (8, "Light Suppliant"),
    (7, "Solar High Priest"),
    (6, "Notary"),
    (5, "Priest of Light"),
    (4, "Unshadowed"),
    (3, "Justice Mentor"),
    (2, "Lightseeker"),
    (1, "White Angel"),
    (0, "Sun"),
]

# Sequence 9 -> 0 cho Secrets Suppliant / Hanged Man Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Hanged_Man_Pathway/Advancement,
# đối chiếu Friends & Fables (khớp từng tên).
SECRETS_SUPPLIANT_SEQUENCES = [
    (9, "Secrets Suppliant"),
    (8, "Listener"),
    (7, "Shadow Ascetic"),
    (6, "Rose Bishop"),
    (5, "Shepherd"),
    (4, "Black Knight"),
    (3, "Trinity Templar"),
    (2, "Profane Presbyter"),
    (1, "Dark Angel"),
    (0, "Hanged Man"),
]

# Sequence 9 -> 0 cho Corpse Collector / Death Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Death_Pathway (+/Advancement),
# đối chiếu Friends & Fables. LƯU Ý: trang "shop" (không đáng tin) đảo
# ngược thứ tự Ferryman/Gatekeeper — bản dưới đây theo 2 nguồn đối chiếu.
CORPSE_COLLECTOR_SEQUENCES = [
    (9, "Corpse Collector"),
    (8, "Gravedigger"),
    (7, "Spirit Medium"),
    (6, "Spirit Guide"),
    (5, "Gatekeeper"),
    (4, "Undying"),
    (3, "Ferryman"),
    (2, "Death Consul"),
    (1, "Pale Emperor"),
    (0, "Death"),
]

# Sequence 9 -> 0 cho Sleepless / Darkness Pathway.
# Nguồn: TikTok tóm tắt chi tiết đối chiếu với lordofthemysteries.fandom.com
# (xác nhận riêng lẻ Sleepless/Midnight Poet/Nightmare/Nightwatcher) và
# fandomwire.com (xác nhận Sleepless/Midnight Poet/Nightmare).
SLEEPLESS_SEQUENCES = [
    (9, "Sleepless"),
    (8, "Midnight Poet"),
    (7, "Nightmare"),
    (6, "Soul Assurer"),
    (5, "Spirit Warlock"),
    (4, "Nightwatcher"),
    (3, "Horror Bishop"),
    (2, "Servant of Concealment"),
    (1, "Knight of Misfortune"),
    (0, "Darkness"),
]

# Sequence 9 -> 0 cho Lawyer / Black Emperor Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Black_Emperor_Pathway/Advancement,
# đối chiếu Friends & Fables (khớp từng tên).
LAWYER_SEQUENCES = [
    (9, "Lawyer"),
    (8, "Barbarian"),
    (7, "Briber"),
    (6, "Baron of Corruption"),
    (5, "Mentor of Disorder"),
    (4, "Earl of the Fallen"),
    (3, "Frenzied Mage"),
    (2, "Duke of Entropy"),
    (1, "Prince of Abolition"),
    (0, "Black Emperor"),
]

# Sequence 9 -> 0 cho Arbiter / Justiciar Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Justiciar_Pathway/Abilities
# (mục lục đầy đủ), đối chiếu Friends & Fables (khớp từng tên).
ARBITER_SEQUENCES = [
    (9, "Arbiter"),
    (8, "Sheriff"),
    (7, "Interrogator"),
    (6, "Judge"),
    (5, "Disciplinary Paladin"),
    (4, "Imperative Mage"),
    (3, "Chaos Hunter"),
    (2, "Balancer"),
    (1, "Hand of Order"),
    (0, "Justiciar"),
]

# Sequence 9 -> 0 cho Assassin / Demoness Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Demoness_Pathway (+/Abilities,
# /Advancement), đối chiếu Friends & Fables (khớp từng tên). Sequence 0 đôi
# khi được ghi là "Primordial Demoness" trên Card of Blasphemy — dùng
# "Demoness" làm tên chính theo quy ước phổ biến hơn.
ASSASSIN_SEQUENCES = [
    (9, "Assassin"),
    (8, "Instigator"),
    (7, "Witch"),
    (6, "Pleasure"),
    (5, "Affliction"),
    (4, "Despair"),
    (3, "Unaging"),
    (2, "Catastrophe"),
    (1, "Apocalypse"),
    (0, "Demoness"),
]

# Sequence 9 -> 0 cho Criminal / Abyss Pathway.
# Nguồn: TikTok tóm tắt đối chiếu với lordofthemysteries.fandom.com/wiki/
# Abyss_Pathway/Abilities (xác nhận riêng lẻ Criminal/Unwinged Angel/Serial
# Killer/Demon qua mô tả ability). LƯU Ý: Friends & Fables ghi tên khác cho
# Sequence 8 ("Coldblooded" thay vì "Unwinged Angel") — ưu tiên bản Fandom
# vì có mô tả ability chi tiết khớp với "Unwinged Angel", nhưng cần xác
# minh thêm nếu có bản dịch chính thức.
CRIMINAL_SEQUENCES = [
    (9, "Criminal"),
    (8, "Unwinged Angel"),
    (7, "Serial Killer"),
    (6, "Devil"),
    (5, "Desire Apostle"),
    (4, "Demon"),
    (3, "Blatherer"),
    (2, "Bloody Archduke"),
    (1, "Filthy Monarch"),
    (0, "Abyss"),
]

# Sequence 9 -> 0 cho Prisoner / Chained Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Chained_Pathway/Advancement
# (mục lục đầy đủ), đối chiếu Friends & Fables (khớp từng tên) và TikTok.
PRISONER_SEQUENCES = [
    (9, "Prisoner"),
    (8, "Lunatic"),
    (7, "Werewolf"),
    (6, "Zombie"),
    (5, "Wraith"),
    (4, "Puppet"),
    (3, "Disciple of Silence"),
    (2, "Ancient Bane"),
    (1, "Abomination"),
    (0, "Chained"),
]

# Sequence 9 -> 0 cho Mystery Pryer / Hermit Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Hermit_Pathway/Advancement +
# /Abilities (Sequence 9-6, 4), Hunting Hidden Sage + Moses Ascetic Order
# (Sequence 3 Clairvoyant, 2 Sage, 1 Knowledge Emperor), /wiki/Hermit_Pathway
# (Sequence 0). Baidu Baike ghi tên khác cho một số Sequence giữa (vd.
# "Combat Scholar" thay vì "Melee Scholar") — có thể là biến thể dịch.
MYSTERY_PRYER_SEQUENCES = [
    (9, "Mystery Pryer"),
    (8, "Melee Scholar"),
    (7, "Warlock"),
    (6, "Scrolls Professor"),
    (5, "Constellations Master"),
    (4, "Mysticologist"),
    (3, "Clairvoyant"),
    (2, "Sage"),
    (1, "Knowledge Emperor"),
    (0, "Hermit"),
]

# Sequence 9 -> 0 cho Savant / Paragon Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Paragon_Pathway/Advancement
# (mục lục đầy đủ), đối chiếu TikTok và Friends & Fables (khớp từng tên —
# 3 nguồn đồng nhất hoàn toàn, độ tin cậy cao).
SAVANT_SEQUENCES = [
    (9, "Savant"),
    (8, "Archaeologist"),
    (7, "Appraiser"),
    (6, "Artisan"),
    (5, "Astronomer"),
    (4, "Alchemist"),
    (3, "Arcane Scholar"),
    (2, "Knowledge Magister"),
    (1, "Illuminator"),
    (0, "Paragon"),
]

# Sequence 9 -> 0 cho Planter / Mother Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Mother_Pathway/Advancement
# (Sequence 9-3), /wiki/Mother_Pathway (Sequence 2 "Desolate Matriarch",
# Sequence 1 "Naturewalker", Sequence 0 "Mother" — xác nhận trực tiếp
# trong văn bản, có trích dẫn WeChat QnA của tác giả).
PLANTER_SEQUENCES = [
    (9, "Planter"),
    (8, "Doctor"),
    (7, "Harvest Priest"),
    (6, "Biologist"),
    (5, "Druid"),
    (4, "Ancient Alchemist"),
    (3, "Pallbearer"),
    (2, "Desolate Matriarch"),
    (1, "Naturewalker"),
    (0, "Mother"),
]

# Sequence 9 -> 0 cho Monster / Wheel of Fortune Pathway.
# Nguồn: lordofthemysteries.fandom.com/wiki/Wheel_of_Fortune_Pathway/
# Advancement (Sequence 9-6, và Chaoswalker/Soothsayer), đối chiếu Friends
# & Fables (khớp từng tên) và Baidu Baike (khớp phần lớn, riêng Sequence 2
# Baidu ghi "Prophet" thay vì "Soothsayer" — dùng "Soothsayer" vì có xác
# nhận trực tiếp từ trang Advancement của Fandom).
MONSTER_SEQUENCES = [
    (9, "Monster"),
    (8, "Robot"),
    (7, "Lucky One"),
    (6, "Calamity Priest"),
    (5, "Winner"),
    (4, "Misfortune Mage"),
    (3, "Chaoswalker"),
    (2, "Soothsayer"),
    (1, "Snake of Mercury"),
    (0, "Wheel of Fortune"),
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
    """Trả về list các dòng (pathway_id, sequence_number, name_en) để insert vào DB."""
    rows = []
    for pathway in PATHWAYS:
        pid = pathway["id"]
        if pid in _SOURCED_SEQUENCES:
            for num, name in _SOURCED_SEQUENCES[pid]:
                rows.append((pid, num, name))
        else:
            # Placeholder — điền tên thật theo tài liệu gốc khi có
            for num in range(9, -1, -1):
                rows.append((pid, num, f"Sequence {num}"))
    return rows

"""
Seed data cho Church (⛪) và Faction (🏛️) — mục 33-34 trong spec.
Đối chiếu nguồn chính thức Quỷ Bí Chi Chủ (Lord of the Mysteries):
7 Nhà Thờ Chính Thống (Seven/Eight Orthodox Churches) + một số Faction/tổ
chức bí mật lớn. Không tự bịa tên — dùng đúng tên đã được xác nhận.

Church controls_pathway: Pathway chính mà Church đó nắm giữ.
"""

# ---------- Churches (⛪ Chính Thống) ----------
# (church_id, name_en, name_vi, controls_pathway_id, description_vi, hq_location_hint)
CHURCHES = [
    (
        "evernight",
        "Church of the Evernight Goddess",
        "Nhà Thờ Nữ Thần Bất Dạ",
        "sleepless",
        "Một trong ba Nhà Thờ ảnh hưởng mạnh nhất tại Vương quốc Loen. Đội quân "
        "Beyonder của Nhà Thờ là Nighthawks (Ưng Đêm), tinh nhuệ hơn là Red Gloves "
        "(Găng Đỏ). Giáo lý xoay quanh bóng tối, bí mật và sự bảo vệ khỏi hiểm hoạ siêu nhiên.",
        "Backlund",
    ),
    (
        "storm",
        "Church of the Lord of Storms",
        "Nhà Thờ Chúa Tể Bão Tố",
        "sailor",
        "Nắm giữ Pathway Tyrant/Warrior, ảnh hưởng mạnh tại quần đảo Rorsted và biển "
        "Sonia. Đội quân chấp pháp của họ là Mandated Punishers.",
        "Pasu Island",
    ),
    (
        "steam",
        "Church of the God of Steam and Machinery",
        "Nhà Thờ Thần Hơi Nước và Máy Móc",
        "savant",
        "Nắm giữ Pathway Paragon, có ảnh hưởng lớn tại Cộng hòa Intis. Sở hữu ít Sealed "
        "Artifact nguy hiểm nhất trong các Nhà Thờ Chính Thống.",
        "Intis",
    ),
    (
        "sun",
        "Church of the Eternal Blazing Sun",
        "Nhà Thờ Thái Dương Vĩnh Hằng",
        "bard",
        "Một trong các Nhà Thờ Chính Thống lâu đời, quan hệ không tốt với Nhà Thờ Bão "
        "Tố và Nhà Thờ Tri Thức & Trí Tuệ.",
        "Intis",
    ),
    (
        "earth_mother",
        "Church of the Earth Mother",
        "Nhà Thờ Mẹ Đất",
        "planter",
        "Nhà Thờ gắn với sự sống, mùa màng và chữa lành, ảnh hưởng rộng khắp các vùng nông nghiệp.",
        "Southern Continent",
    ),
    (
        "wisdom",
        "Church of the God of Knowledge and Wisdom",
        "Nhà Thờ Thần Tri Thức và Trí Tuệ",
        "reader",
        "Tập trung vào tri thức, sách vở và Mysticism học thuật.",
        "Backlund",
    ),
    (
        "combat",
        "Church of the God of Combat",
        "Nhà Thờ Thần Chiến Tranh",
        "hunter",
        "Nhà Thờ gắn với Pathway Hunter, tôn thờ sức mạnh và vinh quang trong chiến trận.",
        "Feysac",
    ),
]

# ---------- Factions / tổ chức bí mật (🏛️) ----------
# (faction_id, name_en, name_vi, alignment, description_vi)
FACTIONS = [
    (
        "nighthawks",
        "Nighthawks",
        "Ưng Đêm",
        "orthodox",
        "Lực lượng Beyonder ngầm dưới trướng Nhà Thờ Nữ Thần Bất Dạ, thường ẩn danh dưới "
        "vỏ bọc cảnh sát hoặc công ty an ninh để xử lý sự vụ siêu nhiên.",
    ),
    (
        "rose",
        "Rose School of Thought",
        "Trường Phái Hoa Hồng",
        "grey",
        "Tổ chức bí mật lớn ở Nam Lục Địa, tin rằng ý chí sinh ra từ dục vọng có thể "
        "định hình thực tại. Nội bộ chia phe Túng Dục và Khắc Chế.",
    ),
    (
        "moses",
        "Moses Ascetic Order",
        "Giáo Đoàn Khổ Hạnh Moses",
        "grey",
        "Một giáo đoàn khổ hạnh nội bộ đầy mâu thuẫn và tha hoá.",
    ),
    (
        "mandated_punishers",
        "Mandated Punishers",
        "Đội Chấp Pháp",
        "orthodox",
        "Lực lượng chấp pháp chính thức của Nhà Thờ Chúa Tể Bão Tố, xử lý sự vụ liên quan "
        "tới tín đồ của Bão Tố.",
    ),
    (
        "independent",
        "Independent",
        "Độc Lập",
        "neutral",
        "Không thuộc về bất kỳ Church hay Faction lớn nào — tự do nhưng không có hậu thuẫn.",
    ),
]

# ---------- Tarot Club (🃏) — mục 35 ----------
# Danh xưng theo lá bài Tarot, đúng canon (tên Tarot dùng làm mật danh, giấu
# danh tính thật). Không gán player cụ thể — chỉ seed các "ghế" Tarot còn trống
# để player có thể xin gia nhập và được cấp một mật danh.
TAROT_SEATS = [
    "The Fool", "The Magician", "The High Priestess", "The Empress", "The Emperor",
    "The Hierophant", "The Lovers", "The Chariot", "Strength", "The Hermit",
    "Wheel of Fortune", "Justice", "The Hanged Man", "Death", "Temperance",
    "The Devil", "The Tower", "The Star", "The Moon", "The Sun", "Judgement", "The World",
]

# ---------- Faction/Church Mission (mục 33-34) ----------
# (mission_id, org_type, org_id, name_vi, monster_id, required_kills,
#  min_reputation, reward_money, reward_exp, reward_reputation)
# org_type: "church" | "faction" — tham chiếu character_church/character_faction.
# min_reputation gate thật: Rank thấp không nhận được Mission bậc cao.
_LOW_TIER = ["street_thug", "ghoul", "hound_of_bones", "cult_fanatic"]
_HIGH_TIER = ["slum_grave_robber", "sand_wraith", "forsaken_dockworker_horror", "sand_pharaoh_remnant"]

_ORGS = [("church", cid) for cid, *_ in CHURCHES] + [("faction", fid) for fid, *_ in FACTIONS]

FACTION_MISSIONS = []
for _i, (_org_type, _org_id) in enumerate(_ORGS):
    _low = _LOW_TIER[_i % len(_LOW_TIER)]
    _high = _HIGH_TIER[_i % len(_HIGH_TIER)]
    FACTION_MISSIONS.append((
        f"{_org_id}_mission_1", _org_type, _org_id,
        f"Thanh trừng: {_low}", _low, 3, 0, 200, 80, 10,
    ))
    FACTION_MISSIONS.append((
        f"{_org_id}_mission_2", _org_type, _org_id,
        f"Nhiệm vụ bậc cao: {_high}", _high, 3, 30, 600, 250, 20,
    ))


TAROT_DESCRIPTION_VI = (
    "Một tổ chức bí mật do chính các thành viên lập nên để trao đổi tài nguyên, thông tin "
    "và hỗ trợ nhau trên con đường tiến cấp. Các cuộc họp diễn ra ở một không gian sương mù "
    "ẩn giấu, và mọi thành viên chỉ biết nhau qua danh xưng lá bài Tarot — danh tính thật "
    "tuyệt đối được bảo mật."
)

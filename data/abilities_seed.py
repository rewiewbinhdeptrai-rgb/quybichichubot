"""
Ability cố định theo Pathway + Sequence (mục 17 trong spec).

Ability được mở khóa khi: character.sequence_number <= ability.sequence_number
(Sequence càng thấp = càng mạnh, nên đạt Sequence N nghĩa là mở luôn
Ability của mọi Sequence >= N mà nhân vật đã đi qua).

Trạng thái dữ liệu:
- Cả 22/22 Pathway giờ đã có đủ 10 Ability (Sequence 9 -> 0) = 220 Ability
  tổng cộng. Không còn Pathway nào fallback "Basic Strike" chung chung
  trong combat.py nữa.
- Tên Ability = tên Sequence thật (từ data/pathways_seed.py, đã đối chiếu
  nguồn — xem SOURCE NOTE trong file đó) + một "dạng thức" (verb) riêng
  theo đúng phong cách/nghề nghiệp của từng Pathway (vd Warrior dùng
  "Strike", Apothecary dùng "Elixir", Lawyer dùng "Verdict"...). Đây vẫn
  là dữ liệu tĩnh trong Database — không phải AI runtime tạo ra (đúng yêu
  cầu mục 17: "AI không được tạo Ability runtime").
- cost / damage_multiplier dùng chung 1 công thức tuyến tính theo độ sâu
  Sequence để đảm bảo cân bằng nhất quán giữa 22 Pathway:
      cost               = 5 + (9 - sequence_number) * 3
      damage_multiplier  = 1.2 + (9 - sequence_number) * 0.15
  (Sequence càng thấp -> cost Spirituality càng cao nhưng damage càng lớn,
  giống hệt công thức đã dùng cho Seer từ bản trước — không đổi số dư cũ.)
"""
from data.pathways_seed import (
    SEER_SEQUENCES,
    APPRENTICE_SEQUENCES,
    MARAUDER_SEQUENCES,
    SPECTATOR_SEQUENCES,
    BARD_SEQUENCES,
    SAILOR_SEQUENCES,
    SECRETS_SUPPLIANT_SEQUENCES,
    READER_SEQUENCES,
    CORPSE_COLLECTOR_SEQUENCES,
    SLEEPLESS_SEQUENCES,
    WARRIOR_SEQUENCES,
    LAWYER_SEQUENCES,
    ARBITER_SEQUENCES,
    HUNTER_SEQUENCES,
    ASSASSIN_SEQUENCES,
    CRIMINAL_SEQUENCES,
    PRISONER_SEQUENCES,
    MYSTERY_PRYER_SEQUENCES,
    SAVANT_SEQUENCES,
    PLANTER_SEQUENCES,
    APOTHECARY_SEQUENCES,
    MONSTER_SEQUENCES,
)

# (pathway_id, danh sách Sequence 9->0 thật, "dạng thức" ghép tên Ability EN,
#  "dạng thức" tiếng Việt — theo bảng thuật ngữ, ghép TRƯỚC tên Sequence,
#  vd "Strike" -> "Đòn Đánh" nên "Warrior Strike" -> "Đòn Đánh Chiến Binh")
PATHWAY_ABILITY_STYLE = [
    ("seer", SEER_SEQUENCES, "Technique", "Bí Thuật"),
    ("apprentice", APPRENTICE_SEQUENCES, "Incantation", "Chú Ngôn"),
    ("marauder", MARAUDER_SEQUENCES, "Maneuver", "Thủ Pháp"),
    ("spectator", SPECTATOR_SEQUENCES, "Illusion", "Ảo Thuật"),
    ("bard", BARD_SEQUENCES, "Hymn", "Thánh Ca"),
    ("sailor", SAILOR_SEQUENCES, "Tempest", "Bão Tố"),
    ("secrets_suppliant", SECRETS_SUPPLIANT_SEQUENCES, "Pact", "Khế Ước"),
    ("reader", READER_SEQUENCES, "Revelation", "Khải Thị"),
    ("corpse_collector", CORPSE_COLLECTOR_SEQUENCES, "Rite", "Nghi Thức"),
    ("sleepless", SLEEPLESS_SEQUENCES, "Nightmare", "Ác Mộng"),
    ("warrior", WARRIOR_SEQUENCES, "Strike", "Đòn Đánh"),
    ("lawyer", LAWYER_SEQUENCES, "Verdict", "Phán Quyết"),
    ("arbiter", ARBITER_SEQUENCES, "Judgment", "Phán Quyết"),
    ("hunter", HUNTER_SEQUENCES, "Hunt", "Săn Đuổi"),
    ("assassin", ASSASSIN_SEQUENCES, "Blade", "Lưỡi Dao"),
    ("criminal", CRIMINAL_SEQUENCES, "Havoc", "Tàn Phá"),
    ("prisoner", PRISONER_SEQUENCES, "Restraint", "Trói Buộc"),
    ("mystery_pryer", MYSTERY_PRYER_SEQUENCES, "Insight", "Minh Giác"),
    ("savant", SAVANT_SEQUENCES, "Construct", "Tạo Vật"),
    ("planter", PLANTER_SEQUENCES, "Growth", "Sinh Trưởng"),
    ("apothecary", APOTHECARY_SEQUENCES, "Elixir", "Ma Dược"),
    ("monster", MONSTER_SEQUENCES, "Fortune", "Vận May"),
]


def build_ability_rows():
    """Trả về list (pathway_id, sequence_number, ability_id, name_en, name_vi,
    cost, damage_multiplier) để insert — dùng cho cả 22 Pathway, không riêng
    Seer nữa. ability_id giữ đúng format cũ f"{pathway_id}_{seq_num}" nên dữ
    liệu Seer cũ (đã có người chơi test) không bị đổi id."""
    rows = []
    for pathway_id, sequences, verb, verb_vi in PATHWAY_ABILITY_STYLE:
        for seq_num, seq_name, seq_name_vi in sequences:
            ability_id = f"{pathway_id}_{seq_num}"
            cost = 5 + (9 - seq_num) * 3
            damage_multiplier = round(1.2 + (9 - seq_num) * 0.15, 2)
            name = f"{seq_name} {verb}"
            name_vi = f"{verb_vi} {seq_name_vi}"
            rows.append((pathway_id, seq_num, ability_id, name, name_vi, cost, damage_multiplier))
    return rows

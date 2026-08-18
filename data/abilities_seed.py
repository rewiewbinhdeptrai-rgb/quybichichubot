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

# (pathway_id, danh sách Sequence 9->0 thật, "dạng thức" ghép tên Ability)
PATHWAY_ABILITY_STYLE = [
    ("seer", SEER_SEQUENCES, "Technique"),
    ("apprentice", APPRENTICE_SEQUENCES, "Incantation"),
    ("marauder", MARAUDER_SEQUENCES, "Maneuver"),
    ("spectator", SPECTATOR_SEQUENCES, "Illusion"),
    ("bard", BARD_SEQUENCES, "Hymn"),
    ("sailor", SAILOR_SEQUENCES, "Tempest"),
    ("secrets_suppliant", SECRETS_SUPPLIANT_SEQUENCES, "Pact"),
    ("reader", READER_SEQUENCES, "Revelation"),
    ("corpse_collector", CORPSE_COLLECTOR_SEQUENCES, "Rite"),
    ("sleepless", SLEEPLESS_SEQUENCES, "Nightmare"),
    ("warrior", WARRIOR_SEQUENCES, "Strike"),
    ("lawyer", LAWYER_SEQUENCES, "Verdict"),
    ("arbiter", ARBITER_SEQUENCES, "Judgment"),
    ("hunter", HUNTER_SEQUENCES, "Hunt"),
    ("assassin", ASSASSIN_SEQUENCES, "Blade"),
    ("criminal", CRIMINAL_SEQUENCES, "Havoc"),
    ("prisoner", PRISONER_SEQUENCES, "Restraint"),
    ("mystery_pryer", MYSTERY_PRYER_SEQUENCES, "Insight"),
    ("savant", SAVANT_SEQUENCES, "Construct"),
    ("planter", PLANTER_SEQUENCES, "Growth"),
    ("apothecary", APOTHECARY_SEQUENCES, "Elixir"),
    ("monster", MONSTER_SEQUENCES, "Fortune"),
]


def build_ability_rows():
    """Trả về list (pathway_id, sequence_number, ability_id, name_en, cost,
    damage_multiplier) để insert — dùng cho cả 22 Pathway, không riêng Seer
    nữa. ability_id giữ đúng format cũ f"{pathway_id}_{seq_num}" nên dữ
    liệu Seer cũ (đã có người chơi test) không bị đổi id."""
    rows = []
    for pathway_id, sequences, verb in PATHWAY_ABILITY_STYLE:
        for seq_num, seq_name in sequences:
            ability_id = f"{pathway_id}_{seq_num}"
            cost = 5 + (9 - seq_num) * 3
            damage_multiplier = round(1.2 + (9 - seq_num) * 0.15, 2)
            name = f"{seq_name} {verb}"
            rows.append((pathway_id, seq_num, ability_id, name, cost, damage_multiplier))
    return rows

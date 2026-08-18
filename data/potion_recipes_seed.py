"""
Công thức Potion (mục 9 — Recipe/Ingredients/Ingredient quantity).

Mỗi entry: (pathway_id, target_sequence, item_id, quantity).

Trạng thái dữ liệu (đã cập nhật — không còn recipe generic dùng chung):
- SEER: 9 công thức thật (Sequence 8 -> 0), mỗi công thức 2 nguyên liệu theo
  chủ đề riêng của Sequence đó, tăng số lượng dần theo Sequence càng thấp.
- 21 PATHWAY CÒN LẠI: mỗi Pathway có 2 nguyên liệu riêng (xem
  data/items_seed.py, PATHWAY_INGREDIENTS bên dưới), dùng chung 1 công thức
  tăng số lượng theo độ sâu Sequence:
      depth = 8 - target_sequence                 # 0 (Seq 8) .. 8 (Seq 0)
      qty_a = 1 + depth // 3                       # 1,1,1,2,2,2,3,3,3
      qty_b = 1 + depth // 2                       # 1,1,2,2,3,3,4,4,5
  Nguyên liệu chưa được viết riêng theo từng Sequence (như Seer đã có) —
  đây là bước kế tiếp nếu muốn nâng sâu hơn nữa — nhưng KHÔNG còn dùng
  chung 1 bộ generic cho cả 21 Pathway nữa, mỗi Pathway đã có công thức
  của riêng mình, Craft chạy đúng theo lore Pathway đó.
"""

# (item_id, quantity) x2, theo Sequence 8 -> 0 của Seer — nguyên liệu nặng dần.
SEER_RECIPES = {
    8: [("ing_greasepaint", 2), ("ing_playing_card", 1)],
    7: [("ing_silver_coin", 2), ("ing_playing_card", 2)],
    6: [("ing_blank_mask", 2), ("ing_silver_coin", 2)],
    5: [("ing_puppet_string", 3), ("ing_blank_mask", 1)],
    4: [("ing_wax_doll", 2), ("ing_puppet_string", 3)],
    3: [("ing_bizarre_powder", 3), ("ing_wax_doll", 2)],
    2: [("ing_old_tome_page", 2), ("ing_bizarre_powder", 3)],
    1: [("ing_miracle_dust", 2), ("ing_old_tome_page", 3)],
    0: [("ing_sealed_letter", 1), ("ing_miracle_dust", 4)],
}

# 2 nguyên liệu riêng cho mỗi Pathway còn lại (item_id đã khai báo trong
# data/items_seed.py). Không dùng chung fallback generic nữa.
PATHWAY_INGREDIENTS = {
    "apprentice": ("ing_apprentice_chalk", "ing_apprentice_key"),
    "marauder": ("ing_marauder_lockpick", "ing_marauder_gloves"),
    "spectator": ("ing_spectator_mirror", "ing_spectator_veil"),
    "bard": ("ing_bard_string", "ing_bard_petal"),
    "sailor": ("ing_sailor_rope", "ing_sailor_shell"),
    "secrets_suppliant": ("ing_secrets_suppliant_rope", "ing_secrets_suppliant_coin"),
    "reader": ("ing_reader_bookmark", "ing_reader_ink"),
    "corpse_collector": ("ing_corpse_collector_shroud", "ing_corpse_collector_bell"),
    "sleepless": ("ing_sleepless_candle", "ing_sleepless_dust"),
    "warrior": ("ing_warrior_bandage", "ing_warrior_whetstone"),
    "lawyer": ("ing_lawyer_seal", "ing_lawyer_parchment"),
    "arbiter": ("ing_arbiter_badge", "ing_arbiter_shackle"),
    "hunter": ("ing_hunter_arrowhead", "ing_hunter_vial"),
    "assassin": ("ing_assassin_needle", "ing_assassin_veil"),
    "criminal": ("ing_criminal_ash", "ing_criminal_coin"),
    "prisoner": ("ing_prisoner_chain", "ing_prisoner_cloth"),
    "mystery_pryer": ("ing_mystery_pryer_lens", "ing_mystery_pryer_notebook"),
    "savant": ("ing_savant_gear", "ing_savant_wire"),
    "planter": ("ing_planter_seed", "ing_planter_sap"),
    "apothecary": ("ing_apothecary_root", "ing_apothecary_vial"),
    "monster": ("ing_monster_dice", "ing_monster_card"),
}

_SOURCED_RECIPES = {
    "seer": SEER_RECIPES,
}


def _formula_recipe(item_a: str, item_b: str, target_sequence: int):
    """Công thức chung cho 21 Pathway: số lượng tăng dần theo độ sâu
    Sequence (Sequence càng thấp = càng khó Chế tạo)."""
    depth = 8 - target_sequence  # 0 (Seq 8) .. 8 (Seq 0)
    qty_a = 1 + depth // 3
    qty_b = 1 + depth // 2
    return [(item_a, qty_a), (item_b, qty_b)]


def build_potion_recipe_rows():
    """Trả về list (pathway_id, target_sequence, item_id, quantity) để insert.
    Dùng chung PATHWAYS từ pathways_seed để không lặp danh sách 22 pathway_id."""
    from data.pathways_seed import PATHWAYS

    rows = []
    for pathway in PATHWAYS:
        pid = pathway["id"]
        sourced = _SOURCED_RECIPES.get(pid)
        for seq_num in range(8, -1, -1):  # Sequence 9 không cần Potion (điểm khởi đầu)
            if sourced and seq_num in sourced:
                recipe = sourced[seq_num]
            else:
                item_a, item_b = PATHWAY_INGREDIENTS[pid]
                recipe = _formula_recipe(item_a, item_b, seq_num)
            for item_id, quantity in recipe:
                rows.append((pid, seq_num, item_id, quantity))
    return rows

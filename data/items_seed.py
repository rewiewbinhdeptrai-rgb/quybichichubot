"""
Item tĩnh (mục 22, 59). Bản demo: 2 Consumable (hồi HP/Spirituality) +
2 Equipment (Vũ khí/Giáp, cộng modifier thật qua EffectEngine khi trang bị)
+ 1 Material (chưa có hệ thống Craft dùng tới, chỉ để demo Túi đồ).

type: material | consumable | equipment
equip_slot: weapon | armor | None
modifier_key/modifier_value: dùng chung EffectEngine (effects.py) khi equip
heal_hp/heal_spirituality: dùng khi Consumable (inventory.use_item)
"""

ITEMS = [
    # item_id, name_en, type, description, heal_hp, heal_spirituality,
    # equip_slot, modifier_key, modifier_value
    (
        "healing_draught", "Healing Draught", "consumable",
        "Hồi 30 HP ngay lập tức.", 30, 0, None, None, None,
    ),
    (
        "spirit_incense", "Spirit Incense", "consumable",
        "Hồi 20 Spirituality ngay lập tức.", 0, 20, None, None, None,
    ),
    (
        "rusty_dagger", "Rusty Dagger", "equipment",
        "Vũ khí cũ kỹ nhưng vẫn sắc. Physical Damage +10% khi trang bị.",
        0, 0, "weapon", "physical_damage_pct", 10,
    ),
    (
        "leather_vest", "Leather Vest", "equipment",
        "Áo giáp da nhẹ. Giảm 10% sát thương nhận vào khi trang bị.",
        0, 0, "armor", "damage_taken_pct", -10,
    ),
    (
        "obscure_journal", "Obscure Journal", "material",
        "Nhật ký cũ ghi lại vài ký hiệu huyền bí — chưa rõ tác dụng.",
        0, 0, None, None, None,
    ),
]

# ---------------------------------------------------------------------------
# Ritual Material (mục 20 — Materials của Nghi thức tiến cấp). type="ritual_material".
# Tách hẳn khỏi "ingredient" (nguyên liệu Chế tạo Potion, mục 9) vì đây là thứ
# bị tiêu thụ ở BƯỚC KHÁC trong flow (Digestion 100% -> Ritual), không phải
# lúc Craft Potion. Hiện dùng chung 3 vật liệu generic cho toàn bộ 22 Pathway
# (đặt tên trung tính, không lore riêng) — giống cách potion_recipes_seed.py
# đang tạm dùng nguyên liệu generic cho 21/22 Pathway: chạy được thật, không
# phải chuỗi giả, nhưng cần thay bằng vật liệu theo lore từng Pathway sau.
# ---------------------------------------------------------------------------
RITUAL_MATERIAL_ITEMS = [
    ("rit_black_candle", "Black Ritual Candle", "ritual_material", "Nến đen dùng để khoanh vùng Nghi thức.", 0, 0, None, None, None),
    ("rit_silver_chalk", "Silver Ritual Chalk", "ritual_material", "Phấn bạc để vẽ vòng tròn nghi thức.", 0, 0, None, None, None),
    ("rit_sealing_wax", "Sealing Wax", "ritual_material", "Sáp niêm phong dùng để khóa nghi thức sau khi hoàn tất.", 0, 0, None, None, None),
]

# ---------------------------------------------------------------------------
# Nguyên liệu Potion (mục 9 — Ingredients). type="ingredient".
#
# Cả 22/22 Pathway giờ có nguyên liệu riêng theo chủ đề:
# - SEER: bộ đầy đủ nhất — 10 nguyên liệu, mỗi Sequence 1 món riêng (đối
#   chiếu cùng nguồn với data/pathways_seed.py).
# - 21 Pathway còn lại: mỗi Pathway có 2 nguyên liệu riêng theo lore/nghề
#   nghiệp (vd Warrior dùng băng gạc + đá mài, Apothecary dùng rễ cây +
#   lọ thuốc rỗng...), số lượng cần trong công thức tăng dần theo Sequence
#   càng thấp — xem PATHWAY_INGREDIENTS trong potion_recipes_seed.py.
# - raw_mystical_essence/spirit_ash/forbidden_ink chỉ còn là fallback dự
#   phòng cho Pathway mới thêm sau này, không còn Pathway nào trong 22
#   pathway hiện tại dùng 3 món này nữa.
# ---------------------------------------------------------------------------
INGREDIENT_ITEMS = [
    # --- Seer (đầy đủ, theo chủ đề từng Sequence) ---
    ("ing_greasepaint", "Cracked Greasepaint", "ingredient", "Phấn hóa trang nứt nẻ của một gánh xiếc lưu động.", 0, 0, None, None, None),
    ("ing_playing_card", "Marked Playing Card", "ingredient", "Lá bài đã bị đánh dấu bằng ký hiệu không thuộc bộ bài thường.", 0, 0, None, None, None),
    ("ing_silver_coin", "Tarnished Silver Coin", "ingredient", "Đồng xu bạc xỉn màu, dùng trong ảo thuật đánh lạc hướng.", 0, 0, None, None, None),
    ("ing_blank_mask", "Blank Porcelain Mask", "ingredient", "Mặt nạ sứ trắng không có biểu cảm.", 0, 0, None, None, None),
    ("ing_puppet_string", "Tangled Puppet String", "ingredient", "Sợi dây rối đã dùng để điều khiển một con rối gỗ.", 0, 0, None, None, None),
    ("ing_wax_doll", "Miniature Wax Doll", "ingredient", "Búp bê sáp nhỏ, dùng trong nghi thức điều khiển từ xa.", 0, 0, None, None, None),
    ("ing_bizarre_powder", "Bizarre Compound Powder", "ingredient", "Bột hợp chất kỳ dị, đổi màu khi tiếp xúc ánh trăng.", 0, 0, None, None, None),
    ("ing_old_tome_page", "Page Torn from an Old Tome", "ingredient", "Một trang giấy xé ra từ sách cổ ghi chép lịch sử bị lãng quên.", 0, 0, None, None, None),
    ("ing_miracle_dust", "Miracle Dust", "ingredient", "Bụi mịn phát sáng yếu ớt, tương truyền liên quan tới phép màu.", 0, 0, None, None, None),
    ("ing_sealed_letter", "Sealed Attendant's Letter", "ingredient", "Thư niêm phong bằng sáp đỏ, chưa ai dám mở.", 0, 0, None, None, None),

    # --- Generic fallback (chỉ dùng nếu tương lai thêm Pathway mới chưa
    # kịp viết nguyên liệu riêng — không còn Pathway nào trong 22 pathway
    # hiện tại dùng bộ này nữa, xem PATHWAY_INGREDIENTS trong
    # potion_recipes_seed.py) ---
    ("raw_mystical_essence", "Raw Mystical Essence", "ingredient", "Tinh chất huyền bí thô, chưa tinh luyện theo Pathway cụ thể.", 0, 0, None, None, None),
    ("spirit_ash", "Spirit Ash", "ingredient", "Tro tàn còn vương lại dư khí linh hồn.", 0, 0, None, None, None),
    ("forbidden_ink", "Forbidden Ink", "ingredient", "Mực viết dùng trong các nghi thức bị cấm.", 0, 0, None, None, None),

    # --- 21 Pathway còn lại: 2 nguyên liệu theo chủ đề riêng/pathway ---
    ("ing_apprentice_chalk", "Astrologer's Chalk", "ingredient", "Phấn vẽ sơ đồ chiêm tinh, còn dính bụi sao.", 0, 0, None, None, None),
    ("ing_apprentice_key", "Bent Brass Key", "ingredient", "Chìa khóa đồng bị bẻ cong sau một nghi thức mở Cánh cửa.", 0, 0, None, None, None),

    ("ing_marauder_lockpick", "Bent Lockpick", "ingredient", "Móc khóa cong vênh vì dùng quá nhiều lần.", 0, 0, None, None, None),
    ("ing_marauder_gloves", "Worn Leather Gloves", "ingredient", "Găng da mòn, không để lại dấu vân tay.", 0, 0, None, None, None),

    ("ing_spectator_mirror", "Cracked Hand Mirror", "ingredient", "Gương cầm tay nứt, phản chiếu sai lệch một chút.", 0, 0, None, None, None),
    ("ing_spectator_veil", "Gauze Veil", "ingredient", "Mạng che mặt mỏng dùng trong ảo thuật thôi miên.", 0, 0, None, None, None),

    ("ing_bard_string", "Broken Lute String", "ingredient", "Dây đàn lute đứt, vẫn còn ngân nhẹ khi chạm vào.", 0, 0, None, None, None),
    ("ing_bard_petal", "Sunlit Petal", "ingredient", "Cánh hoa hong dưới nắng, ấm bất thường.", 0, 0, None, None, None),

    ("ing_sailor_rope", "Frayed Sailor's Rope", "ingredient", "Dây thừng sờn, còn mùi muối biển.", 0, 0, None, None, None),
    ("ing_sailor_shell", "Storm-Worn Seashell", "ingredient", "Vỏ sò bị bão đánh dạt vào bờ, bên trong vọng tiếng gió.", 0, 0, None, None, None),

    ("ing_secrets_suppliant_rope", "Hangman's Cord", "ingredient", "Sợi dây thừng thắt nút hình đặc biệt.", 0, 0, None, None, None),
    ("ing_secrets_suppliant_coin", "Fate-Marked Coin", "ingredient", "Đồng xu khắc ký hiệu định mệnh mờ nhạt.", 0, 0, None, None, None),

    ("ing_reader_bookmark", "Worn Leather Bookmark", "ingredient", "Dấu trang da cũ, kẹp ở đúng một trang sách cấm.", 0, 0, None, None, None),
    ("ing_reader_ink", "Faded Iron-Gall Ink", "ingredient", "Mực sắt cổ đã phai, vẫn còn đọc được dưới ánh nến.", 0, 0, None, None, None),

    ("ing_corpse_collector_shroud", "Burial Shroud Fragment", "ingredient", "Mảnh vải liệm còn vương hơi lạnh.", 0, 0, None, None, None),
    ("ing_corpse_collector_bell", "Funeral Bell", "ingredient", "Chuông tang nhỏ, rung lên không phát ra âm thanh bình thường.", 0, 0, None, None, None),

    ("ing_sleepless_candle", "Midnight Tallow Candle", "ingredient", "Nến mỡ chỉ cháy đúng vào lúc nửa đêm.", 0, 0, None, None, None),
    ("ing_sleepless_dust", "Nightmare Dust", "ingredient", "Bụi mịn thu được từ giấc mơ dữ của người khác.", 0, 0, None, None, None),

    ("ing_warrior_bandage", "Bloodstained Bandage", "ingredient", "Băng gạc dính máu khô từ một trận chiến sinh tử.", 0, 0, None, None, None),
    ("ing_warrior_whetstone", "Battle Whetstone", "ingredient", "Đá mài vũ khí đã qua hàng trăm trận.", 0, 0, None, None, None),

    ("ing_lawyer_seal", "Notary's Wax Seal", "ingredient", "Con dấu sáp công chứng, ràng buộc pháp lý thật sự.", 0, 0, None, None, None),
    ("ing_lawyer_parchment", "Contract Parchment Scrap", "ingredient", "Mảnh giấy da hợp đồng còn sót lại điều khoản chưa ký.", 0, 0, None, None, None),

    ("ing_arbiter_badge", "Tarnished Patrol Badge", "ingredient", "Phù hiệu tuần tra đã xỉn màu.", 0, 0, None, None, None),
    ("ing_arbiter_shackle", "Iron Shackle Fragment", "ingredient", "Mảnh cùm sắt gãy từ một vụ trừng phạt.", 0, 0, None, None, None),

    ("ing_hunter_arrowhead", "Blessed Arrowhead", "ingredient", "Đầu mũi tên được ban phước theo nghi thức máu.", 0, 0, None, None, None),
    ("ing_hunter_vial", "Vial of Sacrificial Blood", "ingredient", "Lọ máu hiến tế nhỏ, vẫn còn ấm.", 0, 0, None, None, None),

    ("ing_assassin_needle", "Poisoned Needle", "ingredient", "Cây kim tẩm độc dùng trong các vụ ám sát im lặng.", 0, 0, None, None, None),
    ("ing_assassin_veil", "Black Silk Veil", "ingredient", "Khăn lụa đen dùng để ẩn danh tính.", 0, 0, None, None, None),

    ("ing_criminal_ash", "Riot Ash", "ingredient", "Tro tàn thu được từ một cuộc bạo loạn.", 0, 0, None, None, None),
    ("ing_criminal_coin", "Counterfeit Coin", "ingredient", "Đồng xu giả tinh xảo, gần như không thể phân biệt.", 0, 0, None, None, None),

    ("ing_prisoner_chain", "Rusted Chain Link", "ingredient", "Mắt xích gỉ sét từ một xà lim cũ.", 0, 0, None, None, None),
    ("ing_prisoner_cloth", "Prison Cloth Scrap", "ingredient", "Mảnh vải tù nhân sờn rách.", 0, 0, None, None, None),

    ("ing_mystery_pryer_lens", "Cracked Observation Lens", "ingredient", "Thấu kính quan sát nứt, vẫn phóng đại được chi tiết nhỏ.", 0, 0, None, None, None),
    ("ing_mystery_pryer_notebook", "Sealed Field Notebook", "ingredient", "Sổ tay ghi chép thực địa được niêm phong.", 0, 0, None, None, None),

    ("ing_savant_gear", "Precision Brass Gear", "ingredient", "Bánh răng đồng chế tác chính xác tới từng milimet.", 0, 0, None, None, None),
    ("ing_savant_wire", "Copper Coil Wire", "ingredient", "Dây đồng cuộn dùng trong các phát minh cơ khí.", 0, 0, None, None, None),

    ("ing_planter_seed", "Blighted Seed", "ingredient", "Hạt giống nhiễm bệnh nhưng vẫn nảy mầm bất thường.", 0, 0, None, None, None),
    ("ing_planter_sap", "Thick Green Sap", "ingredient", "Nhựa cây đặc sánh, chảy chậm như có ý thức.", 0, 0, None, None, None),

    ("ing_apothecary_root", "Moonlit Root", "ingredient", "Rễ cây chỉ đào được dưới ánh trăng tròn.", 0, 0, None, None, None),
    ("ing_apothecary_vial", "Empty Medicine Vial", "ingredient", "Lọ thuốc rỗng còn vương mùi dược liệu cũ.", 0, 0, None, None, None),

    ("ing_monster_dice", "Loaded Dice", "ingredient", "Xúc xắc gian lận, nhưng luôn ra đúng con số cần thiết.", 0, 0, None, None, None),
    ("ing_monster_card", "Wheel-Marked Card", "ingredient", "Lá bài khắc hình bánh xe định mệnh.", 0, 0, None, None, None),
]

ITEMS = ITEMS + INGREDIENT_ITEMS + RITUAL_MATERIAL_ITEMS

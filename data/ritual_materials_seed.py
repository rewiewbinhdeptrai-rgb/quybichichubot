"""
Ritual Materials (mục 20 — Materials cần cho Nghi thức tiến cấp).

Đây là vật liệu bị tiêu thụ ở bước Ritual (sau khi Digestion đã 100%), TÁCH
RIÊNG khỏi Potion Recipe (mục 9, potion_recipes_seed.py) vốn tiêu thụ ở bước
Craft Potion sớm hơn nhiều trong flow. Hai bước phải trả giá nguyên liệu
riêng biệt, không dùng chung một bảng.

Trạng thái dữ liệu: CHƯA có Pathway nào có vật liệu riêng theo lore — cả
22/22 Pathway đang dùng chung 3 vật liệu generic (rit_black_candle,
rit_silver_chalk, rit_sealing_wax trong items_seed.py). Số lượng tăng dần
theo Sequence càng thấp (Nghi thức càng sâu càng tốn nhiều). Đây LÀ dữ liệu
thật trong DB (Ritual chạy được, có transaction thật), nhưng không phải
vật liệu được nghiên cứu riêng theo chủ đề từng Pathway — cần thay dần,
cùng tình trạng với potion_recipes_seed.py hiện tại.
"""

_RITUAL_MATERIAL_ITEMS = ["rit_black_candle", "rit_silver_chalk", "rit_sealing_wax"]


def build_ritual_material_rows():
    """Trả về list (pathway_id, target_sequence, item_id, quantity) để insert.
    Quantity mỗi vật liệu = 1 + (9 - target_sequence) // 3, để Sequence càng
    thấp (gần 0) càng cần nhiều vật liệu hơn Sequence cao."""
    from data.pathways_seed import PATHWAYS

    rows = []
    for pathway in PATHWAYS:
        pid = pathway["id"]
        for seq_num in range(8, -1, -1):  # Sequence 9 không cần Ritual (điểm khởi đầu)
            quantity = 1 + (9 - seq_num) // 3
            for item_id in _RITUAL_MATERIAL_ITEMS:
                rows.append((pid, seq_num, item_id, quantity))
    return rows

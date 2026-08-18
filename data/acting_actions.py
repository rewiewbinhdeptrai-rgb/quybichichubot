"""
Acting Method — hành động gameplay đóng góp Digestion (mục 10-11).

Đây KHÔNG phải "?digest +10%" đơn giản: mỗi action gắn với một pathway cụ
thể, engine (progression.py) validate action có hợp lệ với pathway hiện
tại mới cộng Digestion.

Trạng thái dữ liệu:
- Cả 22/22 Pathway giờ đã có Acting Method riêng theo chủ đề (4 action/
  pathway, gain 5-10%), thiết kế bám theo phong cách nhân vật/nghề nghiệp
  của từng Pathway (vd: Corpse Collector thao tác với tử thi, Savant chế
  tạo máy móc...), không còn pathway nào rơi vào _default.
- _default vẫn giữ lại làm fallback an toàn cho get_actions() — chỉ dùng
  nếu tương lai thêm Pathway mới mà chưa kịp viết Acting Method riêng,
  không phải vì 21 Pathway "còn thiếu" như trước nữa.
"""

ACTING_ACTIONS = {
    "seer": [
        ("divination", "🃏 Bói toán", 8),
        ("observe", "🔍 Quan sát", 5),
        ("deceive", "🎭 Đánh lừa", 10),
        ("evade", "🏃 Né tránh", 6),
    ],
    "apprentice": [
        ("study_spell", "📖 Nghiên cứu phép thuật", 8),
        ("practice_ritual", "🕯️ Luyện tập nghi thức nhỏ", 6),
        ("record_formula", "✍️ Ghi chép công thức", 5),
        ("experiment_material", "⚗️ Thí nghiệm nguyên liệu", 9),
    ],
    "marauder": [
        ("steal", "🖐️ Trộm cắp", 9),
        ("sneak", "🥷 Ẩn nấp", 6),
        ("break_in", "🚪 Đột nhập", 10),
        ("cover_tracks", "🧹 Xóa dấu vết", 5),
    ],
    "spectator": [
        ("hypnotize", "🌀 Thôi miên", 9),
        ("illusion", "🎪 Tạo ảo giác", 8),
        ("psych_read", "🧠 Đọc tâm lý đối phương", 6),
        ("manipulate_perception", "👁️ Thao túng nhận thức", 10),
    ],
    "bard": [
        ("sing", "🎵 Ca hát", 6),
        ("heal_touch", "✨ Chữa lành", 8),
        ("inspire", "🔥 Truyền cảm hứng", 7),
        ("sunlit_meditate", "☀️ Thiền dưới ánh mặt trời", 5),
    ],
    "sailor": [
        ("command_crew", "🗣️ Chỉ huy thủy thủ", 7),
        ("storm_control", "🌩️ Điều khiển bão", 10),
        ("navigate", "🧭 Hàng hải", 5),
        ("suppress_mutiny", "⚡ Trấn áp phản loạn", 8),
    ],
    "secrets_suppliant": [
        ("pry_secret", "🪞 Dò xét bí mật", 9),
        ("fate_knot", "🪢 Thắt nút định mệnh", 8),
        ("trade_secret", "🤝 Trao đổi bí mật", 6),
        ("minor_sacrifice", "🔪 Hiến tế nhỏ", 10),
    ],
    "reader": [
        ("read_forbidden", "📚 Đọc sách cấm", 8),
        ("knowledge_meditate", "🧘 Thiền định tri thức", 6),
        ("decode_text", "🔍 Giải mã văn bản cổ", 7),
        ("observe_spirit", "👻 Quan sát linh hồn", 9),
    ],
    "corpse_collector": [
        ("collect_corpse", "⚰️ Thu thập tử thi", 8),
        ("funeral_rite", "🕯️ Nghi thức tang lễ", 7),
        ("commune_spirit", "👻 Giao tiếp linh hồn", 9),
        ("anatomy_study", "🔬 Nghiên cứu giải phẫu", 6),
    ],
    "sleepless": [
        ("night_watch", "🌙 Thức trắng canh gác", 6),
        ("shadow_control", "🌑 Điều khiển bóng tối", 9),
        ("dream_intrude", "💤 Thâm nhập giấc mơ", 10),
        ("suppress_fear", "😨 Trấn áp nỗi sợ", 7),
    ],
    "warrior": [
        ("physical_train", "🏋️ Rèn luyện thể chất", 6),
        ("charge", "⚔️ Xung trận", 9),
        ("battle_roar", "📢 Gào thét chiến trận", 7),
        ("endure_pain", "🩹 Chịu đau", 8),
    ],
    "lawyer": [
        ("study_law", "⚖️ Nghiên cứu luật", 6),
        ("defend", "🗣️ Biện hộ", 8),
        ("interrogate", "❓ Thẩm vấn", 7),
        ("draft_contract", "📜 Soạn hợp đồng ràng buộc", 9),
    ],
    "arbiter": [
        ("investigate_crime", "🔍 Điều tra tội ác", 8),
        ("judge", "⚖️ Phán xét", 9),
        ("punish", "🔨 Trừng phạt", 10),
        ("patrol", "🚶 Tuần tra", 5),
    ],
    "hunter": [
        ("hunt", "🏹 Săn lùng", 8),
        ("track", "👣 Truy vết", 6),
        ("blood_sacrifice", "🩸 Hiến tế máu", 10),
        ("blood_prayer", "🙏 Cầu nguyện đẫm máu", 7),
    ],
    "assassin": [
        ("assassinate", "🗡️ Ám sát", 10),
        ("seduce", "💋 Quyến rũ", 7),
        ("go_unseen", "🕶️ Ẩn danh", 6),
        ("gather_poison", "🧪 Thu thập độc dược", 8),
    ],
    "criminal": [
        ("commit_crime", "🔥 Gây án", 9),
        ("manipulate_gang", "🕴️ Thao túng băng đảng", 8),
        ("spread_chaos", "💥 Lan truyền hỗn loạn", 10),
        ("evade_law", "🏃 Trốn tránh pháp luật", 6),
    ],
    "prisoner": [
        ("endure_confinement", "⛓️ Chịu đựng giam cầm", 7),
        ("self_restrain", "🔗 Tự trói buộc", 6),
        ("break_out", "🚨 Vượt ngục", 10),
        ("resist_torture", "🩹 Kháng cự tra tấn", 9),
    ],
    "mystery_pryer": [
        ("seclude", "🏚️ Ẩn cư", 5),
        ("pry_mystery", "🔮 Dò xét huyền bí", 9),
        ("record_observation", "📝 Ghi chép quan sát", 6),
        ("avoid_contact", "🚫 Tránh né tiếp xúc", 7),
    ],
    "savant": [
        ("build_machine", "⚙️ Chế tạo máy móc", 9),
        ("calculate", "🧮 Tính toán", 6),
        ("improve_invention", "💡 Cải tiến phát minh", 8),
        ("technical_test", "🔧 Thử nghiệm kỹ thuật", 7),
    ],
    "planter": [
        ("sow_seed", "🌱 Gieo trồng", 6),
        ("nurture_creature", "🐛 Nuôi dưỡng sinh vật", 7),
        ("harvest", "🌾 Thu hoạch", 8),
        ("heal_land", "🌍 Chữa lành đất đai", 9),
    ],
    "apothecary": [
        ("brew_medicine", "⚗️ Bào chế dược liệu", 8),
        ("moon_observe", "🌕 Quan sát trăng", 6),
        ("mix_potion", "🧪 Pha chế thuốc", 9),
        ("study_poison", "☠️ Nghiên cứu độc dược", 7),
    ],
    "monster": [
        ("gamble", "🎲 Đánh bạc", 8),
        ("test_luck", "🍀 Thử vận may", 6),
        ("cause_chaos", "🌪️ Gây hỗn loạn", 10),
        ("read_fate", "🎡 Đọc vận mệnh", 9),
    ],
    "_default": [
        ("study", "📚 Nghiên cứu", 5),
        ("train", "🏋️ Rèn luyện", 5),
        ("meditate", "🧘 Thiền định", 4),
    ],
}


def get_actions(pathway_id: str):
    return ACTING_ACTIONS.get(pathway_id, ACTING_ACTIONS["_default"])

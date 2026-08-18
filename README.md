# Quỷ Bí — Discord Bot (Skeleton)

Skeleton bot Python (discord.py) + SQLite, dựng theo bản MASTER SPECIFICATION
(mục 0–68). Đây là **khung kiến trúc + `/menu` phân tầng + schema DB cơ bản**,
không phải bản đầy đủ toàn bộ hệ thống (Combat, Economy, NPC AI...).

## Chạy thử

```bash
pip install -r requirements.txt
cp .env.example .env      # điền DISCORD_TOKEN của bot bạn
python bot.py
```

Nếu điền `DEV_GUILD_ID` trong `.env`, slash command sẽ đồng bộ tức thời cho
1 server (dùng khi test). Bỏ trống thì sync global (có thể mất tới ~1h để
Discord hiện lệnh).

## Đã có

- `/menu` — menu chính (mục 52–53): hiện hồ sơ nhân vật + dropdown chọn hệ thống.
- **🧬 Con đường** (mục 54–56):
  - Chọn Pathway (22 Pathway, dữ liệu ở `data/pathways_seed.py`) — nếu nhân
    vật chưa có Pathway, có nút **"Nhận Pathway này (Sequence 9)"**.
  - Chọn Sequence 9→0 — Sequence chưa đạt hiển thị 🔒 và **không cho bypass**
    advancement (chọn vào chỉ hiện thông báo, không set được Sequence).
  - Sequence CHÍNH nhân vật đang đứng hiển thị **Digestion % thật** đọc từ
    Engine (không còn placeholder "Chưa có dữ liệu").
- **🎒 Tài sản → 🧪 Ma dược** — flow đầy đủ theo mục 9–12, đọc/ghi DB thật:
  - **Uống Potion** → tạo tiến trình digesting, áp debuff `potion_instability`
    thật (tăng Loss of Control Risk có thể đo được).
  - **Thực hành (Acting Method)** — action riêng theo Pathway
    (`data/acting_actions.py`, Seer có 4 action mẫu: Bói toán/Quan sát/Đánh
    lừa/Né tránh) → cộng % Digestion thật, action không hợp Pathway bị từ chối.
  - **Nghi thức tiến cấp** — chỉ chạy được khi Digestion = 100%; có 15% khả
    năng thất bại gây **Backlash thật** (giảm Digestion + debuff
    `ritual_backlash`) thay vì luôn thành công vô điều kiện (mục 20).
  - Thành công thật sự **UPDATE `characters.sequence_number`** trong DB —
    không có cách nào set trực tiếp từ UI.
- **EffectEngine trung tâm** (`effects.py`, mục 15–16): buff/debuff có
  `modifier_key` (vd `physical_damage_pct`, `damage_taken_pct`,
  `loss_of_control_risk_flat`) được cộng dồn thật qua `get_modifier_sum()` —
  không có buff nào chỉ tồn tại trên embed. `calculate_damage()` và
  `calculate_incoming_damage()` được Combat Engine dùng thật.
- **🎒 Tài sản → 🎒 Túi đồ / ⚔️ Trang bị** (`inventory.py`, mục 22, 59):
  - **Túi đồ** — liệt kê item thật (số lượng, mô tả), dùng Consumable
    (Healing Draught/Spirit Incense) hồi đúng HP/Spirituality và trừ đúng
    1 item khỏi túi.
  - **Trang bị** — Equip/Unequip Vũ khí và Giáp **không có hệ số tính
    riêng**: mỗi lần equip áp thẳng một Effect vào EffectEngine
    (`source="equip:<slot>"`, gần như vĩnh viễn) — dùng lại đúng
    `effects.get_modifier_sum()` mà Combat đang dùng, đúng nguyên tắc mục 16
    "một Effect Engine dùng chung cho mọi hệ thống". Unequip xóa đúng effect
    theo source, không đụng buff/debuff khác.
  - Monster giờ **rớt đồ thật** khi thắng PvE (`drop_item_id`/`drop_chance`
    trong `data/monsters_seed.py`) — không phải loot giả.
- **⚔️ Chiến đấu → 👹 PvE** (`combat.py`, mục 23–27) — trận đấu turn-based
  thật lưu trong bảng `combat_sessions`:
  - **Tấn công** — damage tính qua `effects.calculate_damage()`, Monster
    phản đòn ngay trong lượt.
  - **Dùng Ability** — chỉ hiện Ability đã mở khóa theo Sequence hiện tại
    (mục 17), trừ đúng Spirituality thật, damage nhân theo `damage_multiplier`.
  - **Phòng thủ** — áp buff `defending` (-30% sát thương nhận vào) **có hiệu
    lực thật** lên đòn phản công ngay lượt đó, không phải chỉ hiện chữ.
  - **Rút lui** — 50% thành công; thất bại thì Monster được đánh miễn phí.
  - Thắng/thua đều `db.apply_combat_result()` — một transaction đồng bộ HP +
    Tiền + EXP (mục 49–50). Thua trận: HP về 1, mất 10% tiền (mục 13 —
    hậu quả "nặng", không phải chết hẳn).
  - 3 Monster mẫu trong `data/monsters_seed.py`; 10 Ability mẫu cho Seer
    (một theo mỗi Sequence) trong `data/abilities_seed.py`.
- **🎒 Tài sản → 🎒 Túi đồ / ⚔️ Trang bị** (`inventory.py`, mục 22, 59):
  - **Túi đồ** — liệt kê item thật (số lượng, mô tả), dùng Consumable
    (Healing Draught/Spirit Incense) hồi đúng HP/Spirituality và trừ đúng
    1 item khỏi túi.
  - **Trang bị** — Equip/Unequip Vũ khí và Giáp **không có hệ số tính
    riêng**: mỗi lần equip áp thẳng một Effect vào EffectEngine
    (`source="equip:<slot>"`, gần như vĩnh viễn) — dùng lại đúng
    `effects.get_modifier_sum()` mà Combat đang dùng, đúng nguyên tắc mục 16
    "một Effect Engine dùng chung cho mọi hệ thống". Unequip xóa đúng effect
    theo source, không đụng buff/debuff khác.
  - Monster giờ **rớt đồ thật** khi thắng PvE (`drop_item_id`/`drop_chance`
    trong `data/monsters_seed.py`) — không phải loot giả.
  - Nhân vật mới được cấp 1 Healing Draught khởi đầu (dữ liệu thật trong
    `inventory`, không phải hiển thị giả).
- **⚔️ Chiến đấu → 🏟️ PvP** (`pvp.py`, mục 24) — đối thủ là Character thật,
  turn-based **luân phiên** (không auto-counter cùng lượt như PvE):
  - Thách đấu qua `UserSelect` (chọn thẳng thành viên Discord) — chặn tự
    thách đấu chính mình, chặn thách đấu khi đang có trận khác hoặc lời mời
    khác chưa trả lời, chặn khi một bên đang 0 HP.
  - Chấp nhận/Từ chối — chấp nhận sẽ chốt HP hiện tại (không hồi đầy) của cả
    hai làm điểm bắt đầu và random ai đi trước (Engine quyết định, không phải
    UI); clear buff/debuff cũ trước trận.
  - Mỗi hành động **kiểm tra đúng lượt** (`turn_character_id`) trước khi cho
    thực hiện — hành động sai lượt bị `PvPError` chặn, không silent-fail.
  - Tấn công/Ability dùng lại đúng `effects.calculate_damage()` +
    `effects.calculate_incoming_damage()` của Combat Engine — buff/debuff
    (vd Phòng thủ) có hiệu lực thật giữa hai người chơi thật, không phải chỉ
    hiện trên embed.
  - Thắng/thua/rút lui đều qua `db.apply_pvp_result()` — một transaction
    chuyển **Bảng cược thật** (mặc định 500) từ người thua sang người thắng
    + đồng bộ HP (mục 49-50). Thua/rút lui: HP về 1, không chết hẳn (mục 13).
  - Rút lui trong PvP luôn bị xử thua ngay (khác PvE rút lui 50%), vì đối thủ
    là người thật — không thể để trận "treo" lại được.
- **👤 Nhân vật**, **⚙️ Cài đặt → Ngôn ngữ** (vi/en, lưu vào bảng `users`).
- **🧿 Beyonder Characteristic** (`characteristics.py`, mục 21) — thật, không
  còn là bảng rỗng:
  - Nghi thức tiến cấp **thành công** (`progression.perform_advancement`) tự
    động cấp 1 Characteristic gắn chết vào đúng `(pathway_id, sequence_number)`
    vừa đạt — không phải item rơi ngẫu nhiên, không do AI runtime tạo.
  - `UNIQUE(character_id, pathway_id, sequence_number)` + `INSERT OR IGNORE`
    chặn duplicate nếu Advancement Engine lỡ gọi lại (idempotent).
  - Xem tại **👤 Nhân vật → Beyonder Characteristic**: liệt kê sở hữu, trạng
    thái `stored`/`consumed`, Stability, nguồn gốc.
  - **Tiêu thụ (Consumption)** đã có hiệu lực Engine thật: +5 Spirituality
    tối đa vĩnh viễn qua `db.set_character_spirituality_max()` (mục 15 — không
    phải chỉ đổi cờ trong DB), chặn tiêu thụ 2 lần / tiêu thụ Characteristic
    không phải của mình.
  - **Chưa làm**: Transfer sang Character khác (cần Trade Engine mục 38 làm
    atomic trước — xem docstring đầu `characteristics.py`).
- **📜 Ritual** (`ritual.py`, mục 20) — Nghi thức tiến cấp KHÔNG còn roll 85%
  cố định:
  - Success chance = `potion.stability` (mục 9) + bonus từ Beyonder
    Characteristic đang sở hữu (mục 21) − Loss of Control Risk hiện tại
    (mục 13), kẹp 5–95% — không bao giờ chắc 100% hay chắc thất bại.
  - **Materials** (bảng `ritual_materials`, tách riêng khỏi Potion Recipe)
    bị trừ atomic qua `db.consume_ritual_materials_transaction()`: thiếu bất
    kỳ vật liệu nào thì KHÔNG trừ gì cả (all-or-nothing), đủ thì trừ hết dù
    kết quả sau đó thế nào.
  - 3 outcome thật (mục 20: Ritual Result), không chỉ success/fail:
    `success` (tăng Sequence + cấp Characteristic), `interruption` (mất vật
    liệu, Digestion giữ nguyên, thử lại ngay được), `backlash` (mất vật liệu
    + Digestion -30 + debuff `ritual_backlash`).
  - Mọi lần thử được ghi vào `ritual_history` (roll, chance, outcome) — mục
    20 yêu cầu Result phải lưu lại được, không chỉ hiện trên Embed rồi mất.
  - **Chưa làm**: Location/Time/Participants (Ritual nhóm nhiều người) —
    cần Party Engine (mục 36) trước.
- **🕯️ Vật phẩm thần kỳ — Sealed Artifact** (`artifacts.py`, mục 22) — thật,
  không còn là bảng rỗng:
  - Mỗi Character bắt đầu với 1 `unlabeled_glass_vial` (Unknown grade) trong
    `database.create_character`.
  - **Quan sát (Inspect)** — miễn phí, không giới hạn số lần gọi, mỗi lần mở
    khóa đúng 1 trong 3 stage theo thứ tự cố định `effect → rule →
    side_effect` (bảng `artifact_rules`), khớp flow mục 22 "Unknown → Inspect
    → ... → Discover Rule".
  - **Thực nghiệm (Experiment)** — trừ đúng 1 lượt trong `uses_remaining`
    (từ `usage_limit` tĩnh), áp **Effect thật** qua EffectEngine
    (`effects.apply_effect`), roll `risk_stars × chance%` để kích hoạt Side
    Effect (cũng là Effect thật, không phải text), và tự mở khóa cả 3 stage
    cùng lúc (trải nghiệm trực tiếp = học được cách nó hoạt động).
    Hết `uses_remaining` thì `ArtifactError` chặn Experiment tiếp.
  - 4 Artifact demo có Effect/Side Effect riêng (`data/artifacts_seed.py`) —
    **chưa phải kho Artifact đầy đủ theo lore**, nhưng flow chạy được thật.
  - **Chưa làm**: Acquisition ngoài starter item (loot từ Monster/World),
    Transfer sang Character khác (cần Trade Engine mục 38).
- **🔮 Huyền bí → Kiến thức** (`mysticism.py`, mục 18) — thật:
  - Flow bắt buộc `Unknown → Discovered → Studied → Understood`
    (`character_knowledge`, không có row = Unknown ngầm định).
  - Mỗi bước trừ đúng Spirituality thật qua
    `db.set_character_hp_spirituality()` (không đủ thì `MysticismError`
    chặn, không cho bypass thứ tự — Study trước khi Discover bị chặn).
  - **Thấu hiểu (Understand)** có % Risk thật (`understand_risk`) kích hoạt
    debuff `mysticism_overreach` qua EffectEngine (mục 13, 18: nghiên cứu
    Huyền bí quá sâu là nguồn Loss of Control Risk thật).
  - Một số kiến thức (`mystic_stabilization_technique`) khi Understood áp
    buff **vĩnh viễn** (`mystic_insight`, duration cực lớn) qua EffectEngine
    — hiệu lực thật (mục 15), không chỉ đổi cờ trong DB.
  - **Chưa làm**: Investigation Engine (mục 27) để Discover qua manh mối
    thay vì chỉ trả Spirituality trực tiếp.
- **🔮 Huyền bí → Bói toán** (`divination.py`, mục 19) — thật:
  - 5/8 phương pháp trong spec có Engine chạy được: Tarot, Crystal Ball,
    Astrology, Dream, Spiritual Perception (`data/divination_seed.py`).
  - Kết quả do **Engine roll trước** (`accuracy = base_accuracy −
    loss_of_control_risk`, roll 1-100 → tier `clear/vague/failed/ominous`) —
    đúng mục 19/30: AI (nếu gắn sau) chỉ được diễn đạt lại, không tự quyết
    định tier.
  - Tier `ominous` kích hoạt debuff `divination_backlash` thật (mục 13).
  - Mọi lần Bói toán ghi vào `divination_history` (roll, accuracy, tier).
  - **Chưa làm**: Item/Location/Person Divination (soi mục tiêu cụ thể) —
    cần World/NPC Engine (mục 27–28) tồn tại trước để có mục tiêu thật.
- Các nhóm còn lại (Năng lực, Thế giới, Tổ chức, Giao dịch, Đời sống) vẫn chỉ
  hiện khung "🚧 chưa triển khai" — **đúng nguyên tắc mục 58: không tạo dữ
  liệu giả**.
- Tạo nhân vật qua Modal (mục 57) khi user chưa có Character.

## Database (`database.py`)

SQLite, bảng: `users`, `pathways`, `sequences`, `characters`, `potions`,
`character_progress`, `effect_definitions`, `character_effects`, `action_log`,
`monsters`, `abilities`, `combat_sessions`, `items`, `inventory`,
`character_equipment`, `pvp_sessions`, `character_characteristics`,
`ritual_materials`, `ritual_history`, `artifacts`, `artifact_rules`,
`character_artifacts`, `artifact_history`, `knowledge_definitions`,
`character_knowledge`, `divination_methods`, `divination_history`.
Vẫn là bản rút gọn của schema đầy đủ ở mục 48 — mở rộng thêm các bảng
(`dungeons`, `market`, `npcs`, ...) theo cùng
pattern: mọi state đi qua hàm trong `database.py`/`effects.py`/
`progression.py`/`combat.py`/`inventory.py`/`characteristics.py`/`ritual.py`/
`artifacts.py`/`mysticism.py`/`divination.py`, KHÔNG để UI (`cogs/menu.py`)
tự tính toán số liệu game (mục 1, 15, 51).

## Cấu trúc

```
quyby-bot/
├── bot.py                    # entry point, sync slash command
├── config.py                  # env config + bộ icon thống nhất (mục 54)
├── database.py                 # schema + access layer, nguồn sự thật (mục 48)
├── effects.py                  # EffectEngine trung tâm (mục 15-16)
├── progression.py              # Potion/Acting/Digestion/Advancement (mục 9-12)
├── combat.py                   # Combat Engine PvE (mục 23-27)
├── pvp.py                      # PvP Engine — turn-based luân phiên 2 Character (mục 24)
├── inventory.py                # Item/Equipment engine (mục 22, 59)
├── ritual.py                    # Ritual Engine — success chance thật (mục 20)
├── characteristics.py           # Beyonder Characteristic engine (mục 21)
├── artifacts.py                  # Sealed Artifact engine — Inspect/Experiment (mục 22)
├── mysticism.py                  # Mysticism Knowledge engine (mục 18)
├── divination.py                 # Divination engine (mục 19)
├── data/
│   ├── pathways_seed.py       # dữ liệu tĩnh 22 Pathway (mục 6, 55, 67)
│   ├── effects_seed.py        # định nghĩa buff/debuff (mục 15)
│   ├── acting_actions.py      # Acting Method action theo Pathway (mục 10)
│   ├── monsters_seed.py       # Monster PvE + drop rate (mục 25)
│   ├── abilities_seed.py      # Ability theo Sequence (mục 17)
│   ├── items_seed.py          # Item/Equipment tĩnh (mục 22, 59)
│   ├── potion_recipes_seed.py # Công thức Potion (mục 9)
│   ├── ritual_materials_seed.py # Vật liệu Ritual (mục 20)
│   ├── artifacts_seed.py      # Sealed Artifact tĩnh + Effect riêng (mục 22)
│   ├── knowledge_seed.py      # Mysticism Knowledge tĩnh (mục 18)
│   └── divination_seed.py     # Divination Method tĩnh (mục 19)
└── cogs/
    └── menu.py                 # toàn bộ UI phân tầng /menu (mục 52-65)
```

## Đã tự kiểm thử (không cần token Discord)

`effects.py`, `progression.py`, `combat.py`, `inventory.py` đã chạy test
trực tiếp qua `python3 -c "..."` xác nhận bằng số liệu thật:
- Buff/debuff cộng đúng % damage và % risk.
- Full vòng Uống Potion → Thực hành → Digestion 100% → Nghi thức →
  `sequence_number` đổi thật trong SQLite.
- Combat: Ability trừ đúng Spirituality, Phòng thủ giảm đúng % sát thương
  phản đòn (6 → 4 sát thương, đúng công thức -30%), thắng trận cộng đúng
  tiền/EXP, thua trận trừ đúng 10% tiền + HP về 1, Rút lui 50% tỉ lệ.
- Inventory: dùng Consumable hồi đúng HP và trừ đúng item; equip Vũ khí +
  Giáp cùng lúc cộng/trừ đúng % qua EffectEngine (100→110 dmg, 20→18 dmg
  nhận vào); unequip trả lại đúng số gốc; Monster rớt đồ thật khi thắng.
- PvP: thách đấu trùng bị chặn, hành động sai lượt bị `PvPError` chặn
  (`turn_character_id` kiểm tra đúng), turn luân phiên đúng thứ tự qua nhiều
  lượt, thắng trận cộng đúng 500 Bảng lấy từ người thua (transaction 2 chiều
  qua `apply_pvp_result`), thua trận HP về 1 — test chạy thật 13 lượt tới khi
  một bên 0 HP, số liệu tiền/HP cuối cùng khớp công thức.
- Sealed Artifact: 3 lần Inspect liên tiếp mở đúng 3 stage theo thứ tự cố
  định, lần Inspect thứ 4 trả về `stage=None`; Experiment trừ đúng
  `uses_remaining` (4→3→...→0), lần gọi thứ 5 bị `ArtifactError` chặn đúng
  ("hết lượt sử dụng"); Effect áp thật quan sát được trong
  `character_effects`.
- Mysticism Knowledge: Study bị chặn nếu gọi trước Discover
  (`MysticismError`); full flow Discover→Study→Understand trừ đúng
  Spirituality từng bước (100→70 cho `ritual_symbols_101`); kiến thức có
  `unlock_effect_id` (`mystic_stabilization_technique`) áp đúng buff
  `mystic_insight` vĩnh viễn sau khi Understood.
- Divination: method không tồn tại bị chặn đúng lỗi; không đủ Spirituality
  bị chặn đúng lỗi (test ép Spirituality còn 2, cần 20 cho Spiritual
  Perception); roll thật trả về tier hợp lệ + trừ đúng Spirituality.
- World/Location (mục 31–32, `world.py`): Character mới luôn có
  `location_id` thật ngay từ lúc tạo (không NULL, không cần backfill riêng);
  di chuyển trong cùng thành phố miễn phí, cùng địa điểm bị `WorldError`
  chặn ("Bạn đã ở đây rồi"); di chuyển sang thành phố khác bị chặn đúng khi
  không đủ tiền, và trừ đúng `travel_cost` khi đủ tiền (test: 0 → chặn ở
  250 Bảng → nạp 1000 → trừ còn 750); mỗi lần di chuyển ghi đúng 1 dòng vào
  `travel_log`. Đã test riêng đường **migrate**: tạo DB giả lập kiểu cũ
  (bảng `characters` chưa có cột `location_id`) rồi gọi `init_db()` —
  cột được thêm với `DEFAULT 'backlund_center'` nên Character cũ tự động có
  Location thật, không bị lơ lửng.
- NPC (mục 28, `npc.py`): danh sách NPC tại 1 Location đọc thật qua
  `location_id` (không thấy NPC ở Location khác — test chặn đúng khi Talk
  một NPC không cùng chỗ đứng); Trò chuyện +1 Trust thật mỗi lần, câu thoại
  đổi đúng theo `trust_tier` (test 5 lần liên tiếp: trust 0→5, vẫn tier
  "stranger" — đúng ngưỡng 20); Tặng quà trừ đúng 1 item khỏi Túi đồ thật
  (test: không có item bị chặn, có item thì trừ về 0), +5 Trust nếu đúng
  món NPC thích / +1 nếu không; mọi lần Talk/Gift đều ghi 1 dòng
  `npc_memory` — test xác nhận log đủ 6 dòng sau 5 lần Talk + 1 lần Gift.
  Đã test riêng đường migrate: xoá hết 4 bảng NPC khỏi DB rồi gọi
  `init_db()` lại — tự tạo + seed lại đúng, không mất dữ liệu bảng khác.

Phần UI (`cogs/menu.py`) đã qua `py_compile` (không lỗi cú pháp) nhưng CHƯA
chạy được với discord.py thật trong môi trường này (không có mạng để cài
package `discord.py` trong lần cập nhật này) — bạn nên tự chạy thử `/menu`
trên server test trước khi dùng thật, đặc biệt các view mới: 🕯️ Vật phẩm
thần kỳ, 🔮 Huyền bí → Kiến thức/Bói toán.

## Chưa làm (còn quá lớn để làm "full" trong một lần)

Economy/Market/Auction, AI dialogue thật (Gemini/Groq + Context Builder),
World Event, Dungeon procedural, Church/Faction/Tarot, Investigation/Clue
system, Ranking/Achievement, Contract/Bounty, Ability/Năng lực UI thật
(đang stub dù `abilities` đã có data), localization file `locales/*.json`.
Mỗi hệ thống này tự nó đã bằng khối lượng vừa làm ở trên.

**Mới xong ở bản này:** NPC entity thật (mục 28, `npc.py` +
`data/npc_seed.py`) — 6 NPC gắn thật vào Location đã có (Harold the
Merchant ở Bến cảng Backlund, Father Elias ở Nhà thờ Backlund, Nell the
Informant ở Khu ổ chuột, Old Ambrose ở Thư viện Skruvi, Sister Odette ở
Tingen, Captain Reyes ở Trier). `/menu` → 🗺️ Thế giới → 👤 NPC đã hook
thật: chỉ hiện NPC đứng cùng Location hiện tại của Character, Trò chuyện
(+1 Trust, câu thoại đổi theo `trust_tier`: Người lạ/Quen biết/Tin tưởng),
Tặng quà (trừ thật 1 item khỏi Túi đồ qua `db.remove_inventory_item`, +5
Trust nếu đúng món NPC thích/+1 nếu không). Mọi tương tác log vào
`npc_memory` — NPC "nhớ" hành động của người chơi theo đúng số liệu, không
phải suy diễn AI. **CHƯA có** AI Narrative layer (mục 29 — cần
Gemini/Groq + Context Builder, việc riêng lớn hơn nhiều): dialogue hiện là
ngân hàng câu tĩnh, không sinh động theo ngữ cảnh.

**Quan trọng:** 21/22 Pathway vẫn chỉ có Sequence placeholder
(`"Sequence N"`) và chưa có Ability riêng (`data/pathways_seed.py`,
`data/abilities_seed.py`) — chỉ Seer có dữ liệu đầy đủ. PvP/PvE vừa làm
xong vẫn CHẠY ĐƯỢC với Pathway khác (fallback Basic Strike), nhưng chưa thể
hiện đúng gameplay Beyonder theo Pathway cho tới khi điền dữ liệu 21 Pathway
còn lại theo nguồn gốc (mục 67 — không được để AI runtime bịa tên Sequence).

Gợi ý thứ tự làm tiếp (theo phụ thuộc dữ liệu, không theo số mục spec):

1. Điền đủ tên Sequence + Potion + Ability cho 21 Pathway còn lại (cần đối
   chiếu nguồn gốc cẩn thận — nhiều nguồn tiếng Anh trên mạng ghi tên
   Sequence không khớp nhau).
2. AI dialogue layer thật cho NPC (mục 29 — Gemini/Groq + Context Builder;
   NPC entity + Trust + Memory đã có ở mục 28, đây chỉ còn là lớp mô tả).
3. World/Economy — cần trước Market/Auction/Contract/Bounty (City/Location
   đã có ở mục 31-32).

---

## Cập nhật mới nhất (bản này)

**Đã hoàn thành thêm 6/8 hệ thống còn thiếu theo đánh giá trước đó:**

- **⛪ Church / 🏛️ Faction** (`faction.py`, `data/factions_seed.py`) — 7 Nhà
  Thờ Chính Thống + 5 Faction đúng canon (Nighthawks, Rose School of
  Thought, Moses Ascetic Order...), gia nhập/rời có reputation thật lưu
  DB, một Character chỉ thuộc tối đa 1 Church + 1 Faction cùng lúc.
- **🃏 Tarot Club** (`tarot.py`) — danh tính Tarot tách biệt hoàn toàn danh
  tính Character thật (chỉ lưu/hiện `tarot_seat`), 22 mật danh theo lá bài
  Tarot canon, hội nghị + tin nhắn nội bộ.
- **👥 Party** (`party.py`) — tạo/mời/rời đội 1-5 người, tự chuyển leader
  khi leader rời, atomic đảm bảo 1 Character chỉ ở 1 Party active.
- **💰 Economy / 🤝 Trade / 📜 Contract / ☠️ Bounty** (`economy.py`) — Chợ
  (rao bán/mua), Trade trực tiếp 1-đổi-1 giữa hai người chơi, Contract
  (ký quỹ thưởng khi đăng, trả khi issuer xác nhận hoàn thành), Bounty
  (treo thưởng/nhận thưởng). Toàn bộ đi qua transaction atomic thật trong
  `database.py`: CHECK → REMOVE → ADD → Log → COMMIT trong cùng một
  connection SQLite — nếu bất kỳ bước CHECK nào fail thì không đổi gì cả
  (không có trường hợp A mất hàng mà B không nhận tiền, hoặc ngược lại).
- **🏠 House** (`house.py`) — kho lưu trữ riêng tách biệt Inventory mang
  theo người, cất/lấy đồ atomic. Có Tier nhà (tối đa 5, mỗi Tier +10 ô lưu
  trữ, atomic trừ tiền) và 4 Phòng chức năng nâng cấp độc lập (tối đa cấp 5,
  chi phí tăng dần theo cấp) — mỗi phòng cho bonus cơ học THẬT ở đúng engine
  liên quan, không phải chỉ số trang trí trên Embed:
  - 🔬 Phòng Nghiên cứu → giảm % Spirituality cần cho Mysticism Knowledge
    (`mysticism.py`).
  - 🧪 Phòng Luyện dược → giảm % craft_risk khi Chế tạo Potion (`potions.py`).
  - 🕯️ Phòng Nghi thức → cộng thêm % tỉ lệ thành công Ritual (`ritual.py`).
  - 🗝️ Phòng Cổ vật → giảm % tỉ lệ Side Effect khi Experiment Sealed
    Artifact (`artifacts.py`).
  Nâng cấp phòng/Tier đều là transaction atomic thật trong `database.py`
  (CHECK tiền + cấp hiện tại → REMOVE tiền → ADD cấp → COMMIT).
- **🏆 Achievement / 📊 Ranking** (`achievements.py`) — 12 Achievement khởi
  đầu, tự động mở khoá từ các luồng gameplay có sẵn (tiến cấp Sequence,
  thắng PvE/PvP, hoàn thành Investigation, gia nhập Church/Faction/Tarot,
  giao dịch lần đầu, đủ 50k Bảng...), Ranking tính TRỰC TIẾP từ dữ liệu
  Character sống (không dùng snapshot có thể lệch).
- Tất cả đã wire thật vào `/menu` → 🏛️ Tổ chức / 💰 Giao dịch / 🏠 Đời
  sống (`cogs/menu.py`) — không còn "🚧 đang phát triển" cho 3 nhóm này.

**Lớp mới: `error_handler.py` — ẩn thông tin kỹ thuật khỏi người chơi.**
M��i callback discord.ui trong menu chính, và toàn bộ 6 hệ thống mới ở
trên, được bọc bằng `@error_handler.safe_interaction(...)`: nếu có lỗi hệ
thống bất kỳ (bug, lỗi DB, exception chưa lường trước), người chơi chỉ
thấy một thông báo trung tính kèm mã sự cố ngắn ("🌑 Linh tính truyền đến
một cảm giác bất thường... Mã tham chiếu: xxxxxxxx"), KHÔNG BAO GIỜ thấy
tên bảng/biến/class, traceback, SQL, hay chi tiết implementation. Chi tiết
kỹ thuật đầy đủ vẫn được log riêng cho dev (console + bảng
`engine_error_log`, tra theo mã sự cố). Lỗi nghiệp vụ bình thường (không
đủ tiền, không đủ hàng...) vẫn hiển thị message rõ ràng bằng tiếng Việt
như trước — đây không phải lỗi hệ thống nên không bị ẩn.

**Vẫn CHƯA làm trong bản này** (còn lại đúng như đánh giá trước, để làm
tiếp theo thứ tự phụ thuộc):

- **🏰 Dungeon / 🌑 World Event** — chưa có Engine (seed, map, room, event
  trigger tác động World State thật).
- **🤖 AI Narrative sâu** — vẫn dừng ở mức Engine quyết định → AI viết lại
  câu chữ; chưa có Narrative Engine riêng cho Investigation/World
  Event/Combat/Quest/Lore.
- 21/22 Pathway vẫn còn Sequence placeholder (như ghi chú cũ ở trên) —
  đây là việc lớn nhất còn lại, cần đối chiếu nguồn cẩn thận theo từng
  Pathway.
- Quest tuyến tính có mốc/objective (khác Contract/Bounty đã có) chưa có.


---

## Cập nhật tiếp theo (bản này) — Dungeon + World Event

**🏰 Dungeon (mục 26)** — `dungeon.py`, `data/dungeons_seed.py`:
- Procedural thật theo seed: mỗi run lưu `seed` riêng, RNG tất định
  `seed:room_index` nên cùng seed luôn tái tạo đúng chuỗi phòng (đúng yêu
  cầu "Seed được lưu để có thể truy xuất run").
- Phòng gồm Combat / Treasure / Trap / Secret, phòng cuối luôn là Boss.
- **Không tạo Combat Engine riêng** — phòng Combat/Boss tái dùng đúng
  `combat.py` hiện có; `combat_sessions` được gắn thêm `dungeon_run_id`
  (migration tự thêm cột, không mất dữ liệu cũ) để `combat._finish()` tự
  gọi ngược `dungeon.on_combat_resolved()` khi trận kết thúc.
- Thắng phòng thường → tiến phòng kế; thắng Boss → phát thưởng tổng +
  item thật vào Inventory; thua/chạy trốn → run kết thúc thất bại ngay
  (không cho "thử lại free" né phòng khó).
- 2 Dungeon khởi đầu (Sào Huyệt Khu Ổ Chuột, Phế Tích Chìm Migas) + 5
  Monster/Boss mới, seed bằng `INSERT OR IGNORE` nên không phá DB cũ.
- Đã wire vào `/menu` → ⚔️ Chiến đấu → 🏰 Dungeon.

**🌑 World Event (mục 47)** — `world_event.py`, `data/world_events_seed.py`:
- Trigger tác động THẬT lên `cities.economy/crime/mystical_activity` ngay
  khi kích hoạt (transaction atomic trong `database.py`), không phải chỉ
  gửi một Embed.
- Event tự phát sinh từ chính luồng gameplay có sẵn — khi Player Travel
  tới một City chưa có Event active (12% cơ hội) — không cần thêm
  scheduler/cron riêng vào bot.
- Player có thể chủ động **can thiệp** (`world_event.contribute`): tốn
  100 Bảng thật mỗi lần, đủ ngưỡng đóng góp thì Event tự Resolve — hoàn
  tác ĐÚNG phần delta đã áp, City trở lại nguyên trạng trước Event (đã
  test: city trở về đúng số liệu ban đầu sau khi resolve).
- 6 template Event (nổi dậy giáo phái, bùng nổ thương mại, mất tích bí
  ẩn, hành hương Nhà Thờ, chiến tranh băng đảng, hội tụ huyền bí).
- Đã wire vào `/menu` → 🗺️ Thế giới → 🌑 Sự kiện.

Cả hai hệ thống đã test chạy thật end-to-end (không chỉ compile) bằng
script mô phỏng toàn bộ luồng, và `cogs/menu.py` đã được import-test đầy
đủ để xác nhận không có lỗi wiring/circular import.

**Còn lại đúng như trước**: 21/22 Pathway vẫn còn Sequence placeholder
(việc lớn nhất còn tồn đọng), và AI Narrative sâu cho từng hệ thống riêng
(Investigation/World Event/Combat/Quest/Lore) vẫn chưa có.

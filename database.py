"""
Lớp truy cập Database — nguồn sự thật duy nhất cho toàn bộ Game Engine
(mục 1 & 48 trong spec). Dùng SQLite cho môi trường dev/test.

Mọi thay đổi state (HP, Spirituality, Sequence, ...) phải đi qua đây,
KHÔNG được để UI tự tính toán (mục 15, 51).
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import DB_PATH
from data.pathways_seed import PATHWAYS, build_sequence_rows
from data.effects_seed import EFFECT_DEFINITIONS
from data.monsters_seed import MONSTERS
from data.abilities_seed import build_ability_rows
from data.items_seed import ITEMS
from data.potion_recipes_seed import build_potion_recipe_rows
from data.ritual_materials_seed import build_ritual_material_rows
from data.artifacts_seed import ARTIFACT_EFFECT_DEFINITIONS, ARTIFACTS, ARTIFACT_RULES
from data.knowledge_seed import KNOWLEDGE_DEFINITIONS
from data.divination_seed import DIVINATION_METHODS
from data.world_seed import CITIES, LOCATIONS, DEFAULT_LOCATION_ID
from data.npc_seed import NPCS, NPC_DIALOGUE
from data.investigations_seed import INVESTIGATIONS, INVESTIGATION_CLUES
from data.factions_seed import CHURCHES, FACTIONS, FACTION_MISSIONS
from data.achievements_seed import ACHIEVEMENTS
from data.dungeons_seed import DUNGEONS
from data.quests_seed import QUESTS, QUEST_OBJECTIVES
from data.black_market_seed import BLACK_MARKET_ITEMS, BLACK_MARKET_LISTINGS

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    language TEXT NOT NULL DEFAULT 'vi'
);

CREATE TABLE IF NOT EXISTS pathways (
    pathway_id TEXT PRIMARY KEY,
    icon TEXT NOT NULL,
    name_en TEXT NOT NULL,
    name_vi TEXT NOT NULL DEFAULT '',
    title_en TEXT NOT NULL,
    title_vi TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sequences (
    pathway_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    name_en TEXT NOT NULL,
    name_vi TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (pathway_id, sequence_number),
    FOREIGN KEY (pathway_id) REFERENCES pathways(pathway_id)
);

CREATE TABLE IF NOT EXISTS characters (
    character_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 1,
    exp INTEGER NOT NULL DEFAULT 0,
    hp INTEGER NOT NULL DEFAULT 100,
    hp_max INTEGER NOT NULL DEFAULT 100,
    spirituality INTEGER NOT NULL DEFAULT 100,
    spirituality_max INTEGER NOT NULL DEFAULT 100,
    money INTEGER NOT NULL DEFAULT 0,
    location TEXT NOT NULL DEFAULT 'Backlund',
    pathway_id TEXT,
    sequence_number INTEGER NOT NULL DEFAULT 9,
    loss_of_control_risk INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (pathway_id) REFERENCES pathways(pathway_id)
);

-- Potion hướng tới từng Sequence (mục 9). name_en suy ra từ tên Sequence mục tiêu.
-- stability: độ ổn định công thức (ảnh hưởng debuff potion_instability khi uống — xem effects.py).
-- craft_risk: % khả năng Chế tạo thất bại (mất nguyên liệu, không ra Potion) — xem potions.py.
CREATE TABLE IF NOT EXISTS potions (
    pathway_id TEXT NOT NULL,
    target_sequence INTEGER NOT NULL,
    name_en TEXT NOT NULL,
    stability INTEGER NOT NULL DEFAULT 80,
    craft_risk INTEGER NOT NULL DEFAULT 15,
    PRIMARY KEY (pathway_id, target_sequence),
    FOREIGN KEY (pathway_id) REFERENCES pathways(pathway_id)
);

-- Công thức: nguyên liệu (item_id, type='ingredient' trong bảng items) + số lượng
-- cần để Chế tạo một Potion cụ thể (mục 9: Recipe/Ingredients/Ingredient quantity).
CREATE TABLE IF NOT EXISTS potion_recipes (
    pathway_id TEXT NOT NULL,
    target_sequence INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (pathway_id, target_sequence, item_id),
    FOREIGN KEY (pathway_id, target_sequence) REFERENCES potions(pathway_id, target_sequence),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

-- Potion đã Chế tạo xong và đang sở hữu, CHƯA uống (mục 9: Potion ownership/acquisition).
-- Uống Potion (progression.start_potion) phải trừ đúng 1 ở đây trước khi vào Digestion —
-- không được uống một Potion mà Character chưa từng Chế tạo.
CREATE TABLE IF NOT EXISTS character_potions (
    character_id INTEGER NOT NULL,
    pathway_id TEXT NOT NULL,
    target_sequence INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, pathway_id, target_sequence),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (pathway_id, target_sequence) REFERENCES potions(pathway_id, target_sequence)
);

-- Tiến trình Potion/Acting/Digestion hiện tại của một Character (mục 9-11).
-- status: idle | digesting | ready (đủ 100% Digestion, chờ Nghi thức)
CREATE TABLE IF NOT EXISTS character_progress (
    character_id INTEGER PRIMARY KEY,
    potion_target_sequence INTEGER,
    digestion INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'idle',
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

-- Định nghĩa tĩnh Buff/Debuff (mục 15-16) — nguồn: data/effects_seed.py
CREATE TABLE IF NOT EXISTS effect_definitions (
    effect_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    default_duration INTEGER NOT NULL DEFAULT 3,
    modifier_key TEXT NOT NULL,
    modifier_value REAL NOT NULL
);

-- Buff/Debuff đang active trên một Character. duration đếm theo "lượt hành động".
CREATE TABLE IF NOT EXISTS character_effects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    effect_id TEXT NOT NULL,
    source TEXT,
    stacks INTEGER NOT NULL DEFAULT 1,
    duration INTEGER NOT NULL,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (effect_id) REFERENCES effect_definitions(effect_id)
);

-- Log hành động — phục vụ mục 28 (NPC memory) / debug, không bắt buộc dùng ngay.
CREATE TABLE IF NOT EXISTS action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Monster tĩnh cho PvE (mục 25). drop_item_id/drop_chance: tỉ lệ rớt đồ thật khi thắng.
CREATE TABLE IF NOT EXISTS monsters (
    monster_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    hp INTEGER NOT NULL,
    attack INTEGER NOT NULL,
    reward_money INTEGER NOT NULL DEFAULT 0,
    reward_exp INTEGER NOT NULL DEFAULT 0,
    drop_item_id TEXT,
    drop_chance REAL NOT NULL DEFAULT 0
);

-- Ability cố định theo Pathway/Sequence (mục 17)
CREATE TABLE IF NOT EXISTS abilities (
    ability_id TEXT PRIMARY KEY,
    pathway_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    name_en TEXT NOT NULL,
    name_vi TEXT NOT NULL DEFAULT '',
    cost INTEGER NOT NULL,
    damage_multiplier REAL NOT NULL,
    FOREIGN KEY (pathway_id) REFERENCES pathways(pathway_id)
);

-- Trạng thái một trận PvE đang diễn ra (mục 23-25)
CREATE TABLE IF NOT EXISTS combat_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    monster_id TEXT NOT NULL,
    player_hp INTEGER NOT NULL,
    monster_hp INTEGER NOT NULL,
    turn INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

-- Item tĩnh (mục 22, 59)
CREATE TABLE IF NOT EXISTS items (
    item_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_vi TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL,
    description TEXT,
    heal_hp INTEGER NOT NULL DEFAULT 0,
    heal_spirituality INTEGER NOT NULL DEFAULT 0,
    equip_slot TEXT,
    modifier_key TEXT,
    modifier_value REAL
);

-- Túi đồ của Character (mục 59)
CREATE TABLE IF NOT EXISTS inventory (
    character_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, item_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

-- Trang bị hiện tại theo slot (mục 59)
CREATE TABLE IF NOT EXISTS character_equipment (
    character_id INTEGER NOT NULL,
    slot TEXT NOT NULL,
    item_id TEXT NOT NULL,
    PRIMARY KEY (character_id, slot),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

-- Trận PvP giữa 2 Character thật (mục 24). Turn-based LUÂN PHIÊN (không phải
-- auto-counter như PvE): chỉ character_id == turn_character_id mới được hành
-- động; sau mỗi hành động lượt chuyển sang đối thủ. status: pending (đang chờ
-- đối thủ chấp nhận) -> active -> finished_challenger / finished_opponent /
-- declined / fled_challenger / fled_opponent.
CREATE TABLE IF NOT EXISTS pvp_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    challenger_id INTEGER NOT NULL,
    opponent_id INTEGER NOT NULL,
    challenger_hp INTEGER NOT NULL DEFAULT 0,
    opponent_hp INTEGER NOT NULL DEFAULT 0,
    turn_character_id INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (challenger_id) REFERENCES characters(character_id),
    FOREIGN KEY (opponent_id) REFERENCES characters(character_id)
);

-- Ritual Materials (mục 20) — định nghĩa tĩnh, cùng pattern potion_recipes.
CREATE TABLE IF NOT EXISTS ritual_materials (
    pathway_id TEXT NOT NULL,
    target_sequence INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (pathway_id, target_sequence, item_id),
    FOREIGN KEY (pathway_id, target_sequence) REFERENCES potions(pathway_id, target_sequence),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

-- Lịch sử mỗi lần làm Nghi thức (mục 20: Result phải được lưu, không chỉ
-- hiện trên Embed rồi biến mất — dùng để về sau Investigation/NPC/Achievement
-- có thể tra cứu lại, mục 34 character_progression_history).
CREATE TABLE IF NOT EXISTS ritual_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    pathway_id TEXT NOT NULL,
    target_sequence INTEGER NOT NULL,
    outcome TEXT NOT NULL,
    roll INTEGER NOT NULL,
    success_chance INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

-- Beyonder Characteristic (mục 21). KHÔNG phải item RPG thường: gắn chết vào
-- đúng 1 (pathway_id, sequence_number) đã đạt được, có stability + state riêng,
-- và có lịch sử acquired_at/consumed_at (mục 21: Acquisition/Ownership/Storage/
-- Transfer/Consumption). UNIQUE constraint chặn duplicate cấp 2 lần cho cùng
-- một Sequence của cùng Character (mục 21: "không bị duplicate bất hợp lệ").
-- state: stored (đang giữ) | consumed (đã tiêu thụ để tăng Stability toàn thân)
CREATE TABLE IF NOT EXISTS character_characteristics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    pathway_id TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    name_en TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'advancement',
    stability INTEGER NOT NULL DEFAULT 100,
    state TEXT NOT NULL DEFAULT 'stored',
    acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    consumed_at TEXT,
    UNIQUE (character_id, pathway_id, sequence_number),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (pathway_id, sequence_number) REFERENCES sequences(pathway_id, sequence_number)
);

-- Sealed Artifact (mục 22) — định nghĩa tĩnh. effect_id/side_effect_id trỏ
-- vào effect_definitions (dùng chung EffectEngine, mục 15-16). usage_limit
-- = -1 nghĩa là không giới hạn.
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    grade TEXT NOT NULL,
    origin TEXT NOT NULL,
    sealing_method TEXT NOT NULL,
    risk_stars INTEGER NOT NULL DEFAULT 1,
    effect_id TEXT NOT NULL,
    side_effect_id TEXT,
    side_effect_chance INTEGER NOT NULL DEFAULT 0,
    usage_limit INTEGER NOT NULL DEFAULT -1,
    inspect_hint TEXT,
    FOREIGN KEY (effect_id) REFERENCES effect_definitions(effect_id),
    FOREIGN KEY (side_effect_id) REFERENCES effect_definitions(effect_id)
);

-- Nội dung tiết lộ dần khi Inspect (mục 22: Effect/Rule/Side Effect).
CREATE TABLE IF NOT EXISTS artifact_rules (
    artifact_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    text_vi TEXT NOT NULL,
    PRIMARY KEY (artifact_id, stage),
    FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id)
);

-- Ownership + tiến độ khám phá 1 Artifact cụ thể mà Character đang giữ
-- (mục 22: Unknown -> Inspect -> Experiment -> Discover Rule).
-- discovered_stages: chuỗi các stage đã biết, phân cách bởi dấu phẩy
-- (vd "effect,rule"). uses_remaining giảm dần khi Experiment, -1 = vô hạn.
CREATE TABLE IF NOT EXISTS character_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    discovered_stages TEXT NOT NULL DEFAULT '',
    uses_remaining INTEGER NOT NULL,
    acquired_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (artifact_id) REFERENCES artifacts(artifact_id)
);

-- Lịch sử Inspect/Experiment (mục 22, cùng tinh thần ritual_history).
CREATE TABLE IF NOT EXISTS artifact_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    artifact_id TEXT NOT NULL,
    action TEXT NOT NULL,
    side_effect_triggered INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Mysticism Knowledge tĩnh (mục 18). unlock_effect_id: effect vĩnh viễn khi
-- Understood, trỏ vào effect_definitions — có thể NULL (kiến thức chỉ mang
-- tính lore/tiền đề, chưa gắn cơ chế thưởng).
CREATE TABLE IF NOT EXISTS knowledge_definitions (
    knowledge_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    category TEXT NOT NULL,
    description_vi TEXT NOT NULL,
    discover_cost INTEGER NOT NULL DEFAULT 5,
    study_cost INTEGER NOT NULL DEFAULT 10,
    understand_cost INTEGER NOT NULL DEFAULT 15,
    understand_risk INTEGER NOT NULL DEFAULT 5,
    unlock_effect_id TEXT,
    FOREIGN KEY (unlock_effect_id) REFERENCES effect_definitions(effect_id)
);

-- Tiến độ Knowledge của Character. Không có row = "Unknown" (ngầm định).
-- stage: discovered | studied | understood
CREATE TABLE IF NOT EXISTS character_knowledge (
    character_id INTEGER NOT NULL,
    knowledge_id TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'discovered',
    discovered_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    studied_at TEXT,
    understood_at TEXT,
    PRIMARY KEY (character_id, knowledge_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (knowledge_id) REFERENCES knowledge_definitions(knowledge_id)
);

-- Divination Method tĩnh (mục 19).
CREATE TABLE IF NOT EXISTS divination_methods (
    method_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    spirituality_cost INTEGER NOT NULL,
    base_accuracy INTEGER NOT NULL,
    risk_stars INTEGER NOT NULL DEFAULT 1
);

-- Lịch sử mỗi lần Bói toán — kết quả do Engine roll thật, log lại để tra cứu
-- (mục 19, 30: AI không được tự quyết định tier).
CREATE TABLE IF NOT EXISTS divination_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    method_id TEXT NOT NULL,
    tier TEXT NOT NULL,
    roll INTEGER NOT NULL,
    accuracy INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- World / City / Location (mục 31-32). City là entity thật, không còn String tự do.
CREATE TABLE IF NOT EXISTS cities (
    city_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    description_vi TEXT,
    economy INTEGER NOT NULL DEFAULT 50,
    crime INTEGER NOT NULL DEFAULT 20,
    mystical_activity INTEGER NOT NULL DEFAULT 20,
    church_influence TEXT NOT NULL DEFAULT 'medium',
    travel_cost INTEGER NOT NULL DEFAULT 0
);

-- Location cụ thể bên trong một City (mục 32). Character luôn đứng ở đúng 1
-- Location — không còn chỉ có tên City chung chung.
CREATE TABLE IF NOT EXISTS locations (
    location_id TEXT PRIMARY KEY,
    city_id TEXT NOT NULL,
    name_en TEXT NOT NULL,
    description_vi TEXT,
    location_type TEXT NOT NULL DEFAULT 'district',
    mystical_activity INTEGER NOT NULL DEFAULT 10,
    FOREIGN KEY (city_id) REFERENCES cities(city_id)
);

-- Lịch sử di chuyển thật (mục 32, 49-50) — mỗi lần Di chuyển đều log, kể cả
-- phí đã trừ, để tra soát/đối chiếu về sau.
CREATE TABLE IF NOT EXISTS travel_log (
    travel_id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    from_location_id TEXT,
    to_location_id TEXT NOT NULL,
    money_cost INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (to_location_id) REFERENCES locations(location_id)
);

-- NPC (mục 28). Mỗi NPC đứng thật ở 1 Location — không phải chatbot vô tri.
CREATE TABLE IF NOT EXISTS npcs (
    npc_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    location_id TEXT NOT NULL,
    role TEXT NOT NULL,
    description_vi TEXT,
    favorite_item_id TEXT,
    FOREIGN KEY (location_id) REFERENCES locations(location_id),
    FOREIGN KEY (favorite_item_id) REFERENCES items(item_id)
);

-- Ngân hàng câu thoại tĩnh theo trust_tier (mục 28-29) — CHƯA có AI Narrative
-- layer nên câu thoại là dữ liệu tĩnh, chọn ngẫu nhiên trong đúng tier hiện tại.
CREATE TABLE IF NOT EXISTS npc_dialogue (
    npc_id TEXT NOT NULL,
    trust_tier TEXT NOT NULL,
    line_vi TEXT NOT NULL,
    FOREIGN KEY (npc_id) REFERENCES npcs(npc_id)
);

-- Trust thật giữa MỘT Character và MỘT NPC (mục 28: Relationship) — không
-- dùng chung một biến toàn cục cho mọi người chơi.
CREATE TABLE IF NOT EXISTS character_npc (
    character_id INTEGER NOT NULL,
    npc_id TEXT NOT NULL,
    trust INTEGER NOT NULL DEFAULT 0,
    interactions INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, npc_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (npc_id) REFERENCES npcs(npc_id)
);

-- NPC Memory thật (mục 28: "NPC phải nhớ hành động của người chơi") — log
-- từng lần tương tác kèm trust_delta, không phải suy luận AI runtime.
CREATE TABLE IF NOT EXISTS npc_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    npc_id TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    trust_delta INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (npc_id) REFERENCES npcs(npc_id)
);

-- Investigation (mục 27): Event -> Observe -> Clue -> Analyze -> Hypothesis ->
-- Investigate -> Resolution. investigations là dữ liệu tĩnh gắn với 1
-- Location; clue thuộc 1 investigation theo thứ tự order_index.
CREATE TABLE IF NOT EXISTS investigations (
    investigation_id TEXT PRIMARY KEY,
    location_id TEXT NOT NULL,
    name_en TEXT NOT NULL,
    description_vi TEXT NOT NULL,
    min_clue_ratio INTEGER NOT NULL DEFAULT 60,
    reward_money INTEGER NOT NULL DEFAULT 0,
    reward_exp INTEGER NOT NULL DEFAULT 0,
    reward_item_id TEXT,
    FOREIGN KEY (location_id) REFERENCES locations(location_id),
    FOREIGN KEY (reward_item_id) REFERENCES items(item_id)
);

-- find_chance: % thành công mỗi lần Quan sát (Observe) nhắm vào clue này —
-- đúng mục 27 "Người chơi có thể bỏ sót clue", không phải auto-nhặt hết.
CREATE TABLE IF NOT EXISTS investigation_clues (
    clue_id TEXT PRIMARY KEY,
    investigation_id TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    text_vi TEXT NOT NULL,
    find_chance INTEGER NOT NULL DEFAULT 70,
    is_key_clue INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (investigation_id) REFERENCES investigations(investigation_id)
);

-- Tiến trình MỘT Character trên MỘT Investigation — status: active,
-- resolved_success, resolved_failed (mục 27: Resolution có thể "hiểu sai").
CREATE TABLE IF NOT EXISTS character_investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    investigation_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    UNIQUE (character_id, investigation_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (investigation_id) REFERENCES investigations(investigation_id)
);

-- Clue nào Character này đã thật sự tìm ra — nguồn sự thật cho % tiến độ,
-- không tính lại từ số lần bấm Quan sát (mục 27: "Clue phải được lưu").
CREATE TABLE IF NOT EXISTS character_clues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    investigation_id TEXT NOT NULL,
    clue_id TEXT NOT NULL,
    found_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (character_id, clue_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (clue_id) REFERENCES investigation_clues(clue_id)
);

-- =====================================================================
-- ⛪ Church / 🏛️ Faction (mục 33-34)
-- =====================================================================

CREATE TABLE IF NOT EXISTS churches (
    church_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_vi TEXT NOT NULL,
    controls_pathway_id TEXT,
    description_vi TEXT NOT NULL,
    hq_location_hint TEXT,
    FOREIGN KEY (controls_pathway_id) REFERENCES pathways(pathway_id)
);

CREATE TABLE IF NOT EXISTS factions (
    faction_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_vi TEXT NOT NULL,
    alignment TEXT NOT NULL DEFAULT 'neutral',
    description_vi TEXT NOT NULL
);

-- Một Character chỉ thuộc TỐI ĐA một Church và một Faction (mục 4 profile:
-- "Faction: None" là trạng thái hợp lệ). reputation: -100..100, quyết định
-- cấp bậc hiển thị và có thể ảnh hưởng giá Shop/độ tin tưởng NPC cùng phe.
-- is_member=0 nghĩa là "đã rời" nhưng hàng vẫn giữ lại để Reputation (đã bị
-- LEAVE_PENALTY trừ) không mất nếu gia nhập lại đúng tổ chức này (mục 33-34).
CREATE TABLE IF NOT EXISTS character_church (
    character_id INTEGER PRIMARY KEY,
    church_id TEXT NOT NULL,
    reputation INTEGER NOT NULL DEFAULT 0,
    is_member INTEGER NOT NULL DEFAULT 1,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (church_id) REFERENCES churches(church_id)
);

CREATE TABLE IF NOT EXISTS character_faction (
    character_id INTEGER PRIMARY KEY,
    faction_id TEXT NOT NULL,
    reputation INTEGER NOT NULL DEFAULT 0,
    is_member INTEGER NOT NULL DEFAULT 1,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (faction_id) REFERENCES factions(faction_id)
);

-- Mission của Church/Faction (mục 33-34): min_reputation gate Mission bậc
-- cao thật (Rank thấp bị chặn), kill_progress chỉ tăng qua combat.py._finish
-- (chiến thắng thật), claimed_at NOT NULL chặn double-claim.
CREATE TABLE IF NOT EXISTS faction_missions (
    mission_id TEXT PRIMARY KEY,
    org_type TEXT NOT NULL,
    org_id TEXT NOT NULL,
    name_vi TEXT NOT NULL,
    monster_id TEXT NOT NULL,
    required_kills INTEGER NOT NULL,
    min_reputation INTEGER NOT NULL DEFAULT 0,
    reward_money INTEGER NOT NULL DEFAULT 0,
    reward_exp INTEGER NOT NULL DEFAULT 0,
    reward_reputation INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS character_faction_mission (
    character_id INTEGER NOT NULL,
    mission_id TEXT NOT NULL,
    kill_progress INTEGER NOT NULL DEFAULT 0,
    accepted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    claimed_at TEXT,
    PRIMARY KEY (character_id, mission_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (mission_id) REFERENCES faction_missions(mission_id)
);

-- =====================================================================
-- 🛡️ Guild (Player-created — KHÁC Church/Faction là tổ chức thế giới cố
-- định). Một Character chỉ thuộc TỐI ĐA một Guild cùng lúc. treasury là
-- tiền thật của Guild, tách khỏi characters.money của từng thành viên.
-- =====================================================================

CREATE TABLE IF NOT EXISTS guilds (
    guild_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    leader_character_id INTEGER NOT NULL,
    description_vi TEXT NOT NULL DEFAULT '',
    treasury INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (leader_character_id) REFERENCES characters(character_id)
);

CREATE TABLE IF NOT EXISTS guild_members (
    character_id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    rank TEXT NOT NULL DEFAULT 'member',
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id)
);

-- Log gửi/rút Guild Bank (mục 34 Treasury) — không phải nguồn trạng thái
-- sống (đó là guilds.treasury), chỉ để audit ai đã nộp/rút bao nhiêu.
CREATE TABLE IF NOT EXISTS guild_bank_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    amount INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (guild_id) REFERENCES guilds(guild_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

CREATE TABLE IF NOT EXISTS guild_wars (
    war_id INTEGER PRIMARY KEY AUTOINCREMENT,
    attacker_guild_id INTEGER NOT NULL,
    defender_guild_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    attacker_score INTEGER NOT NULL DEFAULT 0,
    defender_score INTEGER NOT NULL DEFAULT 0,
    win_threshold INTEGER NOT NULL DEFAULT 10,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT,
    FOREIGN KEY (attacker_guild_id) REFERENCES guilds(guild_id),
    FOREIGN KEY (defender_guild_id) REFERENCES guilds(guild_id)
);

-- =====================================================================
-- 🃏 Tarot Club (mục 35) — danh tính Tarot TÁCH BIỆT danh tính Character
-- =====================================================================

CREATE TABLE IF NOT EXISTS tarot_members (
    character_id INTEGER PRIMARY KEY,
    tarot_seat TEXT NOT NULL UNIQUE,
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

CREATE TABLE IF NOT EXISTS tarot_meetings (
    meeting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_vi TEXT NOT NULL,
    called_by_seat TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'open'
);

-- Trao đổi thông tin/tài nguyên nội bộ Tarot Club — chỉ hiện Tarot seat,
-- KHÔNG BAO GIỜ hiện tên Character thật (đúng yêu cầu tách danh tính).
CREATE TABLE IF NOT EXISTS tarot_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL,
    from_seat TEXT NOT NULL,
    content_vi TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (meeting_id) REFERENCES tarot_meetings(meeting_id)
);

-- =====================================================================
-- 👥 Party (mục 36)
-- =====================================================================

CREATE TABLE IF NOT EXISTS parties (
    party_id INTEGER PRIMARY KEY AUTOINCREMENT,
    leader_character_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'active',
    FOREIGN KEY (leader_character_id) REFERENCES characters(character_id)
);

CREATE TABLE IF NOT EXISTS party_members (
    party_id INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (party_id, character_id),
    FOREIGN KEY (party_id) REFERENCES parties(party_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

-- =====================================================================
-- 💰 Economy / 🤝 Trade / 📜 Contract / ☠️ Bounty (mục 37-41)
-- =====================================================================

-- Player rao bán item lấy Bảng — mua/bán qua transaction atomic (mục 38).
CREATE TABLE IF NOT EXISTS market_listings (
    listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_character_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price_per_unit INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_character_id) REFERENCES characters(character_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

-- Log giao dịch đã CHỐT (đúng mục 38: Log -> Commit) — dùng để audit,
-- không phải nguồn trạng thái sống (đó là inventory/characters.money).
CREATE TABLE IF NOT EXISTS trade_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    from_character_id INTEGER,
    to_character_id INTEGER,
    item_id TEXT,
    quantity INTEGER,
    money_amount INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- 🔨 Auction (mục 41) — KHÁC market_listings (giá cố định): có escrow tiền
-- đấu giá thật (trừ ngay khi ra giá, hoàn lại nếu bị trả giá cao hơn) và
-- ends_at để chốt phiên. item bị khoá khỏi Inventory ngay khi tạo phiên,
-- giống cơ chế market_listings.
-- =====================================================================

CREATE TABLE IF NOT EXISTS auctions (
    auction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_character_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    starting_price INTEGER NOT NULL,
    current_price INTEGER NOT NULL,
    highest_bidder_character_id INTEGER,
    status TEXT NOT NULL DEFAULT 'active',
    ends_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (seller_character_id) REFERENCES characters(character_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id),
    FOREIGN KEY (highest_bidder_character_id) REFERENCES characters(character_id)
);

CREATE TABLE IF NOT EXISTS auction_bids (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    auction_id INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (auction_id) REFERENCES auctions(auction_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

CREATE TABLE IF NOT EXISTS contracts (
    contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
    issuer_character_id INTEGER NOT NULL,
    accepted_character_id INTEGER,
    task_vi TEXT NOT NULL,
    reward_money INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (issuer_character_id) REFERENCES characters(character_id),
    FOREIGN KEY (accepted_character_id) REFERENCES characters(character_id)
);

CREATE TABLE IF NOT EXISTS bounties (
    bounty_id INTEGER PRIMARY KEY AUTOINCREMENT,
    issuer_character_id INTEGER,
    target_character_id INTEGER NOT NULL,
    crime_vi TEXT NOT NULL,
    reward_money INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    claimed_by_character_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    claimed_at TEXT,
    FOREIGN KEY (target_character_id) REFERENCES characters(character_id),
    FOREIGN KEY (claimed_by_character_id) REFERENCES characters(character_id)
);

-- =====================================================================
-- 🏠 House (mục 42) — kho riêng, không lẫn với Inventory mang theo người
-- =====================================================================

CREATE TABLE IF NOT EXISTS houses (
    character_id INTEGER PRIMARY KEY,
    tier INTEGER NOT NULL DEFAULT 1,
    storage_slots INTEGER NOT NULL DEFAULT 20,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

CREATE TABLE IF NOT EXISTS house_storage (
    character_id INTEGER NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, item_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

-- house_rooms (mục 42 mở rộng): 4 phòng chức năng nâng cấp độc lập, mỗi
-- phòng cho 1 bonus cơ học thật ở đúng engine liên quan (không phải chỉ số
-- trang trí) — xem house.py cho công thức bonus theo level.
CREATE TABLE IF NOT EXISTS house_rooms (
    character_id INTEGER NOT NULL,
    room_type TEXT NOT NULL,
    level INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (character_id, room_type),
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

-- =====================================================================
-- 🏆 Achievement / 📊 Ranking (mục 45-46)
-- =====================================================================

CREATE TABLE IF NOT EXISTS achievements (
    achievement_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_vi TEXT NOT NULL,
    category TEXT NOT NULL,
    description_vi TEXT NOT NULL,
    reward_money INTEGER NOT NULL DEFAULT 0,
    reward_exp INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS character_achievements (
    character_id INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    unlocked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (character_id, achievement_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (achievement_id) REFERENCES achievements(achievement_id)
);

-- =====================================================================
-- Dev-only technical error log (KHÔNG BAO GIỜ hiển thị cho người chơi —
-- xem error_handler.py). Dùng để đối chiếu incident_id hiện trên UI.
-- =====================================================================

CREATE TABLE IF NOT EXISTS engine_error_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    incident_id TEXT NOT NULL,
    source TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- 🏰 Dungeon (mục 26) — procedural theo room, seed lưu lại để truy xuất run
-- =====================================================================

CREATE TABLE IF NOT EXISTS dungeons (
    dungeon_id TEXT PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_vi TEXT NOT NULL,
    description_vi TEXT NOT NULL,
    location_id TEXT,
    room_count INTEGER NOT NULL DEFAULT 5,
    monster_pool TEXT NOT NULL,
    boss_monster_id TEXT NOT NULL,
    reward_money INTEGER NOT NULL DEFAULT 0,
    reward_exp INTEGER NOT NULL DEFAULT 0,
    reward_item_id TEXT,
    FOREIGN KEY (location_id) REFERENCES locations(location_id),
    FOREIGN KEY (boss_monster_id) REFERENCES monsters(monster_id)
);

-- seed lưu lại (mục 26: "Seed được lưu để có thể truy xuất run") — cùng
-- seed + cùng dungeon_id sẽ luôn sinh ra đúng chuỗi phòng giống hệt.
CREATE TABLE IF NOT EXISTS dungeon_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    dungeon_id TEXT NOT NULL,
    seed INTEGER NOT NULL,
    current_room INTEGER NOT NULL DEFAULT 0,
    total_rooms INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (dungeon_id) REFERENCES dungeons(dungeon_id)
);

CREATE TABLE IF NOT EXISTS dungeon_run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    room_index INTEGER NOT NULL,
    room_type TEXT NOT NULL,
    result_vi TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES dungeon_runs(run_id)
);

-- =====================================================================
-- 🌑 World Event (mục 47) — phải tác động THẬT lên World State (cities),
-- không chỉ gửi một Embed rồi biến mất.
-- =====================================================================

CREATE TABLE IF NOT EXISTS world_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key TEXT NOT NULL,
    name_vi TEXT NOT NULL,
    description_vi TEXT NOT NULL,
    city_id TEXT NOT NULL,
    stage TEXT NOT NULL DEFAULT 'active',
    economy_delta INTEGER NOT NULL DEFAULT 0,
    crime_delta INTEGER NOT NULL DEFAULT 0,
    mystical_delta INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TEXT,
    FOREIGN KEY (city_id) REFERENCES cities(city_id)
);

CREATE TABLE IF NOT EXISTS world_event_participants (
    event_id INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    contribution INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (event_id, character_id),
    FOREIGN KEY (event_id) REFERENCES world_events(event_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

-- =====================================================================
-- 🌍 World State / World History (mục 31, 47-48) — trạng thái TOÀN CỤC
-- (không gắn 1 City cụ thể, khác cities.economy/crime/mystical_activity)
-- và biên niên sử các thay đổi lớn tác động thật lên thế giới.
-- =====================================================================

CREATE TABLE IF NOT EXISTS world_state (
    state_key TEXT PRIMARY KEY,
    state_value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- category: world_event / guild_war / faction / economy / ... — ref_id để
-- trỏ lại bản ghi gốc (event_id, war_id, ...) nếu người chơi muốn tra cứu.
CREATE TABLE IF NOT EXISTS world_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    summary_vi TEXT NOT NULL,
    ref_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================================
-- 🌗 Season / 📊 Ranking mở rộng (mục 44, 46) — Ranking Level/Tiền/Sequence
-- (xem RANKING_FIELDS bên dưới) tính TRỰC TIẾP từ characters vì đó là
-- Character progression VĨNH VIỄN (mục 44: "Không reset Character
-- progression"). Nhưng PvP/Dungeon/Bounty là hoạt động LẶP LẠI theo Season,
-- không thể suy ra từ trạng thái sống — cần bộ đếm riêng, CHỈ áp dụng cho
-- Season đang active, reset tự nhiên khi trỏ sang season_id mới (dữ liệu
-- Season cũ không bị xoá, vẫn tra cứu được qua season_rankings).
-- =====================================================================

CREATE TABLE IF NOT EXISTS seasons (
    season_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_vi TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS character_season_stats (
    season_id INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    pvp_wins INTEGER NOT NULL DEFAULT 0,
    dungeon_clears INTEGER NOT NULL DEFAULT 0,
    bounty_claims INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (season_id, character_id),
    FOREIGN KEY (season_id) REFERENCES seasons(season_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id)
);

-- Chụp Top N của MỖI category tại thời điểm Season kết thúc (mục 46:
-- "Snapshot theo Season") — lưu cả character_name vì Character có thể đổi
-- tên/rời đi sau này, snapshot phải giữ đúng như thời điểm chốt mùa.
CREATE TABLE IF NOT EXISTS season_rankings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    rank INTEGER NOT NULL,
    character_id INTEGER NOT NULL,
    character_name TEXT NOT NULL,
    value INTEGER NOT NULL,
    FOREIGN KEY (season_id) REFERENCES seasons(season_id)
);

-- =====================================================================
-- 📜 Quest tuyến tính có mốc tiến độ (mục 43) — KHÁC Investigation (mục 27,
-- không tuyến tính) và KHÁC Contract/Bounty (giao dịch Player-Player).
-- =====================================================================

CREATE TABLE IF NOT EXISTS quests (
    quest_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    name_vi TEXT NOT NULL,
    name_en TEXT NOT NULL,
    description_vi TEXT NOT NULL,
    min_level INTEGER NOT NULL DEFAULT 1,
    prerequisite_quest_id TEXT,
    repeatable INTEGER NOT NULL DEFAULT 0,
    reward_money INTEGER NOT NULL DEFAULT 0,
    reward_exp INTEGER NOT NULL DEFAULT 0,
    reward_item_id TEXT,
    FOREIGN KEY (prerequisite_quest_id) REFERENCES quests(quest_id),
    FOREIGN KEY (reward_item_id) REFERENCES items(item_id)
);

CREATE TABLE IF NOT EXISTS quest_objectives (
    objective_id INTEGER PRIMARY KEY AUTOINCREMENT,
    quest_id TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    objective_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    target_count INTEGER NOT NULL DEFAULT 1,
    description_vi TEXT NOT NULL,
    FOREIGN KEY (quest_id) REFERENCES quests(quest_id)
);

-- status: LOCKED / AVAILABLE / ACTIVE / COMPLETED / FAILED / EXPIRED
-- (OBJECTIVE_PROGRESS không cần trạng thái riêng — suy ra được từ
-- character_quest_objectives khi status = ACTIVE, tránh 2 nguồn sự thật
-- lệch nhau, đúng tinh thần mục 49).
CREATE TABLE IF NOT EXISTS character_quests (
    character_id INTEGER NOT NULL,
    quest_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE',
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    PRIMARY KEY (character_id, quest_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (quest_id) REFERENCES quests(quest_id)
);

CREATE TABLE IF NOT EXISTS character_quest_objectives (
    character_id INTEGER NOT NULL,
    objective_id INTEGER NOT NULL,
    progress_count INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    PRIMARY KEY (character_id, objective_id),
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (objective_id) REFERENCES quest_objectives(objective_id)
);

-- Black Market (mục 41). Catalog tĩnh giống potions/monsters — seed bằng
-- INSERT OR IGNORE nên có thể thêm listing mới vào DB cũ mà không mất dữ liệu.
CREATE TABLE IF NOT EXISTS black_market_listings (
    listing_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    item_id TEXT,
    quantity INTEGER NOT NULL DEFAULT 1,
    price INTEGER NOT NULL,
    risk_type TEXT NOT NULL DEFAULT 'none',
    risk_chance INTEGER NOT NULL DEFAULT 0,
    description_vi TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(item_id)
);

-- Lịch sử giao dịch Chợ đen — mục 34 (progression history) áp dụng luôn cho
-- đây vì Black Market cũng là một nguồn thay đổi trạng thái Character thật.
CREATE TABLE IF NOT EXISTS black_market_purchase_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    character_id INTEGER NOT NULL,
    listing_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    money_spent INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (character_id) REFERENCES characters(character_id),
    FOREIGN KEY (listing_id) REFERENCES black_market_listings(listing_id)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _migrate_potions_table(conn):
    """DB tạo trước khi có stability/craft_risk (mục 9 mở rộng) sẽ thiếu 2 cột này
    vì CREATE TABLE IF NOT EXISTS không tự thêm cột vào bảng đã tồn tại. Thêm an
    toàn ở đây thay vì bắt người chạy dev xóa DB cũ (đúng tinh thần mục 50: không
    được làm mất dữ liệu Character đang có)."""
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(potions)").fetchall()}
    if "stability" not in existing_cols:
        conn.execute("ALTER TABLE potions ADD COLUMN stability INTEGER NOT NULL DEFAULT 80")
    if "craft_risk" not in existing_cols:
        conn.execute("ALTER TABLE potions ADD COLUMN craft_risk INTEGER NOT NULL DEFAULT 15")


def _migrate_characters_risk_factors(conn):
    """mục 13 mở rộng: Loss of Control Risk giờ được Engine tính từ nhiều yếu tố
    thật (loss_of_control.py), trong đó có Mental State — cột này chưa tồn tại
    ở DB tạo trước bản cập nhật này."""
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(characters)").fetchall()}
    if "mental_state" not in existing_cols:
        conn.execute("ALTER TABLE characters ADD COLUMN mental_state INTEGER NOT NULL DEFAULT 100")


def _migrate_characters_location(conn):
    """DB tạo trước khi có World/Location entity (mục 31-32) sẽ thiếu cột
    location_id. Thêm an toàn, mọi Character cũ được gán về Location mặc định
    (không được để Character nào "lơ lửng" không có Location thật)."""
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(characters)").fetchall()}
    if "location_id" not in existing_cols:
        # DEFAULT ngay trên cột (không chỉ backfill 1 lần) để mọi INSERT sau này
        # (kể cả create_character() không set location_id tường minh) vẫn luôn
        # có Location thật, không bao giờ NULL.
        conn.execute(
            f"ALTER TABLE characters ADD COLUMN location_id TEXT NOT NULL DEFAULT '{DEFAULT_LOCATION_ID}'"
        )


def _migrate_combat_sessions_dungeon(conn):
    """DB tạo trước khi có Dungeon Engine (mục 26) sẽ thiếu cột dungeon_run_id
    trên combat_sessions — cột này cho phép một trận PvE biết nó thuộc phòng
    nào của Dungeon nào để _finish() có thể tự động tiến phòng khi thắng."""
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(combat_sessions)").fetchall()}
    if "dungeon_run_id" not in existing_cols:
        conn.execute("ALTER TABLE combat_sessions ADD COLUMN dungeon_run_id INTEGER")


def _migrate_users_active_character(conn):
    """mục 3: User có thể sở hữu nhiều Character, độc lập hoàn toàn.
    Trước migration này, get_character() luôn trả về Character đầu tiên theo
    character_id — nếu user tạo Character thứ 2, mọi hệ thống (Combat/Party/
    House/Inventory...) vẫn chỉ thấy Character 1 mãi mãi, Character 2 "mồ côi"
    vĩnh viễn. active_character_id sửa đúng gốc: một con trỏ duy nhất, mọi nơi
    đọc qua get_character() đều đồng bộ theo con trỏ này."""
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    if "active_character_id" not in existing_cols:
        conn.execute("ALTER TABLE users ADD COLUMN active_character_id INTEGER")
        # Backfill: user đã có sẵn Character (DB cũ) -> set active = Character
        # đầu tiên của họ, giữ đúng hành vi cũ, không ai bị "mất" Character đang chơi.
        conn.execute(
            """UPDATE users SET active_character_id = (
                   SELECT character_id FROM characters
                   WHERE characters.user_id = users.user_id
                   ORDER BY character_id LIMIT 1
               )
               WHERE active_character_id IS NULL"""
        )


def _ensure_active_season(conn):
    """Đảm bảo luôn có đúng 1 Season active (mục 44) — tạo 'Mùa 1' nếu DB
    mới hoặc nếu Season trước đã kết thúc mà chưa có Season mới thay thế."""
    row = conn.execute("SELECT season_id FROM seasons WHERE status = 'active'").fetchone()
    if row is None:
        next_num = conn.execute("SELECT COUNT(*) AS c FROM seasons").fetchone()["c"] + 1
        conn.execute(
            "INSERT INTO seasons (name_vi, status) VALUES (?, 'active')",
            (f"Mùa {next_num}",),
        )


def _migrate_org_membership_is_member(conn):
    """mục 33-34 mở rộng: character_church/character_faction giờ dùng is_member
    thay vì xoá hàng khi rời, để LEAVE_PENALTY thật sự lưu lại Reputation đã
    bị trừ (không được reset về 0 miễn phí nếu gia nhập lại đúng tổ chức đó)."""
    for table in ("character_church", "character_faction"):
        existing_cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if "is_member" not in existing_cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN is_member INTEGER NOT NULL DEFAULT 1")


def _migrate_name_vi_columns(conn):
    """DB tạo trước khi có bản dịch tiếng Việt cho Pathway/Sequence/Ability/Item
    sẽ thiếu cột name_vi (title_vi riêng cho pathways). Thêm cột an toàn rồi
    backfill lại từ đúng nguồn seed (data/pathways_seed.py, data/abilities_seed.py,
    data/items_seed.py, data/black_market_seed.py) cho các hàng đã tồn tại —
    không xoá/insert lại để không đụng tới FK đang được characters/inventory
    tham chiếu."""
    for table, cols in (
        ("pathways", ["name_vi", "title_vi"]),
        ("sequences", ["name_vi"]),
        ("abilities", ["name_vi"]),
        ("items", ["name_vi"]),
        ("potions", ["name_vi"]),
        ("character_characteristics", ["name_vi"]),
    ):
        existing_cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for col in cols:
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT NOT NULL DEFAULT ''")

    # Backfill: chỉ update hàng đang có name_vi rỗng (không ghi đè nếu người
    # vận hành đã tự chỉnh tay sau migrate).
    for p in PATHWAYS:
        conn.execute(
            "UPDATE pathways SET name_vi = ?, title_vi = ? WHERE pathway_id = ? AND name_vi = ''",
            (p["name_vi"], p["title_vi"], p["id"]),
        )
    for pathway_id, seq_num, seq_name, seq_name_vi in build_sequence_rows():
        conn.execute(
            "UPDATE sequences SET name_vi = ? WHERE pathway_id = ? AND sequence_number = ? AND name_vi = ''",
            (seq_name_vi, pathway_id, seq_num),
        )
    for pathway_id, seq_num, ability_id, name_en, name_vi, cost, dmg in build_ability_rows():
        conn.execute(
            "UPDATE abilities SET name_vi = ? WHERE ability_id = ? AND name_vi = ''",
            (name_vi, ability_id),
        )
    for row in ITEMS + BLACK_MARKET_ITEMS:
        item_id, name_en, name_vi = row[0], row[1], row[2]
        conn.execute(
            "UPDATE items SET name_vi = ? WHERE item_id = ? AND name_vi = ''",
            (name_vi, item_id),
        )
    for pathway_id, seq_num, seq_name, seq_name_vi in build_sequence_rows():
        if seq_num < 9:
            conn.execute(
                "UPDATE potions SET name_vi = ? WHERE pathway_id = ? AND target_sequence = ? AND name_vi = ''",
                (f"Ma Dược {seq_name_vi}", pathway_id, seq_num),
            )
    for pathway_id, seq_num, seq_name, seq_name_vi in build_sequence_rows():
        conn.execute(
            """UPDATE character_characteristics SET name_vi = ?
               WHERE pathway_id = ? AND sequence_number = ? AND name_vi = ''""",
            (f"Đặc Tính {seq_name_vi}", pathway_id, seq_num),
        )


def init_db():
    """Tạo bảng nếu chưa có và seed dữ liệu Pathway/Sequence tĩnh."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate_potions_table(conn)
        _migrate_characters_location(conn)
        _migrate_combat_sessions_dungeon(conn)
        _migrate_characters_risk_factors(conn)
        _migrate_users_active_character(conn)
        _migrate_org_membership_is_member(conn)
        _migrate_name_vi_columns(conn)
        _ensure_active_season(conn)

        existing = conn.execute("SELECT COUNT(*) AS c FROM pathways").fetchone()["c"]
        if existing == 0:
            conn.executemany(
                "INSERT INTO pathways (pathway_id, icon, name_en, name_vi, title_en, title_vi) VALUES (?, ?, ?, ?, ?, ?)",
                [(p["id"], p["icon"], p["name_en"], p["name_vi"], p["title_en"], p["title_vi"]) for p in PATHWAYS],
            )
            conn.executemany(
                "INSERT INTO sequences (pathway_id, sequence_number, name_en, name_vi) VALUES (?, ?, ?, ?)",
                build_sequence_rows(),
            )
            # Potion tên theo Sequence mục tiêu (vd: uống "Clown Potion" để hướng tới Sequence 8 — Clown)
            potion_rows = [
                (pathway_id, seq_num, f"{seq_name} Potion", f"Ma Dược {seq_name_vi}")
                for pathway_id, seq_num, seq_name, seq_name_vi in build_sequence_rows()
                if seq_num < 9  # Sequence 9 là điểm khởi đầu, không cần Potion để "vào" nó
            ]
            conn.executemany(
                "INSERT INTO potions (pathway_id, target_sequence, name_en, name_vi) VALUES (?, ?, ?, ?)",
                potion_rows,
            )

        # INSERT OR IGNORE (không chỉ khi rỗng): cho phép thêm Effect definition mới
        # (vd Loss of Control incident debuffs) vào DB cũ đang chạy.
        conn.executemany(
            """INSERT OR IGNORE INTO effect_definitions
               (effect_id, name_en, type, description, default_duration, modifier_key, modifier_value)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            EFFECT_DEFINITIONS + ARTIFACT_EFFECT_DEFINITIONS,
        )

        # INSERT OR IGNORE (không chỉ khi rỗng): cho phép seed thêm Monster mới
        # (vd Boss Dungeon) vào DB cũ đang chạy mà không đụng tới dữ liệu sẵn có.
        conn.executemany(
            """INSERT OR IGNORE INTO monsters
               (monster_id, name_en, hp, attack, reward_money, reward_exp, drop_item_id, drop_chance)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            MONSTERS,
        )

        existing_abilities = conn.execute("SELECT COUNT(*) AS c FROM abilities").fetchone()["c"]
        if existing_abilities == 0:
            conn.executemany(
                """INSERT INTO abilities (pathway_id, sequence_number, ability_id, name_en, name_vi, cost, damage_multiplier)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                build_ability_rows(),
            )

        existing_items = conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"]
        if existing_items == 0:
            conn.executemany(
                """INSERT INTO items
                   (item_id, name_en, name_vi, type, description, heal_hp, heal_spirituality,
                    equip_slot, modifier_key, modifier_value)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ITEMS,
            )

        # Black Market items (mục 41) — INSERT OR IGNORE để có thể thêm hàng mới
        # vào DB đang chạy mà không đụng tới item đã tồn tại.
        conn.executemany(
            """INSERT OR IGNORE INTO items
               (item_id, name_en, name_vi, type, description, heal_hp, heal_spirituality,
                equip_slot, modifier_key, modifier_value)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            BLACK_MARKET_ITEMS,
        )
        conn.executemany(
            """INSERT OR IGNORE INTO black_market_listings
               (listing_id, category, item_id, quantity, price, risk_type, risk_chance, description_vi)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            BLACK_MARKET_LISTINGS,
        )

        # Phải chạy SAU khi items đã seed (FK potion_recipes.item_id -> items.item_id)
        existing_recipes = conn.execute("SELECT COUNT(*) AS c FROM potion_recipes").fetchone()["c"]
        if existing_recipes == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO potion_recipes (pathway_id, target_sequence, item_id, quantity) "
                "VALUES (?, ?, ?, ?)",
                build_potion_recipe_rows(),
            )

        # Phải chạy SAU khi items đã seed (FK ritual_materials.item_id -> items.item_id)
        existing_ritual_materials = conn.execute(
            "SELECT COUNT(*) AS c FROM ritual_materials"
        ).fetchone()["c"]
        if existing_ritual_materials == 0:
            conn.executemany(
                "INSERT OR IGNORE INTO ritual_materials (pathway_id, target_sequence, item_id, quantity) "
                "VALUES (?, ?, ?, ?)",
                build_ritual_material_rows(),
            )

        # Phải chạy SAU khi effect_definitions đã seed (FK artifacts.effect_id/side_effect_id)
        existing_artifacts = conn.execute("SELECT COUNT(*) AS c FROM artifacts").fetchone()["c"]
        if existing_artifacts == 0:
            conn.executemany(
                """INSERT INTO artifacts
                   (artifact_id, name_en, grade, origin, sealing_method, risk_stars,
                    effect_id, side_effect_id, side_effect_chance, usage_limit, inspect_hint)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ARTIFACTS,
            )
            conn.executemany(
                "INSERT INTO artifact_rules (artifact_id, stage, text_vi) VALUES (?, ?, ?)",
                ARTIFACT_RULES,
            )

        # Phải chạy SAU khi effect_definitions đã seed (FK unlock_effect_id)
        existing_knowledge = conn.execute("SELECT COUNT(*) AS c FROM knowledge_definitions").fetchone()["c"]
        if existing_knowledge == 0:
            conn.executemany(
                """INSERT INTO knowledge_definitions
                   (knowledge_id, name_en, category, description_vi, discover_cost,
                    study_cost, understand_cost, understand_risk, unlock_effect_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                KNOWLEDGE_DEFINITIONS,
            )

        existing_divination = conn.execute("SELECT COUNT(*) AS c FROM divination_methods").fetchone()["c"]
        if existing_divination == 0:
            conn.executemany(
                """INSERT INTO divination_methods
                   (method_id, name_en, spirituality_cost, base_accuracy, risk_stars)
                   VALUES (?, ?, ?, ?, ?)""",
                DIVINATION_METHODS,
            )

        existing_cities = conn.execute("SELECT COUNT(*) AS c FROM cities").fetchone()["c"]
        if existing_cities == 0:
            conn.executemany(
                """INSERT INTO cities
                   (city_id, name_en, description_vi, economy, crime,
                    mystical_activity, church_influence, travel_cost)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                CITIES,
            )
            # Phải chạy SAU khi cities đã seed (FK locations.city_id -> cities.city_id)
            conn.executemany(
                """INSERT INTO locations
                   (location_id, city_id, name_en, description_vi, location_type, mystical_activity)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                LOCATIONS,
            )

        # Phải chạy SAU khi locations + items đã seed (FK location_id / favorite_item_id)
        existing_npcs = conn.execute("SELECT COUNT(*) AS c FROM npcs").fetchone()["c"]
        if existing_npcs == 0:
            conn.executemany(
                """INSERT INTO npcs
                   (npc_id, name_en, location_id, role, description_vi, favorite_item_id)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                NPCS,
            )
            conn.executemany(
                "INSERT INTO npc_dialogue (npc_id, trust_tier, line_vi) VALUES (?, ?, ?)",
                NPC_DIALOGUE,
            )

        # Phải chạy SAU khi locations + items đã seed (FK location_id / reward_item_id)
        existing_investigations = conn.execute(
            "SELECT COUNT(*) AS c FROM investigations"
        ).fetchone()["c"]
        if existing_investigations == 0:
            conn.executemany(
                """INSERT INTO investigations
                   (investigation_id, location_id, name_en, description_vi,
                    min_clue_ratio, reward_money, reward_exp, reward_item_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                INVESTIGATIONS,
            )
            conn.executemany(
                """INSERT INTO investigation_clues
                   (clue_id, investigation_id, order_index, text_vi, find_chance, is_key_clue)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                INVESTIGATION_CLUES,
            )

        # Phải chạy SAU khi pathways đã seed (FK churches.controls_pathway_id)
        existing_churches = conn.execute("SELECT COUNT(*) AS c FROM churches").fetchone()["c"]
        if existing_churches == 0:
            conn.executemany(
                """INSERT INTO churches
                   (church_id, name_en, name_vi, controls_pathway_id, description_vi, hq_location_hint)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                CHURCHES,
            )

        existing_factions = conn.execute("SELECT COUNT(*) AS c FROM factions").fetchone()["c"]
        if existing_factions == 0:
            conn.executemany(
                "INSERT INTO factions (faction_id, name_en, name_vi, alignment, description_vi) "
                "VALUES (?, ?, ?, ?, ?)",
                FACTIONS,
            )

        existing_faction_missions = conn.execute(
            "SELECT COUNT(*) AS c FROM faction_missions"
        ).fetchone()["c"]
        if existing_faction_missions == 0:
            conn.executemany(
                """INSERT INTO faction_missions
                   (mission_id, org_type, org_id, name_vi, monster_id, required_kills,
                    min_reputation, reward_money, reward_exp, reward_reputation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                FACTION_MISSIONS,
            )

        existing_achievements = conn.execute("SELECT COUNT(*) AS c FROM achievements").fetchone()["c"]
        if existing_achievements == 0:
            conn.executemany(
                """INSERT INTO achievements
                   (achievement_id, name_en, name_vi, category, description_vi, reward_money, reward_exp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ACHIEVEMENTS,
            )

        conn.executemany(
            """INSERT OR IGNORE INTO dungeons
               (dungeon_id, name_en, name_vi, description_vi, location_id, room_count,
                monster_pool, boss_monster_id, reward_money, reward_exp, reward_item_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            DUNGEONS,
        )

        existing_quests = conn.execute("SELECT COUNT(*) AS c FROM quests").fetchone()["c"]
        if existing_quests == 0:
            conn.executemany(
                """INSERT INTO quests
                   (quest_id, category, name_vi, name_en, description_vi, min_level,
                    prerequisite_quest_id, repeatable, reward_money, reward_exp, reward_item_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                QUESTS,
            )
            conn.executemany(
                """INSERT INTO quest_objectives
                   (quest_id, order_index, objective_type, target_id, target_count, description_vi)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                QUEST_OBJECTIVES,
            )

        # World State (mục 31/47-48): key-value toàn cục, chỉ seed nếu chưa có
        # để không ghi đè giá trị đã thay đổi bởi gameplay thật.
        existing_world_state = conn.execute("SELECT COUNT(*) AS c FROM world_state").fetchone()["c"]
        if existing_world_state == 0:
            conn.executemany(
                "INSERT INTO world_state (state_key, state_value) VALUES (?, ?)",
                [("global_stability", "70"), ("active_guild_wars", "0")],
            )


# ---------- Users ----------

def get_or_create_user(user_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return dict(row)


def set_user_language(user_id: str, language: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET language = ? WHERE user_id = ?", (language, user_id))


# ---------- Characters ----------

def get_character(user_id: str):
    """Trả về Character đang active của user, theo con trỏ active_character_id
    trên bảng users (mục 3 — nhiều Character/user, nhưng đúng một Character
    active tại một thời điểm). Mọi hệ thống khác (Combat/Party/House/
    Inventory...) đều gọi hàm này -> đổi active_character_id là đổi Character
    xuyên suốt toàn hệ thống, không có nơi nào lệch pha."""
    with get_conn() as conn:
        user = conn.execute(
            "SELECT active_character_id FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if user is None or user["active_character_id"] is None:
            return None
        row = conn.execute(
            "SELECT * FROM characters WHERE character_id = ? AND user_id = ?",
            (user["active_character_id"], user_id),
        ).fetchone()
        return dict(row) if row else None


def list_characters(user_id: str):
    """Toàn bộ Character của user (mục 3), kèm cờ is_active để UI tô sáng
    Character đang chơi mà không cần truy vấn thêm."""
    with get_conn() as conn:
        active_row = conn.execute(
            "SELECT active_character_id FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        active_id = active_row["active_character_id"] if active_row else None
        rows = conn.execute(
            "SELECT * FROM characters WHERE user_id = ? ORDER BY character_id", (user_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["is_active"] = (d["character_id"] == active_id)
            result.append(d)
        return result


def switch_active_character(user_id: str, character_id: int) -> bool:
    """Đổi Character active. Atomic + validate quyền sở hữu ngay trong
    transaction (không cho user A active Character của user B)."""
    with get_conn() as conn:
        owned = conn.execute(
            "SELECT 1 FROM characters WHERE character_id = ? AND user_id = ?",
            (character_id, user_id),
        ).fetchone()
        if owned is None:
            return False
        conn.execute(
            "UPDATE users SET active_character_id = ? WHERE user_id = ?",
            (character_id, user_id),
        )
        return True


def create_character(user_id: str, name: str):
    get_or_create_user(user_id)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO characters (user_id, name, pathway_id, sequence_number)
               VALUES (?, ?, NULL, 9)""",
            (user_id, name),
        )
        new_id = cur.lastrowid
        # Character mới tạo trở thành active ngay (hành vi trực quan nhất cho
        # người chơi vừa bấm "Tạo nhân vật") — đồng bộ tại nguồn, không phải
        # suy luận ở tầng UI.
        conn.execute(
            "UPDATE users SET active_character_id = ? WHERE user_id = ?", (new_id, user_id)
        )
    character = get_character(user_id)
    # Bộ khởi đầu tối thiểu — dữ liệu thật trong inventory, không phải hiển thị giả
    add_inventory_item(character["character_id"], "healing_draught", 1)
    # mục 22: mỗi Character bắt đầu với 1 Sealed Artifact chưa rõ tác dụng —
    # phải Inspect/Experiment thật để dần khám phá, không hiển thị số liệu sẵn.
    grant_artifact(character["character_id"], "unlabeled_glass_vial")
    return character


def get_character_by_id(character_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM characters WHERE character_id = ?", (character_id,)).fetchone()
        return dict(row) if row else None


def set_character_pathway(character_id: int, pathway_id: str, sequence_number: int = 9):
    """Gán Pathway ban đầu. Việc TĂNG Sequence sau này phải đi qua Advancement Engine
    (mục 12), không được set trực tiếp qua đây trong gameplay thật."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE characters SET pathway_id = ?, sequence_number = ? WHERE character_id = ?",
            (pathway_id, sequence_number, character_id),
        )


# ---------- Pathways / Sequences ----------

def list_pathways():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM pathways ORDER BY name_en").fetchall()
        return [dict(r) for r in rows]


def get_pathway(pathway_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM pathways WHERE pathway_id = ?", (pathway_id,)).fetchone()
        return dict(row) if row else None


def list_sequences(pathway_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM sequences WHERE pathway_id = ? ORDER BY sequence_number DESC",
            (pathway_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_sequence(pathway_id: str, sequence_number: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM sequences WHERE pathway_id = ? AND sequence_number = ?",
            (pathway_id, sequence_number),
        ).fetchone()
        return dict(row) if row else None


def get_potion(pathway_id: str, target_sequence: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM potions WHERE pathway_id = ? AND target_sequence = ?",
            (pathway_id, target_sequence),
        ).fetchone()
        return dict(row) if row else None


def get_potion_recipe(pathway_id: str, target_sequence: int):
    """Trả về list dict {item_id, name_en, quantity} — nguyên liệu cần Chế tạo."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.item_id, r.quantity, it.name_en, it.name_vi
               FROM potion_recipes r JOIN items it ON it.item_id = r.item_id
               WHERE r.pathway_id = ? AND r.target_sequence = ?
               ORDER BY it.name_en""",
            (pathway_id, target_sequence),
        ).fetchall()
        return [dict(r) for r in rows]


def get_potion_stock(character_id: int, pathway_id: str, target_sequence: int) -> int:
    with get_conn() as conn:
        row = conn.execute(
            """SELECT quantity FROM character_potions
               WHERE character_id = ? AND pathway_id = ? AND target_sequence = ?""",
            (character_id, pathway_id, target_sequence),
        ).fetchone()
        return row["quantity"] if row else 0


def add_potion_stock(character_id: int, pathway_id: str, target_sequence: int, quantity: int = 1):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO character_potions (character_id, pathway_id, target_sequence, quantity)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(character_id, pathway_id, target_sequence)
               DO UPDATE SET quantity = quantity + excluded.quantity""",
            (character_id, pathway_id, target_sequence, quantity),
        )


def consume_potion_stock(character_id: int, pathway_id: str, target_sequence: int) -> bool:
    """Trừ đúng 1 Potion khỏi kho đã Chế tạo. False nếu không có sẵn (chưa Craft)."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT quantity FROM character_potions
               WHERE character_id = ? AND pathway_id = ? AND target_sequence = ?""",
            (character_id, pathway_id, target_sequence),
        ).fetchone()
        if row is None or row["quantity"] < 1:
            return False
        conn.execute(
            """UPDATE character_potions SET quantity = quantity - 1
               WHERE character_id = ? AND pathway_id = ? AND target_sequence = ?""",
            (character_id, pathway_id, target_sequence),
        )
        return True


def craft_potion_transaction(character_id: int, pathway_id: str, target_sequence: int,
                              recipe: list, success: bool):
    """Atomic (mục 38/50): trừ TOÀN BỘ nguyên liệu trước (dù thành công hay thất bại —
    Chế tạo hỏng vẫn tốn nguyên liệu, đúng mục 9 'Potion failure'), rồi chỉ cộng kho
    Potion nếu success=True. Nếu bất kỳ nguyên liệu nào không đủ, KHÔNG trừ gì cả và
    trả về False (validate trước, không rollback giữa chừng)."""
    with get_conn() as conn:
        for ing in recipe:
            row = conn.execute(
                "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
                (character_id, ing["item_id"]),
            ).fetchone()
            have = row["quantity"] if row else 0
            if have < ing["quantity"]:
                return False
        for ing in recipe:
            conn.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE character_id = ? AND item_id = ?",
                (ing["quantity"], character_id, ing["item_id"]),
            )
        if success:
            conn.execute(
                """INSERT INTO character_potions (character_id, pathway_id, target_sequence, quantity)
                   VALUES (?, ?, ?, 1)
                   ON CONFLICT(character_id, pathway_id, target_sequence)
                   DO UPDATE SET quantity = quantity + 1""",
                (character_id, pathway_id, target_sequence),
            )
        return True


def advance_character_sequence(character_id: int, new_sequence: int):
    """Chỉ được gọi từ progression.perform_advancement() sau khi đã validate
    đủ điều kiện (Digestion 100% + Ritual). KHÔNG gọi trực tiếp từ UI."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE characters SET sequence_number = ? WHERE character_id = ?",
            (new_sequence, character_id),
        )


# ---------- Ritual Materials / History (mục 20) ----------

def get_ritual_materials(pathway_id: str, target_sequence: int):
    """Trả về list dict {item_id, name_en, quantity} — vật liệu cần cho Ritual."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.item_id, r.quantity, it.name_en, it.name_vi
               FROM ritual_materials r JOIN items it ON it.item_id = r.item_id
               WHERE r.pathway_id = ? AND r.target_sequence = ?
               ORDER BY it.name_en""",
            (pathway_id, target_sequence),
        ).fetchall()
        return [dict(r) for r in rows]


def consume_ritual_materials_transaction(character_id: int, materials: list) -> bool:
    """Atomic (mục 38/50): validate ĐỦ tất cả vật liệu trước, chỉ trừ nếu đủ
    hết — không trừ nửa chừng. Trả về False nếu thiếu bất kỳ vật liệu nào
    (không trừ gì cả). Vật liệu bị tiêu thụ dù Nghi thức thành công hay
    thất bại (mục 20: Ritual có Risk thật)."""
    with get_conn() as conn:
        for m in materials:
            row = conn.execute(
                "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
                (character_id, m["item_id"]),
            ).fetchone()
            have = row["quantity"] if row else 0
            if have < m["quantity"]:
                return False
        for m in materials:
            conn.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE character_id = ? AND item_id = ?",
                (m["quantity"], character_id, m["item_id"]),
            )
        return True


def log_ritual(character_id: int, pathway_id: str, target_sequence: int,
                outcome: str, roll: int, success_chance: int):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO ritual_history
               (character_id, pathway_id, target_sequence, outcome, roll, success_chance)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (character_id, pathway_id, target_sequence, outcome, roll, success_chance),
        )


def list_ritual_history(character_id: int, limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM ritual_history WHERE character_id = ?
               ORDER BY id DESC LIMIT ?""",
            (character_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Beyonder Characteristics (mục 21) ----------

def add_character_characteristic(character_id: int, pathway_id: str, sequence_number: int,
                                  name_en: str, source: str, stability: int = 100,
                                  name_vi: str = ""):
    """Cấp 1 Characteristic gắn với (pathway_id, sequence_number) vừa đạt được.
    INSERT OR IGNORE nhờ UNIQUE constraint — nếu Character đã có Characteristic
    này rồi (vd gọi lại do lỗi mạng) thì không tạo bản duplicate. Trả về True
    nếu vừa tạo mới, False nếu đã tồn tại từ trước."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO character_characteristics
               (character_id, pathway_id, sequence_number, name_en, name_vi, source, stability)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (character_id, pathway_id, sequence_number, name_en, name_vi, source, stability),
        )
        return cur.rowcount > 0


def list_character_characteristics(character_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM character_characteristics
               WHERE character_id = ? ORDER BY sequence_number ASC, acquired_at ASC""",
            (character_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_character_characteristic(characteristic_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM character_characteristics WHERE id = ?", (characteristic_id,)
        ).fetchone()
        return dict(row) if row else None


def consume_character_characteristic(characteristic_id: int, character_id: int) -> bool:
    """Tiêu thụ 1 Characteristic đang 'stored' (mục 21: Consumption). Chỉ cho
    tiêu thụ nếu đúng chủ sở hữu và chưa consumed trước đó — trả về False nếu
    không hợp lệ (đã tiêu thụ / không tồn tại / sai chủ)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT state FROM character_characteristics WHERE id = ? AND character_id = ?",
            (characteristic_id, character_id),
        ).fetchone()
        if row is None or row["state"] != "stored":
            return False
        conn.execute(
            """UPDATE character_characteristics
               SET state = 'consumed', consumed_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (characteristic_id,),
        )
        return True


# ---------- Potion / Acting / Digestion progress (mục 9-11) ----------

def get_progress(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM character_progress WHERE character_id = ?", (character_id,)
        ).fetchone()
        if row is None:
            return {
                "character_id": character_id,
                "potion_target_sequence": None,
                "digestion": 0,
                "status": "idle",
            }
        return dict(row)


def upsert_progress(character_id: int, potion_target_sequence, digestion: int, status: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO character_progress (character_id, potion_target_sequence, digestion, status)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(character_id) DO UPDATE SET
                   potion_target_sequence = excluded.potion_target_sequence,
                   digestion = excluded.digestion,
                   status = excluded.status""",
            (character_id, potion_target_sequence, digestion, status),
        )


# ---------- Effects — EffectEngine (mục 15-16) ----------

def get_effect_definition(effect_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM effect_definitions WHERE effect_id = ?", (effect_id,)
        ).fetchone()
        return dict(row) if row else None


def add_character_effect(character_id: int, effect_id: str, source: str, duration: int, stacks: int = 1):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO character_effects (character_id, effect_id, source, stacks, duration)
               VALUES (?, ?, ?, ?, ?)""",
            (character_id, effect_id, source, stacks, duration),
        )


def list_character_effects(character_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT ce.*, ed.name_en, ed.type, ed.description, ed.modifier_key, ed.modifier_value
               FROM character_effects ce
               JOIN effect_definitions ed ON ed.effect_id = ce.effect_id
               WHERE ce.character_id = ? AND ce.duration > 0
               ORDER BY ce.applied_at DESC""",
            (character_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def tick_character_effects(character_id: int):
    """Giảm duration mỗi hiệu ứng đi 1 lượt, xóa hiệu ứng đã hết hạn."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE character_effects SET duration = duration - 1 WHERE character_id = ?",
            (character_id,),
        )
        conn.execute(
            "DELETE FROM character_effects WHERE character_id = ? AND duration <= 0",
            (character_id,),
        )


def clear_character_effects(character_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM character_effects WHERE character_id = ?", (character_id,))


# ---------- Log (mục 28 — nền tảng cho NPC memory sau này) ----------

def log_action(character_id: int, action: str, detail: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO action_log (character_id, action, detail) VALUES (?, ?, ?)",
            (character_id, action, detail),
        )


def list_action_log(character_id: int, limit: int = 15):
    """Trả về các dòng action_log gần nhất cho Character, mới nhất trước —
    dùng cho màn 'Lịch sử' trong submenu Nhân vật (mục 64), lấy thẳng từ log
    ghi bởi các luồng gameplay (mục 28) chứ không phải dữ liệu giả."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT action, detail, created_at FROM action_log
               WHERE character_id = ? ORDER BY id DESC LIMIT ?""",
            (character_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Monsters (mục 25) ----------

def list_monsters():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM monsters ORDER BY hp").fetchall()
        return [dict(r) for r in rows]


def get_monster(monster_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM monsters WHERE monster_id = ?", (monster_id,)).fetchone()
        return dict(row) if row else None


# ---------- Abilities (mục 17) ----------

def list_unlocked_abilities(pathway_id: str, current_sequence: int):
    """Ability có sequence_number >= current_sequence là Ability đã mở khóa
    (Sequence càng thấp càng mạnh, nên đạt Sequence N mở luôn Ability của
    N và mọi Sequence cao hơn N mà nhân vật đã đi qua)."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM abilities
               WHERE pathway_id = ? AND sequence_number >= ?
               ORDER BY sequence_number ASC""",
            (pathway_id, current_sequence),
        ).fetchall()
        return [dict(r) for r in rows]


def get_ability(ability_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM abilities WHERE ability_id = ?", (ability_id,)).fetchone()
        return dict(row) if row else None


# ---------- Combat sessions (mục 23-27) ----------

def get_active_combat_session(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM combat_sessions WHERE character_id = ? AND status = 'active' "
            "ORDER BY session_id DESC LIMIT 1",
            (character_id,),
        ).fetchone()
        return dict(row) if row else None


def create_combat_session(character_id: int, monster_id: str, player_hp: int, monster_hp: int):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO combat_sessions (character_id, monster_id, player_hp, monster_hp)
               VALUES (?, ?, ?, ?)""",
            (character_id, monster_id, player_hp, monster_hp),
        )
        session_id = cur.lastrowid
        row = conn.execute("SELECT * FROM combat_sessions WHERE session_id = ?", (session_id,)).fetchone()
        return dict(row)


def update_combat_session(session_id: int, player_hp: int, monster_hp: int, turn: int, status: str):
    with get_conn() as conn:
        conn.execute(
            """UPDATE combat_sessions
               SET player_hp = ?, monster_hp = ?, turn = ?, status = ?
               WHERE session_id = ?""",
            (player_hp, monster_hp, turn, status, session_id),
        )


def apply_combat_result(character_id: int, final_hp: int, money_delta: int, exp_delta: int):
    """Đồng bộ kết quả trận đấu vào Character trong MỘT transaction
    (mục 49-50) — HP/Tiền/EXP luôn khớp nhau, không update rời rạc."""
    with get_conn() as conn:
        conn.execute(
            """UPDATE characters
               SET hp = ?, money = MAX(0, money + ?), exp = exp + ?
               WHERE character_id = ?""",
            (final_hp, money_delta, exp_delta, character_id),
        )


# Tỉ lệ chia sẻ EXP/Tiền cho thành viên Party không trực tiếp đánh (mục 36 —
# Shared Combat / Loot Rules). Người trực tiếp chiến đấu luôn nhận 100% qua
# apply_combat_result(); phần này chỉ cộng thêm cho đồng đội cùng địa điểm.
PARTY_SHARE_RATIO = 0.3


def apply_party_combat_share(fighter_character_id: int, money_delta: int, exp_delta: int):
    """Nếu fighter đang ở Party active, chia % thưởng cho các thành viên khác
    đang CÙNG location và còn sống (hp > 0). Atomic — một connection, một
    transaction, ROLLBACK tự động nếu có lỗi giữa chừng (mục 50).
    Trả về list các character_id đã nhận chia sẻ (rỗng nếu không có Party)."""
    if money_delta <= 0 and exp_delta <= 0:
        return []
    shared_money = round(money_delta * PARTY_SHARE_RATIO)
    shared_exp = round(exp_delta * PARTY_SHARE_RATIO)
    if shared_money <= 0 and shared_exp <= 0:
        return []

    with get_conn() as conn:
        party = conn.execute(
            """SELECT p.party_id FROM parties p
               JOIN party_members pm ON pm.party_id = p.party_id
               WHERE pm.character_id = ? AND p.status = 'active'""",
            (fighter_character_id,),
        ).fetchone()
        if party is None:
            return []

        fighter_loc = conn.execute(
            "SELECT location FROM characters WHERE character_id = ?",
            (fighter_character_id,),
        ).fetchone()["location"]

        members = conn.execute(
            """SELECT c.character_id FROM party_members pm
               JOIN characters c ON c.character_id = pm.character_id
               WHERE pm.party_id = ? AND pm.character_id != ?
                 AND c.location = ? AND c.hp > 0""",
            (party["party_id"], fighter_character_id, fighter_loc),
        ).fetchall()

        rewarded = []
        for row in members:
            cid = row["character_id"]
            conn.execute(
                """UPDATE characters SET money = MAX(0, money + ?), exp = exp + ?
                   WHERE character_id = ?""",
                (shared_money, shared_exp, cid),
            )
            rewarded.append(cid)
        return rewarded


# ---------- PvP sessions (mục 24) ----------

def get_active_pvp_session(character_id: int):
    """Trận PvP đang active mà character_id là challenger HOẶC opponent."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pvp_sessions WHERE (challenger_id = ? OR opponent_id = ?) "
            "AND status = 'active' ORDER BY session_id DESC LIMIT 1",
            (character_id, character_id),
        ).fetchone()
        return dict(row) if row else None


def get_incoming_challenge(character_id: int):
    """Thách đấu đang chờ mà character_id là người BỊ thách (opponent)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pvp_sessions WHERE opponent_id = ? AND status = 'pending' "
            "ORDER BY session_id DESC LIMIT 1",
            (character_id,),
        ).fetchone()
        return dict(row) if row else None


def get_outgoing_challenge(character_id: int):
    """Thách đấu chính character_id vừa gửi đi, còn đang chờ."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pvp_sessions WHERE challenger_id = ? AND status = 'pending' "
            "ORDER BY session_id DESC LIMIT 1",
            (character_id,),
        ).fetchone()
        return dict(row) if row else None


def create_pvp_challenge(challenger_id: int, opponent_id: int):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO pvp_sessions (challenger_id, opponent_id, status) VALUES (?, ?, 'pending')",
            (challenger_id, opponent_id),
        )
        session_id = cur.lastrowid
        row = conn.execute("SELECT * FROM pvp_sessions WHERE session_id = ?", (session_id,)).fetchone()
        return dict(row)


def get_pvp_session(session_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM pvp_sessions WHERE session_id = ?", (session_id,)).fetchone()
        return dict(row) if row else None


def activate_pvp_session(session_id: int, challenger_hp: int, opponent_hp: int, turn_character_id: int):
    """Chấp nhận thách đấu: chốt HP hiện tại của cả hai bên làm điểm bắt đầu
    trận (không phải hồi đầy) và ai đi trước (mục 1 — Engine quyết định)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE pvp_sessions SET status = 'active', challenger_hp = ?, opponent_hp = ?, "
            "turn_character_id = ? WHERE session_id = ?",
            (challenger_hp, opponent_hp, turn_character_id, session_id),
        )


def set_pvp_status(session_id: int, status: str):
    with get_conn() as conn:
        conn.execute("UPDATE pvp_sessions SET status = ? WHERE session_id = ?", (status, session_id))


def update_pvp_session(session_id: int, challenger_hp: int, opponent_hp: int, turn_character_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE pvp_sessions SET challenger_hp = ?, opponent_hp = ?, turn_character_id = ?, status = ? "
            "WHERE session_id = ?",
            (challenger_hp, opponent_hp, turn_character_id, status, session_id),
        )


def apply_pvp_result(winner_character_id: int, loser_character_id: int, loser_final_hp: int, money_transfer: int):
    """Đồng bộ kết quả PvP trong MỘT transaction (mục 49-50): người thua về
    loser_final_hp (mục 13 — hậu quả "nặng", không chết hẳn, giống PvE), và
    tiền cược chuyển THẬT từ người thua sang người thắng — không chỉ hiện số
    trên embed."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE characters SET hp = ?, money = MAX(0, money - ?) WHERE character_id = ?",
            (loser_final_hp, money_transfer, loser_character_id),
        )
        conn.execute(
            "UPDATE characters SET money = money + ? WHERE character_id = ?",
            (money_transfer, winner_character_id),
        )


# ---------- Items / Inventory / Equipment (mục 22, 59) ----------

def list_items():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM items ORDER BY type, name_en").fetchall()
        return [dict(r) for r in rows]


def get_item(item_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM items WHERE item_id = ?", (item_id,)).fetchone()
        return dict(row) if row else None


def list_inventory(character_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT inv.item_id, inv.quantity, it.name_en, it.name_vi, it.type, it.description,
                      it.equip_slot, it.modifier_key, it.modifier_value,
                      it.heal_hp, it.heal_spirituality
               FROM inventory inv
               JOIN items it ON it.item_id = inv.item_id
               WHERE inv.character_id = ? AND inv.quantity > 0
               ORDER BY it.type, it.name_en""",
            (character_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_inventory_quantity(character_id: int, item_id: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
            (character_id, item_id),
        ).fetchone()
        return row["quantity"] if row else 0


def add_inventory_item(character_id: int, item_id: str, quantity: int = 1):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (character_id, item_id, quantity),
        )


def remove_inventory_item(character_id: int, item_id: str, quantity: int = 1):
    """Trừ số lượng, không cho âm. Trả về False nếu không đủ số lượng (không trừ)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
            (character_id, item_id),
        ).fetchone()
        current = row["quantity"] if row else 0
        if current < quantity:
            return False
        conn.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE character_id = ? AND item_id = ?",
            (quantity, character_id, item_id),
        )
        return True


def get_equipment(character_id: int):
    """Trả về dict slot -> item_id, vd {'weapon': 'rusty_dagger'}."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT slot, item_id FROM character_equipment WHERE character_id = ?",
            (character_id,),
        ).fetchall()
        return {r["slot"]: r["item_id"] for r in rows}


def set_equipment(character_id: int, slot: str, item_id: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO character_equipment (character_id, slot, item_id) VALUES (?, ?, ?)
               ON CONFLICT(character_id, slot) DO UPDATE SET item_id = excluded.item_id""",
            (character_id, slot, item_id),
        )


def clear_equipment_slot(character_id: int, slot: str):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM character_equipment WHERE character_id = ? AND slot = ?",
            (character_id, slot),
        )


def remove_character_effects_by_source(character_id: int, source: str):
    """Gỡ đúng effect được áp bởi một source cụ thể — dùng khi unequip
    (mục 16), không đụng tới các buff/debuff khác đang active."""
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM character_effects WHERE character_id = ? AND source = ?",
            (character_id, source),
        )


def set_character_spirituality_max(character_id: int, spirituality_max: int, spirituality: int):
    """Tăng vĩnh viễn trần Spirituality (vd khi tiêu thụ Beyonder Characteristic —
    mục 21) và đồng bộ luôn giá trị hiện tại trong CÙNG một update."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE characters SET spirituality_max = ?, spirituality = ? WHERE character_id = ?",
            (spirituality_max, spirituality, character_id),
        )


def set_character_hp_spirituality(character_id: int, hp: int, spirituality: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE characters SET hp = ?, spirituality = ? WHERE character_id = ?",
            (hp, spirituality, character_id),
        )


# ---------- Sealed Artifacts (mục 22) ----------

def list_artifacts():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM artifacts ORDER BY risk_stars").fetchall()
        return [dict(r) for r in rows]


def get_artifact(artifact_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)).fetchone()
        return dict(row) if row else None


def get_artifact_rules(artifact_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT stage, text_vi FROM artifact_rules WHERE artifact_id = ?", (artifact_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def grant_artifact(character_id: int, artifact_id: str):
    """Cấp 1 Artifact cho Character (mục 22: Acquisition). uses_remaining khởi
    tạo từ usage_limit tĩnh của Artifact. Không có UNIQUE constraint — một
    Character có thể sở hữu nhiều bản của cùng 1 Artifact (mỗi bản độc lập
    về discovered_stages/uses_remaining), khác với Beyonder Characteristic."""
    artifact = get_artifact(artifact_id)
    if artifact is None:
        return None
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO character_artifacts (character_id, artifact_id, discovered_stages, uses_remaining)
               VALUES (?, ?, '', ?)""",
            (character_id, artifact_id, artifact["usage_limit"]),
        )
        row = conn.execute(
            "SELECT * FROM character_artifacts WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)


def list_character_artifacts(character_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT ca.*, a.name_en, a.grade, a.origin, a.sealing_method, a.risk_stars,
                      a.usage_limit, a.inspect_hint
               FROM character_artifacts ca JOIN artifacts a ON a.artifact_id = ca.artifact_id
               WHERE ca.character_id = ?
               ORDER BY ca.acquired_at ASC""",
            (character_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_character_artifact(character_artifact_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM character_artifacts WHERE id = ?", (character_artifact_id,)
        ).fetchone()
        return dict(row) if row else None


def update_artifact_discovery(character_artifact_id: int, discovered_stages: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE character_artifacts SET discovered_stages = ? WHERE id = ?",
            (discovered_stages, character_artifact_id),
        )


def consume_artifact_use(character_artifact_id: int) -> bool:
    """Trừ 1 lượt sử dụng. uses_remaining = -1 nghĩa là vô hạn (không trừ).
    Trả về False nếu đã hết lượt (uses_remaining == 0)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT uses_remaining FROM character_artifacts WHERE id = ?",
            (character_artifact_id,),
        ).fetchone()
        if row is None or row["uses_remaining"] == 0:
            return False
        if row["uses_remaining"] > 0:
            conn.execute(
                "UPDATE character_artifacts SET uses_remaining = uses_remaining - 1 WHERE id = ?",
                (character_artifact_id,),
            )
        return True


def log_artifact_history(character_id: int, artifact_id: str, action: str, side_effect_triggered: bool):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO artifact_history (character_id, artifact_id, action, side_effect_triggered)
               VALUES (?, ?, ?, ?)""",
            (character_id, artifact_id, action, int(side_effect_triggered)),
        )


def list_artifact_history(character_id: int, limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM artifact_history WHERE character_id = ? ORDER BY id DESC LIMIT ?",
            (character_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Mysticism Knowledge (mục 18) ----------

def list_knowledge_catalog():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM knowledge_definitions ORDER BY name_en").fetchall()
        return [dict(r) for r in rows]


def get_knowledge(knowledge_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM knowledge_definitions WHERE knowledge_id = ?", (knowledge_id,)
        ).fetchone()
        return dict(row) if row else None


def get_character_knowledge(character_id: int):
    """Trả về list các dòng Character ĐÃ có tiến độ (Unknown = không có row,
    ngầm định ở tầng gọi trên — xem mysticism.list_catalog)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM character_knowledge WHERE character_id = ?", (character_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_character_knowledge_row(character_id: int, knowledge_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM character_knowledge WHERE character_id = ? AND knowledge_id = ?",
            (character_id, knowledge_id),
        ).fetchone()
        return dict(row) if row else None


def upsert_character_knowledge(character_id: int, knowledge_id: str, stage: str):
    """stage tăng dần discovered -> studied -> understood. Ghi đúng cột
    timestamp tương ứng trong CÙNG một update (mục 49-50: đồng bộ, không rời rạc)."""
    column = {"discovered": "discovered_at", "studied": "studied_at", "understood": "understood_at"}[stage]
    with get_conn() as conn:
        conn.execute(
            f"""INSERT INTO character_knowledge (character_id, knowledge_id, stage, {column})
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(character_id, knowledge_id) DO UPDATE SET
                   stage = excluded.stage,
                   {column} = CURRENT_TIMESTAMP""",
            (character_id, knowledge_id, stage),
        )


# ---------- Divination (mục 19) ----------

def list_divination_methods():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM divination_methods ORDER BY spirituality_cost").fetchall()
        return [dict(r) for r in rows]


def get_divination_method(method_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM divination_methods WHERE method_id = ?", (method_id,)
        ).fetchone()
        return dict(row) if row else None


def log_divination(character_id: int, method_id: str, tier: str, roll: int, accuracy: int):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO divination_history (character_id, method_id, tier, roll, accuracy)
               VALUES (?, ?, ?, ?, ?)""",
            (character_id, method_id, tier, roll, accuracy),
        )


def list_divination_history(character_id: int, limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM divination_history WHERE character_id = ? ORDER BY id DESC LIMIT ?",
            (character_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- World / City / Location (mục 31-32) ----------

def list_cities():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM cities ORDER BY city_id").fetchall()
        return [dict(r) for r in rows]


def get_city(city_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM cities WHERE city_id = ?", (city_id,)).fetchone()
        return dict(row) if row else None


def list_locations(city_id: str = None):
    with get_conn() as conn:
        if city_id:
            rows = conn.execute(
                "SELECT * FROM locations WHERE city_id = ? ORDER BY location_id", (city_id,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM locations ORDER BY city_id, location_id").fetchall()
        return [dict(r) for r in rows]


def get_location(location_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM locations WHERE location_id = ?", (location_id,)).fetchone()
        return dict(row) if row else None


def set_character_location(character_id: int, from_location_id, to_location_id: str, money_cost: int) -> bool:
    """Atomic (mục 38/50): trừ đúng phí di chuyển (nếu có), cập nhật Location
    thật của Character, và log lại travel_log — không có bước nào tách rời.
    Trả về False nếu không đủ tiền (không trừ gì, không di chuyển)."""
    with get_conn() as conn:
        if money_cost > 0:
            row = conn.execute(
                "SELECT money FROM characters WHERE character_id = ?", (character_id,)
            ).fetchone()
            if row is None or row["money"] < money_cost:
                return False
            conn.execute(
                "UPDATE characters SET money = money - ? WHERE character_id = ?",
                (money_cost, character_id),
            )
        conn.execute(
            "UPDATE characters SET location_id = ? WHERE character_id = ?",
            (to_location_id, character_id),
        )
        conn.execute(
            """INSERT INTO travel_log (character_id, from_location_id, to_location_id, money_cost)
               VALUES (?, ?, ?, ?)""",
            (character_id, from_location_id, to_location_id, money_cost),
        )
        return True


def list_travel_log(character_id: int, limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM travel_log WHERE character_id = ? ORDER BY travel_id DESC LIMIT ?",
            (character_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- NPC (mục 28) ----------

def list_npcs_at_location(location_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM npcs WHERE location_id = ? ORDER BY npc_id", (location_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_npc(npc_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM npcs WHERE npc_id = ?", (npc_id,)).fetchone()
        return dict(row) if row else None


def get_npc_dialogue(npc_id: str, trust_tier: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT line_vi FROM npc_dialogue WHERE npc_id = ? AND trust_tier = ?",
            (npc_id, trust_tier),
        ).fetchall()
        return [r["line_vi"] for r in rows]


def get_character_npc(character_id: int, npc_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM character_npc WHERE character_id = ? AND npc_id = ?",
            (character_id, npc_id),
        ).fetchone()
        return dict(row) if row else {"character_id": character_id, "npc_id": npc_id, "trust": 0, "interactions": 0}


def adjust_npc_trust(character_id: int, npc_id: str, delta: int, action: str, detail: str = "") -> int:
    """Atomic (mục 28, 49-50): cộng dồn Trust thật (kẹp 0-100, không âm vô hạn),
    tăng interactions, và LUÔN log vào npc_memory — NPC phải nhớ mọi lần
    tương tác, không chỉ lưu con số cuối cùng. Trả về Trust mới."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT trust FROM character_npc WHERE character_id = ? AND npc_id = ?",
            (character_id, npc_id),
        ).fetchone()
        current = row["trust"] if row else 0
        new_trust = max(0, min(100, current + delta))

        conn.execute(
            """INSERT INTO character_npc (character_id, npc_id, trust, interactions)
               VALUES (?, ?, ?, 1)
               ON CONFLICT(character_id, npc_id)
               DO UPDATE SET trust = ?, interactions = interactions + 1""",
            (character_id, npc_id, new_trust, new_trust),
        )
        conn.execute(
            """INSERT INTO npc_memory (character_id, npc_id, action, detail, trust_delta)
               VALUES (?, ?, ?, ?, ?)""",
            (character_id, npc_id, action, detail, delta),
        )
        return new_trust


def list_npc_memory(character_id: int, npc_id: str, limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM npc_memory WHERE character_id = ? AND npc_id = ? ORDER BY id DESC LIMIT ?",
            (character_id, npc_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Investigation (mục 27) ----------

def list_investigations_at_location(location_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM investigations WHERE location_id = ? ORDER BY investigation_id",
            (location_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_investigation(investigation_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM investigations WHERE investigation_id = ?", (investigation_id,)
        ).fetchone()
        return dict(row) if row else None


def list_investigation_clues(investigation_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM investigation_clues WHERE investigation_id = ? ORDER BY order_index",
            (investigation_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_character_investigation(character_id: int, investigation_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM character_investigations WHERE character_id = ? AND investigation_id = ?",
            (character_id, investigation_id),
        ).fetchone()
        return dict(row) if row else None


def start_character_investigation(character_id: int, investigation_id: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO character_investigations (character_id, investigation_id, status)
               VALUES (?, ?, 'active')""",
            (character_id, investigation_id),
        )


def list_found_clue_ids(character_id: int, investigation_id: str) -> set:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT clue_id FROM character_clues WHERE character_id = ? AND investigation_id = ?",
            (character_id, investigation_id),
        ).fetchall()
        return {r["clue_id"] for r in rows}


def add_found_clue(character_id: int, investigation_id: str, clue_id: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO character_clues (character_id, investigation_id, clue_id)
               VALUES (?, ?, ?)""",
            (character_id, investigation_id, clue_id),
        )


def resolve_character_investigation(character_id: int, investigation_id: str, status: str):
    with get_conn() as conn:
        conn.execute(
            """UPDATE character_investigations
               SET status = ?, resolved_at = CURRENT_TIMESTAMP
               WHERE character_id = ? AND investigation_id = ?""",
            (status, character_id, investigation_id),
        )


# =====================================================================
# ⛪ Church / 🏛️ Faction (mục 33-34)
# =====================================================================

def list_churches():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM churches").fetchall()]


def get_church(church_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM churches WHERE church_id = ?", (church_id,)).fetchone()
        return dict(row) if row else None


def list_factions():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM factions").fetchall()]


def get_faction(faction_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM factions WHERE faction_id = ?", (faction_id,)).fetchone()
        return dict(row) if row else None


def get_character_church(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT cc.*, ch.name_en, ch.name_vi FROM character_church cc
               JOIN churches ch ON ch.church_id = cc.church_id
               WHERE cc.character_id = ? AND cc.is_member = 1""",
            (character_id,),
        ).fetchone()
        return dict(row) if row else None


def join_church(character_id: int, church_id: str):
    """Rời Church cũ (nếu có) rồi gia nhập Church mới — một Character chỉ
    thuộc một Church tại một thời điểm (mục 3: dữ liệu không được mơ hồ).
    Nếu quay lại ĐÚNG Church đã từng rời, Reputation cũ (đã bị LEAVE_PENALTY
    trừ) được giữ nguyên thay vì reset về 0."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT church_id FROM character_church WHERE character_id = ?", (character_id,)
        ).fetchone()
        if existing and existing["church_id"] == church_id:
            conn.execute(
                "UPDATE character_church SET is_member = 1 WHERE character_id = ?", (character_id,)
            )
        else:
            conn.execute("DELETE FROM character_church WHERE character_id = ?", (character_id,))
            conn.execute(
                "INSERT INTO character_church (character_id, church_id, reputation, is_member) "
                "VALUES (?, ?, 0, 1)",
                (character_id, church_id),
            )


def leave_church(character_id: int, penalty: int = 0):
    """Rời Church: is_member=0 + reputation += penalty (âm) NGAY trên hàng đang
    có — không xoá — để nếu sau này gia nhập lại ĐÚNG Church này, Reputation
    thấp do rời đi vẫn còn đó thật (không reset về 0 miễn phí)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE character_church SET is_member = 0, reputation = reputation + ? "
            "WHERE character_id = ?",
            (penalty, character_id),
        )


def get_character_faction(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT cf.*, f.name_en, f.name_vi FROM character_faction cf
               JOIN factions f ON f.faction_id = cf.faction_id
               WHERE cf.character_id = ? AND cf.is_member = 1""",
            (character_id,),
        ).fetchone()
        return dict(row) if row else None


def join_faction(character_id: int, faction_id: str):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT faction_id FROM character_faction WHERE character_id = ?", (character_id,)
        ).fetchone()
        if existing and existing["faction_id"] == faction_id:
            conn.execute(
                "UPDATE character_faction SET is_member = 1 WHERE character_id = ?", (character_id,)
            )
        else:
            conn.execute("DELETE FROM character_faction WHERE character_id = ?", (character_id,))
            conn.execute(
                "INSERT INTO character_faction (character_id, faction_id, reputation, is_member) "
                "VALUES (?, ?, 0, 1)",
                (character_id, faction_id),
            )


def leave_faction(character_id: int, penalty: int = 0):
    with get_conn() as conn:
        conn.execute(
            "UPDATE character_faction SET is_member = 0, reputation = reputation + ? "
            "WHERE character_id = ?",
            (penalty, character_id),
        )


def adjust_reputation(character_id: int, church: bool, delta: int):
    """church=True chỉnh reputation Church, False chỉnh Faction."""
    table = "character_church" if church else "character_faction"
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {table} SET reputation = reputation + ? WHERE character_id = ?",
            (delta, character_id),
        )


def donate_to_org(character_id: int, church: bool, money_amount: int, rate: float):
    """Quyên góp Tiền -> Reputation, atomic thật (mục 50): trừ Tiền và cộng
    Reputation trong CÙNG một transaction — nếu Character không đủ Tiền,
    KHÔNG connection nào được mở/ghi (kiểm tra trước bằng get_character()
    ở tầng gọi). rate: số Reputation nhận được trên mỗi 1 Tiền quyên góp.
    Trả về Reputation mới."""
    table = "character_church" if church else "character_faction"
    gained = max(1, round(money_amount * rate))
    with get_conn() as conn:
        row = conn.execute("SELECT money FROM characters WHERE character_id = ?", (character_id,)).fetchone()
        if row is None or row["money"] < money_amount:
            raise ValueError("Không đủ Tiền để quyên góp.")
        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?",
            (money_amount, character_id),
        )
        conn.execute(
            f"UPDATE {table} SET reputation = reputation + ? WHERE character_id = ?",
            (gained, character_id),
        )
        new_rep = conn.execute(
            f"SELECT reputation FROM {table} WHERE character_id = ?", (character_id,)
        ).fetchone()["reputation"]
    return gained, new_rep


# ---- Faction/Church Mission (mục 33-34) ------------------------------------

def list_faction_missions(org_type: str, org_id: str):
    with get_conn() as conn:
        return [
            dict(r) for r in conn.execute(
                "SELECT * FROM faction_missions WHERE org_type = ? AND org_id = ?",
                (org_type, org_id),
            ).fetchall()
        ]


def get_faction_mission(mission_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM faction_missions WHERE mission_id = ?", (mission_id,)
        ).fetchone()
        return dict(row) if row else None


def get_character_faction_mission(character_id: int, mission_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM character_faction_mission WHERE character_id = ? AND mission_id = ?",
            (character_id, mission_id),
        ).fetchone()
        return dict(row) if row else None


def list_character_faction_missions(character_id: int, org_type: str, org_id: str):
    with get_conn() as conn:
        return [
            dict(r) for r in conn.execute(
                """SELECT fm.*, cfm.kill_progress, cfm.claimed_at, cfm.accepted_at
                   FROM faction_missions fm
                   JOIN character_faction_mission cfm ON cfm.mission_id = fm.mission_id
                   WHERE cfm.character_id = ? AND fm.org_type = ? AND fm.org_id = ?""",
                (character_id, org_type, org_id),
            ).fetchall()
        ]


def accept_faction_mission(character_id: int, mission_id: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO character_faction_mission (character_id, mission_id, kill_progress) "
            "VALUES (?, ?, 0)",
            (character_id, mission_id),
        )


def progress_faction_mission_kill(character_id: int, monster_id: str, org_type: str, org_id: str, amount: int = 1):
    """Tăng kill_progress cho MỌI Mission (org_type, org_id) Character đang
    ACTIVE (đã accept, chưa claim) mà monster_id khớp — gọi từ combat.py._finish
    sau chiến thắng thật, không phải tự khai (giống quest.progress_objective)."""
    with get_conn() as conn:
        conn.execute(
            """UPDATE character_faction_mission
               SET kill_progress = kill_progress + ?
               WHERE character_id = ? AND claimed_at IS NULL
                 AND mission_id IN (
                     SELECT mission_id FROM faction_missions
                     WHERE org_type = ? AND org_id = ? AND monster_id = ?
                 )""",
            (amount, character_id, org_type, org_id, monster_id),
        )


def claim_faction_mission(character_id: int, mission_id: str):
    """Atomic claim (mục 50): kiểm tra + đánh dấu claimed_at + cộng thưởng
    trong CÙNG transaction — chặn double-claim thật (claimed_at IS NOT NULL
    làm điều kiện WHERE, không phải chỉ kiểm tra ở tầng Python)."""
    mission = get_faction_mission(mission_id)
    with get_conn() as conn:
        cursor = conn.execute(
            "UPDATE character_faction_mission SET claimed_at = CURRENT_TIMESTAMP "
            "WHERE character_id = ? AND mission_id = ? AND claimed_at IS NULL "
            "AND kill_progress >= ?",
            (character_id, mission_id, mission["required_kills"]),
        )
        if cursor.rowcount == 0:
            raise ValueError("Mission chưa đủ điều kiện hoặc đã claim rồi.")
        conn.execute(
            "UPDATE characters SET money = money + ?, exp = exp + ? WHERE character_id = ?",
            (mission["reward_money"], mission["reward_exp"], character_id),
        )
        table = "character_church" if mission["org_type"] == "church" else "character_faction"
        conn.execute(
            f"UPDATE {table} SET reputation = reputation + ? WHERE character_id = ?",
            (mission["reward_reputation"], character_id),
        )
    return mission


# =====================================================================
# 🃏 Tarot Club (mục 35)
# =====================================================================

def get_tarot_membership(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM tarot_members WHERE character_id = ?", (character_id,)
        ).fetchone()
        return dict(row) if row else None


def get_tarot_seat_holder(seat: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tarot_members WHERE tarot_seat = ?", (seat,)).fetchone()
        return dict(row) if row else None


def list_taken_seats() -> set:
    with get_conn() as conn:
        return {r["tarot_seat"] for r in conn.execute("SELECT tarot_seat FROM tarot_members").fetchall()}


def join_tarot_club(character_id: int, seat: str) -> bool:
    """Atomic: chỉ gán ghế nếu ghế đó CHƯA có ai và Character CHƯA là thành
    viên — tránh 2 Character trùng danh xưng Tarot (mục 35: danh tính thật
    được bảo vệ, mỗi mật danh là duy nhất)."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM tarot_members WHERE character_id = ?", (character_id,)
        ).fetchone()
        if already:
            return False
        taken = conn.execute("SELECT 1 FROM tarot_members WHERE tarot_seat = ?", (seat,)).fetchone()
        if taken:
            return False
        conn.execute(
            "INSERT INTO tarot_members (character_id, tarot_seat) VALUES (?, ?)",
            (character_id, seat),
        )
        return True


def leave_tarot_club(character_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM tarot_members WHERE character_id = ?", (character_id,))


def list_tarot_meetings(limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tarot_meetings ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def create_tarot_meeting(topic_vi: str, called_by_seat: str):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tarot_meetings (topic_vi, called_by_seat) VALUES (?, ?)",
            (topic_vi, called_by_seat),
        )
        return cur.lastrowid


def post_tarot_message(meeting_id: int, from_seat: str, content_vi: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO tarot_messages (meeting_id, from_seat, content_vi) VALUES (?, ?, ?)",
            (meeting_id, from_seat, content_vi),
        )


def list_tarot_messages(meeting_id: int, limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tarot_messages WHERE meeting_id = ? ORDER BY created_at ASC LIMIT ?",
            (meeting_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# =====================================================================
# 👥 Party (mục 36)
# =====================================================================

MAX_PARTY_SIZE = 5


def get_character_party(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT p.* FROM parties p
               JOIN party_members pm ON pm.party_id = p.party_id
               WHERE pm.character_id = ? AND p.status = 'active'""",
            (character_id,),
        ).fetchone()
        return dict(row) if row else None


def list_party_members(party_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT pm.role, c.character_id, c.name, c.level, c.sequence_number, c.pathway_id
               FROM party_members pm JOIN characters c ON c.character_id = pm.character_id
               WHERE pm.party_id = ?""",
            (party_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def create_party(leader_character_id: int):
    """Atomic: fail nếu leader đã ở trong một Party khác đang active."""
    with get_conn() as conn:
        existing = conn.execute(
            """SELECT 1 FROM party_members pm JOIN parties p ON p.party_id = pm.party_id
               WHERE pm.character_id = ? AND p.status = 'active'""",
            (leader_character_id,),
        ).fetchone()
        if existing:
            return None
        cur = conn.execute(
            "INSERT INTO parties (leader_character_id) VALUES (?)", (leader_character_id,)
        )
        party_id = cur.lastrowid
        conn.execute(
            "INSERT INTO party_members (party_id, character_id, role) VALUES (?, ?, 'leader')",
            (party_id, leader_character_id),
        )
        return party_id


def join_party(party_id: int, character_id: int) -> bool:
    with get_conn() as conn:
        already = conn.execute(
            """SELECT 1 FROM party_members pm JOIN parties p ON p.party_id = pm.party_id
               WHERE pm.character_id = ? AND p.status = 'active'""",
            (character_id,),
        ).fetchone()
        if already:
            return False
        count = conn.execute(
            "SELECT COUNT(*) AS c FROM party_members WHERE party_id = ?", (party_id,)
        ).fetchone()["c"]
        if count >= MAX_PARTY_SIZE:
            return False
        conn.execute(
            "INSERT INTO party_members (party_id, character_id, role) VALUES (?, ?, 'member')",
            (party_id, character_id),
        )
        return True


def leave_party(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT p.party_id, p.leader_character_id FROM parties p
               JOIN party_members pm ON pm.party_id = p.party_id
               WHERE pm.character_id = ? AND p.status = 'active'""",
            (character_id,),
        ).fetchone()
        if row is None:
            return
        conn.execute(
            "DELETE FROM party_members WHERE party_id = ? AND character_id = ?",
            (row["party_id"], character_id),
        )
        remaining = conn.execute(
            "SELECT character_id FROM party_members WHERE party_id = ? ORDER BY joined_at ASC LIMIT 1",
            (row["party_id"],),
        ).fetchone()
        if remaining is None:
            conn.execute("UPDATE parties SET status = 'disbanded' WHERE party_id = ?", (row["party_id"],))
        elif row["leader_character_id"] == character_id:
            conn.execute(
                "UPDATE parties SET leader_character_id = ? WHERE party_id = ?",
                (remaining["character_id"], row["party_id"]),
            )
            conn.execute(
                "UPDATE party_members SET role = 'leader' WHERE party_id = ? AND character_id = ?",
                (row["party_id"], remaining["character_id"]),
            )


# =====================================================================
# 💰 Economy / 🤝 Trade / 📜 Contract / ☠️ Bounty (mục 37-41)
# =====================================================================

def list_market_listings(limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT ml.*, i.name_en, i.name_vi, c.name AS seller_name FROM market_listings ml
               JOIN items i ON i.item_id = ml.item_id
               JOIN characters c ON c.character_id = ml.seller_character_id
               WHERE ml.status = 'active' ORDER BY ml.created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_market_listing(listing_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT ml.*, i.name_en, i.name_vi FROM market_listings ml
               JOIN items i ON i.item_id = ml.item_id
               WHERE ml.listing_id = ? AND ml.status = 'active'""",
            (listing_id,),
        ).fetchone()
        return dict(row) if row else None


def create_market_listing(seller_character_id: int, item_id: str, quantity: int, price_per_unit: int):
    """Atomic: CHECK tồn kho -> REMOVE khỏi Inventory ngay (item bị 'khoá'
    vào listing) -> tạo listing. Nếu không đủ hàng, không tạo gì cả."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
            (seller_character_id, item_id),
        ).fetchone()
        have = row["quantity"] if row else 0
        if have < quantity:
            return None
        conn.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE character_id = ? AND item_id = ?",
            (quantity, seller_character_id, item_id),
        )
        conn.execute("DELETE FROM inventory WHERE character_id = ? AND quantity <= 0", (seller_character_id,))
        cur = conn.execute(
            """INSERT INTO market_listings (seller_character_id, item_id, quantity, price_per_unit)
               VALUES (?, ?, ?, ?)""",
            (seller_character_id, item_id, quantity, price_per_unit),
        )
        return cur.lastrowid


def cancel_market_listing(listing_id: int, seller_character_id: int) -> bool:
    """Atomic: trả hàng lại Inventory rồi mới đóng listing."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM market_listings WHERE listing_id = ? AND seller_character_id = ? AND status = 'active'",
            (listing_id, seller_character_id),
        ).fetchone()
        if row is None:
            return False
        conn.execute(
            """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (seller_character_id, row["item_id"], row["quantity"]),
        )
        conn.execute("UPDATE market_listings SET status = 'cancelled' WHERE listing_id = ?", (listing_id,))
        return True


def buy_market_listing_transaction(listing_id: int, buyer_character_id: int) -> bool:
    """Atomic mua trọn 1 listing (mục 38):
    CHECK buyer đủ tiền + listing còn active
    -> REMOVE tiền buyer, ADD tiền seller
    -> ADD item vào Inventory buyer, đóng listing
    -> Log trade_history -> COMMIT (get_conn tự commit; nếu exception thì
    KHÔNG commit gì — sqlite3 rollback tự động, đúng mục 38: không để buyer
    mất tiền mà seller không nhận, hoặc ngược lại)."""
    with get_conn() as conn:
        listing = conn.execute(
            "SELECT * FROM market_listings WHERE listing_id = ? AND status = 'active'", (listing_id,)
        ).fetchone()
        if listing is None:
            return False
        total_price = listing["price_per_unit"] * listing["quantity"]
        buyer = conn.execute(
            "SELECT money FROM characters WHERE character_id = ?", (buyer_character_id,)
        ).fetchone()
        if buyer is None or buyer["money"] < total_price:
            return False
        if listing["seller_character_id"] == buyer_character_id:
            return False

        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?",
            (total_price, buyer_character_id),
        )
        conn.execute(
            "UPDATE characters SET money = money + ? WHERE character_id = ?",
            (total_price, listing["seller_character_id"]),
        )
        conn.execute(
            """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (buyer_character_id, listing["item_id"], listing["quantity"]),
        )
        conn.execute("UPDATE market_listings SET status = 'sold' WHERE listing_id = ?", (listing_id,))
        conn.execute(
            """INSERT INTO trade_history (kind, from_character_id, to_character_id, item_id, quantity, money_amount)
               VALUES ('market_buy', ?, ?, ?, ?, ?)""",
            (listing["seller_character_id"], buyer_character_id, listing["item_id"], listing["quantity"], total_price),
        )
        return True


def direct_trade_item_for_money_transaction(from_character_id: int, to_character_id: int,
                                              item_id: str, quantity: int, price: int) -> bool:
    """Atomic Trade trực tiếp 1-đổi-1 giữa hai Character (mục 38):
    CHECK A có đủ item, CHECK B có đủ tiền
    -> REMOVE item khỏi A, REMOVE tiền khỏi B
    -> ADD item vào B, ADD tiền vào A
    -> Log -> COMMIT. Bất kỳ bước CHECK nào fail thì KHÔNG đổi gì cả."""
    with get_conn() as conn:
        stock = conn.execute(
            "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
            (from_character_id, item_id),
        ).fetchone()
        have = stock["quantity"] if stock else 0
        if have < quantity:
            return False
        buyer = conn.execute(
            "SELECT money FROM characters WHERE character_id = ?", (to_character_id,)
        ).fetchone()
        if buyer is None or buyer["money"] < price:
            return False

        conn.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE character_id = ? AND item_id = ?",
            (quantity, from_character_id, item_id),
        )
        conn.execute("DELETE FROM inventory WHERE character_id = ? AND quantity <= 0", (from_character_id,))
        conn.execute(
            """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (to_character_id, item_id, quantity),
        )
        conn.execute("UPDATE characters SET money = money - ? WHERE character_id = ?", (price, to_character_id))
        conn.execute("UPDATE characters SET money = money + ? WHERE character_id = ?", (price, from_character_id))
        conn.execute(
            """INSERT INTO trade_history (kind, from_character_id, to_character_id, item_id, quantity, money_amount)
               VALUES ('direct_trade', ?, ?, ?, ?, ?)""",
            (from_character_id, to_character_id, item_id, quantity, price),
        )
        return True


def list_trade_history(character_id: int, limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM trade_history WHERE from_character_id = ? OR to_character_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (character_id, character_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- Contract (mục 39) ----------

def create_contract(issuer_character_id: int, task_vi: str, reward_money: int):
    """Atomic: trừ reward_money của issuer ngay khi đăng (ký quỹ) để không
    thể quỵt thưởng khi Contract hoàn thành."""
    with get_conn() as conn:
        issuer = conn.execute(
            "SELECT money FROM characters WHERE character_id = ?", (issuer_character_id,)
        ).fetchone()
        if issuer is None or issuer["money"] < reward_money:
            return None
        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?",
            (reward_money, issuer_character_id),
        )
        cur = conn.execute(
            "INSERT INTO contracts (issuer_character_id, task_vi, reward_money) VALUES (?, ?, ?)",
            (issuer_character_id, task_vi, reward_money),
        )
        return cur.lastrowid


def list_open_contracts(limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM contracts WHERE status = 'open' ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_character_contracts(character_id: int, limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM contracts WHERE issuer_character_id = ? OR accepted_character_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (character_id, character_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def accept_contract(contract_id: int, character_id: int) -> bool:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contracts WHERE contract_id = ? AND status = 'open'", (contract_id,)
        ).fetchone()
        if row is None or row["issuer_character_id"] == character_id:
            return False
        conn.execute(
            "UPDATE contracts SET status = 'in_progress', accepted_character_id = ? WHERE contract_id = ?",
            (character_id, contract_id),
        )
        return True


def complete_contract_transaction(contract_id: int, issuer_character_id: int) -> bool:
    """Chỉ issuer mới xác nhận hoàn thành — trả reward (đã ký quỹ trước đó)
    cho người nhận Contract."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contracts WHERE contract_id = ? AND issuer_character_id = ? AND status = 'in_progress'",
            (contract_id, issuer_character_id),
        ).fetchone()
        if row is None or row["accepted_character_id"] is None:
            return False
        conn.execute(
            "UPDATE characters SET money = money + ? WHERE character_id = ?",
            (row["reward_money"], row["accepted_character_id"]),
        )
        conn.execute(
            "UPDATE contracts SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE contract_id = ?",
            (contract_id,),
        )
        conn.execute(
            """INSERT INTO trade_history (kind, from_character_id, to_character_id, money_amount)
               VALUES ('contract_reward', ?, ?, ?)""",
            (issuer_character_id, row["accepted_character_id"], row["reward_money"]),
        )
        return True


def cancel_contract_transaction(contract_id: int, issuer_character_id: int) -> bool:
    """Chỉ huỷ được khi chưa ai nhận — hoàn lại tiền ký quỹ."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM contracts WHERE contract_id = ? AND issuer_character_id = ? AND status = 'open'",
            (contract_id, issuer_character_id),
        ).fetchone()
        if row is None:
            return False
        conn.execute(
            "UPDATE characters SET money = money + ? WHERE character_id = ?",
            (row["reward_money"], issuer_character_id),
        )
        conn.execute("UPDATE contracts SET status = 'cancelled' WHERE contract_id = ?", (contract_id,))
        return True


# ---------- Bounty (mục 40) ----------

def create_bounty(issuer_character_id, target_character_id: int, crime_vi: str, reward_money: int):
    with get_conn() as conn:
        if issuer_character_id is not None:
            issuer = conn.execute(
                "SELECT money FROM characters WHERE character_id = ?", (issuer_character_id,)
            ).fetchone()
            if issuer is None or issuer["money"] < reward_money:
                return None
            conn.execute(
                "UPDATE characters SET money = money - ? WHERE character_id = ?",
                (reward_money, issuer_character_id),
            )
        cur = conn.execute(
            """INSERT INTO bounties (issuer_character_id, target_character_id, crime_vi, reward_money)
               VALUES (?, ?, ?, ?)""",
            (issuer_character_id, target_character_id, crime_vi, reward_money),
        )
        return cur.lastrowid


def list_active_bounties(limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT b.*, c.name AS target_name FROM bounties b
               JOIN characters c ON c.character_id = b.target_character_id
               WHERE b.status = 'active' ORDER BY b.reward_money DESC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def claim_bounty_transaction(bounty_id: int, claimer_character_id: int) -> bool:
    """Atomic: đóng bounty + trả thưởng cho người nhận (thắng PvP với mục
    tiêu là điều kiện Engine kiểm tra ở service layer trước khi gọi hàm này)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM bounties WHERE bounty_id = ? AND status = 'active'", (bounty_id,)
        ).fetchone()
        if row is None or row["target_character_id"] == claimer_character_id:
            return False
        conn.execute(
            "UPDATE characters SET money = money + ? WHERE character_id = ?",
            (row["reward_money"], claimer_character_id),
        )
        conn.execute(
            """UPDATE bounties SET status = 'claimed', claimed_by_character_id = ?,
               claimed_at = CURRENT_TIMESTAMP WHERE bounty_id = ?""",
            (claimer_character_id, bounty_id),
        )
        return True


# =====================================================================
# 🏠 House (mục 42)
# =====================================================================

def get_or_create_house(character_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM houses WHERE character_id = ?", (character_id,)).fetchone()
        if row is None:
            conn.execute("INSERT INTO houses (character_id) VALUES (?)", (character_id,))
            row = conn.execute("SELECT * FROM houses WHERE character_id = ?", (character_id,)).fetchone()
        return dict(row)


def list_house_storage(character_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT hs.item_id, hs.quantity, i.name_en, i.name_vi FROM house_storage hs
               JOIN items i ON i.item_id = hs.item_id
               WHERE hs.character_id = ? AND hs.quantity > 0""",
            (character_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def store_item_in_house_transaction(character_id: int, item_id: str, quantity: int) -> bool:
    """Atomic: chuyển item từ Inventory mang theo người vào kho House."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
            (character_id, item_id),
        ).fetchone()
        have = row["quantity"] if row else 0
        if have < quantity:
            return False
        conn.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE character_id = ? AND item_id = ?",
            (quantity, character_id, item_id),
        )
        conn.execute("DELETE FROM inventory WHERE character_id = ? AND quantity <= 0", (character_id,))
        conn.execute(
            """INSERT INTO house_storage (character_id, item_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (character_id, item_id, quantity),
        )
        return True


def withdraw_item_from_house_transaction(character_id: int, item_id: str, quantity: int) -> bool:
    """Atomic: chiều ngược lại — rút item từ kho House ra Inventory mang theo."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM house_storage WHERE character_id = ? AND item_id = ?",
            (character_id, item_id),
        ).fetchone()
        have = row["quantity"] if row else 0
        if have < quantity:
            return False
        conn.execute(
            "UPDATE house_storage SET quantity = quantity - ? WHERE character_id = ? AND item_id = ?",
            (quantity, character_id, item_id),
        )
        conn.execute(
            """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (character_id, item_id, quantity),
        )
        return True


def get_house_rooms(character_id: int) -> dict:
    """Trả về {room_type: level} cho cả 4 phòng chức năng, mặc định level 0
    cho phòng chưa từng nâng cấp (không cần INSERT trước — giống cách Unknown
    của Mysticism Knowledge ở mục 18: trạng thái ngầm định không lưu DB)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT room_type, level FROM house_rooms WHERE character_id = ?", (character_id,)
        ).fetchall()
        levels = {r["room_type"]: r["level"] for r in rows}
        return {rt: levels.get(rt, 0) for rt in ("research", "potion", "ritual", "artifact")}


def get_house_room_level(character_id: int, room_type: str) -> int:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT level FROM house_rooms WHERE character_id = ? AND room_type = ?",
            (character_id, room_type),
        ).fetchone()
        return row["level"] if row else 0


def upgrade_house_room_transaction(character_id: int, room_type: str, cost: int, max_level: int) -> bool:
    """Atomic: CHECK tiền + level hiện tại chưa kịch trần -> REMOVE tiền
    -> ADD 1 level phòng -> COMMIT (rollback tự động nếu lỗi giữa chừng,
    cùng pattern với Trade ở mục 38)."""
    with get_conn() as conn:
        char = conn.execute(
            "SELECT money FROM characters WHERE character_id = ?", (character_id,)
        ).fetchone()
        if char is None or char["money"] < cost:
            return False
        row = conn.execute(
            "SELECT level FROM house_rooms WHERE character_id = ? AND room_type = ?",
            (character_id, room_type),
        ).fetchone()
        current_level = row["level"] if row else 0
        if current_level >= max_level:
            return False

        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?", (cost, character_id)
        )
        conn.execute(
            """INSERT INTO house_rooms (character_id, room_type, level) VALUES (?, ?, 1)
               ON CONFLICT(character_id, room_type) DO UPDATE SET level = level + 1""",
            (character_id, room_type),
        )
        return True


def upgrade_house_tier_transaction(character_id: int, cost: int, slot_increase: int, max_tier: int) -> bool:
    """Atomic: nâng Tier của House, tăng storage_slots kèm theo. Cùng pattern
    CHECK -> REMOVE -> ADD -> COMMIT như mọi transaction khác trong file này."""
    with get_conn() as conn:
        char = conn.execute(
            "SELECT money FROM characters WHERE character_id = ?", (character_id,)
        ).fetchone()
        if char is None or char["money"] < cost:
            return False
        house = conn.execute(
            "SELECT tier FROM houses WHERE character_id = ?", (character_id,)
        ).fetchone()
        current_tier = house["tier"] if house else 1
        if current_tier >= max_tier:
            return False

        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?", (cost, character_id)
        )
        conn.execute(
            """INSERT INTO houses (character_id, tier, storage_slots) VALUES (?, 2, 20 + ?)
               ON CONFLICT(character_id) DO UPDATE SET tier = tier + 1, storage_slots = storage_slots + ?""",
            (character_id, slot_increase, slot_increase),
        )
        return True


# =====================================================================
# 📜 Quest (mục 43) — LOCKED/AVAILABLE/ACTIVE/COMPLETED/FAILED/EXPIRED
# =====================================================================

def get_quest(quest_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM quests WHERE quest_id = ?", (quest_id,)).fetchone()
        return dict(row) if row else None


def list_quest_objectives(quest_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM quest_objectives WHERE quest_id = ? ORDER BY order_index", (quest_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def list_all_quests():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM quests ORDER BY min_level, quest_id").fetchall()
        return [dict(r) for r in rows]


def get_character_quest(character_id: int, quest_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM character_quests WHERE character_id = ? AND quest_id = ?",
            (character_id, quest_id),
        ).fetchone()
        return dict(row) if row else None


def list_character_quests(character_id: int, status: str = None):
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                """SELECT cq.*, q.name_vi, q.category FROM character_quests cq
                   JOIN quests q ON q.quest_id = cq.quest_id
                   WHERE cq.character_id = ? AND cq.status = ?
                   ORDER BY cq.started_at DESC""",
                (character_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT cq.*, q.name_vi, q.category FROM character_quests cq
                   JOIN quests q ON q.quest_id = cq.quest_id
                   WHERE cq.character_id = ? ORDER BY cq.started_at DESC""",
                (character_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def start_character_quest(character_id: int, quest_id: str) -> bool:
    """Atomic: mở ACTIVE + tạo sẵn dòng progress = 0 cho mọi Objective, để
    progress_objective() sau này chỉ cần UPDATE, không phải INSERT-or-UPDATE
    rải rác (đúng mục 50: transaction cho hành động quan trọng)."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT 1 FROM character_quests WHERE character_id = ? AND quest_id = ?",
            (character_id, quest_id),
        ).fetchone()
        if existing:
            return False
        conn.execute(
            "INSERT INTO character_quests (character_id, quest_id, status) VALUES (?, ?, 'ACTIVE')",
            (character_id, quest_id),
        )
        objectives = conn.execute(
            "SELECT objective_id FROM quest_objectives WHERE quest_id = ?", (quest_id,)
        ).fetchall()
        conn.executemany(
            "INSERT INTO character_quest_objectives (character_id, objective_id) VALUES (?, ?)",
            [(character_id, o["objective_id"]) for o in objectives],
        )
        return True


def list_character_quest_objectives(character_id: int, quest_id: str):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT qo.*, cqo.progress_count, cqo.completed_at
               FROM quest_objectives qo
               JOIN character_quest_objectives cqo
                 ON cqo.objective_id = qo.objective_id AND cqo.character_id = ?
               WHERE qo.quest_id = ? ORDER BY qo.order_index""",
            (character_id, quest_id),
        ).fetchall()
        return [dict(r) for r in rows]


def advance_quest_objectives(character_id: int, objective_type: str, target_id: str, amount: int = 1):
    """Cộng dồn progress cho MỌI Objective đang ACTIVE khớp (type, target_id)
    — một hành động (giết 1 Monster, thu 1 Item...) có thể đóng góp cho
    nhiều Quest cùng lúc nếu chúng đều cần cùng mục tiêu. Kẹp progress_count
    không vượt target_count. Trả về danh sách objective_id vừa đạt đủ."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT cqo.character_id, cqo.objective_id, cqo.progress_count,
                      qo.target_count, qo.quest_id
               FROM character_quest_objectives cqo
               JOIN quest_objectives qo ON qo.objective_id = cqo.objective_id
               JOIN character_quests cq
                 ON cq.character_id = cqo.character_id AND cq.quest_id = qo.quest_id
               WHERE cqo.character_id = ? AND qo.objective_type = ? AND qo.target_id = ?
                 AND cq.status = 'ACTIVE' AND cqo.completed_at IS NULL""",
            (character_id, objective_type, target_id),
        ).fetchall()

        newly_completed = []
        for row in rows:
            new_count = min(row["target_count"], row["progress_count"] + amount)
            done = new_count >= row["target_count"]
            conn.execute(
                """UPDATE character_quest_objectives
                   SET progress_count = ?, completed_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END
                   WHERE character_id = ? AND objective_id = ?""",
                (new_count, done, character_id, row["objective_id"]),
            )
            if done:
                newly_completed.append(row["objective_id"])
        return newly_completed


def complete_character_quest_transaction(character_id: int, quest_id: str, character_hp: int) -> bool:
    """Atomic: chỉ hoàn thành khi MỌI Objective đã completed_at, trả thưởng
    qua đúng 1 hàm apply_combat_result() có sẵn (mục 49: không update rời
    rạc Tiền/EXP ở nhiều nơi), rồi đánh dấu COMPLETED (hoặc reset về
    AVAILABLE-lại-từ-đầu nếu repeatable — engine service layer quyết định
    việc gọi start_character_quest lại)."""
    with get_conn() as conn:
        quest = conn.execute("SELECT * FROM quests WHERE quest_id = ?", (quest_id,)).fetchone()
        cq = conn.execute(
            "SELECT * FROM character_quests WHERE character_id = ? AND quest_id = ? AND status = 'ACTIVE'",
            (character_id, quest_id),
        ).fetchone()
        if quest is None or cq is None:
            return False

        total = conn.execute(
            "SELECT COUNT(*) AS c FROM quest_objectives WHERE quest_id = ?", (quest_id,)
        ).fetchone()["c"]
        done = conn.execute(
            """SELECT COUNT(*) AS c FROM character_quest_objectives cqo
               JOIN quest_objectives qo ON qo.objective_id = cqo.objective_id
               WHERE cqo.character_id = ? AND qo.quest_id = ? AND cqo.completed_at IS NOT NULL""",
            (character_id, quest_id),
        ).fetchone()["c"]
        if total == 0 or done < total:
            return False

        conn.execute(
            "UPDATE characters SET money = money + ?, exp = exp + ? WHERE character_id = ?",
            (quest["reward_money"], quest["reward_exp"], character_id),
        )
        if quest["reward_item_id"]:
            conn.execute(
                """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, 1)
                   ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + 1""",
                (character_id, quest["reward_item_id"]),
            )
        conn.execute(
            "UPDATE character_quests SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP "
            "WHERE character_id = ? AND quest_id = ?",
            (character_id, quest_id),
        )
        return True


# =====================================================================
# 🏆 Achievement / 📊 Ranking (mục 45-46)
# =====================================================================

def list_achievements():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM achievements").fetchall()]


def list_character_achievement_ids(character_id: int) -> set:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT achievement_id FROM character_achievements WHERE character_id = ?", (character_id,)
        ).fetchall()
        return {r["achievement_id"] for r in rows}


def unlock_achievement_transaction(character_id: int, achievement_id: str) -> bool:
    """Atomic: idempotent — nếu đã có thì không cộng thưởng lại lần 2
    (mục 50: mọi thay đổi state phải đồng bộ, không double-reward)."""
    with get_conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM character_achievements WHERE character_id = ? AND achievement_id = ?",
            (character_id, achievement_id),
        ).fetchone()
        if already:
            return False
        ach = conn.execute(
            "SELECT * FROM achievements WHERE achievement_id = ?", (achievement_id,)
        ).fetchone()
        if ach is None:
            return False
        conn.execute(
            "INSERT INTO character_achievements (character_id, achievement_id) VALUES (?, ?)",
            (character_id, achievement_id),
        )
        conn.execute(
            "UPDATE characters SET money = money + ?, exp = exp + ? WHERE character_id = ?",
            (ach["reward_money"], ach["reward_exp"], character_id),
        )
        return True


RANKING_FIELDS = {
    "level": ("level", "Level"),
    "money": ("money", "Tài sản (Bảng)"),
    "sequence": ("sequence_number", "Sequence (thấp hơn = mạnh hơn)"),
}


def get_ranking(field: str, limit: int = 10):
    """Bảng xếp hạng tính TRỰC TIẾP từ characters — luôn đồng bộ tuyệt đối
    với trạng thái sống hiện tại, không cần bảng snapshot riêng có thể bị lệch."""
    column, _ = RANKING_FIELDS.get(field, RANKING_FIELDS["level"])
    order = "ASC" if field == "sequence" else "DESC"
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT character_id, name, level, money, sequence_number, pathway_id "
            f"FROM characters ORDER BY {column} {order} LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- 🌗 Season (mục 44, 46) ----------

# category -> (label_vi, "all_time" tính trực tiếp characters/achievements vĩnh
# viễn, hay "season" tính từ character_season_stats của Season đang active).
SEASON_RANKING_CATEGORIES = {
    "pvp": ("Đối kháng (PvP thắng)", "season", "pvp_wins"),
    "dungeon": ("Dungeon (đã phá)", "season", "dungeon_clears"),
    "bounty": ("Truy nã (đã nhận)", "season", "bounty_claims"),
    "achievement": ("Thành tựu (đã mở khoá)", "achievement", None),
    "guild": ("Guild (Treasury)", "guild", None),
}

# Toàn bộ category Ranking mục 46 gộp làm một, cho UI lặp mà không cần biết
# category nào thuộc RANKING_FIELDS (vĩnh viễn) hay SEASON_RANKING_CATEGORIES
# (theo Season) — value là label hiển thị.
ALL_RANKING_CATEGORIES = {
    **{k: v[1] for k, v in RANKING_FIELDS.items()},
    **{k: v[0] for k, v in SEASON_RANKING_CATEGORIES.items()},
}


def get_active_season():
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM seasons WHERE status = 'active'").fetchone()
        return dict(row) if row else None


def get_season(season_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM seasons WHERE season_id = ?", (season_id,)).fetchone()
        return dict(row) if row else None


def list_seasons(limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM seasons ORDER BY season_id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def increment_season_stat(character_id: int, stat_column: str, amount: int = 1):
    """Cộng dồn 1 bộ đếm Season (pvp_wins/dungeon_clears/bounty_claims) cho
    Season đang active. Gọi như một lệnh TOP-LEVEL riêng SAU KHI transaction
    chính đã commit (giống _hook_guild_war_score trong pvp.py) — không lồng
    vào bên trong get_conn() khác để tránh 'database is locked' (mục 50:
    atomic nhưng đây là hook phụ, không phải một phần bắt buộc của giao dịch
    gốc — nếu hook lỗi, giao dịch gốc vẫn đã thành công)."""
    if stat_column not in ("pvp_wins", "dungeon_clears", "bounty_claims"):
        raise ValueError(f"Cột season stat không hợp lệ: {stat_column}")
    season = get_active_season()
    if season is None:
        return
    with get_conn() as conn:
        conn.execute(
            f"""INSERT INTO character_season_stats (season_id, character_id, {stat_column})
                VALUES (?, ?, ?)
                ON CONFLICT(season_id, character_id)
                DO UPDATE SET {stat_column} = {stat_column} + excluded.{stat_column}""",
            (season["season_id"], character_id, amount),
        )


def get_live_ranking(category: str, limit: int = 10):
    """Ranking SỐNG cho các category mục 46 chưa có trong RANKING_FIELDS
    (PvP/Dungeon/Bounty theo Season đang active, Achievement/Guild vĩnh viễn)."""
    if category not in SEASON_RANKING_CATEGORIES:
        return []
    _, kind, stat_column = SEASON_RANKING_CATEGORIES[category]
    with get_conn() as conn:
        if kind == "season":
            season = get_active_season()
            if season is None:
                return []
            rows = conn.execute(
                f"""SELECT c.character_id, c.name, css.{stat_column} AS value
                    FROM character_season_stats css
                    JOIN characters c ON c.character_id = css.character_id
                    WHERE css.season_id = ? AND css.{stat_column} > 0
                    ORDER BY css.{stat_column} DESC LIMIT ?""",
                (season["season_id"], limit),
            ).fetchall()
        elif kind == "achievement":
            rows = conn.execute(
                """SELECT c.character_id, c.name, COUNT(ca.achievement_id) AS value
                   FROM character_achievements ca
                   JOIN characters c ON c.character_id = ca.character_id
                   GROUP BY c.character_id ORDER BY value DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        else:  # guild
            rows = conn.execute(
                "SELECT guild_id AS character_id, name, treasury AS value "
                "FROM guilds ORDER BY treasury DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def end_season_transaction(new_season_name_vi: str) -> int:
    """Atomic: chụp Top 10 mỗi category (mục 46 'Snapshot theo Season') của
    Season đang active vào season_rankings, đóng Season đó lại, rồi mở Season
    mới — character_season_stats của Season mới rỗng một cách tự nhiên vì
    khoá theo season_id (KHÔNG đụng vào level/money/sequence/achievement —
    đúng mục 44 'Không reset Character progression')."""
    with get_conn() as conn:
        current = conn.execute("SELECT * FROM seasons WHERE status = 'active'").fetchone()
        if current is None:
            return None
        season_id = current["season_id"]

        for field, (_, label) in RANKING_FIELDS.items():
            column, _ = RANKING_FIELDS[field]
            order = "ASC" if field == "sequence" else "DESC"
            top = conn.execute(
                f"SELECT character_id, name, {column} AS value FROM characters "
                f"ORDER BY {column} {order} LIMIT 10"
            ).fetchall()
            for rank, row in enumerate(top, start=1):
                conn.execute(
                    """INSERT INTO season_rankings
                       (season_id, category, rank, character_id, character_name, value)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (season_id, field, rank, row["character_id"], row["name"], row["value"]),
                )

        for category, (_, kind, stat_column) in SEASON_RANKING_CATEGORIES.items():
            if kind == "season":
                top = conn.execute(
                    f"""SELECT c.character_id, c.name, css.{stat_column} AS value
                        FROM character_season_stats css
                        JOIN characters c ON c.character_id = css.character_id
                        WHERE css.season_id = ? AND css.{stat_column} > 0
                        ORDER BY css.{stat_column} DESC LIMIT 10""",
                    (season_id,),
                ).fetchall()
            elif kind == "achievement":
                top = conn.execute(
                    """SELECT c.character_id, c.name, COUNT(ca.achievement_id) AS value
                       FROM character_achievements ca
                       JOIN characters c ON c.character_id = ca.character_id
                       GROUP BY c.character_id ORDER BY value DESC LIMIT 10"""
                ).fetchall()
            else:  # guild
                top = conn.execute(
                    "SELECT guild_id AS character_id, name, treasury AS value "
                    "FROM guilds ORDER BY treasury DESC LIMIT 10"
                ).fetchall()
            for rank, row in enumerate(top, start=1):
                conn.execute(
                    """INSERT INTO season_rankings
                       (season_id, category, rank, character_id, character_name, value)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (season_id, category, rank, row["character_id"], row["name"], row["value"]),
                )

        conn.execute(
            "UPDATE seasons SET status = 'ended', ended_at = CURRENT_TIMESTAMP WHERE season_id = ?",
            (season_id,),
        )
        cur = conn.execute(
            "INSERT INTO seasons (name_vi, status) VALUES (?, 'active')", (new_season_name_vi,)
        )
        conn.execute(
            "INSERT INTO world_history (category, summary_vi, ref_id) VALUES ('season', ?, ?)",
            (f"Mùa '{current['name_vi']}' đã kết thúc. '{new_season_name_vi}' bắt đầu.", str(season_id)),
        )
        return cur.lastrowid


def list_season_ranking_snapshot(season_id: int, category: str, limit: int = 10):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT rank, character_name, value FROM season_rankings
               WHERE season_id = ? AND category = ? ORDER BY rank ASC LIMIT ?""",
            (season_id, category, limit),
        ).fetchall()
        return [dict(r) for r in rows]


# =====================================================================
# Dev-only error log (xem error_handler.py — KHÔNG expose cho player)
# =====================================================================

def log_engine_error(incident_id: str, source: str, detail: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO engine_error_log (incident_id, source, detail) VALUES (?, ?, ?)",
            (incident_id, source, detail),
        )


# =====================================================================
# 🏰 Dungeon (mục 26)
# =====================================================================

def list_dungeons():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM dungeons").fetchall()]


def get_dungeon(dungeon_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM dungeons WHERE dungeon_id = ?", (dungeon_id,)).fetchone()
        return dict(row) if row else None


def get_active_dungeon_run(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM dungeon_runs WHERE character_id = ? AND status = 'active'", (character_id,)
        ).fetchone()
        return dict(row) if row else None


def get_dungeon_run(run_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM dungeon_runs WHERE run_id = ?", (run_id,)).fetchone()
        return dict(row) if row else None


def create_dungeon_run(character_id: int, dungeon_id: str, seed: int, total_rooms: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO dungeon_runs (character_id, dungeon_id, seed, current_room, total_rooms)
               VALUES (?, ?, ?, 0, ?)""",
            (character_id, dungeon_id, seed, total_rooms),
        )
        return cur.lastrowid


def advance_dungeon_run(run_id: int, room_type: str, result_vi: str):
    """Atomic: ghi log phòng vừa xử lý + tăng current_room lên 1 trong cùng
    một transaction (mục 49-50: không được cập nhật một nơi rồi quên nơi khác)."""
    with get_conn() as conn:
        run = conn.execute("SELECT * FROM dungeon_runs WHERE run_id = ?", (run_id,)).fetchone()
        conn.execute(
            "INSERT INTO dungeon_run_events (run_id, room_index, room_type, result_vi) VALUES (?, ?, ?, ?)",
            (run_id, run["current_room"], room_type, result_vi),
        )
        conn.execute("UPDATE dungeon_runs SET current_room = current_room + 1 WHERE run_id = ?", (run_id,))


def finish_dungeon_run(run_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE dungeon_runs SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE run_id = ?",
            (status, run_id),
        )


def list_dungeon_run_events(run_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM dungeon_run_events WHERE run_id = ? ORDER BY room_index ASC", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def link_combat_session_to_dungeon(session_id: int, run_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE combat_sessions SET dungeon_run_id = ? WHERE session_id = ?", (run_id, session_id)
        )


# =====================================================================
# 🌑 World Event (mục 47) — tác động THẬT lên cities (economy/crime/mystical)
# =====================================================================

def list_active_world_events():
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT we.*, c.name_en AS city_name FROM world_events we
               JOIN cities c ON c.city_id = we.city_id
               WHERE we.stage = 'active' ORDER BY we.started_at DESC""",
        ).fetchall()
        return [dict(r) for r in rows]


def trigger_world_event_transaction(event_key: str, name_vi: str, description_vi: str, city_id: str,
                                     economy_delta: int, crime_delta: int, mystical_delta: int) -> int:
    """Atomic: tạo World Event VÀ áp dụng thay đổi thật lên cities trong cùng
    transaction — đúng mục 47 ("phải tác động thật"), clamp về [0, 100]."""
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO world_events
               (event_key, name_vi, description_vi, city_id, economy_delta, crime_delta, mystical_delta)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_key, name_vi, description_vi, city_id, economy_delta, crime_delta, mystical_delta),
        )
        conn.execute(
            """UPDATE cities SET
                 economy = MAX(0, MIN(100, economy + ?)),
                 crime = MAX(0, MIN(100, crime + ?)),
                 mystical_activity = MAX(0, MIN(100, mystical_activity + ?))
               WHERE city_id = ?""",
            (economy_delta, crime_delta, mystical_delta, city_id),
        )
        conn.execute(
            "INSERT INTO world_history (category, summary_vi, ref_id) VALUES ('world_event', ?, ?)",
            (f"Sự kiện '{name_vi}' bùng phát tại {city_id}.", str(cur.lastrowid)),
        )
        return cur.lastrowid


def resolve_world_event_transaction(event_id: int):
    """Atomic: đóng Event và HOÀN TÁC đúng phần delta đã áp — World State
    quay lại đúng như trước khi Event xảy ra (trừ phần Player đã can thiệp
    thêm qua contribute_to_world_event, thứ không bị hoàn tác)."""
    with get_conn() as conn:
        event = conn.execute(
            "SELECT * FROM world_events WHERE event_id = ? AND stage = 'active'", (event_id,)
        ).fetchone()
        if event is None:
            return False
        conn.execute(
            """UPDATE cities SET
                 economy = MAX(0, MIN(100, economy - ?)),
                 crime = MAX(0, MIN(100, crime - ?)),
                 mystical_activity = MAX(0, MIN(100, mystical_activity - ?))
               WHERE city_id = ?""",
            (event["economy_delta"], event["crime_delta"], event["mystical_delta"], event["city_id"]),
        )
        conn.execute(
            "UPDATE world_events SET stage = 'resolved', resolved_at = CURRENT_TIMESTAMP WHERE event_id = ?",
            (event_id,),
        )
        conn.execute(
            "INSERT INTO world_history (category, summary_vi, ref_id) VALUES ('world_event', ?, ?)",
            (f"Sự kiện '{event['name_vi']}' đã được dẹp yên tại {event['city_id']}.", str(event_id)),
        )
        return True


def contribute_to_world_event(event_id: int, character_id: int, delta: int):
    """Player can thiệp vào Event (vd đóng góp dẹp loạn) — ghi nhận riêng,
    KHÔNG tự động resolve Event (Engine quyết định khi nào đủ điều kiện)."""
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO world_event_participants (event_id, character_id, contribution) VALUES (?, ?, ?)
               ON CONFLICT(event_id, character_id) DO UPDATE SET contribution = contribution + excluded.contribution""",
            (event_id, character_id, delta),
        )


def get_world_event(event_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM world_events WHERE event_id = ?", (event_id,)).fetchone()
        return dict(row) if row else None


# =============================================================================
# 🛡️ Guild (Player-created — mục 34 mở rộng, KHÁC Church/Faction cố định)
# =============================================================================

def get_guild(guild_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM guilds WHERE guild_id = ?", (guild_id,)).fetchone()
        return dict(row) if row else None


def get_guild_by_name(name: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM guilds WHERE name = ?", (name,)).fetchone()
        return dict(row) if row else None


def list_guilds():
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT g.*, COUNT(gm.character_id) AS member_count FROM guilds g
               LEFT JOIN guild_members gm ON gm.guild_id = g.guild_id
               GROUP BY g.guild_id ORDER BY g.treasury DESC"""
        ).fetchall()
        return [dict(r) for r in rows]


def get_character_guild(character_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT g.*, gm.rank, gm.joined_at FROM guild_members gm
               JOIN guilds g ON g.guild_id = gm.guild_id
               WHERE gm.character_id = ?""",
            (character_id,),
        ).fetchone()
        return dict(row) if row else None


def list_guild_members(guild_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT gm.*, c.name AS character_name FROM guild_members gm
               JOIN characters c ON c.character_id = gm.character_id
               WHERE gm.guild_id = ? ORDER BY
               CASE gm.rank WHEN 'leader' THEN 0 WHEN 'officer' THEN 1 ELSE 2 END, gm.joined_at""",
            (guild_id,),
        ).fetchall()
        return [dict(r) for r in rows]


GUILD_FOUNDING_COST = 5000


def create_guild_transaction(character_id: int, name: str, description_vi: str):
    """Atomic (mục 38): CHECK chưa có Guild + đủ tiền + tên chưa trùng ->
    REMOVE tiền founding cost -> tạo Guild -> thêm leader vào guild_members."""
    with get_conn() as conn:
        existing_member = conn.execute(
            "SELECT 1 FROM guild_members WHERE character_id = ?", (character_id,)
        ).fetchone()
        if existing_member is not None:
            return None
        name_taken = conn.execute("SELECT 1 FROM guilds WHERE name = ?", (name,)).fetchone()
        if name_taken is not None:
            return None
        character = conn.execute(
            "SELECT money FROM characters WHERE character_id = ?", (character_id,)
        ).fetchone()
        if character is None or character["money"] < GUILD_FOUNDING_COST:
            return None
        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?",
            (GUILD_FOUNDING_COST, character_id),
        )
        cur = conn.execute(
            "INSERT INTO guilds (name, leader_character_id, description_vi) VALUES (?, ?, ?)",
            (name, character_id, description_vi),
        )
        guild_id = cur.lastrowid
        conn.execute(
            "INSERT INTO guild_members (character_id, guild_id, rank) VALUES (?, ?, 'leader')",
            (character_id, guild_id),
        )
        conn.execute(
            "INSERT INTO world_history (category, summary_vi, ref_id) VALUES ('guild', ?, ?)",
            (f"Guild '{name}' được thành lập.", str(guild_id)),
        )
        return guild_id


def disband_guild_transaction(character_id: int) -> bool:
    with get_conn() as conn:
        guild = conn.execute(
            "SELECT * FROM guilds WHERE leader_character_id = ?", (character_id,)
        ).fetchone()
        if guild is None:
            return False
        conn.execute("DELETE FROM guild_members WHERE guild_id = ?", (guild["guild_id"],))
        conn.execute("DELETE FROM guilds WHERE guild_id = ?", (guild["guild_id"],))
        conn.execute(
            "INSERT INTO world_history (category, summary_vi, ref_id) VALUES ('guild', ?, ?)",
            (f"Guild '{guild['name']}' đã giải tán.", str(guild["guild_id"])),
        )
        return True


def recruit_guild_member_transaction(inviter_character_id: int, target_character_id: int) -> str:
    """Trả về mã lỗi rỗng '' nếu thành công, ngược lại trả về lý do."""
    with get_conn() as conn:
        inviter = conn.execute(
            "SELECT * FROM guild_members WHERE character_id = ?", (inviter_character_id,)
        ).fetchone()
        if inviter is None or inviter["rank"] not in ("leader", "officer"):
            return "no_permission"
        target_has_guild = conn.execute(
            "SELECT 1 FROM guild_members WHERE character_id = ?", (target_character_id,)
        ).fetchone()
        if target_has_guild is not None:
            return "already_in_guild"
        conn.execute(
            "INSERT INTO guild_members (character_id, guild_id, rank) VALUES (?, ?, 'member')",
            (target_character_id, inviter["guild_id"]),
        )
        return ""


def leave_guild_transaction(character_id: int) -> bool:
    with get_conn() as conn:
        member = conn.execute(
            "SELECT * FROM guild_members WHERE character_id = ?", (character_id,)
        ).fetchone()
        if member is None:
            return False
        if member["rank"] == "leader":
            other_count = conn.execute(
                "SELECT COUNT(*) AS c FROM guild_members WHERE guild_id = ? AND character_id != ?",
                (member["guild_id"], character_id),
            ).fetchone()["c"]
            if other_count > 0:
                return False  # leader phải chuyển giao hoặc kick hết member trước khi rời
        conn.execute("DELETE FROM guild_members WHERE character_id = ?", (character_id,))
        if member["rank"] == "leader":
            conn.execute("DELETE FROM guilds WHERE guild_id = ?", (member["guild_id"],))
        return True


def kick_guild_member_transaction(kicker_character_id: int, target_character_id: int) -> bool:
    with get_conn() as conn:
        kicker = conn.execute(
            "SELECT * FROM guild_members WHERE character_id = ?", (kicker_character_id,)
        ).fetchone()
        target = conn.execute(
            "SELECT * FROM guild_members WHERE character_id = ?", (target_character_id,)
        ).fetchone()
        if kicker is None or target is None or kicker["guild_id"] != target["guild_id"]:
            return False
        if kicker["rank"] not in ("leader", "officer") or target["rank"] == "leader":
            return False
        conn.execute("DELETE FROM guild_members WHERE character_id = ?", (target_character_id,))
        return True


def deposit_guild_treasury_transaction(character_id: int, amount: int) -> bool:
    with get_conn() as conn:
        member = conn.execute(
            "SELECT * FROM guild_members WHERE character_id = ?", (character_id,)
        ).fetchone()
        if member is None:
            return False
        character = conn.execute(
            "SELECT money FROM characters WHERE character_id = ?", (character_id,)
        ).fetchone()
        if character is None or character["money"] < amount:
            return False
        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?", (amount, character_id)
        )
        conn.execute(
            "UPDATE guilds SET treasury = treasury + ? WHERE guild_id = ?", (amount, member["guild_id"])
        )
        conn.execute(
            "INSERT INTO guild_bank_log (guild_id, character_id, kind, amount) VALUES (?, ?, 'deposit', ?)",
            (member["guild_id"], character_id, amount),
        )
        return True


def withdraw_guild_treasury_transaction(character_id: int, amount: int) -> bool:
    with get_conn() as conn:
        member = conn.execute(
            "SELECT * FROM guild_members WHERE character_id = ?", (character_id,)
        ).fetchone()
        if member is None or member["rank"] not in ("leader", "officer"):
            return False
        guild = conn.execute(
            "SELECT treasury FROM guilds WHERE guild_id = ?", (member["guild_id"],)
        ).fetchone()
        if guild is None or guild["treasury"] < amount:
            return False
        conn.execute(
            "UPDATE guilds SET treasury = treasury - ? WHERE guild_id = ?", (amount, member["guild_id"])
        )
        conn.execute(
            "UPDATE characters SET money = money + ? WHERE character_id = ?", (amount, character_id)
        )
        conn.execute(
            "INSERT INTO guild_bank_log (guild_id, character_id, kind, amount) VALUES (?, ?, 'withdraw', ?)",
            (member["guild_id"], character_id, amount),
        )
        return True


def get_active_guild_war(guild_id: int):
    with get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM guild_wars WHERE status = 'active'
               AND (attacker_guild_id = ? OR defender_guild_id = ?)""",
            (guild_id, guild_id),
        ).fetchone()
        return dict(row) if row else None


def declare_guild_war_transaction(attacker_character_id: int, defender_guild_id: int):
    with get_conn() as conn:
        attacker_member = conn.execute(
            "SELECT * FROM guild_members WHERE character_id = ?", (attacker_character_id,)
        ).fetchone()
        if attacker_member is None or attacker_member["rank"] != "leader":
            return None
        attacker_guild_id = attacker_member["guild_id"]
        if attacker_guild_id == defender_guild_id:
            return None
        already_active = conn.execute(
            """SELECT 1 FROM guild_wars WHERE status = 'active' AND
               (attacker_guild_id IN (?, ?) OR defender_guild_id IN (?, ?))""",
            (attacker_guild_id, defender_guild_id, attacker_guild_id, defender_guild_id),
        ).fetchone()
        if already_active is not None:
            return None
        cur = conn.execute(
            "INSERT INTO guild_wars (attacker_guild_id, defender_guild_id) VALUES (?, ?)",
            (attacker_guild_id, defender_guild_id),
        )
        atk = conn.execute("SELECT name FROM guilds WHERE guild_id = ?", (attacker_guild_id,)).fetchone()
        dfd = conn.execute("SELECT name FROM guilds WHERE guild_id = ?", (defender_guild_id,)).fetchone()
        conn.execute(
            "INSERT INTO world_history (category, summary_vi, ref_id) VALUES ('guild_war', ?, ?)",
            (f"Guild '{atk['name']}' tuyên chiến với Guild '{dfd['name']}'.", str(cur.lastrowid)),
        )
        return cur.lastrowid


def guild_war_contribute_transaction(character_id: int, war_id: int, points: int = 1):
    """Thắng PvP nhắm vào member Guild địch sẽ gọi hàm này (hook trong pvp.py).
    Trả về dict {resolved, winner_guild_id} — tự động Resolve khi 1 bên đạt
    win_threshold, KHÔNG cần scheduler riêng."""
    with get_conn() as conn:
        member = conn.execute(
            "SELECT * FROM guild_members WHERE character_id = ?", (character_id,)
        ).fetchone()
        if member is None:
            return None
        war = conn.execute(
            "SELECT * FROM guild_wars WHERE war_id = ? AND status = 'active'", (war_id,)
        ).fetchone()
        if war is None:
            return None
        if member["guild_id"] == war["attacker_guild_id"]:
            conn.execute(
                "UPDATE guild_wars SET attacker_score = attacker_score + ? WHERE war_id = ?",
                (points, war_id),
            )
        elif member["guild_id"] == war["defender_guild_id"]:
            conn.execute(
                "UPDATE guild_wars SET defender_score = defender_score + ? WHERE war_id = ?",
                (points, war_id),
            )
        else:
            return None
        war = conn.execute("SELECT * FROM guild_wars WHERE war_id = ?", (war_id,)).fetchone()
        resolved = False
        winner_guild_id = None
        if war["attacker_score"] >= war["win_threshold"]:
            resolved, winner_guild_id = True, war["attacker_guild_id"]
        elif war["defender_score"] >= war["win_threshold"]:
            resolved, winner_guild_id = True, war["defender_guild_id"]
        if resolved:
            status = "attacker_won" if winner_guild_id == war["attacker_guild_id"] else "defender_won"
            conn.execute(
                "UPDATE guild_wars SET status = ?, ended_at = CURRENT_TIMESTAMP WHERE war_id = ?",
                (status, war_id),
            )
            winner = conn.execute("SELECT name FROM guilds WHERE guild_id = ?", (winner_guild_id,)).fetchone()
            conn.execute(
                "INSERT INTO world_history (category, summary_vi, ref_id) VALUES ('guild_war', ?, ?)",
                (f"Guild '{winner['name']}' đã thắng cuộc chiến Guild War.", str(war_id)),
            )
        return {
            "attacker_score": war["attacker_score"],
            "defender_score": war["defender_score"],
            "resolved": resolved,
            "winner_guild_id": winner_guild_id,
        }


# =============================================================================
# 🌍 World State / World History (mục 31, 47-48)
# =============================================================================

def get_world_state(key: str, default: str = None):
    with get_conn() as conn:
        row = conn.execute("SELECT state_value FROM world_state WHERE state_key = ?", (key,)).fetchone()
        return row["state_value"] if row else default


def set_world_state(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO world_state (state_key, state_value, updated_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(state_key) DO UPDATE SET state_value = excluded.state_value,
               updated_at = CURRENT_TIMESTAMP""",
            (key, str(value)),
        )


def get_all_world_state():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM world_state ORDER BY state_key").fetchall()
        return {r["state_key"]: r["state_value"] for r in rows}


def log_world_history(category: str, summary_vi: str, ref_id: str = None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO world_history (category, summary_vi, ref_id) VALUES (?, ?, ?)",
            (category, summary_vi, ref_id),
        )


def list_world_history(limit: int = 15):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM world_history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# =============================================================================
# 🔨 Auction (mục 41) — bidding thật, khác market_listings (giá cố định)
# =============================================================================

AUCTION_MIN_INCREMENT = 5  # % giá hiện tại — chống spam ra giá +1 Bảng


def create_auction_transaction(seller_character_id: int, item_id: str, quantity: int,
                                starting_price: int, duration_hours: int):
    """Atomic: CHECK tồn kho -> REMOVE khỏi Inventory (khoá vào phiên đấu giá)
    -> tạo auctions row với ends_at thật."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE character_id = ? AND item_id = ?",
            (seller_character_id, item_id),
        ).fetchone()
        have = row["quantity"] if row else 0
        if have < quantity:
            return None
        conn.execute(
            "UPDATE inventory SET quantity = quantity - ? WHERE character_id = ? AND item_id = ?",
            (quantity, seller_character_id, item_id),
        )
        conn.execute("DELETE FROM inventory WHERE character_id = ? AND quantity <= 0", (seller_character_id,))
        cur = conn.execute(
            """INSERT INTO auctions
               (seller_character_id, item_id, quantity, starting_price, current_price, ends_at)
               VALUES (?, ?, ?, ?, ?, datetime(CURRENT_TIMESTAMP, ? || ' hours'))""",
            (seller_character_id, item_id, quantity, starting_price, starting_price, duration_hours),
        )
        return cur.lastrowid


def _settle_expired_auctions(conn):
    """Chốt LAZY mọi phiên đã hết hạn (mục 41) — không cần scheduler riêng,
    gọi mỗi khi có người xem/thao tác danh sách đấu giá."""
    expired = conn.execute(
        "SELECT * FROM auctions WHERE status = 'active' AND ends_at <= CURRENT_TIMESTAMP"
    ).fetchall()
    for a in expired:
        if a["highest_bidder_character_id"] is None:
            conn.execute(
                """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?)
                   ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
                (a["seller_character_id"], a["item_id"], a["quantity"]),
            )
            conn.execute("UPDATE auctions SET status = 'expired' WHERE auction_id = ?", (a["auction_id"],))
        else:
            conn.execute(
                """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?)
                   ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
                (a["highest_bidder_character_id"], a["item_id"], a["quantity"]),
            )
            conn.execute(
                "UPDATE characters SET money = money + ? WHERE character_id = ?",
                (a["current_price"], a["seller_character_id"]),
            )
            conn.execute("UPDATE auctions SET status = 'sold' WHERE auction_id = ?", (a["auction_id"],))
            conn.execute(
                """INSERT INTO trade_history (kind, from_character_id, to_character_id, item_id, quantity, money_amount)
                   VALUES ('auction_sold', ?, ?, ?, ?, ?)""",
                (a["seller_character_id"], a["highest_bidder_character_id"], a["item_id"],
                 a["quantity"], a["current_price"]),
            )


def list_active_auctions(limit: int = 15):
    with get_conn() as conn:
        _settle_expired_auctions(conn)
        rows = conn.execute(
            """SELECT au.*, i.name_en, i.name_vi, c.name AS seller_name FROM auctions au
               JOIN items i ON i.item_id = au.item_id
               JOIN characters c ON c.character_id = au.seller_character_id
               WHERE au.status = 'active' ORDER BY au.ends_at ASC LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_auction(auction_id: int):
    with get_conn() as conn:
        _settle_expired_auctions(conn)
        row = conn.execute("SELECT * FROM auctions WHERE auction_id = ?", (auction_id,)).fetchone()
        return dict(row) if row else None


def place_bid_transaction(auction_id: int, character_id: int, amount: int) -> str:
    """Trả về '' nếu thành công, ngược lại mã lỗi. Escrow thật: trừ tiền
    người ra giá mới NGAY, hoàn tiền người giữ giá cao nhất trước đó NGAY
    trong cùng transaction (mục 15/51: hiệu lực thật, không chỉ hiển thị)."""
    with get_conn() as conn:
        _settle_expired_auctions(conn)
        auction = conn.execute(
            "SELECT * FROM auctions WHERE auction_id = ? AND status = 'active'", (auction_id,)
        ).fetchone()
        if auction is None:
            return "not_found"
        if auction["seller_character_id"] == character_id:
            return "own_auction"
        min_required = auction["current_price"]
        if auction["highest_bidder_character_id"] is not None:
            min_required = auction["current_price"] + max(
                1, auction["current_price"] * AUCTION_MIN_INCREMENT // 100
            )
        if amount < min_required:
            return "bid_too_low"
        bidder = conn.execute(
            "SELECT money FROM characters WHERE character_id = ?", (character_id,)
        ).fetchone()
        if bidder is None or bidder["money"] < amount:
            return "not_enough_money"
        conn.execute(
            "UPDATE characters SET money = money - ? WHERE character_id = ?", (amount, character_id)
        )
        if auction["highest_bidder_character_id"] is not None:
            conn.execute(
                "UPDATE characters SET money = money + ? WHERE character_id = ?",
                (auction["current_price"], auction["highest_bidder_character_id"]),
            )
        conn.execute(
            "UPDATE auctions SET current_price = ?, highest_bidder_character_id = ? WHERE auction_id = ?",
            (amount, character_id, auction_id),
        )
        conn.execute(
            "INSERT INTO auction_bids (auction_id, character_id, amount) VALUES (?, ?, ?)",
            (auction_id, character_id, amount),
        )
        return ""


def cancel_auction_transaction(seller_character_id: int, auction_id: int) -> bool:
    """Chỉ huỷ được khi CHƯA có ai ra giá — có bid rồi thì phải chờ chốt
    phiên bình thường (tránh việc rút hàng sau khi đã escrow tiền người mua)."""
    with get_conn() as conn:
        auction = conn.execute(
            "SELECT * FROM auctions WHERE auction_id = ? AND seller_character_id = ? AND status = 'active'",
            (auction_id, seller_character_id),
        ).fetchone()
        if auction is None or auction["highest_bidder_character_id"] is not None:
            return False
        conn.execute(
            """INSERT INTO inventory (character_id, item_id, quantity) VALUES (?, ?, ?)
               ON CONFLICT(character_id, item_id) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (seller_character_id, auction["item_id"], auction["quantity"]),
        )
        conn.execute("UPDATE auctions SET status = 'cancelled' WHERE auction_id = ?", (auction_id,))
        return True


# =====================================================================
# 🕯️ Black Market (mục 41)
# =====================================================================

def list_black_market_catalog():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM black_market_listings ORDER BY category, price"
        ).fetchall()
        return [dict(r) for r in rows]


def get_black_market_listing(listing_id: str):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM black_market_listings WHERE listing_id = ?", (listing_id,)
        ).fetchone()
        return dict(row) if row else None


def log_black_market_purchase(character_id: int, listing_id: str, outcome: str, money_spent: int):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO black_market_purchase_log (character_id, listing_id, outcome, money_spent)
               VALUES (?, ?, ?, ?)""",
            (character_id, listing_id, outcome, money_spent),
        )


def list_black_market_history(character_id: int, limit: int = 20):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM black_market_purchase_log WHERE character_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (character_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def charge_black_market_price(character_id: int, price: int) -> bool:
    """Bước CHECK+REMOVE atomic đầu tiên của giao dịch Chợ đen (mục 38: atomic
    transaction). Việc ADD item / áp Trap / tạo Bounty được quyết định ở
    black_market.py SAU khi biết kết quả roll rủi ro — nhưng tiền luôn bị trừ
    trước, đúng bản chất \"đã trả tiền chợ đen thì không đòi lại được\"."""
    with get_conn() as conn:
        row = conn.execute("SELECT money FROM characters WHERE character_id = ?", (character_id,)).fetchone()
        if row is None or row["money"] < price:
            return False
        conn.execute("UPDATE characters SET money = money - ? WHERE character_id = ?", (price, character_id))
        return True


# =====================================================================
# ☠️ Loss of Control — Risk Engine inputs (mục 13 mở rộng)
# =====================================================================

def get_risk_inputs(character_id: int):
    """Gom mọi số liệu thật cần để loss_of_control.compute_risk() tính Risk
    đa yếu tố — không còn dựa vào một con số tĩnh duy nhất."""
    character = get_character_by_id(character_id)
    if character is None:
        return None

    progress = get_progress(character_id)
    potion_stability = None
    if progress["status"] == "digesting" and progress["potion_target_sequence"] is not None and character["pathway_id"]:
        potion = get_potion(character["pathway_id"], progress["potion_target_sequence"])
        if potion:
            potion_stability = potion["stability"]

    characteristics = list_character_characteristics(character_id)
    stored_stabilities = [c["stability"] for c in characteristics if c["state"] == "stored"]

    return {
        "character": character,
        "digestion_status": progress["status"],
        "potion_stability": potion_stability,
        "characteristic_stabilities": stored_stabilities,
    }


def update_character_risk(character_id: int, risk: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE characters SET loss_of_control_risk = ? WHERE character_id = ?",
            (max(0, min(100, risk)), character_id),
        )


def adjust_mental_state(character_id: int, delta: int) -> int:
    """Cộng/trừ Mental State, kẹp trong [0, 100]. Trả về giá trị mới thật đã lưu."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT mental_state FROM characters WHERE character_id = ?", (character_id,)
        ).fetchone()
        if row is None:
            return 0
        new_value = max(0, min(100, row["mental_state"] + delta))
        conn.execute(
            "UPDATE characters SET mental_state = ? WHERE character_id = ?",
            (new_value, character_id),
        )
        return new_value


def interrupt_digestion(character_id: int, digestion_loss_pct: int):
    """Sự cố mất kiểm soát nặng làm gián đoạn tiêu hoá Potion đang dở (mục 13:
    Loss of Control có thể gây Interruption cho tiến trình Advancement)."""
    progress = get_progress(character_id)
    if progress["status"] != "digesting":
        return
    new_digestion = max(0, round(progress["digestion"] * (1 - digestion_loss_pct / 100)))
    upsert_progress(character_id, progress["potion_target_sequence"], new_digestion, "digesting")

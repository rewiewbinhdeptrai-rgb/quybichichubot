# Quỷ Bí ("Mystery") — Discord Bot (Skeleton)

> This is an English translation of `README.md`. The Vietnamese file is the
> source of truth for this project — if the two ever disagree, `README.md`
> wins. Spec references like "item 12" below correspond to sections of the
> internal MASTER SPECIFICATION document (items 0–68), which is not included
> in this repo.

Python skeleton bot (discord.py) + SQLite, built against the internal MASTER
SPECIFICATION (items 0–68). This is the **architecture skeleton + layered
`/menu` UI + base DB schema**, not a full implementation of every system
(Combat, Economy, NPC AI, ...).

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in your bot's DISCORD_TOKEN
python bot.py
```

If you set `DEV_GUILD_ID` in `.env`, slash commands sync instantly for that
one server (useful for testing). Leave it blank to sync globally (can take
up to ~1h for Discord to show the commands).

## What's implemented

- `/menu` — main menu (items 52–53): shows the character profile + a dropdown
  to pick a system.
- **🧬 Pathway** (items 54–56):
  - Choose a Pathway (22 Pathways, data in `data/pathways_seed.py`) — if the
    character has no Pathway yet, a **"Take this Pathway (Sequence 9)"**
    button appears.
  - Choose Sequence 9→0 — Sequences not yet reached show 🔒 and **cannot be
    bypassed** for advancement (selecting one just shows a notice, it does
    not set the Sequence).
  - The character's CURRENT Sequence shows a **real Digestion %** read from
    the Engine (no longer a "no data" placeholder).
- **🎒 Assets → 🧪 Potion** — full flow per items 9–12, reads/writes the real
  DB:
  - **Drinking a Potion** → starts a digesting process, applies a real
    `potion_instability` debuff (raises measurable Loss of Control Risk).
  - **Acting Method** — action set per Pathway (`data/acting_actions.py`,
    Seer has 4 sample actions: Divination/Observation/Deception/Evasion) →
    adds real Digestion %, actions that don't fit the Pathway are rejected.
  - **Advancement Ritual** — only runnable at Digestion = 100%; has a 15%
    chance of failure causing a real **Backlash** (reduces Digestion + applies
    the `ritual_backlash` debuff) instead of always succeeding unconditionally
    (item 20).
  - Success genuinely **UPDATEs `characters.sequence_number`** in the DB —
    there's no way to set it directly from the UI.
- **Central EffectEngine** (`effects.py`, items 15–16): buffs/debuffs with a
  `modifier_key` (e.g. `physical_damage_pct`, `damage_taken_pct`,
  `loss_of_control_risk_flat`) are genuinely summed via `get_modifier_sum()`
  — no buff exists only as embed text. `calculate_damage()` and
  `calculate_incoming_damage()` are actually used by the Combat Engine.
- **🎒 Assets → 🎒 Bag / ⚔️ Equipment** (`inventory.py`, items 22, 59):
  - **Bag** — lists real items (quantity, description); using a Consumable
    (Healing Draught/Spirit Incense) heals the correct HP/Spirituality and
    deducts exactly 1 item from the bag.
  - **Equipment** — Equip/Unequip Weapon and Armor have **no separate stat
    system**: every equip applies an Effect straight into the EffectEngine
    (`source="equip:<slot>"`, effectively permanent) — reusing the exact same
    `effects.get_modifier_sum()` that Combat already uses, per item 16's
    principle of "one shared Effect Engine for every system." Unequip removes
    exactly that source's effect, without touching other buffs/debuffs.
  - Monsters now **actually drop loot** on PvE wins (`drop_item_id`/
    `drop_chance` in `data/monsters_seed.py`) — not fake loot.
- **⚔️ Combat → 👹 PvE** (`combat.py`, items 23–27) — real turn-based battles
  stored in the `combat_sessions` table:
  - **Attack** — damage computed via `effects.calculate_damage()`, the
    Monster counters immediately in the same turn.
  - **Use Ability** — only shows Abilities unlocked at the current Sequence
    (item 17), deducts the correct Spirituality, damage scaled by
    `damage_multiplier`.
  - **Defend** — applies the `defending` buff (-30% incoming damage) with
    **real effect** on the counter-attack that same turn, not just flavor
    text.
  - **Flee** — 50% success; on failure the Monster gets a free hit.
  - Win/loss both go through `db.apply_combat_result()` — one transaction
    that syncs HP + Money + EXP (items 49–50). Losing: HP drops to 1, lose
    10% of money (item 13 — a "severe" consequence, not permadeath).
  - 3 sample Monsters in `data/monsters_seed.py`; 10 sample Abilities for
    Seer (one per Sequence) in `data/abilities_seed.py`.
  - New characters start with 1 Healing Draught (real data in `inventory`,
    not a fake display).
- **⚔️ Combat → 🏟️ PvP** (`pvp.py`, item 24) — opponents are real Characters,
  turn-based and **alternating** (not same-turn auto-counter like PvE):
  - Challenge via `UserSelect` (pick a Discord member directly) — self-
    challenge is blocked, as is challenging while already in another
    match or with an unanswered invite pending, or when either side is at
    0 HP.
  - Accept/Decline — accepting locks in both sides' current HP (not a full
    heal) as the starting point and randomizes who goes first (decided by
    the Engine, not the UI); clears old buffs/debuffs before the match.
  - Every action **checks whose turn it is** (`turn_character_id`) before
    allowing it — acting out of turn is blocked with `PvPError`, never a
    silent no-op.
  - Attack/Ability reuse the exact same `effects.calculate_damage()` +
    `effects.calculate_incoming_damage()` from the Combat Engine — buffs/
    debuffs (e.g. Defend) have real effect between two real players, not
    just embed text.
  - Win/loss/flee all go through `db.apply_pvp_result()` — one transaction
    that transfers the **real wager** (default 500 Bảng) from the loser to
    the winner + syncs HP (items 49-50). Loss/flee: HP drops to 1, not
    permadeath (item 13).
  - Fleeing in PvP is always scored as an immediate loss (unlike PvE's 50%
    flee chance), because the opponent is a real person — a match can't be
    left "hanging."
- **👤 Character**, **⚙️ Settings → Language** (vi/en, stored in the `users`
  table).
- **🧿 Beyonder Characteristic** (`characteristics.py`, item 21) — real, no
  longer an empty table:
  - A **successful** Advancement Ritual (`progression.perform_advancement`)
    automatically grants 1 Characteristic permanently tied to the exact
    `(pathway_id, sequence_number)` just reached — not random loot, not
    generated by the runtime AI.
  - `UNIQUE(character_id, pathway_id, sequence_number)` + `INSERT OR IGNORE`
    blocks duplicates if the Advancement Engine happens to be called again
    (idempotent).
  - View under **👤 Character → Beyonder Characteristic**: lists ownership,
    `stored`/`consumed` state, Stability, origin.
  - **Consumption** already has a real Engine effect: +5 max Spirituality
    permanently via `db.set_character_spirituality_max()` (item 15 — not just
    flipping a flag in the DB), blocks consuming twice / consuming a
    Characteristic that isn't yours.
  - **Not yet done**: Transfer to another Character (needs the Trade Engine
    from item 38 to be atomic first — see the docstring at the top of
    `characteristics.py`).
- **📜 Ritual** (`ritual.py`, item 20) — the Advancement Ritual is no longer a
  fixed 85% roll:
  - Success chance = `potion.stability` (item 9) + bonus from owned Beyonder
    Characteristics (item 21) − current Loss of Control Risk (item 13),
    clamped to 5–95% — never a guaranteed success or guaranteed failure.
  - **Materials** (`ritual_materials` table, kept separate from the Potion
    Recipe) are deducted atomically via
    `db.consume_ritual_materials_transaction()`: missing any material means
    NOTHING is deducted (all-or-nothing); if you have enough, everything is
    deducted regardless of the outcome afterward.
  - 3 real outcomes (item 20: Ritual Result), not just success/fail:
    `success` (raises Sequence + grants a Characteristic), `interruption`
    (loses materials, Digestion unchanged, can retry immediately),
    `backlash` (loses materials + Digestion -30 + `ritual_backlash` debuff).
  - Every attempt is logged to `ritual_history` (roll, chance, outcome) —
    item 20 requires the Result to be persisted, not just shown in an Embed
    and lost.
  - **Not yet done**: Location/Time/Participants (group Rituals) — needs the
    Party Engine (item 36) first.
- **🕯️ Sealed Artifact** (`artifacts.py`, item 22) — real, no longer an empty
  table:
  - Every Character starts with 1 `unlabeled_glass_vial` (Unknown grade) via
    `database.create_character`.
  - **Inspect** — free, unlimited calls, each call unlocks exactly 1 of the 3
    stages in a fixed order `effect → rule → side_effect`
    (`artifact_rules` table), matching item 22's flow "Unknown → Inspect →
    ... → Discover Rule".
  - **Experiment** — deducts exactly 1 use from `uses_remaining` (drawn from
    the static `usage_limit`), applies a **real Effect** via the
    EffectEngine (`effects.apply_effect`), rolls `risk_stars × chance%` to
    trigger a Side Effect (also a real Effect, not just text), and unlocks
    all 3 stages at once (direct experience = learning how it works
    firsthand). Once `uses_remaining` hits 0, `ArtifactError` blocks further
    Experiments.
  - 4 demo Artifacts each with their own Effect/Side Effect
    (`data/artifacts_seed.py`) — **not yet a full lore-accurate Artifact
    catalog**, but the flow genuinely runs.
  - **Not yet done**: Acquisition beyond the starter item (loot from
    Monsters/World), Transfer to another Character (needs the Trade Engine
    from item 38).
- **🔮 Mysticism → Knowledge** (`mysticism.py`, item 18) — real:
  - Mandatory flow `Unknown → Discovered → Studied → Understood`
    (`character_knowledge`; no row means implicitly Unknown).
  - Each step deducts real Spirituality via
    `db.set_character_hp_spirituality()` (insufficient Spirituality is
    blocked by `MysticismError`, no bypassing the order — Study before
    Discover is blocked).
  - **Understand** has a real Risk % (`understand_risk`) that can trigger the
    `mysticism_overreach` debuff via the EffectEngine (items 13, 18: probing
    Mysticism too deeply is a real source of Loss of Control Risk).
  - Some Knowledge (`mystic_stabilization_technique`) applies a **permanent**
    buff (`mystic_insight`, extremely long duration) via the EffectEngine
    once Understood — a real effect (item 15), not just a flag flip in the
    DB.
  - **Not yet done**: an Investigation Engine (item 27) so Discovery happens
    through clues instead of directly spending Spirituality.
- **🔮 Mysticism → Divination** (`divination.py`, item 19) — real:
  - 5 of the 8 methods in the spec have a working Engine: Tarot, Crystal
    Ball, Astrology, Dream, Spiritual Perception (`data/divination_seed.py`).
  - Results are **rolled by the Engine first** (`accuracy = base_accuracy −
    loss_of_control_risk`, roll 1-100 → tier `clear/vague/failed/ominous`) —
    per items 19/30: the AI (if wired in later) may only rephrase the
    result, never decide the tier itself.
  - The `ominous` tier triggers a real `divination_backlash` debuff
    (item 13).
  - Every Divination is logged to `divination_history` (roll, accuracy,
    tier).
  - **Not yet done**: Item/Location/Person Divination (reading a specific
    target) — needs the World/NPC Engine (items 27–28) to exist first so
    there's a real target.
- The remaining groups (Ability, World, Faction, Trade, House) still just
  show a "🚧 not yet implemented" placeholder — **per item 58's principle: no
  fake data**.
- Character creation via a Modal (item 57) when the user has no Character
  yet.

## Database (`database.py`)

SQLite, tables: `users`, `pathways`, `sequences`, `characters`, `potions`,
`character_progress`, `effect_definitions`, `character_effects`,
`action_log`, `monsters`, `abilities`, `combat_sessions`, `items`,
`inventory`, `character_equipment`, `pvp_sessions`,
`character_characteristics`, `ritual_materials`, `ritual_history`,
`artifacts`, `artifact_rules`, `character_artifacts`, `artifact_history`,
`knowledge_definitions`, `character_knowledge`, `divination_methods`,
`divination_history`.
Still a reduced version of the full schema in item 48 — new tables
(`dungeons`, `market`, `npcs`, ...) extend it following the same pattern:
every piece of state goes through a function in `database.py`/`effects.py`/
`progression.py`/`combat.py`/`inventory.py`/`characteristics.py`/`ritual.py`/
`artifacts.py`/`mysticism.py`/`divination.py`; the UI (`cogs/menu.py`) never
computes game numbers itself (items 1, 15, 51).

## Structure

```
quyby-bot/
├── bot.py                    # entry point, syncs slash commands
├── config.py                  # env config + unified icon set (item 54)
├── database.py                 # schema + access layer, source of truth (item 48)
├── effects.py                  # central EffectEngine (items 15-16)
├── progression.py              # Potion/Acting/Digestion/Advancement (items 9-12)
├── combat.py                   # PvE Combat Engine (items 23-27)
├── pvp.py                      # PvP Engine — alternating turns between 2 Characters (item 24)
├── inventory.py                # Item/Equipment engine (items 22, 59)
├── ritual.py                    # Ritual Engine — real success chance (item 20)
├── characteristics.py           # Beyonder Characteristic engine (item 21)
├── artifacts.py                  # Sealed Artifact engine — Inspect/Experiment (item 22)
├── mysticism.py                  # Mysticism Knowledge engine (item 18)
├── divination.py                 # Divination engine (item 19)
├── data/
│   ├── pathways_seed.py       # static data for the 22 Pathways (items 6, 55, 67)
│   ├── effects_seed.py        # buff/debuff definitions (item 15)
│   ├── acting_actions.py      # Acting Method actions per Pathway (item 10)
│   ├── monsters_seed.py       # PvE Monsters + drop rate (item 25)
│   ├── abilities_seed.py      # Abilities per Sequence (item 17)
│   ├── items_seed.py          # static Item/Equipment data (items 22, 59)
│   ├── potion_recipes_seed.py # Potion recipes (item 9)
│   ├── ritual_materials_seed.py # Ritual materials (item 20)
│   ├── artifacts_seed.py      # static Sealed Artifacts + their Effects (item 22)
│   ├── knowledge_seed.py      # static Mysticism Knowledge (item 18)
│   └── divination_seed.py     # static Divination Methods (item 19)
└── cogs/
    └── menu.py                 # the entire layered `/menu` UI (items 52-65)
```

## Self-tested (no Discord token required)

`effects.py`, `progression.py`, `combat.py`, `inventory.py` have been run
directly through `python3 -c "..."` and confirmed with real numbers:
- Buffs/debuffs correctly sum % damage and % risk.
- Full loop of Drink Potion → Acting Method → Digestion 100% → Ritual →
  `sequence_number` genuinely changes in SQLite.
- Combat: Ability deducts the correct Spirituality, Defend reduces the
  counter-attack's incoming damage by the correct % (6 → 4 damage, matching
  the -30% formula), winning correctly adds money/EXP, losing correctly
  deducts 10% money + HP drops to 1, Flee succeeds 50% of the time.
- Inventory: using a Consumable heals the correct HP and deducts the correct
  item; equipping Weapon + Armor together correctly adds/reduces % via the
  EffectEngine (100→110 dmg, 20→18 incoming dmg); unequipping correctly
  restores the original numbers; Monsters genuinely drop loot on wins.
- PvP: duplicate challenges are blocked, acting out of turn is blocked by
  `PvPError` (`turn_character_id` correctly checked), turns alternate
  correctly across multiple rounds, winning correctly adds 500 Bảng taken
  from the loser (two-way transaction via `apply_pvp_result`), losing drops
  HP to 1 — tested through 13 real rounds until one side hits 0 HP, final
  money/HP figures match the formula.
- Sealed Artifact: 3 consecutive Inspects unlock exactly the 3 stages in the
  fixed order, the 4th Inspect returns `stage=None`; Experiment correctly
  deducts `uses_remaining` (4→3→...→0), the 5th call is correctly blocked by
  `ArtifactError` ("out of uses"); the applied Effect is observable in
  `character_effects`.
- Mysticism Knowledge: Study is blocked if called before Discover
  (`MysticismError`); the full Discover→Study→Understand flow deducts the
  correct Spirituality at each step (100→70 for `ritual_symbols_101`);
  Knowledge with an `unlock_effect_id` (`mystic_stabilization_technique`)
  correctly applies the permanent `mystic_insight` buff once Understood.
- Divination: a nonexistent method is correctly blocked; insufficient
  Spirituality is correctly blocked (test forced Spirituality down to 2,
  Spiritual Perception needs 20); a real roll returns a valid tier + deducts
  the correct Spirituality.
- World/Location (items 31–32, `world.py`): new Characters always have a real
  `location_id` from creation (never NULL, no separate backfill needed);
  moving within the same city is free, moving to the same location is
  blocked by `WorldError` ("You are already here"); moving to a different
  city is correctly blocked when funds are insufficient, and correctly
  deducts `travel_cost` when there's enough (test: 0 → blocked at 250 Bảng →
  topped up to 1000 → deducted down to 750); each move logs exactly 1 row in
  `travel_log`. The **migration** path was tested separately: an old-style
  simulated DB (`characters` table missing the `location_id` column) then
  calling `init_db()` — the column is added with `DEFAULT 'backlund_center'`
  so existing Characters automatically get a real Location, never left
  dangling.
- NPC (item 28, `npc.py`): the NPC list for a Location is genuinely read via
  `location_id` (NPCs from other Locations don't show up — test correctly
  blocks Talking to an NPC not at the same spot); Talking adds +1 real Trust
  each time, dialogue lines correctly change by `trust_tier` (test: 5
  consecutive calls: trust 0→5, still tier "stranger" — correctly below the
  threshold of 20); Gifting correctly deducts 1 item from the real Bag
  (test: blocked with no item, deducts down to 0 with an item), +5 Trust for
  the NPC's liked item / +1 otherwise; every Talk/Gift logs 1 row to
  `npc_memory` — test confirms exactly 6 rows after 5 Talks + 1 Gift. The
  migration path was tested separately too: dropping all 4 NPC tables from
  the DB then calling `init_db()` again — they are correctly recreated and
  reseeded, without losing data in other tables.

The UI layer (`cogs/menu.py`) has passed `py_compile` (no syntax errors) but
has NOT yet been run against real discord.py in this environment (no network
access to install the `discord.py` package during this update) — you should
test `/menu` yourself on a test server before using it live, especially the
newer views: 🕯️ Sealed Artifact, 🔮 Mysticism → Knowledge/Divination.

## Not yet done (too large to do "fully" in one pass)

Economy/Market/Auction, real AI dialogue (Gemini/Groq + Context Builder),
World Event, procedural Dungeon, Church/Faction/Tarot, the
Investigation/Clue system, Ranking/Achievement, Contract/Bounty, a real
Ability UI (currently a stub even though `abilities` already has data),
the `locales/*.json` localization files. Each of these systems is on its
own roughly as much work as everything done above.

**Newly finished in this update:** a real NPC entity (item 28, `npc.py` +
`data/npc_seed.py`) — 6 NPCs genuinely attached to existing Locations
(Harold the Merchant at Backlund Harbor, Father Elias at Backlund Church,
Nell the Informant in the Slums, Old Ambrose at Skruvi Library, Sister
Odette in Tingen, Captain Reyes in Trier). `/menu` → 🗺️ World → 👤 NPC is
now genuinely hooked up: only shows NPCs at the Character's current
Location, Talking (+1 Trust, dialogue changes with `trust_tier`:
Stranger/Acquaintance/Trusted), Gifting (genuinely deducts 1 item from the
Bag via `db.remove_inventory_item`, +5 Trust for the NPC's liked item / +1
otherwise). Every interaction is logged to `npc_memory` — the NPC "remembers"
player actions from real data, not AI inference. **NOT yet implemented**:
the AI Narrative layer (item 29 — needs Gemini/Groq + a Context Builder, a
much bigger separate effort of its own): dialogue is currently a static
bank of lines, it doesn't adapt to context.

**Important:** 21 of the 22 Pathways still only have placeholder Sequences
(`"Sequence N"`) and no Abilities of their own
(`data/pathways_seed.py`, `data/abilities_seed.py`) — only Seer has full
data. PvP/PvE, just finished, still WORK with other Pathways (falling back
to Basic Strike), but can't yet show correct Beyonder gameplay per Pathway
until the remaining 21 Pathways are filled in from real sources (item 67 —
the runtime AI must never invent Sequence names).

Suggested order for continuing (by data dependency, not by spec item
number):

1. Fill in the Sequence + Potion + Ability names for the remaining 21
   Pathways (needs careful cross-referencing of sources — many English
   sources online disagree on Sequence names).
2. A real AI dialogue layer for NPCs (item 29 — Gemini/Groq + Context
   Builder; the NPC entity + Trust + Memory already exist per item 28, this
   is just the description layer left).
3. World/Economy — needed before Market/Auction/Contract/Bounty (City/
   Location already exist per items 31-32).

---

## Latest update (this pass)

**6 of the 8 previously-missing systems from the earlier assessment are now
done:**

- **⛪ Church / 🏛️ Faction** (`faction.py`, `data/factions_seed.py`) — 7
  canonical Orthodox Churches + 5 canonical Factions (Nighthawks, Rose
  School of Thought, Moses Ascetic Order, ...), joining/leaving with real
  reputation stored in the DB, a Character can belong to at most 1 Church
  + 1 Faction at a time.
- **🃏 Tarot Club** (`tarot.py`) — Tarot identity is fully separate from the
  real Character identity (only `tarot_seat` is stored/shown), the 22
  canonical Tarot codenames, meetings + internal messaging.
- **👥 Party** (`party.py`) — create/invite/leave a 1-5 person party,
  leadership auto-transfers when the leader leaves, atomically guarantees a
  Character is in at most 1 active Party.
- **💰 Economy / 🤝 Trade / 📜 Contract / ☠️ Bounty** (`economy.py`) — a
  Market (list/buy), direct 1-for-1 Trade between two players, Contracts
  (reward escrowed on posting, paid out when the issuer confirms
  completion), Bounties (post/claim a reward). Everything goes through a
  real atomic transaction in `database.py`: CHECK → REMOVE → ADD → Log →
  COMMIT within the same SQLite connection — if any CHECK step fails,
  nothing changes at all (no case where A loses an item and B doesn't get
  paid, or vice versa).
- **🏠 House** (`house.py`) — a separate storage chest distinct from the
  Inventory carried on the person, atomic deposit/withdraw. Has a House
  Tier (max 5, each Tier +10 storage slots, atomic money deduction) and 4
  independently upgradeable Function Rooms (max level 5, cost rises with
  level) — each room gives a REAL mechanical bonus in the matching engine,
  not just decorative stats on an Embed:
  - 🔬 Research Room → reduces the % Spirituality cost for Mysticism
    Knowledge (`mysticism.py`).
  - 🧪 Alchemy Room → reduces % craft_risk when crafting Potions
    (`potions.py`).
  - 🕯️ Ritual Room → adds % to the Ritual success chance (`ritual.py`).
  - 🗝️ Relic Room → reduces the % Side Effect chance when Experimenting on a
    Sealed Artifact (`artifacts.py`).
  Upgrading a room/Tier is always a real atomic transaction in
  `database.py` (CHECK money + current level → REMOVE money → ADD level →
  COMMIT).
- **🏆 Achievement / 📊 Ranking** (`achievements.py`) — 12 starting
  Achievements, auto-unlocked from existing gameplay flows (Sequence
  advancement, winning PvE/PvP, completing an Investigation, joining a
  Church/Faction/Tarot, first trade, reaching 50k Bảng, ...), Ranking is
  computed DIRECTLY from live Character data (no snapshot that could go
  stale).
- All of the above are genuinely wired into `/menu` → 🏛️ Faction / 💰 Trade
  / 🏠 House (`cogs/menu.py`) — no longer "🚧 in development" for these 3
  groups.

**New module: `error_handler.py` — hides technical details from players.**
Every discord.ui callback in the main menu, and all 6 new systems above,
are wrapped with `@error_handler.safe_interaction(...)`: if any system
error occurs (a bug, a DB error, an unforeseen exception), the player only
sees a neutral message with a short incident code ("🌑 A strange feeling
washes over you... Reference code: xxxxxxxx"), and NEVER sees table/
variable/class names, a traceback, SQL, or implementation details. Full
technical details are still logged separately for devs (console + the
`engine_error_log` table, searchable by incident code). Normal business
errors (not enough money, not enough stock, ...) still show a clear message
in Vietnamese as before — those aren't system errors, so they aren't
hidden.

**Still NOT done in this pass** (same as the earlier assessment, to be
tackled next in dependency order):

- **🏰 Dungeon / 🌑 World Event** — no Engine yet (seed, map, room, an event
  trigger that genuinely affects World State).
- **🤖 Deep AI Narrative** — still at the level of "Engine decides →
  AI rephrases it"; no dedicated Narrative Engine yet for
  Investigation/World Event/Combat/Quest/Lore.
- 21 of 22 Pathways still have placeholder Sequences (as noted above) —
  this is the single largest remaining task, needs careful source
  cross-referencing per Pathway.
- Linear Quests with milestones/objectives (distinct from the existing
  Contract/Bounty) don't exist yet.


---

## Next update (this pass) — Dungeon + World Event

**🏰 Dungeon (item 26)** — `dungeon.py`, `data/dungeons_seed.py`:
- Genuinely procedural by seed: each run stores its own `seed`, deterministic
  RNG via `seed:room_index` so the same seed always reproduces the same room
  sequence (matches the requirement "the seed is stored so a run can be
  reproduced").
- Rooms are Combat / Treasure / Trap / Secret; the last room is always a
  Boss.
- **No separate Combat Engine was created** — Combat/Boss rooms reuse the
  existing `combat.py`; `combat_sessions` gained a `dungeon_run_id` column
  (migration adds the column automatically, no data loss) so
  `combat._finish()` can call back into `dungeon.on_combat_resolved()` when
  a battle ends.
- Winning a normal room → advances to the next room; beating the Boss →
  grants the overall reward + real items into the Inventory; losing/fleeing
  → the run ends in failure immediately (no "free retry" to dodge a hard
  room).
- 2 starting Dungeons (Slum Den, Sunken Migas Ruins) + 5 new
  Monsters/Bosses, seeded with `INSERT OR IGNORE` so it never breaks an
  existing DB.
- Wired into `/menu` → ⚔️ Combat → 🏰 Dungeon.

**🌑 World Event (item 47)** — `world_event.py`,
`data/world_events_seed.py`:
- Triggers have a REAL effect on `cities.economy/crime/mystical_activity` the
  moment they activate (atomic transaction in `database.py`), not just an
  Embed being sent.
- Events spawn organically from existing gameplay — when a Player Travels to
  a City with no active Event (12% chance) — no separate
  scheduler/cron needed in the bot.
- Players can actively **contribute** (`world_event.contribute`): costs a
  real 100 Bảng each time; once the contribution threshold is met, the
  Event auto-Resolves — correctly reverting the exact delta that was
  applied, returning the City to its pre-Event state (tested: the city
  returns to exactly its original numbers after resolving).
- 6 Event templates (cult uprising, trade boom, mysterious disappearance,
  Church pilgrimage, gang war, mystical convergence).
- Wired into `/menu` → 🗺️ World → 🌑 Events.

Both systems have been tested end-to-end for real (not just compiled) with
a script that simulates the full flow, and `cogs/menu.py` has been fully
import-tested to confirm there's no wiring/circular-import error.

**Same as before**: 21 of 22 Pathways still have placeholder Sequences
(the single largest outstanding task), and deep AI Narrative for each
individual system (Investigation/World Event/Combat/Quest/Lore) still
doesn't exist.

# d2r-sp-tuned

**SPTuned**: a single-player tuning mod for **Diablo II: Resurrected** (tested against build 3.4.95032). Vanilla drop rates and costs assume thousands of players trading on Battle.net. SPTuned adjusts them for one person playing offline. Every part can be switched on or off in [`settings.toml`](settings.toml).

| Part | What it does | Default |
|---|---|---|
| **Runes** | High runes become reachable: ~1 Ber per 12 h of Hell farming instead of ~1,000 h. No rune drops less often than vanilla from any source. | on, `sp` preset |
| **Loot** | Chase items reachable solo: uber keys 1 in 3 runs, Ancient Statues 1 in 9, Sunder Charms 4x, SoJ ~every 11 h, Rainbow Facet ~every 5 h. | on, `sp` preset |
| **Uniques** | 63 commonly used uniques (Bartuc's, Titan's Revenge, Arreat's Face and the other level-42 class uniques, Shako, War Traveler, Griffon's, Windforce...) ~every 22 h of Hell farming each instead of 230-8,000 h. | on, `sp` preset |
| **Bosses** | Duriel, Mephisto, Diablo and Baal drop as on the first (quest) kill every time. | on |
| **Mercs** | Reviving a mercenary costs one fifth of vanilla. | on, `0.2` |
| **Base MF** | Every character finds items as if wearing 300% Magic Find, so you wear your strongest gear instead of MF gear. | on, `300` |

**All changes in one place:** [docs/index.html](docs/index.html), a hub page with a nav bar to the Runes, Loot and Uniques pages. Download the `docs/` folder and open `index.html` in a browser; GitHub shows HTML as source.

**Rune design with all the numbers:** [docs/rune-proposal.html](docs/rune-proposal.html). Download it and open it in a browser; GitHub shows HTML as source.

**Loot design with all the numbers:** [docs/loot-proposal.html](docs/loot-proposal.html).

**Every boosted unique, vanilla vs modded hours per preset:** [docs/uniques-proposal.html](docs/uniques-proposal.html).

## Quick start

Requirements: Python 3.11+ and a built [CascLib](https://github.com/ladislav-zezula/CascLib):
- Windows: `CascLib.dll` (CMake + Visual Studio: `cmake -S . -B build -A x64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && cmake --build build --config Release`).
- Linux / Steam Deck: `libcasc.so` (`cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && cmake --build build -j`). On SteamOS, build inside a distrobox, since the system has no compiler. Pass the `.so` as `--dll`, and point `game_dir` at the D2R folder inside the Proton prefix.

```powershell
# 1. Extract the vanilla data tables from your own install (read-only)
python tools/casc_extract.py --game "H:/Diablo II Resurrected" --dll path/to/CascLib.dll --filter "excel/" --out reference

# 2. Edit settings.toml (game_dir, which parts are on, presets)

# 3. Build the mod into <game_dir>/mods/SPTuned
python build.py
```

Then in the Battle.net launcher: Diablo II: Resurrected → Game Settings → Additional command line arguments: `-mod SPTuned -txt`. Mods work offline only, so Battle.net characters are never affected. With `savepath = "../"` your normal offline characters show up in the mod.

`python build.py --dry-run` shows what would change without writing anything. The build always starts from vanilla, so it's safe to re-run after any settings change. A part you switch off has its files removed from the mod folder, so the game uses vanilla for it.

**After a game patch.** The mod ships full copies of the tables it changes, so until you rebuild, the game plays with the old ones: new items, monsters or drop fixes from the patch stay hidden. Re-extract, then rebuild:

```powershell
python tools/casc_extract.py --game "H:/Diablo II Resurrected" --dll path/to/CascLib.dll --filter "excel/" --out reference
python build.py
```

The extractor records the game version (`reference/game-version.txt`) and the build writes it into the mod folder. `python build.py` warns when the extracted tables are older than the installed game, and `python build.py --check` tells you whether the mod is still current without building anything (exit code 1 if not).

## Settings

```toml
[runes]
enabled = true
preset = "sp"                 # mild | sp | generous | custom
rune_mult = 12                # custom: rune slice of gem/jewelry/rune drops (1 = vanilla)
curve_q = 1.12                # custom: each rune q times rarer than the one below (1 = vanilla ladder)
countess_vanilla_floor = true # Countess keeps exact vanilla rune drops plus bonus rolls
countess_bonus_rolls = 1

[loot]
enabled = true
preset = "sp"                 # mild | sp | generous | custom
uber_keys_mult = 4            # custom: Key of Terror / Hate / Destruction
ancient_statue_mult = 3       # custom: Colossal Summit statues
sunder_mult = 4               # custom: Latent Sunder Charms from Heralds
sunder_even_types = true      # custom: all six Sunder types equally likely
essence_mult = 2              # custom: Token of Absolution essences
jewelry_mult = 2              # custom: more rings/amulets/jewels/charms
jewelry_unique_mod = 1000     # custom: 0..1024, unique odds for jewelry (unique jewel 85+ = Rainbow Facet)
jewelry_set_mod = 896         # custom: 0..1024, set odds for jewelry
chase_jewelry_rarity = true   # custom: SoJ, Bul-Kathos, Mara's, Highlord's... picked more often

[uniques]
enabled = true
preset = "sp"                 # mild 60 h | sp 25 h | generous 10 h per listed unique | custom
hours_per_item = 25           # custom only
exclude = []                  # names from CHASE in tools/uniques.py
extra = []                    # more uniques, by uniqueitems.txt index

[bosses]
enabled = true
keep_ancient_statues = true   # keep the expansion's Uber Ancient summon drops at vanilla rate

[mercs]
enabled = true
revive_cost_fraction = 0.2    # 1.0 = vanilla

[base_mf]
enabled = true
magic_find = 300              # built-in MF for every character; worn MF adds on top
```

| Rune preset | Rune share ×F | Curve q | Ber (farming) | Ber (Hell Baal, with Bosses on) |
|---|---|---|---|---|
| vanilla | 1 | n/a | ~1 per 1,000 h | 1 in 57,074 kills |
| mild | 8 | 1.16 | ~1 per 40 h | |
| **sp** | 12 | 1.12 | ~1 per 12 h | 1 in 633 kills |
| generous | 16 | 1.10 | ~1 per 6 h | |

## How each part works

**Runes** (`treasureclassex.txt`)
1. *Rune ladder.* The fall-through weights in `Runes 1`–`Runes 17` are recalculated so that each rune is exactly `q` times rarer than the one below it.
2. *Rune share.* The rune entry in every `Act N Good` treasure class (gem/jewelry/rune group) is multiplied by `F`. Each monster table picks that group more often, so rings, amulets, jewels, charms and gems keep vanilla rates (±0.7%). The extra weight comes out of NoDrop, so equipment and gold don't change.
3. *Countess floor.* Her guaranteed rune rolls use an untouched copy of the vanilla ladder (`Runes N Classic`), and a bonus roll on the new curve is added last in her drop list.

The build checks all 894 rune-dropping treasure classes at `/players 1` and `/players 8` and reports if any rune got rarer than vanilla.

**Bosses** (`monstats.txt`, `treasureclassex.txt`)
Each act boss's regular, champion and unique drop columns point at its quest table (`Baalq (H)` and so on): more equipment picks, better quality odds, no gold or junk. Andariel already works this way in vanilla. The expansion's regular Hell Mephisto, Diablo and Baal tables also roll *Ancient Statue* (Uber Ancient summon material), which the quest tables lack. A wrapper (`Baalq (H) SP` = quest table + `Baal (H) Statue Roll`) keeps the statue chance exactly vanilla. Terror-zone boss tables are untouched.

**Loot** (`treasureclassex.txt`, `uniqueitems.txt`)
- *Item boosts.* Uber key, Ancient Statue, Sunder and essence weights are multiplied wherever they drop; the extra weight comes out of NoDrop, so those tables' other drops keep their rates. Herald tables have no NoDrop, so other Herald drops get ~1.5% rarer with sunders x4.
- *Jewelry.* The jewelry share of every gem/jewelry/rune table is multiplied (gems and runes kept), and the `Jewelry A/B/C` tables get unique/set quality modifiers. These are the columns the game uses to guarantee Annihilus, and the highest modifier on a drop chain wins. Only rings, amulets, jewels and charms are affected. A unique jewel at item level 85+ is always a Rainbow Facet.
- *Rarity.* SoJ and Bul-Kathos go from 1.6% to about 12% of unique rings; Mara's, Highlord's, Cat's Eye, Atma's, Metalgrid and Seraph's Hymn get higher weights among amulets.

Works offline: Pandemonium/Uber Tristram, and Diablo Clone (sell **one** SoJ to a vendor in Hell for Annihilus). The Herald Sunder table carries a ladder-season flag, so confirm in one terror-zone session that Heralds drop Sunders offline.

**Uniques** (`treasureclassex.txt`)
Most chase uniques are the only unique on their base, so a rarity weight can't single them out. Instead every drop table that can drop equipment (normal, champion, unique, boss and terror-zone tables, all difficulties) gets one extra entry, the same trick the game uses for Annihilus: an `SP Chase uL` table holding the bases of the listed uniques up to unique item level L, with the Unique quality modifier at 1024, so a pick is always that unique. Each table only offers uniques its monsters can roll (table level, +2 for champions, +3 for uniques, the boss's level for boss tables, lair level +3 for superuniques such as the Countess, Cow King and Council); otherwise the game would make a rare of that base instead. The entry's weight is proportional to the table's equipment weight, so bosses and champions roll it more often, and it comes out of NoDrop, so nothing else drops less. Champion and unique item tables have no NoDrop, so for them it comes out of their equipment entry (about 2% fewer of their regular items).

| Unique (Hell lvl-85 farming, no MF) | vanilla | `sp` |
|---|---|---|
| Bartuc's Cut-Throat | ~880 h | ~22 h |
| Arreat's Face | ~1,100 h | ~22 h |
| Titan's Revenge | ~320 h | ~21 h |
| Harlequin Crest (Shako) | ~1,900 h | ~22 h |
| War Traveler | ~1,600 h | ~22 h |
| Griffon's Eye | ~6,600 h | ~22 h |
| Crown of Ages, Arachnid Mesh, Tomb Reaver, Stormlash (item level 86-87) | 900-8,000 h | ~75 h |

Item level 86-87 uniques need monster level 86+, so in level-85 zones only champions, uniques and bosses roll them (as in vanilla). While levelling, fewer uniques are eligible, so each comes faster: in Nightmare Act 5 Arreat's Face or Bartuc's takes ~9 h instead of 650-860 h. The full list is in [docs/uniques-proposal.html](docs/uniques-proposal.html); `python tools/uniques.py report` prints it too.

**Base MF** (`itemratio.txt`)
The game rolls each item's quality from `itemratio.txt` and divides the odds by (100 + effective MF) / 100. Effective MF has the game's diminishing returns: at 300% it is 136% for uniques, 187% for sets, 200% for rares and the full 300% for magic items. The part divides every Ratio by that factor and multiplies its Divisor by it, picking the whole-number pair closest to the real MF math (uniques within 4%, sets and rares within 3%), so every drop for every character rolls as if that MF were worn. MF you do wear still applies on top. Runes, keys, gems and the Uniques part's chase roll don't use these odds. The hours on the docs pages are computed without it, so with Base MF on, unique, set and rare drops come about 2.4-3 times as often as the pages show.

**Mercs** (`hireling.txt`)
Revive price = multiplier ÷ divisor scaling, capped at max. Setting divisor 2 → 10 and max 50,000 → 10,000 makes every revive one fifth of vanilla. Automatic revival isn't something these data tables can express.

Both table sets the game ships are written: `excel/` (with the 3.x expansion) and `excel/base/`.

## Repository layout

| Path | What |
|---|---|
| `settings.toml` | Which parts are on, presets, values |
| `build.py` | Builds the mod from vanilla + settings |
| `tools/runes.py` | Runes part; `report` / `check` CLI to explore presets |
| `tools/bosses.py` | Bosses part |
| `tools/loot.py` | Loot part, plus the quality-odds calculator |
| `tools/uniques.py` | Uniques part; `report` CLI prints vanilla vs modded hours per unique |
| `tools/mercs.py` | Mercs part |
| `tools/basemf.py` | Base MF part |
| `tools/tables.py` | Byte-exact table read/write shared by all parts |
| `tools/tc_calc.py` | Treasure-class calculator: expected runes per kill |
| `tools/casc_extract.py` | Pulls files out of the game's CASC storage through CascLib |
| `tools/make_page.py` | Regenerates `docs/rune-proposal.html` (standalone) and `docs/rune-index.html` (artifact version) |
| `tools/make_loot_page.py` | Regenerates `docs/loot-proposal.html` and `docs/loot-index.html` |
| `tools/make_uniques_page.py` | Regenerates `docs/uniques-proposal.html` and `docs/uniques-index.html` |
| `tools/site_nav.py` | Shared nav bar for every page; run it to regenerate the hub `docs/index.html` (and `docs/hub-index.html`) |

Blizzard's game files are deliberately not in this repo (`reference/` is git-ignored). Everything is generated from your own install.

# d2r-sp-tuned

**SPTuned**: a single-player tuning mod for **Diablo II: Resurrected** (tested against build 3.4.95032). Vanilla drop rates and costs assume thousands of players trading on Battle.net. SPTuned adjusts them for one person playing offline. Every part can be switched on or off in [`settings.toml`](settings.toml).

| Part | What it does | Default |
|---|---|---|
| **Runes** | High runes become reachable: ~1 Ber per 12 h of Hell farming instead of ~1,000 h. No rune drops less often than vanilla from any source. | on, `sp` preset |
| **Bosses** | Duriel, Mephisto, Diablo and Baal drop as on the first (quest) kill every time. | on |
| **Mercs** | Reviving a mercenary costs one fifth of vanilla. | on, `0.2` |

**Rune design with all the numbers:** [docs/rune-proposal.html](docs/rune-proposal.html). Download it and open it in a browser; GitHub shows HTML as source.

**Proposed next part, Loot** (uber keys, Ancient Statues, Sunder Charms, SoJ and other endgame jewelry, Rainbow Facets): [docs/loot-proposal.html](docs/loot-proposal.html). Not in the build yet.

## Quick start

Requirements: Windows, Python 3.11+, and a built [CascLib](https://github.com/ladislav-zezula/CascLib) `CascLib.dll` (CMake + Visual Studio: `cmake -S . -B build -A x64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && cmake --build build --config Release`).

```powershell
# 1. Extract the vanilla data tables from your own install (read-only)
python tools/casc_extract.py --game "H:/Diablo II Resurrected" --dll path/to/CascLib.dll --filter "excel/" --out reference

# 2. Edit settings.toml (game_dir, which parts are on, presets)

# 3. Build the mod into <game_dir>/mods/SPTuned
python build.py
```

Then in the Battle.net launcher: Diablo II: Resurrected → Game Settings → Additional command line arguments: `-mods SPTuned -txt`. Mods work offline only, so Battle.net characters are never affected. With `savepath = "../"` your normal offline characters show up in the mod.

`python build.py --dry-run` shows what would change without writing anything. The build always starts from vanilla, so it's safe to re-run after any settings change. A part you switch off has its files removed from the mod folder, so the game uses vanilla for it.

## Settings

```toml
[runes]
enabled = true
preset = "sp"                 # mild | sp | generous | custom
rune_mult = 12                # custom: rune slice of gem/jewelry/rune drops (1 = vanilla)
curve_q = 1.12                # custom: each rune q times rarer than the one below (1 = vanilla ladder)
countess_vanilla_floor = true # Countess keeps exact vanilla rune drops plus bonus rolls
countess_bonus_rolls = 1

[bosses]
enabled = true
keep_ancient_statues = true   # keep the expansion's Uber Ancient summon drops at vanilla rate

[mercs]
enabled = true
revive_cost_fraction = 0.2    # 1.0 = vanilla
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
| `tools/mercs.py` | Mercs part |
| `tools/tables.py` | Byte-exact table read/write shared by all parts |
| `tools/tc_calc.py` | Treasure-class calculator: expected runes per kill |
| `tools/casc_extract.py` | Pulls files out of the game's CASC storage through CascLib |
| `tools/make_page.py` | Regenerates `docs/rune-proposal.html` (standalone) and `docs/index.html` (artifact version) |

Blizzard's game files are deliberately not in this repo (`reference/` is git-ignored). Everything is generated from your own install.

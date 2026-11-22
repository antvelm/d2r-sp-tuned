# d2r-sp-runes

Single-player rune rebalance for **Diablo II: Resurrected** (tested against build 3.4.95032).

Vanilla Hell rune rates assume thousands of players trading on Battle.net. Solo, a Ber takes on the order of a thousand hours of farming. This mod makes runewords reachable in a single-player game and leaves every other drop alone.

**Proposal with all the numbers:** [docs/rune-proposal.html](docs/rune-proposal.html). Download it and open it in a browser; GitHub shows HTML as source.

| Preset | Rune share ×F | Curve q | Ber (farming) | Ber (Hell Baal) |
|---|---|---|---|---|
| vanilla | 1 | n/a | ~1 per 1,000 h | 1 in 57,074 kills |
| mild | 8 | 1.16 | ~1 per 40 h | 1 in ~2,600 kills |
| **sp** (default) | 12 | 1.12 | ~1 per 12 h | 1 in ~790 kills |
| generous | 16 | 1.10 | ~1 per 6 h | 1 in ~400 kills |

## How it works

1. **Rune ladder.** The fall-through weights in `Runes 1`–`Runes 17` are recalculated so that each rune is exactly `q` times rarer than the one below it.
2. **Rune share.** The rune entry in every `Act N Good` treasure class (the gem/jewelry/rune group) is multiplied by `F`. Each monster table picks that group more often, so rings, amulets, jewels, charms and gems keep their vanilla rates (±0.7%). The extra weight comes out of NoDrop, so equipment and gold don't change.

No rune drops less often than vanilla from any source (all 894 rune-dropping tables checked, every preset, `/players 1` and `8`). Countess keeps her exact vanilla rune rolls on an untouched copy of the vanilla ladder and gets one extra roll on the new curve.

Magic Find doesn't affect runes, and the mod doesn't touch it.

## Requirements

- Windows, Python 3.10+
- A built [CascLib](https://github.com/ladislav-zezula/CascLib) `CascLib.dll` (CMake + Visual Studio: `cmake -S . -B build -A x64 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 && cmake --build build --config Release`)

## Usage

```powershell
# 1. Extract the vanilla data tables from your own install (read-only)
python tools/casc_extract.py --game "C:/Program Files (x86)/Diablo II Resurrected" --dll path/to/CascLib.dll --filter "excel/" --out reference

# 2. See the odds for a preset, and confirm no rune got rarer than vanilla
python tools/runes_mod.py report --preset sp
python tools/runes_mod.py check --preset sp

# 3. Write the mod
python tools/runes_mod.py build --preset sp --mod "C:/Program Files (x86)/Diablo II Resurrected/mods/SPTuned"
```

Start the game with `-mods SPTuned -txt` (Battle.net launcher → Game Settings → Additional command line arguments). Mods run offline only.

## Repository layout

| Path | What |
|---|---|
| `tools/casc_extract.py` | Pulls files out of the game's CASC storage through CascLib |
| `tools/tc_calc.py` | Treasure-class calculator: expected runes per kill |
| `tools/runes_mod.py` | Presets, the rebalance itself, reports, build |
| `tools/make_page.py` | Regenerates `docs/rune-proposal.html` (standalone) and `docs/index.html` (artifact fragment) from `docs/template.html` |

Blizzard's game files are deliberately not in this repo (`reference/` is git-ignored). Everything is generated from your own install.

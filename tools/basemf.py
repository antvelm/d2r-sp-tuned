"""Base MF part: every character finds items as if wearing `magic_find` % MF.

The game rolls an item's quality (itemratio.txt) like this, per quality:

    chance = (Ratio - (ilvl - qlvl) // Divisor) * 128
    chance = chance * 100 // (100 + effective MF)       # Magic Find
    chance = max(chance, Min)
    chance -= chance * tc_quality_mod // 1024           # treasure class bonus
    P = 128 / chance

Effective MF has diminishing returns for the better qualities:
unique MF*250/(MF+250), set MF*500/(MF+500), rare MF*600/(MF+600), magic MF.

Dividing Ratio by f = (100 + effective MF) / 100 and multiplying Divisor by f
gives the same chance before the Min clamp, so the rewritten table behaves
like that much MF on every drop, for every character, with no gear. MF the
player does wear still applies on top. Runes, keys, gems and the Uniques
part's chase roll don't use these odds, so they are unchanged.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tables import header  # noqa: E402

# quality column -> diminishing-returns cap (None = full MF)
QUALITIES = (("Unique", 250), ("Set", 500), ("Rare", 600), ("Magic", None))


def effective(mf, cap):
    return mf if cap is None else mf * cap // (mf + cap)


def best_pair(ratio, div, f, mn):
    """Whole-number (Ratio, Divisor) whose chance, after the Min clamp, is closest
    to the vanilla chance divided by f, over every level gap 0..98."""
    target = [max((ratio - d // div) * 128 / f, mn) for d in range(99)]
    r0, d0 = ratio / f, div * f
    best = None
    for r in range(max(1, int(r0) - 3), int(r0) + 4):
        for dv in range(max(1, int(d0) - 3), int(d0) + 5):
            err = max(abs(max((r - d // dv) * 128, mn) / t - 1) for d, t in enumerate(target))
            if best is None or err < best[0]:
                best = (err, r, dv)
    return best


def apply(itemratio, mf):
    """Mutates itemratio rows in place. Returns change lines."""
    if mf <= 0:
        return []
    h = header(itemratio)
    log = []
    for q, cap in QUALITIES:
        e = effective(mf, cap)
        f = (100 + e) / 100
        worst = 0.0
        for r in itemratio[1:]:
            if not r or not r[h[q]].strip():
                continue
            err, ratio, div = best_pair(int(r[h[q]]), int(r[h[q + "Divisor"]]), f, int(r[h[q + "Min"]] or 0))
            r[h[q]], r[h[q + "Divisor"]] = str(ratio), str(div)
            worst = max(worst, err)
        log.append(f"{q.lower()}: like {e}% effective MF (x{f:.2f} chance, within {worst:.0%})")
    return log


def p_quality(ratio, div, mn, ilvl, qlvl, mf=0, cap=None, tc_mod=0):
    """Chance of one quality roll, with the game's integer math."""
    c = (ratio - (ilvl - qlvl) // div) * 128
    c = c * 100 // (100 + effective(mf, cap))
    c = max(c, mn)
    c -= c * tc_mod // 1024
    return 1.0 if c <= 128 else 128 / c

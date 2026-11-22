"""Runes part: single-player rune rebalance (treasureclassex.txt).

1. Rune ladder ("Runes 1".."Runes 17"). Each Runes N holds two runes plus a
   fall-through to Runes N-1 with a huge weight, which is what makes high
   runes nearly impossible. The fall-through weights are recomputed so that
   each rune is exactly `q` times rarer than the rune below it.
2. Rune share. The Runes entry in every "Good" TC (gems/jewelry/runes) is
   multiplied by `rune_mult`. Each parent TC picks Good more often so jewelry
   and gems keep vanilla rates; the extra weight comes out of NoDrop, so
   equipment and gold don't change.
3. Countess floor (optional). Countess keeps her exact vanilla rune rolls on
   an untouched copy of the vanilla ladder and gets a bonus roll on the new
   curve, so none of her runes ever gets rarer.

Exploration CLI (the mod itself is built by ../build.py):
    python tools/runes.py report --preset sp
    python tools/runes.py check  --preset sp
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tables import read_table, rows_to_tcs, header, blank_row_like  # noqa: E402
from tc_calc import Calc, RUNE_NAMES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VANILLA = os.path.join(HERE, "..", "reference", "data", "global", "excel", "treasureclassex.txt")

PRESETS = {
    "vanilla": None,
    "mild": {"q": 1.16, "rune_mult": 8},       # ~1 Ber / 40 h farming
    "sp": {"q": 1.12, "rune_mult": 12},        # ~1 Ber / 12 h (recommended)
    "generous": {"q": 1.10, "rune_mult": 16},  # ~1 Ber / 6 h
}

RUNES_RE = re.compile(r"^Runes (\d+)$")
CLASSIC = " Classic"
COUNTESS_RUNE_RE = re.compile(r"^Countess Rune( \((N|H)\))?$")


# ----------------------------------------------------------------------- design
def ladder(q, top=33):
    """Own + fall-through weights for Runes 1..17 such that, from any entry
    point, each rune is exactly `q` times rarer than the rune below it.
    Returns {tier: (w_first, w_second_or_None, w_fallthrough_or_None)}."""
    SCALE = 1000
    w = [None] + [q ** -(i - 1) for i in range(1, top + 1)]
    out, below = {}, 0.0
    for k in range(1, 18):
        a, b = 2 * k - 1, 2 * k
        own = [w[a]] if b > top else [w[a], w[b]]
        f = SCALE / own[0]
        ow = [max(1, round(x * f)) for x in own]
        out[k] = (ow[0], ow[1] if len(ow) > 1 else None, round(below * f) if k > 1 else None)
        below += sum(own)
    return out


def _cols(rows):
    col = header(rows)
    return col, [col[f"Item{k}"] for k in range(1, 11)], [col[f"Prob{k}"] for k in range(1, 11)]


def countess_keep_vanilla(rows, bonus_picks):
    """Point 'Countess Rune*' at a vanilla ladder copy ('Runes N Classic') and
    append a 'Countess Bonus Rune*' roll (new curve) as the LAST entry of her
    sequential drop list. TCs may only reference rows above them, so new rows
    go right after the rows they derive from."""
    col, ic, pc = _cols(rows)
    names = [r[0] for r in rows]
    out = []
    for r in rows:
        out.append(r)
        if r[0] == "Runes 12":  # Countess tops out at Runes 12
            for k in range(1, 13):
                c = list(rows[names.index(f"Runes {k}")])
                c[0] = f"Runes {k}{CLASSIC}"
                for j in range(10):
                    if RUNES_RE.match(c[ic[j]].strip()):
                        c[ic[j]] = c[ic[j]].strip() + CLASSIC
                out.append(c)
        if COUNTESS_RUNE_RE.match(r[0]):
            top = next(r[ic[j]].strip() for j in range(10) if RUNES_RE.match(r[ic[j]].strip()))
            bonus = blank_row_like(rows)
            bonus[0] = r[0].replace("Countess Rune", "Countess Bonus Rune")
            bonus[col["Picks"]] = str(bonus_picks)
            bonus[ic[0]], bonus[pc[0]] = top, "1"
            for j in range(10):
                if RUNES_RE.match(r[ic[j]].strip()):
                    r[ic[j]] = r[ic[j]].strip() + CLASSIC
            if bonus_picks > 0:
                out.append(bonus)
    if bonus_picks > 0:
        for r in out[1:]:
            if not r[0].startswith("Countess") or int(r[col["Picks"]] or 0) >= 0:
                continue
            rune_tc = next((r[ic[j]].strip() for j in range(10)
                            if COUNTESS_RUNE_RE.match(r[ic[j]].strip())), None)
            if not rune_tc:
                continue
            free = next(j for j in range(10) if not r[ic[j]].strip())
            r[ic[free]] = rune_tc.replace("Countess Rune", "Countess Bonus Rune")
            r[pc[free]] = "1"
            r[col["Picks"]] = str(int(r[col["Picks"]]) - 1)
    return out


def apply(rows, q=1.12, rune_mult=12, countess_floor=True, countess_bonus_picks=1):
    """Return a new treasureclassex table. q <= 1 keeps the vanilla ladder;
    rune_mult <= 1 keeps the vanilla rune share."""
    rows = [list(r) for r in rows]
    if countess_floor:
        rows = countess_keep_vanilla(rows, countess_bonus_picks)
    col, ic, pc = _cols(rows)
    by_name = {r[0]: r for r in rows[1:] if r and r[0]}

    if q and q > 1:  # 1) rune ladder
        for k, (wa, wb, fall) in ladder(q).items():
            r = by_name[f"Runes {k}"]
            for j in range(10):
                name = r[ic[j]].strip()
                if name == f"r{2 * k - 1:02d}":
                    r[pc[j]] = str(wa)
                elif name == f"r{2 * k:02d}" and wb is not None:
                    r[pc[j]] = str(wb)
                elif RUNES_RE.match(name):
                    r[pc[j]] = str(fall)

    if rune_mult and rune_mult > 1:  # 2) rune share inside "Good" TCs
        growth = {}
        for name, r in by_name.items():
            if " Good" not in name:
                continue
            old = new = 0
            for j in range(10):
                if not r[pc[j]].strip():
                    continue
                w = int(r[pc[j]])
                old += w
                if RUNES_RE.match(r[ic[j]].strip()):
                    w *= rune_mult
                    r[pc[j]] = str(w)
                new += w
            if new != old:
                growth[name] = new / old
        # 3) parents pick Good more often; weights x10 for rounding precision
        for name, r in by_name.items():
            if int(r[col["Picks"]] or 0) <= 0:
                continue
            hits = [j for j in range(10) if r[ic[j]].strip() in growth and r[pc[j]].strip()]
            if not hits:
                continue
            for j in range(10):
                if r[pc[j]].strip():
                    r[pc[j]] = str(int(r[pc[j]]) * 10)
            nd = int(r[col["NoDrop"]] or 0) * 10
            added = 0
            for j in hits:
                w = int(r[pc[j]])
                nw = round(w * growth[r[ic[j]].strip()])
                added += nw - w
                r[pc[j]] = str(nw)
            if nd:
                r[col["NoDrop"]] = str(max(0, nd - added))
    return rows


def apply_preset(rows, preset):
    return rows if preset is None else apply(rows, preset["q"], preset["rune_mult"])


def floor_check(vanilla_rows, new_rows, players=(1, 8)):
    """List of (players, tc, rune, ratio) where a rune got rarer than vanilla."""
    tv, tn = rows_to_tcs(vanilla_rows), rows_to_tcs(new_rows)
    fails = []
    for pl in players:
        cv, cn = Calc(tv, pl), Calc(tn, pl)
        for t in tv:
            if RUNES_RE.match(t) or t not in tn:
                continue
            va, vb = cv.runes(t), cn.runes(t)
            for i in range(1, 34):
                if va[i] > 1e-12 and vb[i] < va[i] * 0.999:
                    fails.append((pl, t, RUNE_NAMES[i], vb[i] / va[i]))
    return fails


# ---------------------------------------------------------------------- report
SCENARIOS = [
    ("Hell Act 5 normal monster", "Act 5 (H) H2H C"),
    ("Hell Act 5 champion", "Act 5 (H) Champ C"),
    ("Hell Act 5 unique (boss pack)", "Act 5 (H) Unique C"),
    ("Pindleskin (Hell)", "Act 5 (H) Super Cx"),
    ("Hell Cow", "Cow (H)"),
    ("Countess (Hell)", "Countess (H)"),
    ("Andariel (Hell)", "Andarielq (H)"),
    ("Mephisto (Hell)", "Mephisto (H)"),
    ("Diablo (Hell)", "Diablo (H)"),
    ("Baal (Hell)", "Baal (H)"),
]
KEY_RUNES = ["Tal", "Shael", "Lum", "Ist", "Vex", "Ohm", "Lo", "Ber", "Jah", "Zod"]
# Rough single-player hour: 900 normal, 80 champion, 20 unique kills in lvl-85 zones.
HOUR_MIX = [("Act 5 (H) H2H C", 900), ("Act 5 (H) Champ C", 80), ("Act 5 (H) Unique C", 20)]


def report(rows, players):
    c = Calc(rows_to_tcs(rows), players)
    out = {"scenarios": [], "ladder": [], "hour": {}}
    for label, tc in SCENARIOS:
        v = c.runes(tc)
        out["scenarios"].append({
            "label": label, "tc": tc, "per_kill": sum(v),
            "odds": {RUNE_NAMES[i]: (1 / v[i] if v[i] else None) for i in range(1, 34)},
        })
    v = c.runes("Runes 17")
    out["ladder"] = [{"rune": RUNE_NAMES[i], "p": v[i]} for i in range(1, 34)]
    hv = [0.0] * 34
    for tc, n in HOUR_MIX:
        sub = c.runes(tc)
        for i in range(34):
            hv[i] += n * sub[i]
    out["hour"] = {RUNE_NAMES[i]: hv[i] for i in range(1, 34)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["report", "check", "weights"])
    ap.add_argument("--preset", default="sp", choices=list(PRESETS))
    ap.add_argument("--vanilla", default=VANILLA)
    ap.add_argument("--players", type=int, default=1)
    a = ap.parse_args()
    preset = PRESETS[a.preset]
    rows = read_table(a.vanilla)
    new = apply_preset(rows, preset)
    if a.cmd == "weights":
        print(ladder(preset["q"]) if preset else "vanilla")
    elif a.cmd == "check":
        fails = floor_check(rows, new)
        for pl, t, r, x in fails:
            print(f"/players {pl}: {t} {r} {x:.3f}x vanilla")
        print("OK: no rune rarer than vanilla" if not fails else f"FAIL: {len(fails)} reductions")
        sys.exit(1 if fails else 0)
    else:
        rep = report(new, a.players)
        for s in rep["scenarios"]:
            odds = "  ".join(f"{r}:{s['odds'][r]:,.0f}" if s["odds"][r] else f"{r}:-" for r in KEY_RUNES)
            print(f"{s['label']:<30} {odds}")
        print("per hour:", {r: round(rep["hour"][r], 3) for r in KEY_RUNES})


if __name__ == "__main__":
    main()

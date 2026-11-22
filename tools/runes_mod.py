"""Single-player rune rebalance for D2R.

Reads the vanilla treasureclassex.txt (extracted from your own install),
applies a preset, and can either print/emit a report or write the mod file.

    python tools/runes_mod.py report --preset sp --json out.json
    python tools/runes_mod.py build  --preset sp --mod "H:/Diablo II Resurrected/mods/SPTuned"

How the rebalance works
-----------------------
1. Rune ladder ("Runes 1".."Runes 17"). Each Runes N holds two runes (3:2)
   plus a fall-through to Runes N-1 with a big weight. That fall-through
   weight is what makes high runes astronomically rare. We recompute it from
   a target curve: inside a single top-tier rune roll, every tier is `ratio`
   times rarer than the tier just below it.
2. "Good" TC share. In the Act/difficulty "Good" TCs (gems/jewelry/runes),
   the Runes entry weight is multiplied by `good_mult`, so more Good rolls
   become runes instead of chipped gems.
Everything else (gold, equipment, NoDrop, MF) is untouched.
"""
import argparse
import csv
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tc_calc import Calc, RUNE_NAMES  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VANILLA = os.path.join(HERE, "..", "reference", "data", "global", "excel", "treasureclassex.txt")

PRESETS = {
    "vanilla": None,
    # Mild: roughly 10x more high runes, low runes barely change.
    "mild": {"q": 1.16, "rune_mult": 8},
    # Recommended single-player curve.
    "sp": {"q": 1.12, "rune_mult": 12},
    # Generous: runewords on tap.
    "generous": {"q": 1.10, "rune_mult": 16},
}

RUNES_RE = re.compile(r"^Runes (\d+)$")


# --------------------------------------------------------------------------- io
def read_table(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        return list(csv.reader(f, delimiter="\t"))


def write_table(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    w.writerows(rows)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())


def rows_to_tcs(rows):
    from tc_calc import load_tcs  # reuse parser via temp string
    hdr = rows[0]
    col = {h: i for i, h in enumerate(hdr)}
    tcs = {}
    for r in rows[1:]:
        if not r or not r[0] or r[0].lower() == "expansion":
            continue
        r = r + [""] * (len(hdr) - len(r))
        entries = []
        for k in range(1, 11):
            name = r[col[f"Item{k}"]].strip().strip('"')
            prob = r[col[f"Prob{k}"]].strip()
            if name and prob:
                entries.append((name, int(prob)))
        tcs[r[0]] = {"picks": int(r[col["Picks"]] or 0),
                     "nodrop": int(r[col["NoDrop"]] or 0), "entries": entries}
    return tcs


# ----------------------------------------------------------------------- design
def ladder(q, top=33):
    """Own + fall-through weights for Runes 1..17 such that, from any entry
    point, each rune is exactly `q` times rarer than the rune below it.

    Returns {tier: (w_first, w_second_or_None, w_fallthrough_or_None)}.
    """
    SCALE = 1000
    w = [None] + [q ** -(i - 1) for i in range(1, top + 1)]   # w[i] for rune i
    out = {}
    below = 0.0                       # total mass of runes 1..(2k-2)
    for k in range(1, 18):
        a, b = 2 * k - 1, 2 * k
        if b > top:                   # tier 17: Zod alone
            own = [w[a]]
        else:
            own = [w[a], w[b]]
        # normalise so the tier's first rune has weight SCALE
        f = SCALE / own[0]
        ow = [max(1, round(x * f)) for x in own]
        fall = round(below * f) if k > 1 else None
        out[k] = (ow[0], ow[1] if len(ow) > 1 else None, fall)
        below += sum(own)
    return out


CLASSIC = " Classic"
COUNTESS_RUNE_RE = re.compile(r"^Countess Rune( \((N|H)\))?$")


def countess_keep_vanilla(rows, col, ic, pc, bonus_picks):
    """Countess never drops fewer of any rune than in vanilla.

    * Her 'Countess Rune*' TCs are pointed at an untouched copy of the vanilla
      ladder ('Runes N Classic'), so her guaranteed rune rolls are exactly vanilla.
    * A new 'Countess Bonus Rune*' TC (same ladder top, new curve) is appended
      as the LAST entry of her sequential drop list. It only adds drops; if the
      engine's per-kill item cap is ever hit, this is what gets cut, not vanilla.
    TCs may only reference TCs defined above them, so new rows are inserted
    right after the rows they derive from.
    """
    names = [r[0] for r in rows]
    out = []
    for r in rows:
        out.append(r)
        if r[0] == "Runes 12":  # vanilla ladder copy, Runes 1..12 (Countess tops out at 12)
            for k in range(1, 13):
                c = list(rows[names.index(f"Runes {k}")])
                c[0] = f"Runes {k}{CLASSIC}"
                for j in range(10):
                    if RUNES_RE.match(c[ic[j]].strip()):
                        c[ic[j]] = c[ic[j]].strip() + CLASSIC
                out.append(c)
        m = COUNTESS_RUNE_RE.match(r[0])
        if m:
            ladder_top = next(r[ic[j]].strip() for j in range(10) if RUNES_RE.match(r[ic[j]].strip()))
            bonus = [""] * len(r)
            bonus[0] = r[0].replace("Countess Rune", "Countess Bonus Rune")
            bonus[col["Picks"]] = str(bonus_picks)
            bonus[ic[0]], bonus[pc[0]] = ladder_top, "1"
            for j in range(10):
                if RUNES_RE.match(r[ic[j]].strip()):
                    r[ic[j]] = r[ic[j]].strip() + CLASSIC
            out.append(bonus)
    # append the bonus roll to every Countess top-level (sequential) TC
    for r in out[1:]:
        if not r[0].startswith("Countess") or int(r[col["Picks"]] or 0) >= 0:
            continue
        rune_tc = next((r[ic[j]].strip() for j in range(10) if COUNTESS_RUNE_RE.match(r[ic[j]].strip())), None)
        if not rune_tc:
            continue
        free = next(j for j in range(10) if not r[ic[j]].strip())
        r[ic[free]] = rune_tc.replace("Countess Rune", "Countess Bonus Rune")
        r[pc[free]] = "1"
        r[col["Picks"]] = str(int(r[col["Picks"]]) - 1)
    return out


def apply_preset(rows, preset):
    if preset is None:
        return rows
    rows = [list(r) for r in rows]
    hdr = rows[0]
    col = {h: i for i, h in enumerate(hdr)}
    ic = [col[f"Item{k}"] for k in range(1, 11)]
    pc = [col[f"Prob{k}"] for k in range(1, 11)]
    for r in rows[1:]:
        r += [""] * (len(hdr) - len(r))

    rows = countess_keep_vanilla(rows, col, ic, pc, preset.get("countess_bonus", 1))
    by_name = {r[0]: r for r in rows[1:] if r and r[0]}

    # 1) rune ladder
    lad = ladder(preset["q"])
    for k, (wa, wb, fall) in lad.items():
        r = by_name[f"Runes {k}"]
        for j in range(10):
            name = r[ic[j]].strip()
            if not name:
                continue
            if name == f"r{2 * k - 1:02d}":
                r[pc[j]] = str(wa)
            elif name == f"r{2 * k:02d}" and wb is not None:
                r[pc[j]] = str(wb)
            elif RUNES_RE.match(name):
                r[pc[j]] = str(fall)

    # 2) more runes inside every "Good" TC, other contents unchanged
    F = preset["rune_mult"]
    growth = {}
    for name, r in by_name.items():
        if not name.endswith(" Good") and " Good " not in name + " ":
            continue
        if " Good" not in name:
            continue
        old = new = 0
        for j in range(10):
            if not r[pc[j]].strip():
                continue
            w = int(r[pc[j]])
            old += w
            if RUNES_RE.match(r[ic[j]].strip()):
                w = w * F
                r[pc[j]] = str(w)
            new += w
        if new != old:
            growth[name] = new / old

    # 3) parents pick Good more often so jewelry/gem rates stay as they were;
    #    extra weight comes out of NoDrop. Weights x10 for rounding precision.
    for name, r in by_name.items():
        picks = int(r[col["Picks"]] or 0)
        if picks <= 0:
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
    # distribution inside one Runes 17 roll
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
    ap.add_argument("cmd", choices=["report", "build", "weights", "check"])
    ap.add_argument("--preset", default="sp", choices=list(PRESETS))
    ap.add_argument("--vanilla", default=VANILLA)
    ap.add_argument("--players", type=int, default=1)
    ap.add_argument("--json")
    ap.add_argument("--mod", help="mod folder, e.g. <D2R>/mods/SPTuned")
    a = ap.parse_args()

    rows = read_table(a.vanilla)
    preset = PRESETS[a.preset]
    new = apply_preset(rows, preset)

    if a.cmd == "check":
        # Guarantee: no rune from any TC is rarer than in vanilla.
        tv, tn = rows_to_tcs(rows), rows_to_tcs(new)
        fails = 0
        for pl in (1, 8):
            cv, cn = Calc(tv, pl), Calc(tn, pl)
            for t in tv:
                if RUNES_RE.match(t):
                    continue
                va, vb = cv.runes(t), cn.runes(t)
                for i in range(1, 34):
                    if va[i] > 1e-12 and vb[i] < va[i] * 0.999:
                        fails += 1
                        print(f"/players {pl}: {t} {RUNE_NAMES[i]} {vb[i] / va[i]:.3f}x vanilla")
        print("OK: no rune rarer than vanilla" if not fails else f"FAIL: {fails} reductions")
        sys.exit(1 if fails else 0)
    if a.cmd == "weights":
        print(ladder(preset["q"]))
    elif a.cmd == "report":
        rep = report(new, a.players)
        if a.json:
            with open(a.json, "w") as f:
                json.dump(rep, f, indent=1)
        for s in rep["scenarios"]:
            odds = "  ".join(f"{r}:{s['odds'][r]:,.0f}" if s["odds"][r] else f"{r}:-" for r in KEY_RUNES)
            print(f"{s['label']:<30} {odds}")
        print("per hour:", {r: round(rep["hour"][r], 3) for r in KEY_RUNES})
    else:
        if not a.mod:
            sys.exit("--mod required")
        name = os.path.basename(os.path.normpath(a.mod))
        dest = os.path.join(a.mod, f"{name}.mpq", "data", "global", "excel", "treasureclassex.txt")
        write_table(new, dest)
        print("wrote", dest)


if __name__ == "__main__":
    main()

"""Bosses part: act bosses always drop as on the first (quest) kill.

Duriel, Mephisto, Diablo and Baal have a quest treasure class ('Baalq (H)')
that the game uses only while the quest is open: more equipment picks,
better quality odds, no gold or junk. This points every column of
monstats.txt at it. Andariel already works this way in vanilla.

The 3.x expansion's regular Hell Mephisto/Diablo/Baal tables also roll
'Ancient Statue N' (Uber Ancient summon material), which the quest tables
lack. With keep_statues, each such boss gets a wrapper:

    '<Q> SP'           Picks -2 : <Q> x1, '<R> Statue Roll' x1
    '<R> Statue Roll'  same Picks as <R>; NoDrop absorbs every non-statue
                       weight, so the per-pick statue chance equals vanilla.

Terror-zone (Desecrated) and Herald boss tables are not touched.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tables import header, blank_row_like  # noqa: E402

DIFFS = ["", "(N)", "(H)"]
TC_KINDS = ["TreasureClass", "TreasureClassChamp", "TreasureClassUnique", "TreasureClassQuest"]
STATUE_PREFIX = "Ancient Statue"


def _entries(row, th):
    out = []
    for k in range(1, 11):
        name, prob = row[th[f"Item{k}"]].strip(), row[th[f"Prob{k}"]].strip()
        if name and prob:
            out.append((name, int(prob)))
    return out


def apply(monstats, tcs, keep_statues=True):
    """Mutates monstats and tcs in place; returns a list of change lines."""
    mh, th = header(monstats), header(tcs)
    index = {r[0]: i for i, r in enumerate(tcs) if r and r[0]}
    log = []

    def insert_after(anchor, row):
        pos = index[anchor] + 1
        tcs.insert(pos, row)
        for n, i in list(index.items()):
            if i >= pos:
                index[n] = i + 1
        index[row[0]] = pos

    for m in monstats[1:]:
        for d in DIFFS:
            sfx = f"({d[1]})" if d else ""
            if f"TreasureClassQuest{sfx}" not in mh:
                continue
            R = m[mh[f"TreasureClass{sfx}"]].strip()
            Q = m[mh[f"TreasureClassQuest{sfx}"]].strip()
            if not Q or Q == R or Q not in index or R not in index:
                continue
            target = Q
            reg = tcs[index[R]]
            statues = [(n, p) for n, p in _entries(reg, th) if n.startswith(STATUE_PREFIX)]
            if keep_statues and statues:
                roll, wrap = f"{R} Statue Roll", f"{Q} SP"
                if wrap not in index:
                    total = sum(p for _, p in _entries(reg, th)) + int(reg[th["NoDrop"]] or 0)
                    r1 = blank_row_like(tcs)
                    r1[0], r1[th["Picks"]] = roll, reg[th["Picks"]]
                    r1[th["NoDrop"]] = str(total - sum(p for _, p in statues))
                    for j, (n, p) in enumerate(statues, start=1):
                        r1[th[f"Item{j}"]], r1[th[f"Prob{j}"]] = n, str(p)
                    r2 = blank_row_like(tcs)
                    qrow = tcs[index[Q]]
                    r2[0], r2[th["Picks"]] = wrap, "-2"
                    for c in ("Unique", "Set", "Rare", "Magic"):  # same quality odds as Q
                        r2[th[c]] = qrow[th[c]]
                    r2[th["Item1"]], r2[th["Prob1"]] = Q, "1"
                    r2[th["Item2"]], r2[th["Prob2"]] = roll, "1"
                    insert_after(max(Q, R, key=lambda n: index[n]), r1)
                    insert_after(roll, r2)
                target = wrap
            changed = []
            for kind in TC_KINDS:
                c = mh[f"{kind}{sfx}"]
                if m[c].strip() and m[c].strip() != target:
                    changed.append(f"{kind}{sfx} {m[c]} -> {target}")
                    m[c] = target
            if changed:
                log.append(f"{m[0]}: " + "; ".join(changed))
    return log

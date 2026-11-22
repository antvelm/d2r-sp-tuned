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

    def has_statue(name, seen=()):
        if name.startswith(STATUE_PREFIX):
            return True
        if name not in index or name in seen:
            return False
        return any(has_statue(n, seen + (name,)) for n, _ in _entries(tcs[index[name]], th))

    def statue_roll(name):
        """Copy of `name`'s TC tree that keeps only the statue rolls, at the
        same per-pick odds (every other weight becomes NoDrop). Handles
        statues nested in sub-tables, e.g. Duriel (H) -> Duriel (H) - Base."""
        roll = f"{name} Statue Roll"
        if roll in index:
            return roll
        src = tcs[index[name]]
        picks = int(src[th["Picks"]] or 0)
        kept = []
        for n, p in _entries(src, th):
            if n.startswith(STATUE_PREFIX):
                kept.append((n, p))
            elif has_statue(n):
                kept.append((statue_roll(n), p))
        row = blank_row_like(tcs)
        row[0] = roll
        if picks < 0:   # sequential: keep the statue-bearing entries and their counts
            row[th["Picks"]] = str(-sum(p for _, p in kept))
        else:           # weighted: same picks, non-statue weight moves to NoDrop
            total = sum(p for _, p in _entries(src, th)) + int(src[th["NoDrop"]] or 0)
            row[th["Picks"]] = str(picks)
            row[th["NoDrop"]] = str(total - sum(p for _, p in kept))
        for j, (n, p) in enumerate(kept, start=1):
            row[th[f"Item{j}"]], row[th[f"Prob{j}"]] = n, str(p)
        insert_after(name, row)
        return roll

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
            if keep_statues and has_statue(R) and not has_statue(Q):
                wrap = f"{Q} SP"
                if wrap not in index:
                    roll = statue_roll(R)
                    r2 = blank_row_like(tcs)
                    qrow = tcs[index[Q]]
                    r2[0], r2[th["Picks"]] = wrap, "-2"
                    for c in ("Unique", "Set", "Rare", "Magic"):  # same quality odds as Q
                        r2[th[c]] = qrow[th[c]]
                    r2[th["Item1"]], r2[th["Prob1"]] = Q, "1"
                    r2[th["Item2"]], r2[th["Prob2"]] = roll, "1"
                    insert_after(max(Q, roll, key=lambda n: index[n]), r2)
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

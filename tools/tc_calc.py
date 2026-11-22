"""Treasure-class calculator for D2R treasureclassex.txt.

Computes the expected number of each rune dropped per kill of a given
treasure class, following the game's rules:

* Picks > 0  : roll `Picks` times; each roll picks one entry by weight,
               or nothing with weight NoDrop (scaled by player count).
* Picks < 0  : sequential guaranteed drops: entry i is dropped Prob_i
               times until |Picks| drops have happened.
* NoDrop scaling for /players N (party members nearby count the same):
      n = 1 + N // 2   (1->1, 2-3->2, 4-5->3, 6-7->4, 8->5)
      p = NoDrop / (NoDrop + Sum);  NoDrop' = Sum * p^n / (1 - p^n)
  (floor applied as the game does.)

Ignores the 6-items-per-kill cap and quality (MF) since runes have no quality.
Monster-level TC upgrades are not applied: pass the final TC name.
"""
import csv
import math
import re
import sys
from functools import lru_cache

RUNE_RE = re.compile(r"^r(\d\d)$")


def load_tcs(path):
    tcs = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    hdr = rows[0]
    col = {h: i for i, h in enumerate(hdr)}
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
        tcs[r[0]] = {
            "picks": int(r[col["Picks"]] or 0),
            "nodrop": int(r[col["NoDrop"]] or 0),
            "entries": entries,
        }
    return tcs


def nodrop_for_players(nodrop, total, players):
    if nodrop <= 0:
        return 0
    n = 1 + players // 2
    p = nodrop / (nodrop + total)
    pn = p ** n
    return int(math.floor(total * pn / (1 - pn)))


class Calc:
    def __init__(self, tcs, players=1):
        self.tcs = tcs
        self.players = players
        self._cache = {}

    def runes(self, tc_name):
        """Expected count of each rune (index 1..33) for one 'pick' of this TC."""
        if tc_name in self._cache:
            return self._cache[tc_name]
        m = RUNE_RE.match(tc_name)
        if m:
            v = [0.0] * 34
            v[int(m.group(1))] = 1.0
            return v
        tc = self.tcs.get(tc_name)
        if tc is None:  # plain item code (armor, gold, gem, ...)
            return [0.0] * 34
        v = [0.0] * 34
        if tc["picks"] < 0:
            left = -tc["picks"]
            for name, prob in tc["entries"]:
                if left <= 0:
                    break
                cnt = min(prob, left)
                left -= cnt
                sub = self.runes(name)
                for i in range(34):
                    v[i] += cnt * sub[i]
        else:
            total = sum(p for _, p in tc["entries"])
            nd = nodrop_for_players(tc["nodrop"], total, self.players)
            denom = total + nd
            for name, prob in tc["entries"]:
                sub = self.runes(name)
                w = prob / denom
                for i in range(34):
                    v[i] += tc["picks"] * w * sub[i]
        self._cache[tc_name] = v
        return v


RUNE_NAMES = [None, "El", "Eld", "Tir", "Nef", "Eth", "Ith", "Tal", "Ral", "Ort",
              "Thul", "Amn", "Sol", "Shael", "Dol", "Hel", "Io", "Lum", "Ko",
              "Fal", "Lem", "Pul", "Um", "Mal", "Ist", "Gul", "Vex", "Ohm", "Lo",
              "Sur", "Ber", "Jah", "Cham", "Zod"]


def main():
    path = sys.argv[1]
    players = int(sys.argv[2])
    tcs = load_tcs(path)
    c = Calc(tcs, players)
    for name in sys.argv[3:]:
        v = c.runes(name)
        print(f"== {name} (/players {players}) total runes/kill = {sum(v):.4f}")
        for i in range(1, 34):
            if v[i] > 0:
                print(f"  {RUNE_NAMES[i]:>5}: 1 in {1 / v[i]:,.0f}")


if __name__ == "__main__":
    main()

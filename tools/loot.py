"""Loot part: chase items tuned for solo play.

Chase items a solo player would otherwise farm for hundreds or thousands of
hours: uber keys, Ancient Statues, Sunder Charms, unique/set rings and
amulets (SoJ, BK, Mara's...), Rainbow Facets.

Levers
------
* boost(item, x): multiply an item's weight in every weighted TC that drops it.
  The extra weight comes out of NoDrop (weights x10 first if NoDrop is too
  small), so every other drop from that TC keeps its rate.
* jewelry quality: Unique/Set columns on the 'Jewelry A/B/C' TCs. The game uses
  the highest quality modifier along the TC chain, so this raises unique/set
  odds for rings, amulets, jewels (unique jewel at ilvl 85+ = Rainbow Facet)
  and charms without touching weapons/armor.
* jewelry rarity: rarity weights of chosen unique rings/amulets in
  uniqueitems.txt, so an SoJ is not 1.6% of unique rings.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tables import header  # noqa: E402

KEY_CODES = ("pk1", "pk2", "pk3")
ESSENCE_CODES = ("tes", "ceh", "bet", "fed")
STATUE_PREFIX = "Ancient Statue"
SUNDER_TC = "Sunder Charms"
JEWELRY_TCS = ("Jewelry A", "Jewelry B", "Jewelry C")

PRESETS = {
    "mild": dict(uber_keys_mult=2, ancient_statue_mult=2, sunder_mult=2, sunder_even_types=False,
                 essence_mult=1, jewelry_mult=1, jewelry_unique_mod=992, jewelry_set_mod=768,
                 chase_jewelry_rarity=True),
    "sp": dict(uber_keys_mult=4, ancient_statue_mult=3, sunder_mult=4, sunder_even_types=True,
               essence_mult=2, jewelry_mult=2, jewelry_unique_mod=1000, jewelry_set_mod=896,
               chase_jewelry_rarity=True),
    "generous": dict(uber_keys_mult=8, ancient_statue_mult=5, sunder_mult=8, sunder_even_types=True,
                     essence_mult=3, jewelry_mult=3, jewelry_unique_mod=1008, jewelry_set_mod=960,
                     chase_jewelry_rarity=True),
}

# unique ring/amulet -> new rarity (vanilla in comments)
CHASE_RARITY = {
    "The Stone of Jordan": 10,       # 1
    "Bul Katho's Wedding Band": 10,  # 1
    "Wisp": 5,                       # 1
    "Mara's Kaleidoscope": 10,       # 5
    "Highlord's Wrath": 10,          # 5
    "The Cat's Eye": 10,             # 5
    "Atma's Scarab": 10,             # 5
    "Metalgrid": 8,                  # 2
    "Seraph's Hymn": 8,              # 3
}


def _entries(row, th):
    out = []
    for k in range(1, 11):
        n, p = row[th[f"Item{k}"]].strip(), row[th[f"Prob{k}"]].strip()
        if n and p:
            out.append((k, n.strip('"'), int(p)))
    return out


def boost(tcs, match, mult):
    """Multiply the weight of entries for which match(name) is True in every
    weighted TC; take the added weight from NoDrop. Returns change lines."""
    if mult == 1:
        return []
    th = header(tcs)
    log = []
    for r in tcs[1:]:
        if not r or not r[0] or int(r[th["Picks"]] or 0) <= 0:
            continue
        hits = [(k, n, p) for k, n, p in _entries(r, th) if match(n)]
        if not hits:
            continue
        nd = int(r[th["NoDrop"]] or 0)
        added = sum(round(p * mult) - p for _, _, p in hits)
        if nd and nd < added:           # make room: scale the whole row x10
            for k, _, p in _entries(r, th):
                r[th[f"Prob{k}"]] = str(p * 10)
            nd *= 10
            hits = [(k, n, p * 10) for k, n, p in hits]
            added *= 10
        for k, _, p in hits:
            r[th[f"Prob{k}"]] = str(round(p * mult))
        note = ""
        if nd:
            r[th["NoDrop"]] = str(max(0, nd - added))
            if nd < added:
                note = " (NoDrop exhausted, other drops slightly reduced)"
        elif added:
            note = " (no NoDrop, other drops slightly reduced)"
        log.append(f"{r[0]}: {', '.join(n for _, n, _ in hits)} x{mult}{note}")
    return log


def grow_in_good(tcs, match, mult):
    """Multiply matching entries inside every '* Good' TC by `mult`, then make
    each parent pick that Good TC proportionally more often (extra weight from
    NoDrop, weights x10 for precision) so the Good TC's other contents
    (gems, runes) keep their per-kill rates. Same method as the runes part."""
    if mult == 1:
        return []
    th = header(tcs)
    growth = {}
    for r in tcs[1:]:
        if not r or " Good" not in r[0]:
            continue
        ents = _entries(r, th)
        old = sum(p for _, _, p in ents)
        new = 0
        for k, n, p in ents:
            if match(n):
                p = round(p * mult)
                r[th[f"Prob{k}"]] = str(p)
            new += p
        if new != old:
            growth[r[0]] = new / old
    for r in tcs[1:]:
        if not r or not r[0] or int(r[th["Picks"]] or 0) <= 0:
            continue
        hits = [(k, n, p) for k, n, p in _entries(r, th) if n in growth]
        if not hits:
            continue
        for k, _, p in _entries(r, th):
            r[th[f"Prob{k}"]] = str(p * 10)
        nd = int(r[th["NoDrop"]] or 0) * 10
        added = 0
        for k, n, p in hits:
            w = p * 10
            nw = round(w * growth[n])
            added += nw - w
            r[th[f"Prob{k}"]] = str(nw)
        if nd:
            r[th["NoDrop"]] = str(max(0, nd - added))
    return [f"jewelry x{mult} in {len(growth)} gem/jewelry/rune tables"]


def jewelry_quality(tcs, unique_mod, set_mod):
    th = header(tcs)
    for r in tcs[1:]:
        if r and r[0] in JEWELRY_TCS:
            if unique_mod:
                r[th["Unique"]] = str(unique_mod)
            if set_mod:
                r[th["Set"]] = str(set_mod)


def jewelry_rarity(uniques, table=CHASE_RARITY):
    uh = header(uniques)
    log = []
    for r in uniques[1:]:
        if r and r[0] in table:
            old = r[uh["rarity"]]
            r[uh["rarity"]] = str(table[r[0]])
            log.append(f"{r[0]}: rarity {old} -> {table[r[0]]}")
    return log


def apply(tcs, uniques, cfg):
    """cfg keys: uber_keys_mult, ancient_statue_mult, sunder_mult,
    sunder_even_types, essence_mult, jewelry_mult, jewelry_unique_mod,
    jewelry_set_mod, chase_jewelry_rarity."""
    log = []
    log += boost(tcs, lambda n: n in KEY_CODES, cfg.get("uber_keys_mult", 1))
    log += boost(tcs, lambda n: n.startswith(STATUE_PREFIX), cfg.get("ancient_statue_mult", 1))
    log += boost(tcs, lambda n: n == SUNDER_TC, cfg.get("sunder_mult", 1))
    log += boost(tcs, lambda n: n in ESSENCE_CODES, cfg.get("essence_mult", 1))
    if cfg.get("sunder_even_types"):
        th = header(tcs)
        for r in tcs[1:]:
            if r and r[0] == SUNDER_TC:
                for k, n, p in _entries(r, th):
                    r[th[f"Prob{k}"]] = "1"
                log.append("Sunder Charms: all six types equally likely")
    log += grow_in_good(tcs, lambda n: n in JEWELRY_TCS, cfg.get("jewelry_mult", 1))
    jewelry_quality(tcs, cfg.get("jewelry_unique_mod", 0), cfg.get("jewelry_set_mod", 0))
    if cfg.get("chase_jewelry_rarity"):
        log += jewelry_rarity(uniques)
    return log


# ---------------------------------------------------------------------- report
# Quality math for rings/amulets/jewels/charms (itemratio.txt, expansion, not
# uber, not class-specific): Unique 400/1/6400, Set 160/2/5600. No Magic Find.
#   c = max((ratio - (ilvl - qlvl) // div) * 128, min);  c -= c * tc_mod // 1024
#   P = 128 / c.  Unique is tried first, then set.
U_RATIO, U_DIV, U_MIN = 400, 1, 6400
S_RATIO, S_DIV, S_MIN = 160, 2, 5600


def p_quality(ilvl, qlvl, mod, ratio, div, mn):
    c = max((ratio - (ilvl - qlvl) // div) * 128, mn)
    c -= c * mod // 1024
    return 1.0 if c <= 128 else 128 / c


def tc_quality_table(rows):
    th = header(rows)
    out = {}
    for r in rows[1:]:
        if not r or not r[0] or r[0].lower() == "expansion":
            continue
        out[r[0]] = (int(r[th["Picks"]] or 0), int(r[th["NoDrop"]] or 0),
                     [(n, p) for _, n, p in _entries(r, th)],
                     int(r[th["Unique"]] or 0), int(r[th["Set"]] or 0))
    return out


def item_paths(tcs, name, code, umod=0, smod=0, seen=()):
    """Yield (expected count, unique_mod, set_mod) for every path from TC
    `name` down to base item `code` (max quality modifier along the path)."""
    t = tcs.get(name)
    if t is None:
        if name == code:
            yield 1.0, umod, smod
        return
    if name in seen:
        return
    picks, nd, ents, u, s = t
    umod, smod = max(umod, u), max(smod, s)
    if picks < 0:
        left = -picks
        for n, p in ents:
            k = min(p, left)
            left -= k
            for e, a, b in item_paths(tcs, n, code, umod, smod, seen + (name,)):
                yield k * e, a, b
    else:
        tot = sum(p for _, p in ents) + nd
        for n, p in ents:
            for e, a, b in item_paths(tcs, n, code, umod, smod, seen + (name,)):
                yield picks * p / tot * e, a, b


def unique_odds(tcs, uniques, tc_name, code, qlvl, ilvl, wanted=None):
    """Expected uniques of base `code` per kill of `tc_name` (optionally only
    the named uniques), and expected set items of that base."""
    uh = header(uniques)
    elig = [(r[0], int(r[uh["rarity"]] or 0)) for r in uniques[1:]
            if r and r[uh["code"]] == code and int(r[uh["lvl"]] or 0) <= ilvl
            and int(r[uh["rarity"]] or 0) > 0]
    tot = sum(w for _, w in elig)
    share = (sum(w for n, w in elig if wanted is None or n in wanted) / tot) if tot else 0
    u = s = 0.0
    for e, um, sm in item_paths(tcs, tc_name, code):
        pu = p_quality(ilvl, qlvl, um, U_RATIO, U_DIV, U_MIN) if tot else 0
        ps = p_quality(ilvl, qlvl, sm, S_RATIO, S_DIV, S_MIN)
        u += e * pu * share
        s += e * (1 - pu) * ps
    return u, s

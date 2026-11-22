"""Uniques part: commonly used unique gear made reachable solo, no Magic Find.

Most chase uniques are the only unique on their base (Arreat's Face is the
only unique Slayer Guard), so their uniqueitems.txt rarity changes nothing.
Vanilla, without MF, each takes hundreds to thousands of hours of Hell
farming: Arreat's Face ~1,100 h, Bartuc's ~900 h, Shako ~1,900 h.

Lever: an extra "chase roll", the same trick the game uses for Annihilus.

* 'SP Chase uL' treasure classes list the base items of the chosen uniques
  whose unique item level is <= L, with Unique = 1024: a pick is always
  that unique. A base shared with other uniques picks among them by their
  normal rarity, so it gets a proportionally bigger weight (Nightwing's
  Veil x2 for Veil of Steel, Stormlash x6 for Horizon's Tornado).
* Every drop table that can drop equipment (normal, champion, unique and
  boss tables of all difficulties, terror zones included) gets one entry
  for the chase table matching its monster level. Its weight is
  proportional to the table's equipment weight, so bosses and champions,
  which drop more equipment, roll it more often.
* The weight comes out of NoDrop, so every other drop keeps its rate.
  Champion/unique item tables have no NoDrop; there it comes out of their
  equipment entry (~1-2% fewer regular items from them).
* Level gate: a table only offers uniques its monsters can roll (table
  level, +2 champions, +3 uniques, boss monster level for boss tables).
  Below that level a unique fails and the game drops a rare of that base
  instead, so the gate is what keeps the roll clean.

The chase weight is solved so that, in Hell lvl-85 farming (900 normal,
80 champion, 20 unique kills an hour), each listed unique drops about once
every `hours_per_item` hours on average.
"""
import copy
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tables import header, blank_row_like  # noqa: E402

PRESETS = {"mild": 60, "sp": 25, "generous": 10}

# display name -> uniqueitems.txt index
CHASE = {
    # class uniques, required level 42
    "Bartuc's Cut-Throat": "Cutthroat1",
    "Titan's Revenge": "Titan's Revenge",
    "Lycander's Aim": "Lycander's Aim",
    "Lycander's Flank": "Lycander's Flank",
    "Arreat's Face": "Arreat's Face",
    "Jalal's Mane": "Jalal's Mane",
    "Homunculus": "Homunculus",
    "Herald of Zakarum": "Herald of Zakarum",
    "The Oculus": "The Oculus",
    # class uniques, elite
    "Jade Talon": "Jadetalon",
    "Spirit Keeper": "Spiritkeeper",
    "Ravenlore": "Ravenlore",
    "Eschuta's Temper": "Eschuta's temper",
    "Death's Fathom": "Fathom",
    "Thunderstroke": "Thunderstroke",
    "Alma Negra": "Alma Negra",
    # helms
    "Harlequin Crest (Shako)": "Harlequin Crest",
    "Vampire Gaze": "Vampiregaze",
    "Andariel's Visage": "Andariel's Visage",
    "Crown of Ages": "Crown of Ages",
    "Nightwing's Veil": "Nightwing's Veil",
    "Griffon's Eye": "Griffon's Eye",
    "Kira's Guardian": "Kira's Guardian",
    # body armor
    "Skin of the Vipermagi": "Skin of the Vipermagi",
    "Shaftstop": "Shaftstop",
    "Duriel's Shell": "Duriel's Shell",
    "Guardian Angel": "Guardian Angel",
    "Leviathan": "Leviathan",
    "Arkaine's Valor": "Arkaine's Valor",
    "Ormus' Robes": "Ormus' Robes",
    "Templar's Might / Tyrael's Might": "Templar's Might",
    # gloves
    "Chance Guards": "Chance Guards",
    "Magefist": "Magefist",
    "Frostburn": "Frostburn",
    "Dracul's Grasp": "Dracul's Grasp",
    "Steelrend": "Steelrend",
    # belts
    "String of Ears": "String of Ears",
    "Snowclash": "Snowclash",
    "Thundergod's Vigor": "Thudergod's Vigor",
    "Nosferatu's Coil": "Nosferatu's Coil",
    "Verdungo's Hearty Cord": "Verdugo's Hearty Cord",
    "Arachnid Mesh": "Arachnid Mesh",
    # boots
    "Waterwalk": "Waterwalk",
    "Silkweave": "Silkweave",
    "War Traveler": "Wartraveler",
    "Gore Rider": "Gorerider",
    "Sandstorm Trek": "Sandstorm Trek",
    "Marrowwalk": "Marrowwalk",
    # shields
    "Lidless Wall": "Lidless Wall",
    "Stormshield": "Stormshield",
    # weapons
    "Buriza-Do Kyanon": "Buriza-Do Kyanon",
    "Lightsabre": "Lightsabre",
    "Wizardspike": "Wizardspike",
    "Heaven's Light": "Heaven's Light",
    "Death's Web": "Deaths's Web",
    "Doombringer": "Doombringer",
    "Fleshripper": "Fleshripper",
    "Eaglehorn": "Eaglehorn",
    "Windforce": "Windforce",
    "The Reaper's Toll": "The Reaper's Toll",
    "The Grandfather": "The Grandfather",
    "Tomb Reaver": "Tomb Reaver",
    "Stormlash": "Stormlash",
}

PREFIX = "SP Chase"
HOUR = [("Act 5 (H) H2H C", 900), ("Act 5 (H) Champ C", 80), ("Act 5 (H) Unique C", 20)]
AUTO_TC = re.compile(r"^(weap|armo|bow|mele|mac|spea|pole|swor|axe|jav|staf|scep|wand|knif|club|hamm)\d+$", re.I)
DIFFS = ["", "(N)", "(H)"]


def _entries(row, th):
    out = []
    for k in range(1, 11):
        n, p = row[th[f"Item{k}"]].strip(), row[th[f"Prob{k}"]].strip()
        if n and p:
            out.append((k, n.strip('"'), int(p)))
    return out


def resolve(names, uniques):
    """settings names (display or index) -> [(index, code, lvl, weight)];
    unknown names reported. A base shared with other uniques (Nightwing's
    Veil / Veil of Steel) gets weight total rarity / own rarity, so the
    listed unique still comes up at the target rate; its siblings get the
    rest of those picks."""
    uh = header(uniques)
    by_index = {r[0]: r for r in uniques[1:] if r and r[0]}
    lower = {k.lower(): v for k, v in CHASE.items()}
    rar = {}
    for r in uniques[1:]:
        if r and r[0] and r[uh["spawnable"]] == "1" and int(r[uh["rarity"]] or 0) > 0:
            rar.setdefault(r[uh["code"]], []).append((r[0], int(r[uh["rarity"]])))
    out, missing, seen = [], [], set()
    for n in names:
        idx = CHASE.get(n) or lower.get(n.lower()) or n
        r = by_index.get(idx)
        if r is None or r[uh["spawnable"]] != "1" or int(r[uh["rarity"]] or 0) <= 0:
            missing.append(n)
            continue
        code = r[uh["code"]]
        if code in seen:                # one entry per base
            continue
        seen.add(code)
        sib = rar.get(code, [])
        w = max(1, round(sum(x for _, x in sib) / int(r[uh["rarity"]])))
        out.append((idx, code, int(r[uh["lvl"]] or 0), w))
    return out, missing


def _equipment_tcs(tcs, th):
    """Names of pure equipment TCs (every entry an auto weap/armo TC or another
    equipment TC): 'Act 5 (H) Equip C', 'Act 5 (H) Melee C', 'Act 5 (H) Bow C'..."""
    rows = {r[0]: r for r in tcs[1:] if r and r[0]}
    eq = set()
    changed = True
    while changed:
        changed = False
        for name, r in rows.items():
            if name in eq or int(r[th["Picks"]] or 0) <= 0 or int(r[th["NoDrop"]] or 0):
                continue
            ents = _entries(r, th)
            if ents and all(AUTO_TC.match(n) or n in eq for _, n, _ in ents):
                eq.add(name)
                changed = True
    return eq


def _boss_levels(monstats):
    """TC name -> lowest level of a boss monster that uses it."""
    if monstats is None:
        return {}
    mh = header(monstats)
    out = {}
    for m in monstats[1:]:
        if not m or m[mh["boss"]] != "1":
            continue
        for d in DIFFS:
            lv = m[mh["Level" + d]] if ("Level" + d) in mh else ""
            if not lv.strip():
                continue
            for c, i in mh.items():
                if c.startswith("TreasureClass") and c.endswith(d) and (d or "(" not in c):
                    t = m[i].strip()
                    if t:
                        out[t] = min(out.get(t, 999), int(lv))
    return out


def _children_levels(tcs, th, boss_lv):
    """Propagate boss levels into the sub-tables they pick from
    ('Mephisto (H) Desecrated A' -> 'Mephisto Item (H) Desecrated A')."""
    rows = {r[0]: r for r in tcs[1:] if r and r[0]}
    out = dict(boss_lv)
    stack = list(boss_lv)
    while stack:
        n = stack.pop()
        r = rows.get(n)
        if r is None:
            continue
        for _, c, _ in _entries(r, th):
            if c in rows and (c not in out or out[c] > out[n]):
                out[c] = out[n]
                stack.append(c)
    return out


def _gate(name, row, th, eq_rows, lv_of):
    if name in lv_of:
        return lv_of[name]
    lv = row[th["level"]].strip()
    if lv:
        g = int(lv)
    else:
        # no level of its own and not a boss table (Cow (H)...): stay a tier
        # below its equipment table, whose level is that tier's top monster level
        g = max((int(r[th["level"]] or 0) for r in eq_rows), default=0) - 3
    if "Citem" in name:
        g += 2
    elif "Uitem" in name:
        g += 3
    return g


def _insert(tcs, th, items, k, monstats):
    """Add chase TCs and entries with chase weight = k * equipment weight
    per drop table. Returns change lines."""
    eq = _equipment_tcs(tcs, th)
    rows = {r[0]: r for r in tcs[1:] if r and r[0]}
    lv_of = _children_levels(tcs, th, _boss_levels(monstats))
    items = sorted(items, key=lambda t: t[2])
    levels = sorted({t[2] for t in items})
    log, used, targets = [], set(), []

    for r in tcs[1:]:
        if not r or not r[0] or r[0] in eq or r[0].startswith(PREFIX) or int(r[th["Picks"]] or 0) <= 0:
            continue
        ents = _entries(r, th)
        eq_ents = [(j, n, p) for j, n, p in ents if n in eq]
        if not eq_ents:
            continue
        g = _gate(r[0], r, th, [rows[n] for _, n, _ in eq_ents], lv_of)
        top = max((lv for lv in levels if lv <= g), default=None)
        if top is None:
            continue
        if len(ents) >= 10:
            log.append(f"{r[0]}: no free slot, skipped")
            continue
        targets.append((r, ents, eq_ents, top))

    for r, ents, eq_ents, top in targets:
        scale = 100
        nd = int(r[th["NoDrop"]] or 0) * scale
        E = sum(p for _, _, p in eq_ents) * scale
        w = max(1, round(k * E))
        for j, _, p in ents:
            r[th[f"Prob{j}"]] = str(p * scale)
        if nd >= w:
            r[th["NoDrop"]] = str(nd - w)
        else:                            # no NoDrop: take it from the equipment entries
            if nd:
                r[th["NoDrop"]] = str(nd)
            left = w
            for j, _, p in sorted(eq_ents, key=lambda e: -e[2]):
                cut = min(left, p * scale - 1)
                r[th[f"Prob{j}"]] = str(p * scale - cut)
                left -= cut
                if not left:
                    break
        slot = len(ents) + 1
        r[th[f"Item{slot}"]], r[th[f"Prob{slot}"]] = f"{PREFIX} u{top}", str(w)
        used.add(top)

    # chase tables, chained by level: 'SP Chase u55' = 'SP Chase u50' + the items at 55
    new_rows, prev, count = [], None, 0
    for lv in levels:
        here = [(code, w) for _, code, l, w in items if l == lv]
        ents = ([(f"{PREFIX} u{prev}", count)] if prev else [])
        chunks = [here[i:i + 9] for i in range(0, len(here), 9)]
        if len(chunks) > 1 or len(ents) + len(here) > 10:
            for c_i, ch in enumerate(chunks):
                sub = blank_row_like(tcs)
                sub[0] = f"{PREFIX} u{lv} part{c_i + 1}"
                _fill(sub, th, ch)
                new_rows.append(sub)
                ents.append((sub[0], sum(w for _, w in ch)))
        else:
            ents += here
        row = blank_row_like(tcs)
        row[0] = f"{PREFIX} u{lv}"
        _fill(row, th, ents)
        new_rows.append(row)
        count += sum(w for _, w in here)
        prev = lv
    first = min(tcs.index(r) for r, *_ in targets) if targets else len(tcs)
    tcs[first:first] = new_rows
    log.append(f"{len(targets)} drop tables get a chase roll; {len(new_rows)} chase tables, "
               f"{len(items)} uniques, levels {levels[0]}-{levels[-1]}")
    return log


def _fill(row, th, ents):
    row[th["Picks"]] = "1"
    row[th["Unique"]] = "1024"
    for j, (n, p) in enumerate(ents, start=1):
        row[th[f"Item{j}"]], row[th[f"Prob{j}"]] = n, str(p)


def _tc_dict(tcs, th):
    out = {}
    for r in tcs[1:]:
        if r and r[0]:
            out[r[0]] = (int(r[th["Picks"]] or 0), int(r[th["NoDrop"]] or 0),
                         [(n, p) for _, n, p in _entries(r, th)])
    return out


def expect(T, name, pred, seen=()):
    t = T.get(name)
    if t is None:
        return 1.0 if pred(name) else 0.0
    if name in seen:
        return 0.0
    picks, nd, ents = t
    if picks < 0:
        left, s = -picks, 0.0
        for n, w in ents:
            k = min(w, left)
            left -= k
            s += k * expect(T, n, pred, seen + (name,))
        return s
    tot = sum(w for _, w in ents) + nd
    return picks * sum(w / tot * expect(T, n, pred, seen + (name,)) for n, w in ents)


def chase_per_hour(tcs, code=None, hour=HOUR):
    th = header(tcs)
    T = _tc_dict(tcs, th)

    def via_chase(name, seen=(), inside=False):
        t = T.get(name)
        if t is None:
            return 1.0 if inside and (code is None or name == code) else 0.0
        if name in seen:
            return 0.0
        inside = inside or name.startswith(PREFIX)
        picks, nd, ents = t
        if picks < 0:
            left, s = -picks, 0.0
            for n, w in ents:
                k = min(w, left)
                left -= k
                s += k * via_chase(n, seen + (name,), inside)
            return s
        tot = sum(w for _, w in ents) + nd
        return picks * sum(w / tot * via_chase(n, seen + (name,), inside) for n, w in ents)

    return sum(n * via_chase(t) for t, n in hour)


def apply(tcs, uniques, cfg, monstats=None):
    """Mutates tcs in place. cfg: hours_per_item, items (names). Returns log lines."""
    th = header(tcs)
    items, missing = resolve(cfg["items"], uniques)
    log = [f"unknown or unspawnable, skipped: {', '.join(missing)}"] if missing else []
    if not items:
        return log
    # solve k on a scratch copy: chase drops/hour are linear in k
    trial = copy.deepcopy(tcs)
    _insert(trial, th, items, 0.01, monstats)
    got = chase_per_hour(trial)
    want = sum(t[3] for t in items) / float(cfg["hours_per_item"])
    k = 0.01 * want / got if got else 0
    log += _insert(tcs, th, items, k, monstats)
    log.append(f"chase rate k={k:.4f} of equipment weight: ~{chase_per_hour(tcs):.2f} chase uniques "
               f"per Hell lvl-85 hour, ~1 per {cfg['hours_per_item']} h each")
    return log


# ---------------------------------------------------------------------- report
# Vanilla odds model: auto TCs (weapN/armoN: bases of item level N-2..N,
# weighted by 'rarity') + itemratio.txt quality math (no Magic Find).
def _auto_tcs(excel):
    from tables import read_table
    Q, base = {}, {}
    for f, pre in (("weapons.txt", "weap"), ("armor.txt", "armo")):
        t = read_table(os.path.join(excel, f))
        h = header(t)
        for r in t[1:]:
            if not r or not r[h["code"]]:
                continue
            base[r[h["code"]]] = (int(r[h["level"]] or 0), r[h["type"]])
            rar = int(r[h["rarity"]] or 0)
            if r[h["spawnable"]] == "1" and rar > 0:
                n = max(3, -(-int(r[h["level"]] or 0) // 3) * 3)
                Q.setdefault(f"{pre}{n}", (1, 0, [], 0, 0))[2].append((r[h["code"]], rar))
    it = read_table(os.path.join(excel, "itemtypes.txt"))
    ih = header(it)
    types = {r[ih["Code"]]: r for r in it[1:] if r and r[ih["Code"]]}

    def is_class(t, seen=()):
        r = types.get(t)
        if not r or t in seen:
            return False
        return bool(r[ih["Class"]]) or any(is_class(r[ih[e]], seen + (t,)) for e in ("Equiv1", "Equiv2") if r[ih[e]])
    return Q, {c: (lv, is_class(t)) for c, (lv, t) in base.items()}


def unique_rates(tcs, uniques, excel, hour=None):
    """{index: (normal path per hour, chase path per hour)} for the CHASE uniques."""
    import loot
    hour = hour or [("Act 5 (H) H2H C", 85, 900), ("Act 5 (H) Champ C", 87, 80), ("Act 5 (H) Unique C", 88, 20)]
    autos, bases = _auto_tcs(excel)
    Q = loot.tc_quality_table(tcs)
    Q.update(autos)
    uh = header(uniques)
    out = {}
    for idx, code, ulvl, _ in resolve(list(CHASE), uniques)[0]:
        sib = [(x[0], int(x[uh["rarity"]] or 0), int(x[uh["lvl"]] or 0)) for x in uniques[1:]
               if x and x[uh["code"]] == code and x[uh["spawnable"]] == "1"]
        qlvl, cls = bases[code]
        ratio, div, mn = (240, 3, 6400) if cls else (400, 1, 6400)
        normal = chase = 0.0
        for t, il, n in hour:
            el = [(s, w) for s, w, lv in sib if lv <= il and w > 0]
            share = sum(w for s, w in el if s == idx) / max(1, sum(w for _, w in el))
            for e, um, _ in loot.item_paths(Q, t, code):
                normal += n * e * loot.p_quality(il, qlvl, um, ratio, div, mn) * share * (um < 1024)
                chase += n * e * share * (um >= 1024)
        out[idx] = (normal, chase)
    return out


def main():
    import argparse
    from tables import read_table
    ap = argparse.ArgumentParser(description="Uniques part: vanilla vs modded hours per chase unique")
    ap.add_argument("cmd", choices=["report"])
    ap.add_argument("--preset", default="sp", choices=list(PRESETS))
    ap.add_argument("--excel", default=os.path.join(os.path.dirname(__file__), "..", "reference", "data", "global", "excel"))
    a = ap.parse_args()
    tc = read_table(os.path.join(a.excel, "treasureclassex.txt"))
    un = read_table(os.path.join(a.excel, "uniqueitems.txt"))
    ms = read_table(os.path.join(a.excel, "monstats.txt"))
    van = unique_rates(tc, un, a.excel)
    mod_tc = [list(r) for r in tc]
    apply(mod_tc, un, {"hours_per_item": PRESETS[a.preset], "items": list(CHASE)}, ms)
    mod = unique_rates(mod_tc, un, a.excel)
    inv = {v: k for k, v in CHASE.items()}
    print(f"Hell lvl-85 farming (900 normal / 80 champion / 20 unique kills an hour), no MF, preset {a.preset}")
    print(f"{'unique':34} {'vanilla h':>10} {'modded h':>9}")
    for idx, (vn, _) in van.items():
        mn, mc = mod[idx]
        print(f"{inv[idx]:34} {1 / vn if vn else float('inf'):10,.0f} {1 / (mn + mc) if mn + mc else float('inf'):9,.0f}")


if __name__ == "__main__":
    main()

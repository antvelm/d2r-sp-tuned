"""Compute the Uniques part's numbers and render docs/uniques-proposal.html
(standalone) + docs/uniques-index.html (artifact version) from
docs/uniques-template.html. Data also goes to docs/uniques-data.json.

    python tools/make_uniques_page.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bosses  # noqa: E402
import loot  # noqa: E402
import runes  # noqa: E402
import uniques  # noqa: E402
from site_nav import nav  # noqa: E402
from tables import read_table, header  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
V = os.path.join(ROOT, "reference", "data", "global", "excel")
HELL = [("Act 5 (H) H2H C", 85, 900), ("Act 5 (H) Champ C", 87, 80), ("Act 5 (H) Unique C", 88, 20)]
NM = [("Act 5 (N) H2H C", 62, 900), ("Act 5 (N) Champ C", 64, 80), ("Act 5 (N) Unique C", 65, 20)]
# slot groups, in CHASE order: (label, first name of the group)
GROUPS = [("Class · req 42", "Bartuc's Cut-Throat"), ("Class · elite", "Jade Talon"),
          ("Helm", "Harlequin Crest (Shako)"), ("Body armor", "Skin of the Vipermagi"),
          ("Gloves", "Chance Guards"), ("Belt", "String of Ears"), ("Boots", "Waterwalk"),
          ("Shield", "Lidless Wall"), ("Weapon", "Buriza-Do Kyanon")]


def load(excel):
    """(treasureclassex, uniqueitems, monstats, superunique lair levels) of one table set."""
    return (read_table(os.path.join(excel, "treasureclassex.txt")),
            read_table(os.path.join(excel, "uniqueitems.txt")),
            read_table(os.path.join(excel, "monstats.txt")),
            uniques.superunique_levels(excel))


def modded(tc, un, ms, lairs, hours):
    m = [list(r) for r in tc]
    log = uniques.apply(m, un, {"hours_per_item": hours, "items": list(uniques.CHASE)}, ms, lairs)
    return m, log


def main():
    tc, un, ms, lairs = load(V)
    uh = header(un)
    U = {r[0]: r for r in un[1:] if r and r[0]}
    names = {}
    for f in ("weapons.txt", "armor.txt"):
        t = read_table(os.path.join(V, f))
        h = header(t)
        names.update({r[h["code"]]: r[h["name"]] for r in t[1:] if r and r[h["code"]]})

    hrs = lambda d, i, both=True: (1 / (d[i][0] + d[i][1] * both)) if (d[i][0] + d[i][1] * both) else None
    van_h, van_n = uniques.unique_rates(tc, un, V, HELL), uniques.unique_rates(tc, un, V, NM)
    mod = {}
    for p, h in uniques.PRESETS.items():
        m, _ = modded(tc, un, ms, lairs, h)
        mod[p] = (uniques.unique_rates(m, un, V, HELL), uniques.unique_rates(m, un, V, NM))

    starts = {first: label for label, first in GROUPS}
    rows, cat = [], None
    for disp, idx in uniques.CHASE.items():
        cat = starts.get(disp, cat)
        r = U[idx]
        code = r[uh["code"]]
        row = dict(name=disp, index=idx, base=names.get(code, code), code=code, cat=cat,
                   ilvl=int(r[uh["lvl"]]), req=int(r[uh["lvl req"]]),
                   vh=hrs(van_h, idx, False), vn=hrs(van_n, idx, False))
        for p in mod:
            row[f"{p}_h"], row[f"{p}_n"] = hrs(mod[p][0], idx), hrs(mod[p][1], idx)
        rows.append({k: round(v, 1) if isinstance(v, float) else v for k, v in row.items()})

    # table counts (sp) and chase odds per Hell Baal kill with every part on (sp presets)
    m, log = modded(tc, un, ms, lairs, uniques.PRESETS["sp"])
    drop = int(next(line for line in log if "drop tables get" in line).split()[0])
    chase_tables = sum(1 for r in m if r and r[0].startswith(uniques.PREFIX))
    tcb, unb, msb, lairs_b = load(os.path.join(V, "base"))
    _, logb = modded(tcb, unb, msb, lairs_b, uniques.PRESETS["sp"])
    drop_b = int(next(line for line in logb if "drop tables get" in line).split()[0])
    full = runes.apply(tc)
    full = [list(r) for r in full]
    loot.apply(full, [list(r) for r in un], loot.PRESETS["sp"])
    uniques.apply(full, un, {"hours_per_item": uniques.PRESETS["sp"], "items": list(uniques.CHASE)}, ms, lairs)
    bosses.apply([list(r) for r in ms], full)
    baal = uniques.chase_per_hour(full, hour=[("Baalq (H) SP", 1)])
    meta = dict(drop_tables=drop, drop_tables_base=drop_b, chase_tables=chase_tables,
                baal_one_in=round(1 / baal) if baal else "-")

    json.dump({"meta": meta, "rows": rows}, open(os.path.join(ROOT, "docs", "uniques-data.json"), "w"), indent=1)
    tpl = open(os.path.join(ROOT, "docs", "uniques-template.html"), encoding="utf-8").read()
    html = (tpl.replace("__DATA__", json.dumps(rows, separators=(",", ":")))
               .replace("__META__", json.dumps(meta, separators=(",", ":")))
               .replace("__NAV__", nav("uniques")))
    open(os.path.join(ROOT, "docs", "uniques-index.html"), "w", encoding="utf-8").write(html)
    standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                  '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                  + html.replace("</style>\n", "</style>\n</head>\n<body>\n", 1) + "\n</body>\n</html>\n")
    open(os.path.join(ROOT, "docs", "uniques-proposal.html"), "w", encoding="utf-8").write(standalone)
    print(meta)
    print(f"{len(rows)} uniques -> docs/uniques-proposal.html, docs/uniques-index.html")


if __name__ == "__main__":
    main()

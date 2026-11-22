"""Compute loot proposal numbers (full pipeline: runes sp -> loot -> bosses)
and render docs/loot-proposal.html (standalone) + docs/loot-index.html."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import bosses  # noqa: E402
import loot  # noqa: E402
import runes  # noqa: E402
from tables import read_table, rows_to_tcs  # noqa: E402
from tc_calc import Calc  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
V = os.path.join(ROOT, "reference", "data", "global", "excel")
HOUR = [("Act 5 (H) H2H C", 85, 900), ("Act 5 (H) Champ C", 87, 80), ("Act 5 (H) Unique C", 88, 20)]


def exp_items(tcs, name, pred, seen=()):
    t = tcs.get(name)
    if t is None:
        return 1.0 if pred(name) else 0.0
    if name in seen:
        return 0.0
    if t["picks"] < 0:
        left, s = -t["picks"], 0.0
        for n, w in t["entries"]:
            k = min(w, left)
            left -= k
            s += k * exp_items(tcs, n, pred, seen + (name,))
        return s
    tot = sum(w for _, w in t["entries"]) + t["nodrop"]
    return t["picks"] * sum(w / tot * exp_items(tcs, n, pred, seen + (name,)) for n, w in t["entries"])


def boss_tc(monstats, mid):
    h = {c: i for i, c in enumerate(monstats[0])}
    return next(r for r in monstats if r[0] == mid)[h["TreasureClass(H)"]]


def build(preset):
    tc = read_table(os.path.join(V, "treasureclassex.txt"))
    un = read_table(os.path.join(V, "uniqueitems.txt"))
    ms = read_table(os.path.join(V, "monstats.txt"))
    tc = runes.apply(tc)
    if preset:
        loot.apply(tc, un, loot.PRESETS[preset])
    bosses.apply(ms, tc)
    return tc, un, ms


def numbers(preset):
    tc, un, ms = build(preset)
    T = rows_to_tcs(tc)
    Q = loot.tc_quality_table(tc)
    code = lambda c: (lambda n: n == c)
    out = {}
    for key, c, src in [("Key of Terror", "pk1", "Countess (H)"), ("Key of Hate", "pk2", "Summoner (H)"),
                        ("Key of Destruction", "pk3", "Nihlathak (H)")]:
        out[key] = {"per": exp_items(T, src, code(c)), "unit": "boss kill", "src": src}
    for key, mid, c in [("Talic's Anguish (Act 1)", "andariel", "ua1"), ("Korlic's Pain (Act 2)", "duriel", "ua2"),
                        ("Madawc's Ire (Act 3)", "mephisto", "ua3"), ("Bul-Kathos' Nightmare (Act 4)", "diablo", "ua4"),
                        ("Worusk's End (Act 5)", "baalcrab", "ua5")]:
        t = boss_tc(ms, mid)
        out[key] = {"per": exp_items(T, t, code(c)), "unit": "boss kill", "src": t}
    herald = "Act 5 (H) Herald A"
    out["Latent Sunder Charm (any)"] = {"per": exp_items(T, herald, lambda n: n.startswith("PreCrafted")), "unit": "Herald kill", "src": herald}
    out["Black Cleft (rarest Sunder)"] = {"per": exp_items(T, herald, lambda n: n == "PreCrafted Black Cleft"), "unit": "Herald kill", "src": herald}
    for key, cd, want in [("The Stone of Jordan", "rin", {"The Stone of Jordan"}),
                          ("Bul-Kathos' Wedding Band", "rin", {"Bul Katho's Wedding Band"}),
                          ("Mara's Kaleidoscope", "amu", {"Mara's Kaleidoscope"}),
                          ("Highlord's Wrath", "amu", {"Highlord's Wrath"}),
                          ("Any unique ring", "rin", None), ("Any unique amulet", "amu", None),
                          ("Rainbow Facet", "jew", None)]:
        out[key] = {"per": sum(n * loot.unique_odds(Q, un, t, cd, 1, il, want)[0] for t, il, n in HOUR),
                    "unit": "hour", "src": "Hell lvl-85 farming"}
    out["Set ring/amulet"] = {"per": sum(n * (loot.unique_odds(Q, un, t, "rin", 1, il)[1] + loot.unique_odds(Q, un, t, "amu", 1, il)[1]) for t, il, n in HOUR),
                              "unit": "hour", "src": "Hell lvl-85 farming"}
    out["Rings + amulets (all qualities)"] = {"per": sum(n * sum(e for e, _, _ in loot.item_paths(Q, t, cd)) for t, _, n in HOUR for cd in ("rin", "amu")),
                                              "unit": "hour", "src": "Hell lvl-85 farming"}
    for key, c, mid in [("Essence of Suffering", "tes", "andariel"), ("Essence of Hatred", "ceh", "mephisto"),
                        ("Essence of Terror", "bet", "diablo"), ("Essence of Destruction", "fed", "baalcrab")]:
        t = boss_tc(ms, mid)
        out[key] = {"per": exp_items(T, t, code(c)), "unit": "boss kill", "src": t}
    # side effects: rune floor & herald other drops
    tv = read_table(os.path.join(V, "treasureclassex.txt"))
    out["_rune_floor_fails"] = len(runes.floor_check(tv, tc, players=(1,))) if preset else 0
    return out


def main():
    data = {"presets": {p: numbers(p) for p in (None, "mild", "sp", "generous")},
            "params": loot.PRESETS, "rarity": loot.CHASE_RARITY}
    data["presets"]["vanilla"] = data["presets"].pop(None)
    # 'vanilla' column = vanilla drop tables (no runes/bosses either)
    tc = read_table(os.path.join(V, "treasureclassex.txt"))
    T = rows_to_tcs(tc)
    van = data["presets"]["vanilla"]
    for key, src in [("Madawc's Ire (Act 3)", "Mephisto (H)"), ("Bul-Kathos' Nightmare (Act 4)", "Diablo (H)"),
                     ("Worusk's End (Act 5)", "Baal (H)"), ("Korlic's Pain (Act 2)", "Duriel (H)")]:
        c = {"Madawc": "ua3", "Bul-Ka": "ua4", "Worusk": "ua5", "Korlic": "ua2"}[key[:6]]
        van[key] = {"per": exp_items(T, src, lambda n, c=c: n == c), "unit": "boss kill", "src": src}
    for key, c, src in [("Essence of Hatred", "ceh", "Mephisto (H)"), ("Essence of Terror", "bet", "Diablo (H)"),
                        ("Essence of Destruction", "fed", "Baal (H)")]:
        van[key] = {"per": exp_items(T, src, lambda n, c=c: n == c), "unit": "boss kill", "src": src}
    json.dump(data, open(os.path.join(ROOT, "docs", "loot-data.json"), "w"), indent=1)
    tpl = os.path.join(ROOT, "docs", "loot-template.html")
    if os.path.exists(tpl):
        rune_tpl = open(os.path.join(ROOT, "docs", "template.html"), encoding="utf-8").read()
        style = rune_tpl.split("<style>", 1)[1].split("</style>", 1)[0].strip(chr(10))
        html = (open(tpl, encoding="utf-8").read().replace("__STYLE__", style)
                .replace("__DATA__", json.dumps(data, separators=(",", ":"))))
        open(os.path.join(ROOT, "docs", "loot-index.html"), "w", encoding="utf-8").write(html)
        standalone = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                      '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                      + html.replace("</style>\n", "</style>\n</head>\n<body>\n", 1) + "\n</body>\n</html>\n")
        open(os.path.join(ROOT, "docs", "loot-proposal.html"), "w", encoding="utf-8").write(standalone)
    for k, v in data["presets"]["vanilla"].items():
        if k.startswith("_"):
            continue
        row = [data["presets"][p].get(k, {}).get("per", 0) for p in ("vanilla", "mild", "sp", "generous")]
        fmt = lambda x: f"1 in {1 / x:,.1f}" if x and x < 1 else (f"{x:.2f}" if x else "-")
        unit = v["unit"]
        print(f"{k:34} per {unit:11} " + " | ".join(f"{fmt(x):>14}" for x in row))
    print("rune floor fails:", {p: data['presets'][p]['_rune_floor_fails'] for p in data['presets']})


if __name__ == "__main__":
    main()

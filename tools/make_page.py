"""Regenerate docs/index.html from docs/template.html with fresh numbers.

    python tools/make_page.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import runes_mod as m  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SHOW_ROWS = ["Runes 17", "Runes 16", "Runes 12", "Act 5 (H) Good", "Act 5 (H) H2H C"]


def tc_rows(rows):
    tcs = m.rows_to_tcs(rows)
    return {n: tcs[n] for n in SHOW_ROWS}


def main():
    vanilla = m.read_table(m.VANILLA)
    data = {"presets": {}}
    for name, preset in m.PRESETS.items():
        rows = m.apply_preset(vanilla, preset)
        rep = m.report(rows, 1)
        rep["params"] = preset
        rep["rows"] = tc_rows(rows)
        data["presets"][name] = rep
    data["hour_mix"] = m.HOUR_MIX
    tpl = open(os.path.join(ROOT, "docs", "template.html"), encoding="utf-8").read()
    out = tpl.replace("__DATA__", json.dumps(data, separators=(",", ":")))
    with open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8") as f:
        f.write(out)
    print("wrote docs/index.html", len(out) // 1024, "KB")


if __name__ == "__main__":
    main()

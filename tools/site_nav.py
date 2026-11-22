"""Shared site pieces for the docs pages, and the hub page.

    python tools/site_nav.py     # writes docs/index.html (hub, standalone)
                              # and docs/hub-index.html (hub, artifact version)

nav(current) is the bar every page shows at the top (generators replace
__NAV__ in their templates with it). Links are relative, so they work from
the docs/ folder and inside a multi-file artifact.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PAGES = [("hub", "Overview", "index.html"), ("runes", "Runes", "rune-proposal.html"),
         ("loot", "Loot", "loot-proposal.html"), ("uniques", "Uniques", "uniques-proposal.html")]

NAV_CSS = """<style>
.sp-nav{--nv-bg:#ffffff;--nv-fg:#1c1f26;--nv-muted:#5d6472;--nv-line:#d9dce3;--nv-gold:#8a6d2b;--nv-soft:#efe6cf;
  background:var(--nv-bg);border-bottom:1px solid var(--nv-line);font:500 14px/1.2 "Inter",system-ui,-apple-system,"Segoe UI",sans-serif}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) .sp-nav{--nv-bg:#1a1c22;--nv-fg:#e7e4dc;--nv-muted:#9aa0ab;--nv-line:#2c2f37;--nv-gold:#c7ab6b;--nv-soft:#2b2618}}
:root[data-theme="dark"] .sp-nav{--nv-bg:#1a1c22;--nv-fg:#e7e4dc;--nv-muted:#9aa0ab;--nv-line:#2c2f37;--nv-gold:#c7ab6b;--nv-soft:#2b2618}
.sp-nav .sp-in{max-width:1180px;margin:0 auto;display:flex;flex-wrap:wrap;align-items:center;gap:6px 18px;
  padding-block:10px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.sp-nav .sp-brand{font:700 15px/1 "Cinzel",Georgia,serif;color:var(--nv-gold);letter-spacing:.04em;text-decoration:none}
.sp-nav .sp-links{display:flex;flex-wrap:wrap;gap:4px}
.sp-nav a.sp-l{color:var(--nv-muted);text-decoration:none;padding:6px 10px;border-radius:6px}
.sp-nav a.sp-l:hover{color:var(--nv-fg);background:var(--nv-soft)}
.sp-nav a.sp-l[aria-current="page"]{color:var(--nv-fg);background:var(--nv-soft);box-shadow:inset 0 -2px 0 var(--nv-gold)}
.sp-nav a:focus-visible{outline:2px solid var(--nv-gold);outline-offset:2px}
</style>"""


def nav(current):
    cur = ' aria-current="page"'
    links = "".join(f'<a class="sp-l" href="{href}"{cur if key == current else ""}>{label}</a>'
                    for key, label, href in PAGES)
    return (NAV_CSS + '\n<nav class="sp-nav" aria-label="SPTuned pages"><div class="sp-in">'
            '<a class="sp-brand" href="index.html">SPTuned</a>'
            f'<div class="sp-links">{links}</div></div></nav>\n')


def standalone(html):
    """Artifact fragment -> full document to open straight from the repo."""
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + html.replace("</style>\n", "</style>\n</head>\n<body>\n", 1) + "\n</body>\n</html>\n")


def main():
    tpl = open(os.path.join(ROOT, "docs", "hub-template.html"), encoding="utf-8").read()
    u = json.load(open(os.path.join(ROOT, "docs", "uniques-data.json")))
    rows = u["rows"]
    med = lambda k: sorted(r[k] for r in rows if r[k])[len([r for r in rows if r[k]]) // 2]
    facts = dict(uniques=len(rows), u_van=f"{med('vh'):,.0f}", u_sp=f"{med('sp_h'):,.0f}",
                 drop_tables=u["meta"]["drop_tables"], baal_one_in=u["meta"]["baal_one_in"])
    html = tpl.replace("__NAV__", nav("hub"))
    for k, v in facts.items():
        html = html.replace(f"__{k.upper()}__", str(v))
    open(os.path.join(ROOT, "docs", "hub-index.html"), "w", encoding="utf-8").write(html)
    open(os.path.join(ROOT, "docs", "index.html"), "w", encoding="utf-8").write(standalone(html))
    print("wrote docs/index.html and docs/hub-index.html", facts)


if __name__ == "__main__":
    main()

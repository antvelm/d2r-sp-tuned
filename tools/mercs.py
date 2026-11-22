"""Mercs part: cheaper mercenary revive (hireling.txt).

The revive price is data-driven: every hireling row has
resurrectcostmultiplier (15), resurrectcostdivisor (2) and resurrectcostmax
(50000). The price scales with multiplier / divisor and is capped by max, so
dividing by `fraction` and scaling the cap gives `fraction` of the vanilla
price at every level. Divisor must stay an integer, so fractions that don't
divide evenly are rounded (the effective fraction is reported).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from tables import header  # noqa: E402


def apply(hireling, revive_cost_fraction=0.2):
    """Mutates hireling in place; returns a list of change lines."""
    if revive_cost_fraction >= 1:
        return []
    h = header(hireling)
    div_c, max_c = h["resurrectcostdivisor"], h["resurrectcostmax"]
    seen = {}
    for r in hireling[1:]:
        if not r[div_c].strip():
            continue
        div, cap = int(r[div_c]), int(r[max_c])
        new_div = max(1, round(div / revive_cost_fraction))
        new_cap = round(cap * revive_cost_fraction)
        r[div_c], r[max_c] = str(new_div), str(new_cap)
        seen[(div, cap, new_div, new_cap)] = seen.get((div, cap, new_div, new_cap), 0) + 1
    return [f"{n} rows: divisor {d} -> {nd} (cost x{d / nd:.3f}), max {c} -> {nc}"
            for (d, c, nd, nc), n in seen.items()]

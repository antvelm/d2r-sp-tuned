"""Build the SPTuned mod from settings.toml.

    python build.py                      # build with settings.toml
    python build.py --settings my.toml   # another settings file
    python build.py --dry-run            # show what would change, write nothing

Always starts from the vanilla tables, applies the enabled parts in memory
(runes -> bosses on treasureclassex.txt, bosses on monstats.txt, mercs on
hireling.txt) and writes both table sets the game ships: excel/ (with the
3.x expansion) and excel/base/. Files of disabled parts are removed from the
mod folder so the game falls back to vanilla for them.
"""
import argparse
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import bosses  # noqa: E402
import loot  # noqa: E402
import mercs  # noqa: E402
import runes  # noqa: E402
from tables import read_table, write_table, write_modinfo  # noqa: E402

TABLE_SETS = ("", "base")
MANAGED = ("treasureclassex", "monstats", "hireling", "uniqueitems")
LOOT_KEYS = ("uber_keys_mult", "ancient_statue_mult", "sunder_mult", "sunder_even_types",
             "essence_mult", "jewelry_mult", "jewelry_unique_mod", "jewelry_set_mod",
             "chase_jewelry_rarity")


def loot_params(cfg):
    p = cfg.get("preset", "sp")
    if p == "custom":
        base = dict(loot.PRESETS["sp"])
        base.update({k: cfg[k] for k in LOOT_KEYS if k in cfg})
        return base
    if p in loot.PRESETS:
        return dict(loot.PRESETS[p])
    sys.exit(f"settings: unknown loot.preset '{p}' (mild | sp | generous | custom)")


def rune_params(cfg):
    p = cfg.get("preset", "sp")
    if p == "custom":
        q, mult = float(cfg.get("curve_q", 1.12)), int(cfg.get("rune_mult", 12))
    elif p in runes.PRESETS and runes.PRESETS[p]:
        q, mult = runes.PRESETS[p]["q"], runes.PRESETS[p]["rune_mult"]
    else:
        sys.exit(f"settings: unknown runes.preset '{p}' (mild | sp | generous | custom)")
    return dict(q=q, rune_mult=mult,
                countess_floor=bool(cfg.get("countess_vanilla_floor", True)),
                countess_bonus_picks=int(cfg.get("countess_bonus_rolls", 1)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", default=os.path.join(ROOT, "settings.toml"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-check", action="store_true", help="skip the rune vanilla-floor check")
    a = ap.parse_args()
    with open(a.settings, "rb") as f:
        s = tomllib.load(f)

    excel = os.path.join(ROOT, s.get("vanilla_excel", "reference/data/global/excel"))
    if not os.path.exists(os.path.join(excel, "treasureclassex.txt")):
        sys.exit(f"no vanilla tables in {excel}; extract them first (see README)")
    name = s.get("mod_name", "SPTuned")
    mpq = os.path.join(s["game_dir"], "mods", name, f"{name}.mpq")
    R, L, B, M = (s.get(k, {}) for k in ("runes", "loot", "bosses", "mercs"))
    on = {k: bool(v.get("enabled", False)) for k, v in
          (("runes", R), ("loot", L), ("bosses", B), ("mercs", M))}
    print("parts:", ", ".join(f"{k} {'ON' if v else 'off'}" for k, v in on.items()))
    if on["runes"]:
        rp = rune_params(R)
        print(f"  runes: preset {R.get('preset', 'sp')} (q={rp['q']}, rune_mult={rp['rune_mult']}, "
              f"countess floor {'on' if rp['countess_floor'] else 'off'})")
    if on["loot"]:
        lp = loot_params(L)
        print(f"  loot: preset {L.get('preset', 'sp')} (" + ", ".join(f"{k}={v}" for k, v in lp.items()) + ")")

    for sub in TABLE_SETS:
        src = os.path.join(excel, sub)
        if not os.path.exists(os.path.join(src, "treasureclassex.txt")):
            continue
        out = {}
        tc_v = read_table(os.path.join(src, "treasureclassex.txt"))
        tc = tc_v
        if on["runes"]:
            tc = runes.apply(tc_v, **rp)
        if on["loot"]:
            tc = [list(r) for r in tc]
            un = read_table(os.path.join(src, "uniqueitems.txt"))
            log = loot.apply(tc, un, lp)
            reduced = [line for line in log if "reduced" in line and "Pandemonium Key" not in line]
            print(f"  excel/{sub}: loot -> {len(log)} table changes"
                  + (f" ({len(reduced)} tables without NoDrop lose a little of their other drops)" if reduced else ""))
            if lp.get("chase_jewelry_rarity"):
                out["uniqueitems"] = un
        if (on["runes"] or on["loot"]) and not a.no_check:
            fails = runes.floor_check(tc_v, tc)
            print(f"  excel/{sub}: rune floor check "
                  + ("OK (no rune rarer than vanilla)" if not fails else f"{len(fails)} runes rarer than vanilla"))
        if on["bosses"]:
            tc = [list(r) for r in tc]
            ms = read_table(os.path.join(src, "monstats.txt"))
            log = bosses.apply(ms, tc, keep_statues=bool(B.get("keep_ancient_statues", True)))
            print(f"  excel/{sub}: bosses -> {len(log)} boss/difficulty entries now use quest drops")
            out["monstats"] = ms
        if on["runes"] or on["loot"] or on["bosses"]:
            out["treasureclassex"] = tc
        if on["mercs"]:
            hl = read_table(os.path.join(src, "hireling.txt"))
            for line in mercs.apply(hl, float(M.get("revive_cost_fraction", 0.2))):
                print(f"  excel/{sub}: mercs {line}")
            out["hireling"] = hl

        if a.dry_run:
            continue
        dest = os.path.join(mpq, "data", "global", "excel", sub)
        for t in MANAGED:
            path = os.path.join(dest, f"{t}.txt")
            if t in out:
                write_table(out[t], path)
            else:
                for ext in (".txt", ".bin"):  # disabled part: fall back to vanilla
                    stale = os.path.join(dest, t + ext)
                    if os.path.exists(stale):
                        os.remove(stale)
                        print(f"  removed {stale}")

    if a.dry_run:
        print("dry run: nothing written")
        return
    write_modinfo(mpq, name, s.get("savepath", "../"))
    print(f"mod written to {os.path.dirname(mpq)}")
    print(f"launch with: -mods {name} -txt")


if __name__ == "__main__":
    main()

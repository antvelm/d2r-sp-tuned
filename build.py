"""Build the SPTuned mod from settings.toml.

    python build.py                      # build with settings.toml
    python build.py --settings my.toml   # another settings file
    python build.py --dry-run            # show what would change, write nothing
    python build.py --check              # is the built mod still current for the installed game?

Always starts from the vanilla tables, applies the enabled parts in memory
(runes -> loot -> uniques -> bosses on treasureclassex.txt, bosses on monstats.txt, mercs on
hireling.txt, base MF on itemratio.txt) and writes both table sets the game ships: excel/ (with the
3.x expansion) and excel/base/. Files of disabled parts are removed from the
mod folder so the game falls back to vanilla for them.
"""
import argparse
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import basemf  # noqa: E402
import bosses  # noqa: E402
import loot  # noqa: E402
import mercs  # noqa: E402
import runes  # noqa: E402
import uniques  # noqa: E402
from tables import (read_table, write_table, write_modinfo,  # noqa: E402
                    game_version, read_version, write_version)

TABLE_SETS = ("", "base")
MANAGED = ("treasureclassex", "monstats", "hireling", "uniqueitems", "itemratio")
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


def uniques_params(cfg):
    p = cfg.get("preset", "sp")
    if p == "custom":
        hours = float(cfg.get("hours_per_item", 25))
    elif p in uniques.PRESETS:
        hours = uniques.PRESETS[p]
    else:
        sys.exit(f"settings: unknown uniques.preset '{p}' (mild | sp | generous | custom)")
    items = cfg.get("items") or list(uniques.CHASE)
    items = [n for n in items if n not in set(cfg.get("exclude", []))] + list(cfg.get("extra", []))
    return dict(hours_per_item=hours, items=items)


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


def extracted_version(excel):
    """Game version recorded by casc_extract.py in the extraction root (reference/)."""
    d = os.path.abspath(excel)
    for _ in range(5):
        v = read_version(d)
        if v:
            return v
        d = os.path.dirname(d)
    return None


def version_status(game, tables, label):
    """Line describing how `tables` (version the data came from) compares to `game`."""
    if not game:
        return False, f"installed game version unknown (no .build.info in game_dir); can't check the {label}"
    if not tables:
        return False, (f"{label}: game version not recorded. Re-extract with tools/casc_extract.py "
                       "(it now records the version), then rebuild.")
    if tables != game:
        return False, (f"{label} come from game {tables}, but the installed game is {game}. "
                       "Re-extract with tools/casc_extract.py, then run python build.py, or the mod's "
                       "old tables hide new items, monsters and fixes from the patch.")
    return True, f"{label} match the installed game ({game})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--settings", default=os.path.join(ROOT, "settings.toml"))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-check", action="store_true", help="skip the rune vanilla-floor check")
    ap.add_argument("--check", action="store_true",
                    help="only report whether the built mod and extracted tables match the installed game")
    a = ap.parse_args()
    with open(a.settings, "rb") as f:
        s = tomllib.load(f)

    excel = os.path.join(ROOT, s.get("vanilla_excel", "reference/data/global/excel"))
    if not os.path.exists(os.path.join(excel, "treasureclassex.txt")):
        sys.exit(f"no vanilla tables in {excel}; extract them first (see README)")
    name = s.get("mod_name", "SPTuned")
    mpq = os.path.join(s["game_dir"], "mods", name, f"{name}.mpq")
    mod_dir = os.path.dirname(mpq)
    game_v, ref_v = game_version(s["game_dir"]), extracted_version(excel)
    if a.check:
        ok_ref, line_ref = version_status(game_v, ref_v, "extracted tables")
        ok_mod, line_mod = version_status(game_v, read_version(mod_dir), "built mod tables")
        if not os.path.isdir(mod_dir):
            ok_mod, line_mod = False, f"no mod built yet in {mod_dir}"
        print(("OK   " if ok_ref else "OLD  ") + line_ref)
        print(("OK   " if ok_mod else "OLD  ") + line_mod)
        sys.exit(0 if ok_ref and ok_mod else 1)
    ok_ref, line_ref = version_status(game_v, ref_v, "extracted tables")
    if ok_ref:
        print(line_ref)
    else:
        bar = "!" * 78
        for line in (bar, "WARNING: " + line_ref, bar):
            print(line)
    R, L, U, B, M, F = (s.get(k, {}) for k in ("runes", "loot", "uniques", "bosses", "mercs", "base_mf"))
    on = {k: bool(v.get("enabled", False)) for k, v in
          (("runes", R), ("loot", L), ("uniques", U), ("bosses", B), ("mercs", M), ("base_mf", F))}
    mf = int(F.get("magic_find", 300))
    if on["base_mf"] and mf <= 0:
        on["base_mf"] = False
    print("parts:", ", ".join(f"{k} {'ON' if v else 'off'}" for k, v in on.items()))
    if on["runes"]:
        rp = rune_params(R)
        print(f"  runes: preset {R.get('preset', 'sp')} (q={rp['q']}, rune_mult={rp['rune_mult']}, "
              f"countess floor {'on' if rp['countess_floor'] else 'off'})")
    if on["loot"]:
        lp = loot_params(L)
        print(f"  loot: preset {L.get('preset', 'sp')} (" + ", ".join(f"{k}={v}" for k, v in lp.items()) + ")")
    if on["uniques"]:
        up = uniques_params(U)
        print(f"  uniques: preset {U.get('preset', 'sp')} (~1 per {up['hours_per_item']:g} h each, "
              f"{len(up['items'])} uniques)")

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
        if on["uniques"]:
            tc = [list(r) for r in tc]
            un_u = read_table(os.path.join(src, "uniqueitems.txt"))
            ms_u = read_table(os.path.join(src, "monstats.txt"))
            for line in uniques.apply(tc, un_u, up, ms_u, uniques.superunique_levels(src)):
                print(f"  excel/{sub}: uniques {line}")
        if (on["runes"] or on["loot"] or on["uniques"]) and not a.no_check:
            fails = runes.floor_check(tc_v, tc)
            print(f"  excel/{sub}: rune floor check "
                  + ("OK (no rune rarer than vanilla)" if not fails else f"{len(fails)} runes rarer than vanilla"))
        if on["bosses"]:
            tc = [list(r) for r in tc]
            ms = read_table(os.path.join(src, "monstats.txt"))
            log = bosses.apply(ms, tc, keep_statues=bool(B.get("keep_ancient_statues", True)))
            print(f"  excel/{sub}: bosses -> {len(log)} boss/difficulty entries now use quest drops")
            out["monstats"] = ms
        if on["runes"] or on["loot"] or on["uniques"] or on["bosses"]:
            out["treasureclassex"] = tc
        if on["mercs"]:
            hl = read_table(os.path.join(src, "hireling.txt"))
            for line in mercs.apply(hl, float(M.get("revive_cost_fraction", 0.2))):
                print(f"  excel/{sub}: mercs {line}")
            out["hireling"] = hl

        if on["base_mf"]:
            ir = read_table(os.path.join(src, "itemratio.txt"))
            print(f"  excel/{sub}: base MF {mf}% -> " + "; ".join(basemf.apply(ir, mf)))
            out["itemratio"] = ir

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
    if ref_v:
        write_version(mod_dir, ref_v)    # lets `python build.py --check` spot a later game patch
    print(f"mod written to {os.path.dirname(mpq)}")
    print(f"launch with: -mod {name} -txt")


if __name__ == "__main__":
    main()

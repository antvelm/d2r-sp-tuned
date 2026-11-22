"""Shared helpers for D2R .txt data tables.

Tables are read and written as raw tab-separated lines (CRLF, latin-1) with
no CSV unquoting, so every cell the mod doesn't change is written back
byte-for-byte (cells like "gld,mul=1280" keep their quotes).
"""
import json
import os


def read_table(path):
    with open(path, "rb") as f:
        lines = f.read().decode("latin-1").split("\r\n")
    if lines and lines[-1] == "":
        lines.pop()
    rows = [ln.split("\t") for ln in lines]
    width = len(rows[0])
    for r in rows[1:]:
        if len(r) < width:
            r += [""] * (width - len(r))
    return rows


def write_table(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(("\r\n".join("\t".join(r) for r in rows) + "\r\n").encode("latin-1"))


def header(rows):
    return {h: i for i, h in enumerate(rows[0])}


def rows_to_tcs(rows):
    """treasureclassex rows -> {name: {picks, nodrop, entries[(name, weight)]}}"""
    col = header(rows)
    tcs = {}
    for r in rows[1:]:
        if not r or not r[0] or r[0].lower() == "expansion":
            continue
        entries = []
        for k in range(1, 11):
            name = r[col[f"Item{k}"]].strip().strip('"')
            prob = r[col[f"Prob{k}"]].strip()
            if name and prob:
                entries.append((name, int(prob)))
        tcs[r[0]] = {"picks": int(r[col["Picks"]] or 0),
                     "nodrop": int(r[col["NoDrop"]] or 0), "entries": entries}
    return tcs


def blank_row_like(rows):
    """Empty row with the *eol end marker set the way vanilla rows have it."""
    r = [""] * len(rows[0])
    if rows[0][-1] == "*eol":
        r[-1] = "0"
    return r


def write_modinfo(mpq_dir, name, savepath):
    os.makedirs(mpq_dir, exist_ok=True)
    with open(os.path.join(mpq_dir, "modinfo.json"), "w", encoding="utf-8") as f:
        json.dump({"name": name, "savepath": savepath}, f, indent=2)


# ------------------------------------------------------------ game version
VERSION_FILE = "game-version.txt"   # written next to the extracted data / into the mod folder


def game_version(game_dir):
    """Installed game version from <game_dir>/.build.info (e.g. '3.4.95032'), or None."""
    try:
        with open(os.path.join(game_dir, ".build.info"), encoding="utf-8", errors="replace") as f:
            lines = [ln.rstrip("\r\n") for ln in f if ln.strip()]
    except OSError:
        return None
    cols = [c.split("!")[0] for c in lines[0].split("|")]
    rows = [dict(zip(cols, ln.split("|"))) for ln in lines[1:]]
    rows.sort(key=lambda r: r.get("Active") != "1")      # active install first
    return next((r["Version"] for r in rows if r.get("Version")), None)


def read_version(folder):
    try:
        with open(os.path.join(folder, VERSION_FILE), encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def write_version(folder, version):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, VERSION_FILE), "w", encoding="utf-8") as f:
        f.write(version + "\n")

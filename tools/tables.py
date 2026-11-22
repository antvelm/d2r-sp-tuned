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

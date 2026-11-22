"""Extract files from a local Diablo II: Resurrected install using CascLib.

Usage:
    python tools/casc_extract.py --game "H:/Diablo II Resurrected" \
        --dll "I:/Github/CascLib/build/Release/CascLib.dll" \
        --out reference --filter "global/excel/"

Only reads the game's CASC storage; never writes to the install.
Extracted files are Blizzard data and are git-ignored on purpose.
"""
import argparse
import ctypes
import os
import sys
from ctypes import c_void_p, c_char_p, c_uint32, c_uint64, byref, POINTER

FIND_DATA_SIZE = 8192  # larger than CASC_FIND_DATA; filename is the first field (char[MAX_PATH])


def load(dll_path):
    # WinDLL only exists on Windows; on Linux (Steam Deck) load libcasc.so with CDLL.
    lib = (ctypes.WinDLL if os.name == "nt" else ctypes.CDLL)(dll_path)
    lib.CascOpenStorage.argtypes = [c_char_p, c_uint32, POINTER(c_void_p)]
    lib.CascOpenStorage.restype = ctypes.c_bool
    lib.CascCloseStorage.argtypes = [c_void_p]
    lib.CascFindFirstFile.argtypes = [c_void_p, c_char_p, c_void_p, c_char_p]
    lib.CascFindFirstFile.restype = c_void_p
    lib.CascFindNextFile.argtypes = [c_void_p, c_void_p]
    lib.CascFindNextFile.restype = ctypes.c_bool
    lib.CascFindClose.argtypes = [c_void_p]
    lib.CascOpenFile.argtypes = [c_void_p, c_char_p, c_uint32, c_uint32, POINTER(c_void_p)]
    lib.CascOpenFile.restype = ctypes.c_bool
    lib.CascGetFileSize64.argtypes = [c_void_p, POINTER(c_uint64)]
    lib.CascGetFileSize64.restype = ctypes.c_bool
    lib.CascReadFile.argtypes = [c_void_p, c_void_p, c_uint32, POINTER(c_uint32)]
    lib.CascReadFile.restype = ctypes.c_bool
    lib.CascCloseFile.argtypes = [c_void_p]
    lib.GetCascError.restype = c_uint32
    return lib


def list_files(lib, storage):
    buf = ctypes.create_string_buffer(FIND_DATA_SIZE)
    h = lib.CascFindFirstFile(storage, b"*", buf, None)
    if not h:
        raise RuntimeError(f"CascFindFirstFile failed: {lib.GetCascError()}")
    try:
        while True:
            yield buf.value.decode("utf-8", "replace")
            if not lib.CascFindNextFile(h, buf):
                break
    finally:
        lib.CascFindClose(h)


def read_file(lib, storage, name):
    hf = c_void_p()
    if not lib.CascOpenFile(storage, name.encode("utf-8"), 0, 0, byref(hf)):
        raise RuntimeError(f"open {name}: {lib.GetCascError()}")
    try:
        size = c_uint64()
        lib.CascGetFileSize64(hf, byref(size))
        data = ctypes.create_string_buffer(size.value)
        got = c_uint32()
        if not lib.CascReadFile(hf, data, size.value, byref(got)):
            raise RuntimeError(f"read {name}: {lib.GetCascError()}")
        return data.raw[: got.value]
    finally:
        lib.CascCloseFile(hf)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--dll", required=True)
    ap.add_argument("--out", default="reference")
    ap.add_argument("--filter", action="append", default=[],
                    help="substring a path must contain (repeatable)")
    ap.add_argument("--list", action="store_true", help="only list matching names")
    a = ap.parse_args()

    lib = load(a.dll)
    storage = c_void_p()
    if not lib.CascOpenStorage(a.game.encode("utf-8"), 0, byref(storage)):
        sys.exit(f"CascOpenStorage failed: {lib.GetCascError()}")
    try:
        n = 0
        for name in list_files(lib, storage):
            norm = name.replace("\\", "/").lower()
            if a.filter and not any(f.lower() in norm for f in a.filter):
                continue
            if a.list:
                print(name)
                n += 1
                continue
            rel = norm.split(":", 1)[-1]  # drop "data:" style prefix
            dest = os.path.join(a.out, *rel.split("/"))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(read_file(lib, storage, name))
            n += 1
        print(f"{n} files", file=sys.stderr)
    finally:
        lib.CascCloseStorage(storage)


if __name__ == "__main__":
    main()

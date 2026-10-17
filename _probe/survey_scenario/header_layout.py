"""Locate the deflate body offset and dump the DE header preceding it.

Usage: python header_layout.py <file> [<file> ...]
"""
import os
import sys
import zlib


def find_stream(data, limit=8192):
    hits = []
    for off in range(0, min(limit, len(data) - 2)):
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(data[off:])
            out += d.flush()
            if d.eof and len(d.unused_data) == 0 and len(out) > 500:
                hits.append((off, len(out)))
        except Exception:
            pass
    return hits


def dump(data, start, end, label):
    print(f"\n--- {label} [{start}..{end}) ---")
    for base in range(start, end, 16):
        ch = data[base:min(base + 16, end)]
        print(f"  {base:6d}  " + " ".join(f"{x:02x}" for x in ch).ljust(47) +
              " |" + "".join(chr(x) if 32 <= x < 127 else "." for x in ch) + "|")


def analyze(path):
    print("=" * 100)
    print(f"FILE: {path}  ({os.path.getsize(path)} bytes)")
    with open(path, "rb") as f:
        data = f.read()
    hits = find_stream(data)
    if not hits:
        print("  no compressed stream found")
        return
    off, outlen = hits[0]
    print(f"  version string: {data[:4]!r}")
    print(f"  body stream offset: {off}   inflated size: {outlen}")
    dump(data, 0, off, "FULL HEADER (all plaintext before stream)")
    print(f"\n  u32 LE interpretation of header:")
    for b in range(0, off - 3, 4):
        v = int.from_bytes(data[b:b + 4], "little")
        extra = ""
        if 32 <= v < 1 << 24 and 4 <= v <= 100000:
            extra = f"  (maybe len={v})"
        print(f"    +{b:4d}: {v:>14d}{extra}")
    # inflate and dump head
    d = zlib.decompressobj(-15)
    out = d.decompress(data[off:]) + d.flush()
    dump(out, 0, min(256, len(out)), "INFLATED BODY first 256 bytes")
    dump(out, max(0, len(out) - 256), len(out), "INFLATED BODY last 256 bytes")
    # look for ascii strings in the inflated body
    strings = []
    cur = b""
    for i, byte in enumerate(out):
        if 32 <= byte < 127:
            cur += bytes([byte])
        else:
            if len(cur) >= 6:
                strings.append((i - len(cur), cur.decode("ascii")))
            cur = b""
    print(f"\n  ascii strings (len>=6) in inflated body: {len(strings)} total; first 40:")
    for o, s in strings[:40]:
        print(f"    @{o:<9d} {s[:100]}")
    print(f"\n  last 20 strings:")
    for o, s in strings[-20:]:
        print(f"    @{o:<9d} {s[:100]}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyze(p)

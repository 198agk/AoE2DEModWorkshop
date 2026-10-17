"""Probe AoE2DE scenario/campaign file headers.

Read-only inspection. Prints hex + ascii of first 64 bytes, and tries
various decompression strategies on the remainder.
"""
import os
import sys
import zlib
import struct

PY = sys.executable


def hexdump(data, offset=0, length=64):
    out = []
    for i in range(0, min(length, len(data)), 16):
        chunk = data[i:i + 16]
        hexpart = " ".join(f"{b:02x}" for b in chunk)
        hexpart = hexpart.ljust(47)
        asciipart = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append(f"  {offset + i:08x}  {hexpart}  |{asciipart}|")
    return "\n".join(out)


def try_decompress(data, wbits, label):
    """Try to decompress data[offset:] entirely with given wbits."""
    try:
        d = zlib.decompressobj(wbits)
        out = d.decompress(data)
        out += d.flush()
        return (True, len(out), len(data) - len(d.unused_data) if d.unused_data else len(data))
    except Exception as e:
        return (False, None, f"{type(e).__name__}: {e}")


def scan_for_zlib(data, limit=4096):
    """Find candidate deflate stream start offsets by brute force."""
    hits = []
    for off in range(0, min(limit, len(data) - 2)):
        b0, b1 = data[off], data[off + 1]
        # zlib header check: CMF/FLG, CM=8, (b0*256+b1) % 31 == 0
        if (b0 & 0x0F) == 8 and ((b0 << 8) | b1) % 31 == 0:
            hits.append((off, "zlib", (b0, b1)))
    return hits


def probe(path, show=64):
    print("=" * 100)
    print(f"FILE: {path}")
    print(f"SIZE: {os.path.getsize(path)} bytes")
    with open(path, "rb") as f:
        data = f.read()
    print(f"HEAD {show} BYTES:")
    print(hexdump(data, 0, show))
    print()
    # Try printing as ascii text for header region
    txt = data[:show]
    printable = "".join(chr(b) if 32 <= b < 127 else "." for b in txt)
    print(f"ASCII: {printable}")
    print(f"repr of first 32: {data[:32]!r}")
    print()

    # Try decompression at various offsets with various wbits
    print("-- decompression attempts (whole-tail) --")
    for off in [0, 4, 8, 12, 16, 20, 24, 28, 32, 40, 48, 56, 60, 64, 72, 80, 96, 128]:
        if off >= len(data):
            continue
        for wbits in [15, -15, 31, 47]:
            ok, outlen, consumed = try_decompress(data[off:], wbits, "")
            if ok and outlen > 0:
                print(f"  offset={off:4d} wbits={wbits:3d}  -> OK, {outlen} bytes out")
    print()
    print("-- zlib header candidate offsets in first 256 bytes --")
    hits = scan_for_zlib(data, 256)
    print(f"  {hits[:40]}")
    print()
    # Brute force: find first offset where decompress succeeds producing > 1000 bytes
    print("-- brute force first 512 offsets, wbits=-15, min 200 bytes --")
    found = []
    for off in range(0, min(512, len(data) - 2)):
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(data[off:])
            out += d.flush()
            if len(out) > 200:
                found.append((off, len(out)))
        except Exception:
            pass
    print(f"  {found[:20]}")
    print()
    return data


if __name__ == "__main__":
    paths = sys.argv[1:]
    for p in paths:
        probe(p)

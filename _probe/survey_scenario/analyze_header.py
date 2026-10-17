"""Deep header analysis for AoE2DE scenario/campaign files.

For each file:
 - dump the first N bytes as little-endian uint32 array
 - find ALL offsets in 0..2048 where raw inflate (wbits=-15) consumes
   EXACTLY to EOF (strong evidence of the true stream start)
 - report decompressed size
"""
import os
import sys
import zlib

MAXSCAN = 4096


def u32dump(data, start=0, length=256):
    lines = []
    for base in range(start, min(start + length, len(data)), 16):
        vals = []
        for i in range(0, 16, 4):
            if base + i + 4 <= len(data):
                v = int.from_bytes(data[base + i:base + i + 4], "little")
                vals.append(f"{v:>12d}")
        lines.append(f"  {base:08x}  " + " ".join(vals))
    return "\n".join(lines)


def exact_stream_offsets(data, limit=MAXSCAN):
    """Return offsets where raw-inflate consumes exactly to EOF."""
    res = []
    for off in range(0, min(limit, len(data) - 2)):
        try:
            d = zlib.decompressobj(-15)
            out = d.decompress(data[off:])
            out += d.flush()
            if d.eof and len(d.unused_data) == 0 and len(out) > 500:
                res.append((off, len(out), len(data) - off))
        except Exception:
            pass
    return res


def check_all_wbits(data, off):
    out = {}
    for wb in (15, -15, 31, 47):
        try:
            d = zlib.decompressobj(wb)
            o = d.decompress(data[off:])
            o += d.flush()
            out[wb] = (len(o), d.eof, len(d.unused_data))
        except Exception as e:
            out[wb] = f"{type(e).__name__}"
    return out


def analyze(path):
    print("=" * 100)
    print(f"FILE: {path}")
    size = os.path.getsize(path)
    print(f"SIZE: {size}")
    with open(path, "rb") as f:
        data = f.read()

    print("\n-- uint32 (LE) dump of first 256 bytes --")
    print(u32dump(data, 0, 256))

    print("\n-- exact-to-EOF raw-inflate stream offsets (scan 0..4095) --")
    hits = exact_stream_offsets(data)
    for off, outlen, inlen in hits:
        print(f"   offset={off}  compressed_in={inlen}  inflated_out={outlen}  "
              f"ratio={outlen/max(inlen,1):.2f}x")
    print(f"   (total {len(hits)} exact hits)")

    if hits:
        off = hits[0][0]
        print(f"\n-- wbits matrix at offset {off} --")
        for wb, v in check_all_wbits(data, off).items():
            print(f"   wbits={wb:3d}: {v}")
        print(f"\n-- first 32 bytes of the compressed stream (offset {off}) --")
        print("   " + " ".join(f"{b:02x}" for b in data[off:off + 32]))
        print(f"\n-- 64 bytes BEFORE offset {off} (possible trailer/header end) --")
        s = max(0, off - 64)
        print("   " + " ".join(f"{b:02x}" for b in data[s:off]))
        print("   ascii: " + "".join(chr(b) if 32 <= b < 127 else "." for b in data[s:off]))
        # decompress and inspect the head of the inflated data
        d = zlib.decompressobj(-15)
        out = d.decompress(data[off:]) + d.flush()
        print(f"\n-- first 512 bytes of INFLATED data --")
        for b in range(0, min(512, len(out)), 16):
            ch = out[b:b + 16]
            print(f"   {b:08x}  " + " ".join(f"{x:02x}" for x in ch).ljust(47) +
                  " |" + "".join(chr(x) if 32 <= x < 127 else "." for x in ch) + "|")
    print()


if __name__ == "__main__":
    for p in sys.argv[1:]:
        analyze(p)

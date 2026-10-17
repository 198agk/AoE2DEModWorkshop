"""Parse the Genie .dat Sounds section (DE) and reconcile with sounds.json.

Format (Genie DE, VER 8.9): after the version header the file is a sequence of
length-prefixed sections in a FIXED order. We only need the Sounds section, so
we walk sections in order and stop when we have it.

Every Genie section is introduced by a uint32 element count, followed by that
many records. Byte-string fields are: uint16 length + length bytes (CP1252).
Sounds section record: uint16 id, uint16 play_delay, uint32 file_count,
  file_count x (uint16 slp_len + slp_len bytes, uint32 cache_time)
"""
import json, struct, zlib, sys
from pathlib import Path

def walk(blob):
    ctx = {"data": blob, "off": 0}

    def u8():
        v = blob[ctx["off"]]; ctx["off"] += 1; return v

    def u16():
        v = struct.unpack_from("<H", blob, ctx["off"])[0]; ctx["off"] += 2; return v

    def i16():
        v = struct.unpack_from("<h", blob, ctx["off"])[0]; ctx["off"] += 2; return v

    def u32():
        v = struct.unpack_from("<I", blob, ctx["off"])[0]; ctx["off"] += 4; return v

    def i32():
        v = struct.unpack_from("<i", blob, ctx["off"])[0]; ctx["off"] += 4; return v

    def f32():
        v = struct.unpack_from("<f", blob, ctx["off"])[0]; ctx["off"] += 4; return v

    def count():
        return u32()

    def s16():
        n = u16()
        v = blob[ctx["off"]:ctx["off"] + n].decode("cp1252", "replace")
        ctx["off"] += n
        return v

    return ctx, dict(u8=u8, u16=u16, i16=i16, u32=u32, i32=i32, f32=f32,
                     count=count, s16=s16)


R = dict(u8=None, u16=None, i16=None, u32=None, i32=None, f32=None, count=None, s16=None)

def skip(fn, *a):
    R[fn](*a)

# ---- minimal section skippers (order per Genie DE docs) ----
def snd_skip_list(ctx, n):
    return [R["i32"]() for _ in range(n)]

def main():
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat\empires2_x2_p1.dat")
    raw = p.read_bytes()
    blob = zlib.decompressobj(-15).decompress(raw)
    print(f"input {len(raw)} -> decompressed {len(blob)}")
    hdr = blob[:16]
    print("header bytes:", hdr.hex(), "| ascii:", hdr[:12])
    ctx, fns = walk(blob)
    R.update(fns)
    print(f"off after 16-byte fixed header conceptually = {ctx['off']}")
    return blob, ctx


if __name__ == "__main__":
    main()

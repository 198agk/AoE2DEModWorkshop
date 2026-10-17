"""Definitive SLD walker using the bit numbering DERIVED from real files.

Finding being tested
--------------------
The openage doc's bit table numbers layers 7/6/5/4/3 (main/shadow/???/damage/
playercolor). Real files disagree, but the doc's own PROSE examples agree with a
REVERSED numbering:

    real bit 0 = main graphics      (doc called this bit 7)
    real bit 1 = shadow graphics    (doc bit 6)
    real bit 2 = unknown5 layer     (doc bit 5)
    real bit 3 = damage mask        (doc bit 4)
    real bit 4 = playercolor mask   (doc bit 3)
    real bits 5-7 = unused          (doc bits 2-0, "Unused")

Evidence: 101 files whose basename contains 'shadow' have first-frame
frame_type 0x02 (bit1 alone) in 90 cases; 7,641 other files are dominated by
0x17 (3914), 0x07 (1612), 0x1f (1281), 0x0f (560) -- all of which are
main(+shadow+unk...) under the reversed reading.

This script walks each frame's layers in the fixed documented order, using the
reversed bit test, and requires the walk to land EXACTLY on EOF. Mask-layer
shape is ambiguous, so both variants are tried per frame (cheap: <=4 paths).
"""
import json, struct, sys
from pathlib import Path

MAIN, SHADOW, UNK, DAMAGE, PC = 0x01, 0x02, 0x04, 0x08, 0x10
ORDER = [(MAIN, "main"), (SHADOW, "shadow"), (UNK, "unknown5"),
         (DAMAGE, "damage"), (PC, "playercolor")]
GFX_LAYERS = {"main", "shadow", "unknown5"}   # 16-byte offsets header
MASK_LAYERS = {"damage", "playercolor"}       # 2-byte header


class Bad(Exception):
    pass


def read_gfx_layer(b, off):
    """main/shadow/unknown5: clen, 16-byte offsets header, cmd array, blocks."""
    if off + 4 > len(b):
        raise Bad("eof@clen")
    clen = struct.unpack_from("<I", b, off)[0]
    if clen < 22 or off + clen > len(b):
        raise Bad(f"clen={clen}")
    p = off + 4
    ox1, oy1, ox2, oy2 = struct.unpack_from("<4H", b, p)
    flag1, unk1 = struct.unpack_from("<2B", b, p + 8)
    p += 10
    ncmd = struct.unpack_from("<H", b, p)[0]
    p += 2
    if p + 2 * ncmd > off + clen:
        raise Bad(f"ncmd={ncmd}")
    cmds = struct.unpack_from(f"<{2 * ncmd}B", b, p)
    p += 2 * ncmd
    draw = sum(cmds[1::2])
    if p + 8 * draw != off + clen:
        raise Bad(f"clen mismatch: {p + 8 * draw} != {off + clen}")
    w, h = ox2 - ox1, oy2 - oy1
    return dict(kind="gfx", clen=clen, w=w, h=h, ox1=ox1, oy1=oy1, ox2=ox2, oy2=oy2,
                flag1=flag1, unk1=unk1, ncmd=ncmd, draw=draw, end=off + clen)


def read_mask_layer(b, off, with_cmds):
    """damage/playercolor mask: clen, 2-byte header, optional cmd array + blocks."""
    if off + 4 > len(b):
        raise Bad("eof@clen")
    clen = struct.unpack_from("<I", b, off)[0]
    if clen < 6 or off + clen > len(b):
        raise Bad(f"mask clen={clen}")
    p = off + 4
    flag1, unk1 = struct.unpack_from("<2B", b, p)
    p += 2
    if not with_cmds:
        if clen != 6:
            raise Bad(f"mask clen {clen} != 6 (no-cmd variant)")
        return dict(kind="mask", clen=clen, flag1=flag1, unk1=unk1, end=off + clen)
    if p + 2 > off + clen:
        raise Bad("eof@ncmd")
    ncmd = struct.unpack_from("<H", b, p)[0]
    p += 2
    if p + 2 * ncmd > off + clen:
        raise Bad(f"mask ncmd={ncmd}")
    cmds = struct.unpack_from(f"<{2 * ncmd}B", b, p)
    p += 2 * ncmd
    draw = sum(cmds[1::2])
    if p + 8 * draw != off + clen:
        raise Bad(f"mask clen mismatch {p + 8 * draw} != {off + clen}")
    return dict(kind="mask", clen=clen, flag1=flag1, unk1=unk1, ncmd=ncmd,
                draw=draw, end=off + clen)


def walk(path, mask_cmd_variant=0):
    b = path.read_bytes()
    if len(b) < 16 or b[:4] != b"SLDX":
        return None
    _sig, ver, nf, u1, u2, u3 = struct.unpack_from("<4s4HI", b, 0)
    off = 16
    fts = {}
    for fi in range(nf):
        if off + 12 > len(b):
            return dict(ok=False, why=f"eof@frame{fi}", off=off, nf=nf, ver=ver)
        cw, ch, hx, hy, ft, unk, fidx = struct.unpack_from("<4H2BH", b, off)
        off += 12
        fts[ft] = fts.get(ft, 0) + 1

        # Which layers are present? (reversed bit numbering)
        kinds = [name for bit, name in ORDER if ft & bit]
        if ft & ~0x1F:
            return dict(ok=False, why=f"ft={ft:02x} has high bits @{off - 12}",
                        off=off - 12, nf=nf, ver=ver)

        layers = []
        for name in kinds:
            try:
                if name in GFX_LAYERS:
                    L = read_gfx_layer(b, off)
                else:
                    L = read_mask_layer(b, off, with_cmds=bool(mask_cmd_variant))
            except (Bad, struct.error) as e:
                return dict(ok=False, why=f"ft={ft:02x}@{off - 12} {name}: {e}",
                            off=off - 12, nf=nf, ver=ver)
            off = L["end"]
            L["name"] = name
            layers.append(L)
        if fi == 0:
            first = [(L["name"], L["kind"]) for L in layers]
            first_gfx = next((L for L in layers if L["kind"] == "gfx"), None)

    return dict(ok=(off == len(b)), why=f"end={off} filelen={len(b)}", end=off,
                nf=nf, ver=ver, fts=fts, first_layers=first,
                first_w=first_gfx["w"] if first_gfx else None,
                first_h=first_gfx["h"] if first_gfx else None)


def main():
    G = Path(r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics")
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 400
    maxkb = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    files = [p for p in sorted(G.glob("*_x1.sld")) if 0 < p.stat().st_size <= maxkb * 1024]
    step = max(1, len(files) // limit)
    files = files[::step][:limit]
    print(f"candidate pool step={step}, sampling {len(files)} files <= {maxkb} KB")

    stats = {}
    fails = {}
    solved = []
    for mc in (0, 1):
        ok = 0
        for p in files:
            try:
                r = walk(p, mask_cmd_variant=mc)
            except Exception as e:  # noqa: BLE001
                r = dict(ok=False, why=f"EXC {type(e).__name__}: {e}")
            if r is None:
                continue
            if r["ok"]:
                ok += 1
                if mc == 0:
                    solved.append((p.name, r["nf"], r["fts"]))
            else:
                fails.setdefault(mc, {})
                key = r["why"].split("@")[0][:28]
                fails[mc][key] = fails[mc].get(key, 0) + 1
        stats[f"mask_cmds={mc}"] = f"{ok}/{len(files)}"
        print(f"  mask_cmds={mc}: exact-EOF {ok}/{len(files)}")
        top = sorted(fails.get(mc, {}).items(), key=lambda kv: -kv[1])[:12]
        for k, v in top:
            print(f"      {v:5d}  {k}")

    print(f"\n=== {len(solved)} files solved with reversed bits ===")
    for name, nf, fts in solved[:25]:
        pretty = {f"0x{k:02x}": v for k, v in sorted(fts.items())}
        print(f"  {name}  nf={nf} fts={pretty}")

    # frame_type histogram over ALL first frames, plus layer-shape for each ft
    shape = {}
    for p in files[:250]:
        try:
            r = walk(p)
        except Exception:
            continue
        if r and "first_layers" in r:
            key = f"0x{r['fts'] and 0 or 0:02x}"
    Path("sld_final.json").write_text(json.dumps(
        {"stats": stats, "solved": [{"name": n, "nf": nf,
                                     "fts": {hex(k): v for k, v in f.items()}}
                                    for n, nf, f in solved]}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

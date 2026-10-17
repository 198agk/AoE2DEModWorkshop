# -*- coding: utf-8 -*-
"""Full invariant suite under the DECISIVE layout rule.

Layout (all verified):
  file header 16 B : <4s 2H 2H H = SIG 'SLDX' | ver u16 | num_frames u16
                     | u1 u16 | frame_offset u16 | magic u16
  frame header 12 B: canvas_w u16 | canvas_h u16 | centre_x i16 | centre_y i16
                     | frame_type u8 | unknown u8 | frame_index u16
  layer record     : u32 size | (size-4) payload | pad  ->  next = q + ceil4(size)
    main / shadow  : 4x u16 rect | u16 fmt | u16 ncmd | ncmd*(u8,u8) | blocks
                     size == 16 + 2*ncmd + 8*sum(draw)
    playercolor    : u16 fmt | u16 ncmd | ncmd*(u8,u8) | blocks
                     size ==  8 + 2*ncmd + 8*sum(draw)
    unknown2       : (still unknown)
  block grid       : bw = ceil(rect_w/4), bh = ceil(rect_h/4)
                     span = sum(skip+draw) must equal bw*bh, and
                     playercolor.span must equal main.span.

Read-only.
"""
import os
import struct
import collections
import json

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\sld_invariants_out.json"
BITNAMES = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
ceil4 = lambda x: x + ((4 - x % 4) % 4)

files = sorted(f for f in os.listdir(GP) if f.lower().endswith(".sld"))
zero = 0
stat = collections.Counter()
bad_examples = collections.defaultdict(list)
frames_total = 0
fo_hist = collections.Counter()
un_shape = collections.Counter()
un_samples = []
ver_hist = collections.Counter()
numframes_mismatch = []
files_ok = 0


def walk_file(b, fo):
    """yield one dict per frame; raise on structure error."""
    p = fo
    prev = None
    it = 0
    while p < len(b):
        if p + 12 > len(b):
            raise ValueError("frame hdr past EOF f%d" % it)
        cw, ch, cx, cy, ft, un, idx = struct.unpack_from("<2H 2h 2B H", b, p)
        if prev is not None and idx != prev + 1:
            raise ValueError("frame_index break f%d %d->%d" % (it, prev, idx))
        prev = idx
        q = p + 12
        layers = {}
        for bit, nm in BITNAMES:
            if not (ft & (1 << bit)):
                continue
            if q + 4 > len(b):
                raise ValueError("size past EOF f%d %s" % (it, nm))
            size = struct.unpack_from("<I", b, q)[0]
            if size < 4 or q + size > len(b):
                raise ValueError("size=%d bad f%d %s" % (size, it, nm))
            layers[nm] = (q, size)
            q = q + ceil4(size)
        yield dict(p=p, idx=idx, ft=ft, cw=cw, ch=ch, layers=layers)
        p = q
        it += 1
    if p != len(b):
        raise ValueError("overrun %d" % p)


def parse_main(b, q, size):
    rect = struct.unpack_from("<4H", b, q + 4)
    fmt, ncmd = struct.unpack_from("<2H", b, q + 12)
    if 16 + 2 * ncmd > size:          # ncmd cannot fit: report as-is, min cmds
        return rect, fmt, ncmd, None
    cmds = [(b[q + 16 + 2 * i], b[q + 17 + 2 * i]) for i in range(ncmd)]
    return rect, fmt, ncmd, cmds


def parse_pc(b, q, size):
    fmt, ncmd = struct.unpack_from("<2H", b, q + 4)
    if 8 + 2 * ncmd > size:
        return fmt, ncmd, None
    cmds = [(b[q + 8 + 2 * i], b[q + 9 + 2 * i]) for i in range(ncmd)]
    return fmt, ncmd, cmds


for fn in files:
    b = open(os.path.join(GP, fn), "rb").read()
    if len(b) == 0:
        zero += 1
        stat["zero_byte"] += 1
        continue
    sig, ver, n, u1, fo, magic = struct.unpack_from("<4s 2H 2H H", b, 0)
    fo_hist[fo] += 1
    ver_hist[ver] += 1
    if sig != b"SLDX":
        stat["bad_sig"] += 1
        continue
    nf = 0
    try:
        for fr in walk_file(b, fo):
            nf += 1
            m = fr["layers"].get("main")
            pc = fr["layers"].get("playercolor")
            sh = fr["layers"].get("shadow")
            dm = fr["layers"].get("damage")
            un2 = fr["layers"].get("unknown2")
            gm = None
            if m:
                rect, fmt, ncmd, cmds = parse_main(b, m[0], m[1])
                if cmds is None:
                    stat["main_ncmd_overflow"] += 1
                else:
                    comp = 16 + 2 * ncmd + 8 * sum(c[1] for c in cmds)
                    stat["main_comp_bad"] += (comp != m[1])
                    if comp != m[1] and len(bad_examples["main_comp"]) < 5:
                        bad_examples["main_comp"].append((fn, fr["idx"], comp, m[1]))
                    span = sum(c[0] + c[1] for c in cmds)
                    w, h = rect[2] - rect[0], rect[3] - rect[1]
                    bw, bh = (w + 3) // 4, (h + 3) // 4
                    stat["main_span_ok"] += (span == bw * bh and bw > 0 and bh > 0)
                    if not (span == bw * bh and bw > 0 and bh > 0):
                        stat["main_span_bad"] += 1
                        if len(bad_examples["main_span"]) < 5:
                            bad_examples["main_span"].append(
                                (fn, fr["idx"], rect, span, bw, bh, span - bw * bh))
                    gm = (span, bw, bh)
            if sh:
                rect, fmt, ncmd, cmds = parse_main(b, sh[0], sh[1])
                if cmds is None:
                    stat["shadow_ncmd_overflow"] += 1
                else:
                    comp = 16 + 2 * ncmd + 8 * sum(c[1] for c in cmds)
                    if comp != sh[1]:
                        stat["shadow_comp_bad"] += 1
                    span = sum(c[0] + c[1] for c in cmds)
                    w, h = rect[2] - rect[0], rect[3] - rect[1]
                    bw, bh = (w + 3) // 4, (h + 3) // 4
                    if not (span == bw * bh and bw > 0 and bh > 0):
                        stat["shadow_span_bad"] += 1
            if dm:
                rect, fmt, ncmd, cmds = parse_main(b, dm[0], dm[1])
                if cmds is None:
                    stat["damage_ncmd_overflow"] += 1
                else:
                    comp = 16 + 2 * ncmd + 8 * sum(c[1] for c in cmds)
                    if comp != dm[1]:
                        stat["damage_comp_bad"] += 1
            if pc:
                fmt, ncmd, cmds = parse_pc(b, pc[0], pc[1])
                if cmds is None:
                    stat["pc_ncmd_overflow"] += 1
                else:
                    comp = 8 + 2 * ncmd + 8 * sum(c[1] for c in cmds)
                    stat["pc_comp_ok"] += (comp == pc[1])
                    if comp != pc[1]:
                        stat["pc_comp_bad"] += 1
                        if len(bad_examples["pc_comp"]) < 5:
                            bad_examples["pc_comp"].append((fn, fr["idx"], comp, pc[1]))
                    span = sum(c[0] + c[1] for c in cmds)
                    if gm:
                        stat["pc_span_match"] += (span == gm[0])
                        if span != gm[0]:
                            stat["pc_span_bad"] += 1
                            if len(bad_examples["pc_span"]) < 5:
                                bad_examples["pc_span"].append((fn, fr["idx"], span, gm[0]))
            if un2:
                q, size = un2
                # shape census: leading u32, then ascending u16 run, then rest
                lead = struct.unpack_from("<I", b, q + 4)[0]
                rest = size - 8
                k = 0
                vals = []
                o = q + 8
                last = -1
                while o + 2 <= q + size and k < 64:
                    v = struct.unpack_from("<H", b, o)[0]
                    if v <= last:
                        break
                    vals.append(v)
                    last = v
                    o += 2
                    k += 1
                un_shape[(lead, k, size % 8, size % 4)] += 1
                if len(un_samples) < 12:
                    un_samples.append((fn, fr["idx"], size, lead, k, vals[:10],
                                       b[q + 8:q + 8 + 24].hex(" ")))
        if nf != n:
            numframes_mismatch.append((fn, n, nf))
        files_ok += 1
        frames_total += nf
    except ValueError as e:
        stat["walk_fail"] += 1
        if len(bad_examples["walk_fail"]) < 20:
            bad_examples["walk_fail"].append((fn, str(e)))

print("files               :", len(files))
print("zero-byte           :", zero)
print("files walked OK     :", files_ok)
print("total frames        :", frames_total)
print("version histogram   :", dict(ver_hist))
print("frame_offset hist   :", dict(fo_hist))
print("num_frames mismatch :", len(numframes_mismatch), numframes_mismatch[:8])
print()
for k in sorted(stat):
    print("  %-18s %d" % (k, stat[k]))
print()
print("bad examples:")
for k, v in bad_examples.items():
    for e in v:
        print("  %-12s %s" % (k, e))
print()
print("unknown2 shape census (lead, ascending_k, size%8, size%4) -> count")
for k, v in un_shape.most_common(24):
    print("   %s  %d" % (str(k), v))
print()
print("unknown2 samples:")
for s in un_samples:
    print("   fn=%s idx=%d size=%d lead=%d k=%d vals=%s" % (s[0], s[1], s[2], s[3], s[4], s[5]))
    print("        bytes: %s" % s[6])

json.dump(dict(files=len(files), zero=zero, ok=files_ok, frames=frames_total,
               ver=dict(ver_hist), fo=dict(fo_hist),
               numframes_mismatch=numframes_mismatch, stat=dict(stat),
               bad_examples={k: v for k, v in bad_examples.items()},
               un_shape=[(str(k), v) for k, v in un_shape.most_common(60)],
               un_samples=[list(s) for s in un_samples]),
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("\nwrote", OUT)

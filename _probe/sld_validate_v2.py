# -*- coding: utf-8 -*-
"""HYPOTHESIS: the u16 at header offset 10 is `frame_offset` -- the byte offset
at which frame 0's header begins (14 or 16, not always 16).  The earlier parser
hard-coded 16, which is why exactly the files with 14 failed.

Test: re-walk every .sld using frame_offset, require exact EOF.
Also: characterise the `unknown2` layer now that far more samples are reachable.

Read-only.
"""
import os
import struct
import collections

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
GP = os.path.join(GAME, "resources", "_common", "drs", "graphics")
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\sld_validate_v2_out.txt"

BITS = [(0, "main"), (1, "shadow"), (2, "unknown2"), (3, "damage"), (4, "playercolor")]
PAD = lambda x: x + ((4 - x % 4) % 4)


def walk(b, fo):
    sig, ver, n, z, fo_hdr, magic = struct.unpack_from("<4s 2H 2H H", b, 0)
    p, off = fo, 0
    comp_ok = collections.Counter()
    comp_bad = collections.Counter()
    span_ok = collections.Counter()
    span_bad = collections.Counter()
    seen = collections.Counter()
    idx_bad = 0
    first_idx = None
    u2_shapes = collections.Counter()
    u2_samples = []
    while off < n:
        if p + 12 > len(b):
            return None, "frame header past EOF @%d (frame %d/%d)" % (p, off, n)
        cw, ch, cx, cy, ft, un, fi = struct.unpack_from("<2H 2h 2B H", b, p)
        if first_idx is None:
            first_idx = fi
        elif fi != first_idx + off:
            idx_bad += 1
        p += 12
        rects, recs = {}, {}
        for bit, nm in BITS:
            if not (ft & (1 << bit)):
                continue
            seen[nm] += 1
            if p + 4 > len(b):
                return None, "layer size past EOF (frame %d layer %s)" % (off, nm)
            size = struct.unpack_from("<I", b, p)[0]
            q = p + 4
            rect = None
            if nm in ("main", "shadow"):
                rect = struct.unpack_from("<4H", b, q)
                q += 8
            fmt, ncmd = struct.unpack_from("<2H", b, q)
            q += 4
            cmds = [(b[q + 2 * i], b[q + 2 * i + 1]) for i in range(ncmd)]
            q += 2 * ncmd
            draws = sum(c[1] for c in cmds)
            span = sum(c[0] + c[1] for c in cmds)
            base = 16 if nm in ("main", "shadow") else 8
            (comp_ok if base + 2 * ncmd + 8 * draws == size else comp_bad)[nm] += 1
            if rect:
                bw = (rect[2] - rect[0] + 3) // 4
                bh = (rect[3] - rect[1] + 3) // 4
                (span_ok if bw * bh == span and bw > 0 and bh > 0 else span_bad)[nm] += 1
                rects[nm] = (bw, bh, span)
            elif nm == "playercolor":
                recs[nm] = span
            elif nm == "unknown2":
                pay = b[p + 4:p + size]
                # shape: u32 then a run of ascending u16 then 8-aligned block data
                v = struct.unpack_from("<I", pay, 0)[0] if len(pay) >= 4 else -1
                us = []
                end = min(len(pay) - 1, 4 + 2 * 40)
                for i in range(4, end, 2):
                    us.append(struct.unpack_from("<H", pay, i)[0])
                k = 0
                for i, x in enumerate(us):
                    if i > 0 and x < us[i - 1]:
                        break
                    if x > 8192:
                        break
                    k += 1
                rest = len(pay) - 4 - 2 * k
                u2_shapes[(v, k, rest % 8, rest % 4)] += 1
                if len(u2_samples) < 12:
                    u2_samples.append((v, k, rest, us[:10]))
            if rects.get(nm) or nm != "main":
                pass
            p = PAD(p + size)
        if "main" in rects and "playercolor" in recs:
            (span_ok if rects["main"][2] == recs["playercolor"] else span_bad)["pc==main"] += 1
        off += 1
    return dict(fo=fo, n=n, walked=off, eof_ok=(p == len(b)), p=p, blen=len(b),
                idx_bad=idx_bad, comp_ok=comp_ok, comp_bad=comp_bad, span_ok=span_ok,
                span_bad=span_bad, seen=seen, z=z, magic=magic,
                u2_shapes=u2_shapes, u2_samples=u2_samples), None


def main():
    sld = sorted(f for f in os.listdir(GP) if f.endswith(".sld"))
    tot = collections.Counter()
    fo_hist = collections.Counter()
    comp_bad = collections.Counter()
    span_bad = collections.Counter()
    idx_bad_files = []
    fails = []
    u2_shapes = collections.Counter()
    u2_samples = []
    nfr = 0
    for fn in sld:
        b = open(os.path.join(GP, fn), "rb").read()
        if len(b) == 0:
            tot["zero"] += 1
            continue
        sig, ver, n, z, fo, magic = struct.unpack_from("<4s 2H 2H H", b, 0)
        if sig != b"SLDX":
            fails.append((fn, "bad sig %r" % sig))
            continue
        fo_hist[fo] += 1
        r, err = walk(b, fo)
        if err:
            fails.append((fn, err))
            continue
        tot["files"] += 1
        nfr += r["walked"]
        if r["eof_ok"]:
            tot["eof_ok"] += 1
        else:
            fails.append((fn, "eof p=%d len=%d" % (r["p"], r["blen"])))
        if r["idx_bad"]:
            idx_bad_files.append((fn, r["idx_bad"], r["walked"]))
        for k, v in r["comp_bad"].items():
            comp_bad[k] += v
        for k, v in r["span_bad"].items():
            span_bad[k] += v
        for k, v in r["u2_shapes"].items():
            u2_shapes[k] += v
        if len(u2_samples) < 20:
            u2_samples += r["u2_samples"][:6]
    out = []
    A = out.append
    A("=== file-header variant ===")
    A("u16@10 (frame_offset) histogram: %s" % dict(fo_hist))
    A("")
    A("=== walk results ===")
    A("files scanned          : %d" % len(sld))
    A("zero-byte              : %d" % tot["zero"])
    A("files walked OK        : %d" % tot["files"])
    A("  -> reaching EXACT EOF: %d" % tot["eof_ok"])
    A("total frames           : %d" % nfr)
    A("frame_index discontinuities: %d files" % len(idx_bad_files))
    A("")
    A("=== residual comp==size failures (base+2*ncmd+8*sum(draw)) ===")
    if comp_bad:
        for k, v in comp_bad.items():
            A("    %-12s bad=%d" % (k, v))
    else:
        A("    NONE - all five layer kinds match on every frame")
    A("")
    A("=== residual span==bw*bh failures ===")
    if span_bad:
        for k, v in span_bad.items():
            A("    %-12s bad=%d" % (k, v))
    else:
        A("    NONE")
    A("")
    A("=== unknown2 shape census: (u32_lead, ascending_u16_count, rest%%8, rest%%4) ===")
    for k, v in u2_shapes.most_common(16):
        A("    lead=%-4d k=%-4d rest%%8=%-3d rest%%4=%-3d  count=%d" % (k[0], k[1], k[2], k[3], v))
    A("")
    A("=== unknown2 samples (lead, k, rest, first u16s) ===")
    for s in u2_samples[:12]:
        A("    %s" % (s,))
    A("")
    A("=== FAILURES: %d ===" % len(fails))
    for fn, why in fails[:60]:
        A("    %-52s %s" % (fn, why))
    txt = "\n".join(out)
    io = open(OUT, "w", encoding="utf-8")
    io.write(txt)
    io.close()
    print(txt)


main()

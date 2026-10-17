# -*- coding: utf-8 -*-
"""Step 2: search AoE2DE_s.exe for (a) ASCII/UTF-16 string anchors and
(b) NUMERIC little-endian tables containing the villager task-variant ids.

Why numeric: the internal codes (VMBAS/VMBLD/...) returned 0 ASCII hits in the
parent agent's search, so the engine does not name the family by codename.  If
the engine hardcoded the family it would most plausibly hold the ids as 2-byte
little-endian, either as adjacent pairs or as a contiguous run.

Everything here is read-only: the file is opened 'rb' and never written.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import struct, os, sys, json, itertools, re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = _HERE_PATH("_probe", "taskfamily")

# male group (dat TaskSwapGroup=1) and female group (=2), from probe 1
TSG1 = [56, 83, 118, 120, 122, 123, 124, 156, 259, 579, 592, 1810, 1892, 2333]
TSG2 = [57, 212, 214, 216, 218, 220, 222, 293, 354, 581, 590, 1891, 2334]
TSG3 = [13, 2147, 2171, 2356, 2630]
FAMILY = sorted(set(TSG1) | set(TSG2))

def main():
    b = open(EXE, "rb").read()
    n = len(b)
    print("exe size            : %d B" % n)

    # ---- PE header basics, so an offset can be turned into an RVA ---------
    pe_off = struct.unpack_from("<I", b, 0x3C)[0]
    assert b[pe_off:pe_off + 4] == b"PE\0\0", "not a PE"
    nsec = struct.unpack_from("<H", b, pe_off + 6)[0]
    opt_size = struct.unpack_from("<H", b, pe_off + 20)[0]
    opt_off = pe_off + 24
    magic = struct.unpack_from("<H", b, opt_off)[0]
    image_base = struct.unpack_from("<I", b, opt_off + 28)[0] if magic == 0x10B \
        else struct.unpack_from("<Q", b, opt_off + 24)[0]
    sec_off = opt_off + opt_size
    sections = []
    for i in range(nsec):
        o = sec_off + i * 40
        name = b[o:o + 8].rstrip(b"\0").decode("latin-1")
        vsize = struct.unpack_from("<I", b, o + 8)[0]
        vaddr = struct.unpack_from("<I", b, o + 12)[0]
        rawsize = struct.unpack_from("<I", b, o + 16)[0]
        rawptr = struct.unpack_from("<I", b, o + 20)[0]
        sections.append((name, vaddr, vsize, rawptr, rawsize))
    print("image_base          : 0x%X   sections=%d" % (image_base, nsec))
    for s in sections:
        print("   %-9s vaddr=0x%08X vsize=0x%08X rawptr=0x%08X rawsize=0x%08X"
              % (s[0], s[1], s[2], s[3], s[4]))

    def to_rva(off):
        for name, vaddr, vsize, rawptr, rawsize in sections:
            if rawptr <= off < rawptr + rawsize:
                return image_base + vaddr + (off - rawptr), name
        return None, None

    report = {"image_base": image_base, "sections": [
        {"name": s[0], "vaddr": s[1], "vsize": s[2], "rawptr": s[3],
         "rawsize": s[4]} for s in sections], "strings": {}, "numeric": {}}

    # ---- (a) string anchors, ASCII + UTF-16LE -----------------------------
    print("\n=== (a) string anchors ===")
    anchors = ["linkedUnits", "linkedTechs", "unitlines", "unitcategories",
               "objreplacement", "dropsites", "sharedbuildings", "buttons.json",
               "TaskSwap", "task_swap", "TaskSwapGroup", "task swap",
               "transform into another unit", "switches villager types",
               "worker_object_group", "WorkerObjectGroup", "Villager", "villager"]
    sres = {}
    for a in anchors:
        for enc, label in (("ascii", "A"), ("utf-16-le", "W")):
            try:
                pat = a.encode(enc)
            except Exception:
                continue
            offs = []
            i = 0
            while True:
                j = b.find(pat, i)
                if j < 0:
                    break
                offs.append(j)
                i = j + 1
                if len(offs) >= 8:
                    break
            if offs:
                rvas = [to_rva(o) for o in offs]
                print("  %-32s %s  n=%-3d offsets=%s" %
                      (a, label, len(offs),
                       ", ".join("0x%X(rva=0x%X,%s)" % (o, r[0] or 0, r[1])
                                 for o, r in zip(offs, rvas))))
                sres["%s|%s" % (a, label)] = [{"off": o, "rva": r[0], "sec": r[1]}
                                              for o, r in zip(offs, rvas)]
            else:
                sres["%s|%s" % (a, label)] = []
                print("  %-32s %s  n=0   <-- ABSENT" % (a, label))
    report["strings"] = sres

    # ---- (b) numeric LE tables -------------------------------------------
    print("\n=== (b) numeric little-endian search ===")
    nums = {}

    def scan_u16(vals, label):
        """Find every offset where the u16 LE sequence `vals` occurs."""
        pats = b"".join(struct.pack("<H", v) for v in vals)
        offs = []
        i = 0
        while True:
            j = b.find(pats, i)
            if j < 0:
                break
            offs.append(j)
            i = j + 1
        return pats, offs

    def scan_u32(vals, label):
        pats = b"".join(struct.pack("<I", v) for v in vals)
        offs = []
        i = 0
        while True:
            j = b.find(pats, i)
            if j < 0:
                break
            offs.append(j)
            i = j + 1
        return pats, offs

    probes = [
        ("u16", [83, 118]), ("u16", [118, 212]), ("u16", [83, 293]),
        ("u16", [293, 83]), ("u16", [118, 83]),
        ("u16", [83, 118, 120, 122]),
        ("u16", [56, 57]), ("u16", [57, 56]),
        ("u16", [83, 293, 1810]),
        ("u16", TSG1), ("u16", TSG2), ("u16", TSG3),
        ("u16", FAMILY),
        ("u32", [83, 118]), ("u32", [118, 212]), ("u32", [83, 293]),
        ("u32", FAMILY),
    ]
    for kind, vals in probes:
        pats, offs = (scan_u16 if kind == "u16" else scan_u32)(vals, kind)
        key = "%s:%s" % (kind, ",".join(map(str, vals)))
        show = offs[:6]
        print("  %-7s len=%-3d %-46s n=%-4d %s" %
              (kind, len(vals), str(vals)[:46], len(offs),
               " ".join("0x%X" % o for o in show)))
        nums[key] = {"kind": kind, "pattern_len": len(vals),
                     "matches": len(offs),
                     "offsets": offs[:200],
                     "rvas": [(to_rva(o)[0], to_rva(o)[1]) for o in offs[:200]]}
    report["numeric"] = nums

    # ---- (c) is there a FIXED-STRIDE id table near any hit? --------------
    print("\n=== (c) stride analysis around the longest family match ===")
    for key, v in nums.items():
        if v["matches"] and v["pattern_len"] >= 4:
            for off in v["offsets"][:3]:
                print("  %s @0x%X rva=0x%X sec=%s" % (key, off, *to_rva(off)))
                for stride in (2, 4):
                    seq = [struct.unpack_from("<H", b, off + stride * k)[0]
                           for k in range(16)]
                    print("     stride %d: %s" % (stride, seq))
    # ---- (d) how many of the u16 pair matches are plausibly real tables? --
    print("\n=== (d) u16 [83,118] hit context ===")
    for off in nums.get("u16:83,118", {}).get("offsets", [])[:10]:
        lo = max(0, off - 16); hi = min(n, off + 24)
        ctx = b[lo:hi]
        rva, sec = to_rva(off)
        print("  @0x%X rva=0x%X sec=%s" % (off, rva or 0, sec))
        print("     hex : %s" % ctx.hex(" "))
        print("     u16 : %s" % [struct.unpack_from("<H", b, lo + 2 * k)[0]
                                 for k in range(len(ctx) // 2)])

    with open(os.path.join(OUT, "exe_scan.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("\nwrote exe_scan.json")
    print("DONE")

if __name__ == "__main__":
    main()

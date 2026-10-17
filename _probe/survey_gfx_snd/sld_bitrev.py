"""Test the 'doc bit numbers are reversed' hypothesis for SLD frame_type.

Hypothesis: the openage doc lists main/shadow/???/damage/playercolor as bits
7/6/5/4/3, but the real encoding uses bits 0/1/2/3/4 (real_bit = 7 - doc_bit).
Prediction: a file whose basename says 'shadow' should have frames whose
frame_type bit 1 (value 0x02) is the only graphics bit set, whereas a normal
main-graphics file should have bit 0 (value 0x01) set.
"""
import json, struct
from pathlib import Path

G = Path(r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\drs\graphics")


def first_ft(p):
    b = p.read_bytes()[:64]
    if len(b) < 28 or b[:4] != b"SLDX":
        return None
    nf = struct.unpack_from("<H", b, 6)[0]
    if nf == 0:
        return "noframes"
    # header 16 B (4s 4H I), frame header 12 B (4H 2B H):
    #   canvas_w@16 canvas_h@18 hs_x@20 hs_y@22 frame_type@24 unknown1@25 frame_index@26
    return struct.unpack_from("<B", b, 24)[0]


def main():
    files = sorted(G.glob("*_x1.sld"))
    shadow, other = [], []
    for p in files:
        ft = first_ft(p)
        if ft is None:
            continue
        name = p.name.lower()
        if "shadow" in name:
            shadow.append((p.name, ft))
        else:
            other.append((p.name, ft))

    def hist(rows):
        h = {}
        for _, ft in rows:
            h[ft] = h.get(ft, 0) + 1
        return dict(sorted(h.items(), key=lambda kv: -kv[1]))

    print(f"files scanned: {len(files)}")
    print(f"\n=== basename contains 'shadow' (n={len(shadow)}) ===")
    print("frame_type histogram:", {hex(k) if isinstance(k, int) else k: v for k, v in hist(shadow).items()})
    # how often is ONLY bit1 set among the gfx bits {0,1,2}?
    only_bit1 = sum(1 for _, ft in shadow if isinstance(ft, int) and (ft & 0x07) == 0x02)
    print(f"  frames whose gfx bits (0x07) == 0x02 exactly: {only_bit1}/{len(shadow)}")
    bit0 = sum(1 for _, ft in shadow if isinstance(ft, int) and (ft & 0x01))
    print(f"  frames with bit0 (value 0x01) set: {bit0}/{len(shadow)}")

    print(f"\n=== other files (n={len(other)}) ===")
    print("frame_type histogram:", {hex(k) if isinstance(k, int) else k: v for k, v in hist(other).items()})
    bit0o = sum(1 for _, ft in other if isinstance(ft, int) and (ft & 0x01))
    print(f"  frames with bit0 (value 0x01) set: {bit0o}/{len(other)}")

    # The doc's prose claims 0x17 = main+shadow+???+playercolor.
    # Under reversal, 0x17 = bits 0,1,2,4 = main+shadow+???+playercolor. Consistent.
    print("\n=== worked check of the doc's own example ===")
    print("doc prose: 0x17 = main + shadow + ??? + playercolor")
    print("reversed mapping (bit0=main,1=shadow,2=???,3=damage,4=playercolor):")
    for v in (0x00, 0x01, 0x02, 0x03, 0x07, 0x0F, 0x17, 0x1F):
        names = [n for bit, n in ((0, "main"), (1, "shadow"), (2, "unknown5"),
                                  (3, "damage"), (4, "playercolor")) if v & (1 << bit)]
        print(f"  {v:#04x} = {v:08b} -> {names or ['(no layers)']}")

    out = {
        "shadow_files": [{"name": n, "first_ft": ft} for n, ft in shadow],
        "other_files_sample": [{"name": n, "first_ft": ft} for n, ft in other[:60]],
        "shadow_hist": hist(shadow),
        "other_hist": hist(other),
        "shadow_only_bit1": only_bit1, "shadow_with_bit0": bit0, "other_with_bit0": bit0o,
        "shadow_n": len(shadow), "other_n": len(other),
    }
    Path("sld_bitrev.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

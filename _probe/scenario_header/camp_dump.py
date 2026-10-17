import os, struct, glob, sys

CAMP = r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign"

files = sorted(glob.glob(os.path.join(CAMP, "*.aoe2campaign")))
print(f"campaign files: {len(files)}")
targets = files[:3] + [f for f in files if 'e3' in f.lower() or 'E3' in f][:2]
for p in sorted(set(targets)):
    b = open(p, 'rb').read()
    print(f"\n### {os.path.basename(p)}  size={len(b)}")
    print("  first 160 bytes:")
    for off in range(0, min(160, len(b)), 16):
        c = b[off:off+16]
        print(f"    {off:5d}: {c.hex(' '):<47} |{''.join(chr(x) if 32<=x<127 else '.' for x in c)}|")
    # look for embedded '1.NN\0\0\0\0' magic positions
    import re
    hits = [m.start() for m in re.finditer(rb"1\.\d\d\x00\x00\x00\x00", b)]
    print(f"  magic '1.NN\\0\\0\\0\\0' hits: {len(hits)} -> first 12: {hits[:12]}")
    print(f"  version strings seen: {sorted({b[h:h+4].decode() for h in hits})}")

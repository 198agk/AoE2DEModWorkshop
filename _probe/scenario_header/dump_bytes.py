import struct, os, sys, json, zlib

FILES = [
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario", "TheSiege"),
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\default0.aoe2scenario", "default0"),
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\7V1变态山谷-炮塔盛宴-变态难.aoe2scenario", "7V1"),
    (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign\0_E3_Scenario.aoe2scenario", "0_E3"),
]

for path, tag in FILES:
    if not os.path.exists(path):
        print(f"### {tag}: MISSING {path}")
        continue
    b = open(path, 'rb').read()
    print(f"### {tag}  size={len(b)}")
    print("  first 96 bytes hex:")
    for off in range(0, 96, 16):
        chunk = b[off:off+16]
        print(f"    {off:4d}: {chunk.hex(' ')}  |{''.join(chr(c) if 32<=c<127 else '.' for c in chunk)}|")
    ver = b[:4].decode('ascii', 'replace')
    hl = struct.unpack_from('<I', b, 4)[0]
    print(f"  version={ver!r} header_length_field(u32@4)={hl}")
    # c4 for scenario_instructions is str32: u32 len + bytes
    print()

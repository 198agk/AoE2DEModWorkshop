import struct, os, zlib, sys

def pstr32(b, off):
    n = struct.unpack_from('<I', b, off)[0]
    return n, b[off+4:off+4+n]

def parse_header(b):
    """Parse FileHeader per AoE2ScenarioParser structure (v1.36+ / v1.40+ family)."""
    out = {}
    off = 0
    out['version'] = b[0:4].decode('ascii', 'replace'); off = 4
    out['header_length'] = struct.unpack_from('<I', b, off)[0]; off += 4
    out['savable'] = struct.unpack_from('<i', b, off)[0]; off += 4
    out['timestamp'] = struct.unpack_from('<I', b, off)[0]; off += 4
    n, s = pstr32(b, off); off += 4 + n
    out['instructions_len'] = n
    out['instructions'] = s
    out['individual_victories_used'] = struct.unpack_from('<I', b, off)[0]; off += 4
    out['player_count'] = struct.unpack_from('<I', b, off)[0]; off += 4
    out['unknown_value'] = struct.unpack_from('<I', b, off)[0]; off += 4
    out['unknown_value_2'] = struct.unpack_from('<I', b, off)[0]; off += 4
    amt = struct.unpack_from('<I', b, off)[0]; off += 4
    out['amount_of_unknown_numbers'] = amt
    out['unknown_numbers'] = list(struct.unpack_from(f'<{amt}I', b, off)); off += 4*amt
    n, s = pstr32(b, off); off += 4 + n
    out['creator_len'] = n
    out['creator_name'] = s
    out['trigger_count'] = struct.unpack_from('<I', b, off)[0]; off += 4
    out['deflate_offset'] = off
    return out

FILES = [
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario", "TheSiege"),
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\default0.aoe2scenario", "default0"),
    (r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\7V1变态山谷-炮塔盛宴-变态难.aoe2scenario", "7V1"),
    (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\campaign\0_E3_Scenario.aoe2scenario", "0_E3"),
]

for path, tag in FILES:
    b = open(path, 'rb').read()
    print(f"### {tag} size={len(b)}")
    try:
        h = parse_header(b)
    except Exception as e:
        print("   PARSE FAIL:", type(e).__name__, e); continue
    for k, v in h.items():
        if k == 'instructions':
            print(f"   {k} = <{len(v)} bytes> {v[:60]!r}")
        elif k == 'creator_name':
            print(f"   {k} = {v!r}")
        else:
            print(f"   {k} = {v}")
    off = h['deflate_offset']
    rest = b[off:]
    print(f"   -> try zlib.decompressobj(-15) at off={off}, rest={len(rest)}B")
    for label, wbits in (("-15 raw", -15), ("15 zlib", 15), ("31 gzip", 31), ("47 auto", 47)):
        try:
            d = zlib.decompressobj(wbits)
            out = d.decompress(rest)
            out += d.flush()
            print(f"      [{label}] OK out={len(out)}B eof={d.eof}")
        except Exception as e:
            print(f"      [{label}] FAIL {type(e).__name__}: {e}")
    print()

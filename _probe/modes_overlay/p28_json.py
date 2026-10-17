"""p28: does the engine GENERICALLY open a json file by constructed name? This decides whether
`Pompeii.json` (0 literal occurrences in the exe) is read at all.
Tests:
  1. every NUL-terminated string that is exactly '.json' / '.JSON' / 'json' and its strict refs
  2. JSON-library fingerprints: nlohmann, rapidjson, jsoncpp, Json::, JsonValue, Value@json,
     Document@rapidjson, JsonDocument, json_object, cJSON, QJson
  3. RTTI names mentioning json (count + samples)
  4. strict refs to the remaining candidate suffixes
Read-only -> p28_out.txt
"""
import os, struct, re

EXE = r"D:\Games\Steam\steamapps\common\AoE2DE\AoE2DE_s.exe"
OUT = r"D:\Software\DeepSeek Harness\工作区2\_probe\modes_overlay"
F = open(os.path.join(OUT, "p28_out.txt"), "w", encoding="utf-8")
def P(*a): print(*a, file=F)

buf = open(EXE, "rb").read(); N = len(buf)
e = struct.unpack_from("<I", buf, 0x3c)[0]
nsec = struct.unpack_from("<H", buf, e+6)[0]
optsz = struct.unpack_from("<H", buf, e+20)[0]
so = e + 24 + optsz
sects = []
for i in range(nsec):
    o = so + i*40
    nm = buf[o:o+8].rstrip(b"\0").decode()
    vs, va, rs, ra = struct.unpack_from("<IIII", buf, o+8)
    sects.append((nm, va, vs, ra, rs))
def r2o(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs):
            o = ra + (rva - va); return o if 0 <= o < N else None
    return None
def o2r(o):
    for nm, va, vs, ra, rs in sects:
        if ra <= o < ra + rs: return va + (o - ra)
    return None
def sec(rva):
    for nm, va, vs, ra, rs in sects:
        if va <= rva < va + max(vs, rs): return nm
    return "?"
_, tva, tvs, tra, trs = [s for s in sects if s[0] == ".text"][0]
text = buf[tra:tra+trs]

def strict_refs(target_rva):
    out = []
    for p in range(1, len(text) - 4):
        d = struct.unpack_from("<i", text, p)[0]
        if (tva + p + 4) + d == target_rva and (text[p-1] & 0xC7) == 0x05:
            out.append(tva + p)
    return out

P("#"*100)
P("# 1) every NUL-terminated string with basename exactly '.json' / '.json'-suffixed bare form")
for needle in (b".json", b".JSON", b"json", b"Json"):
    pat = b"\0" + needle + b"\0"
    s = 0; hits = []
    while True:
        i = buf.find(pat, s)
        if i < 0: break
        hits.append(i + 1); s = i + 1
    P(f"   exact '.{needle.decode()}'-as-whole-string ('\\0{needle.decode()}\\0'): {len(hits)} hit(s)")
    for rva in hits:
        rr = o2r(rva)
        refs = strict_refs(rr) if rr else []
        P(f"       rva {rr:#x} [{sec(rr)}] strict_refs={len(refs)} {[hex(x) for x in refs[:6]]}")

P("")
P("#"*100)
P("# 2) string-start occurrences of '.json' as a SUFFIX fragment, with the string they terminate")
s = 0; cnt = 0; withref = 0
P("    (showing strings whose text ends in '.json' and which are followed by NUL)")
idx = []
p = 0
while True:
    i = buf.find(b".json\0", p)
    if i < 0: break
    idx.append(i); p = i + 1
P(f"   total '.json\\0' byte occurrences: {len(idx)}")
for i in idx:
    a = i
    while a > 0 and buf[a-1] != 0: a -= 1
    name = buf[a:i+5].decode("latin-1")
    rva = o2r(a)
    refs = strict_refs(rva) if rva is not None else []
    if refs: withref += 1
    tag = f" strict_refs={len(refs)} {[hex(x) for x in refs[:4]]}" if refs else " strict_refs=0"
    P(f"     {rva if rva is None else hex(rva)} {name!r}{tag}")
P(f"   -> {withref} of {len(idx)} '.json' strings are referenced by code at their exact start")

P("")
P("#"*100)
P("# 3) JSON library fingerprints anywhere in the image")
for fp in (b"nlohmann", b"rapidjson", b"jsoncpp", b"JSONCPP", b"Json::Value", b"json_object",
           b"cJSON", b"QJson", b"JsonDocument", b"Value@json", b"Document@rapidjson",
           b"basic_json", b"jansson", b"picojson", b"simdjson", b"json_parse", b"parse_json"):
    c = buf.count(fp)
    if c:
        i = buf.find(fp); a = max(0, i-60); b2 = min(N, i+80)
        P(f"   {fp!r}: {c} hit(s); first ctx fo {i:#x} [{sec(o2r(i)) if o2r(i) else '?'}]")
        P(f"       {buf[a:b2]!r}")
    else:
        P(f"   {fp!r}: 0")

P("")
P("#"*100)
P("# 4) RTTI names containing 'json' (case-insensitive)")
o = r2o([s for s in sects if s[0]=='.rdata'][0][1])
# brute: find '.?AV' / '.?AU' names mentioning json
names = set()
p = 0
while True:
    i = buf.find(b".?A", p)
    if i < 0: break
    q = buf.find(b"\0", i, i+400)
    if q > 0:
        try:
            nm = buf[i:q].decode("latin-1")
            if len(nm) < 400 and all(32 <= ord(c) < 127 for c in nm):
                if "json" in nm.lower(): names.add(nm)
        except Exception: pass
    p = i + 1
P(f"   distinct RTTI names mentioning 'json': {len(names)}")
for nm in sorted(names)[:40]: P(f"     {nm}")
F.close()
print("wrote p28_out.txt")

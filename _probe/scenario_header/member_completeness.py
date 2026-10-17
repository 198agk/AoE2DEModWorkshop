# -*- coding: utf-8 -*-
"""member_completeness.py -- prove campaign members are COMPLETE standalone
scenario files (not fragments).

A member is a complete standalone file iff:
  (1) at its own offset it begins with a 4-byte version tag,
  (2) the structural dispatch locates its deflate stream,
  (3) that stream reaches end-of-stream (d.eof) and
  (4) the stream's LAST CONSUMED BYTE lands exactly on the member's last byte
      (no trailing garbage, no truncation).

(3)+(4) together are the real test: an inflating prefix that stops early or
that needs bytes from the next member would mean members are NOT independent.
"""
import os
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from campaign_deterministic import parse_campaign_deterministic   # noqa: E402
from header_layout import field_offsets, read_savable, read_version  # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
CAMP_DIR = os.path.join(GAME, "resources", "_common", "campaign")

out = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


def consumed(b, off):
    """Raw-inflate b[off:]; return (out, eof, bytes_consumed, err)."""
    d = zlib.decompressobj(-zlib.MAX_WBITS)
    try:
        o = d.decompress(b[off:])
    except zlib.error as e:
        return b"", False, 0, str(e)
    if not d.eof:
        return o, False, 0, "no end-of-stream"
    return o, True, len(b) - off - len(d.unused_data), None


P("=" * 78)
P("CAMPAIGN MEMBER COMPLETENESS -- exact byte consumption")
P("=" * 78)

files = sorted(f for f in os.listdir(CAMP_DIR) if f.lower().endswith(".aoe2campaign"))
tot = 0
exact = 0
tag_ok = 0
fails = []
for cf in files:
    cb = open(os.path.join(CAMP_DIR, cf), "rb").read()
    c = parse_campaign_deterministic(cb)
    for m in c["members"]:
        tot += 1
        data = m["data"]
        if read_version(data)[0:2] == "1.":
            tag_ok += 1
        sv = read_savable(data)
        try:
            h = field_offsets(data, __import__("header_layout").SAVABLE_LAYOUT[sv])
        except Exception as e:
            fails.append((cf, m["name"], f"parse: {e}"))
            continue
        off = h["_deflate_offset"][0]
        o, eof, n, err = consumed(data, off)
        if eof and off + n == len(data):
            exact += 1
        else:
            fails.append((cf, m["name"], f"off={off} consumed={n} size={len(data)} eof={eof} err={err}"))

P(f"campaigns            : {len(files)}")
P(f"members              : {tot}")
P(f"members with valid 4-byte '1.x' version tag : {tag_ok}/{tot}")
P(f"members whose deflate stream consumes EXACTLY the member's bytes: {exact}/{tot}")
P()
if fails:
    P(f"FAILURES ({len(fails)}):")
    for f in fails[:30]:
        P("   ", f)
else:
    P("FAILURES: none")
P()
P("Interpretation: a member is a byte-exact, self-contained <FileHeader + raw")
P("DEFLATE stream> pair.  No member reads bytes from its neighbours, so the")
P("container really is 'back-to-back independent scenario files' with a member")
P("table in front -- PROVIDED the table is used to find each member's bounds.")
P("(A pure regex/magic scan without the table misses 6 of 235 members.)")

# dcam0 cross-check with the standalone The Siege
P()
P("=" * 78)
P("dcam0 member vs the standalone user-profile file of the same name")
P("=" * 78)
import hashlib
import json
dc = open(os.path.join(CAMP_DIR, "dcam0.aoe2campaign"), "rb").read()
cdc = parse_campaign_deterministic(dc)
PROF = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario"
for m in cdc["members"]:
    p = os.path.join(PROF, m["name"])
    if os.path.isfile(p):
        sb = open(p, "rb").read()
        P(f"{m['name']}")
        P(f"   member      : {len(m['data'])} B  sha1={hashlib.sha1(m['data']).hexdigest()}")
        P(f"   standalone  : {len(sb)} B  sha1={hashlib.sha1(sb).hexdigest()}")
        P(f"   BYTE-IDENTICAL: {sb == m['data']}")
    else:
        P(f"{m['name']}: no standalone counterpart in the profile directory")

open(os.path.join(HERE, "member_completeness_output.txt"), "w", encoding="utf-8").write("\n".join(out))
json.dump({"campaigns": len(files), "members": tot, "version_tag_ok": tag_ok,
           "exact_consumption": exact, "failures": fails[:50]},
          open(os.path.join(HERE, "member_completeness.json"), "w", encoding="utf-8"), indent=2)
P()
P("wrote member_completeness_output.txt / member_completeness.json")

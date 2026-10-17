# -*- coding: utf-8 -*-
"""oracle_check.py -- read AoE2ScenarioParser as the format ORACLE (never imported by
the shipped locator) and record:

  (a) exactly which exception the library raises for each pre-1.36 file;
  (b) the FileHeader retriever list from versions/DE/v*/structure.json for every
      version the library ships, so the claim "IVU was removed at 1.40" and the
      claim "no schema directory exists for pre-1.36" are read from source, not
      recalled;
  (c) whether the library can parse a 1.36+ file and what header length it computes,
      to cross-check our independently-derived deflate_offset.
"""
import json
import os
import sys

LIB = r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages\AoE2ScenarioParser"
VERS = os.path.join(LIB, "versions", "DE")

out = []
def P(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


P("=" * 78)
P("(b) ORACLE: FileHeader retriever lists shipped by the library")
P("=" * 78)
P(f"versions/DE directory entries: {sorted(os.listdir(VERS))}")
P()
P("NOTE: structure.json is loaded by json.load, so Python dict insertion order == file")
P("order == the library's BINARY READ ORDER.  (A raw alphabetical sort destroys it.)")
P()
TABLE = {}
for v in sorted(os.listdir(VERS)):
    if not v.startswith("v"):
        continue
    sj = os.path.join(VERS, v, "structure.json")
    if not os.path.isfile(sj):
        P(f"{v}: NO structure.json")
        continue
    st = json.load(open(sj, encoding="utf-8"))
    fh = st.get("FileHeader")
    if fh is None:
        P(f"{v}: no FileHeader section (keys={list(st)[:12]})")
        continue
    rets = fh.get("retrievers", {})
    names = list(rets)                      # INSERTION ORDER = binary order
    has_ivu = "individual_victories_used" in names
    TABLE[v] = names
    P(f"{v:6s} n={len(names):2d} ivu={str(has_ivu):5s} order={names}")
    for k, val in rets.items():
        extra = {kk: vv for kk, vv in val.items()
                 if kk not in ("type", "default", "comment", "dependencies")}
        if extra:
            P(f"        {k}: EXTRA {extra}")

P()
P("versions carrying individual_victories_used: "
  f"{sorted(v for v, n in TABLE.items() if 'individual_victories_used' in n)}")
P("versions NOT carrying it                  : "
  f"{sorted(v for v, n in TABLE.items() if 'individual_victories_used' not in n)}")
# do any two versions differ?
sig = {}
for v, n in TABLE.items():
    sig.setdefault(tuple(n), []).append(v)
P()
P(f"distinct retriever ORDERS across shipped versions: {len(sig)}")
for order, vs in sig.items():
    P(f"   {sorted(vs)}")
    P(f"      {list(order)}")

P()
P("=" * 78)
P("(a) ORACLE: what the library does with pre-1.36 files")
P("=" * 78)
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
TARGETS = [
    ("1.21", os.path.join(GAME, r"resources\_common\drs\gamedata_x2", "real_world_britain.scx")),
    ("1.21", os.path.join(GAME, r"resources\_common\drs\gamedata_x2", "real_world_antarctica.scx")),
    ("1.33", os.path.join(GAME, r"resources\_common\drs\gamedata_x2", "real_world_nippon.scx")),
    ("1.35", os.path.join(GAME, r"resources\_common\campaign", "0_E3_Scenario.aoe2scenario")),
    ("1.36", os.path.join(GAME, r"resources\_common\drs\gamedata_x2", "special_map_canyons.scx")),
    ("1.53", r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\resources\_common\scenario\The Siege.aoe2scenario"),
]
sys.path.insert(0, LIB)
try:
    from AoE2ScenarioParser.scenarios.aoe2_de_scenario import AoE2DEScenario
    P("AoE2DEScenario imported OK")
except Exception as e:
    P(f"import failed: {type(e).__name__}: {e}")
    AoE2DEScenario = None

P()
for label, path in TARGETS:
    if not os.path.isfile(path):
        P(f"{label}: MISSING {path}")
        continue
    exists = os.path.isdir(os.path.join(VERS, f"v{label}"))
    if AoE2DEScenario is None:
        P(f"{label}: (no library)")
        continue
    try:
        s = AoE2DEScenario.from_file(path)
        fh = getattr(s, "_file_header", None)
        P(f"{label}: OK  version={getattr(s,'scenario_version',None)} "
          f"library_header_len={len(fh) if fh is not None else None}  "
          f"(versions/DE/v{label} exists={exists})")
    except Exception as e:
        P(f"{label}: {type(e).__name__}: {e}   (versions/DE/v{label} exists={exists})")

P()
P("=" * 78)
P("(c) ORACLE: does the library's header length agree with our structural locator?")
P("=" * 78)
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from legacy_grammar import CANDS  # noqa: E402
from scenario_header import decompress_body  # noqa: E402

for label, path in TARGETS:
    if not os.path.isfile(path) or AoE2DEScenario is None:
        continue
    b = open(path, "rb").read()
    mine = None
    for cname, fn in CANDS:
        try:
            off, info = fn(b)
        except Exception:
            continue
        data, eof, err = decompress_body(b, off)
        if eof and len(data) > 1000:
            mine = (cname, off, len(data))
            break
    try:
        s = AoE2DEScenario.from_file(path)
        fh = getattr(s, "_file_header", None)
        lib_len = len(fh) if fh is not None else None
    except Exception as e:
        lib_len = f"FAILED({type(e).__name__})"
    P(f"{label}: our_layout={mine[0] if mine else None} our_deflate_offset="
      f"{mine[1] if mine else None} library_header_len={lib_len} "
      f"agree={mine and isinstance(lib_len,int) and mine[1]==lib_len}")

open(os.path.join(HERE, "oracle_check_output.txt"), "w", encoding="utf-8").write("\n".join(out))
print()
print("wrote oracle_check_output.txt")

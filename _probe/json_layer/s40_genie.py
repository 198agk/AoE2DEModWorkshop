import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import re, os
S = _HERE_PATH("_probe", "source", "genieutils")
for f in (r"include\genie\dat\Research.h", r"include\genie\dat\UnitLine.h",
          r"include\genie\dat\Civ.h", r"include\genie\dat\DatFile.h"):
    p = os.path.join(S, f)
    s = open(p, encoding="utf-8", errors="replace").read()
    print("=" * 72)
    print(f)
    print("=" * 72)
    i = s.find("class")
    print(s[i:i + 2200])
    print()
# DatFile: how UnitLines are gated + what sections exist
p = os.path.join(S, r"src\dat\DatFile.cpp")
s = open(p, encoding="utf-8", errors="replace").read()
print("=" * 72)
print("DatFile.cpp: gating + section names")
print("=" * 72)
for m in re.finditer(r".{0,120}(readUnitLines|writeUnitLines|UnitLines|GV_SWGB|GV_C32).{0,140}", s):
    print(repr(m.group(0)))

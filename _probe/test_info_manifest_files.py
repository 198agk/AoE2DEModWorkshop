# -*- coding: utf-8 -*-
r"""PIN: emit_data_mod must REPORT the info.json it wrote, not crash on it.

## The defect this exists to catch

2026-11-16 01:06: desktop/src-tauri was rebuilt, the built exe was copied into the
bundle, and _probe/ship_and_verify.py went from "all 13 tables present" straight to
a dead program:

    /api/build (page shape, 1) FAIL NameError: name 'info_abs' is not defined
    ConnectionResetError: [WinError 10054] ...

Commit 070fbb7 (Land techs on the slots officials reused) replaced the three lines
that wrote info.json with a call to write_info_json(...) -- a good refactor, because
a rename must rewrite info.json in place without rebuilding the folder.  But the
manifest line below it still measured info_abs, and that local was now gone.
write_info_json RETURNS the path, so the fix is to keep that return in info_abs.

Why it survived every earlier gate: no test in _probe/test_*.py built a whole mod
through emit_data_mod and then looked at the manifest -- the test that touches
info.json (test_info_json_shape.py) reads the SOURCE, and the tests that walk a
manifest read one produced by the running engine.  A NameError there is a 500 on the
screen for the player pressing the build button, the most-used button in the app.

Run:  python -X utf8 _probe\test_info_manifest_files.py
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.mod import emitter as E                       # noqa: E402

fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


print("A  a whole data mod, built end to end, reports the info.json it wrote")
tmp = tempfile.mkdtemp(prefix="info_manifest_")
mod_dir = os.path.join(tmp, "m1")
info = E.make_info("manifest pin", author="aoe2mod")
raised = None
man = None
try:
    man = E.emit_data_mod(mod_dir, b"\x00" * 4096, info)
except Exception as exc:                                    # noqa: BLE001
    raised = exc
check("emit_data_mod returns instead of raising", raised is None,
      "%s: %s" % (type(raised).__name__, raised) if raised else "")

if man is not None:
    info_abs = os.path.join(mod_dir, "info.json")
    check("the folder really holds info.json", os.path.isfile(info_abs), info_abs)
    rows = man.get("files") or []
    first = rows[0] if rows else {}
    check("the first manifest row is info.json", first.get("rel") == "info.json",
          "%r" % (first.get("rel"),))
    check("its byte count is the file on disk, not a guess",
          first.get("bytes") == os.path.getsize(info_abs),
          "manifest %s vs disk %s" % (first.get("bytes"), os.path.getsize(info_abs)))
    check("every manifest row that counts bytes exists on disk",
          all(os.path.isfile(os.path.join(mod_dir, r["rel"].replace("/", os.sep)))
              for r in rows if r.get("bytes")),
          "%s" % [r.get("rel") for r in rows])
    check("the info.json is COMPACT (no space after a colon)",
          b'": ' not in open(info_abs, "rb").read(),
          open(info_abs, "rb").read()[:120].decode("utf-8", "replace"))

print()
print("B  the source keeps the return value: a refactor must not re-orphan the name")
import inspect                                              # noqa: E402
src = inspect.getsource(E.emit_data_mod)
check("emit_data_mod assigns write_info_json's return to info_abs",
      "info_abs = write_info_json(" in src,
      "%r" % [ln.strip() for ln in src.splitlines() if "write_info_json(" in ln])
check("and the manifest still measures that variable",
      "os.path.getsize(info_abs)" in src)
check("the appended tuple carries the variable, not the throwing-away call",
      'written.append(("info.json", write_info_json(' not in src)

print()
print("INFO MANIFEST FILES: emit_data_mod reports the info.json it wrote; the")
print("  build route answers ok instead of NameError.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)

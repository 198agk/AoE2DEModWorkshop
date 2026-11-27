# -*- coding: utf-8 -*-
"""Does 「下载并装好」 replace the installed copy without eating the player's data?

Asked 2026-11-18 (verbatim): 「我要自动更新的，而不是自己手动去下载新版来自己
安装覆盖」.  The 关于 page could already say 远端有 1.0002; what it could not do
was act on that sentence, so the upgrade path was: read a number, open a browser,
download 286 MB by hand, quit, unzip over the folder, hope.

Auto-update on Windows is not one operation, it is four, and each has a way of
being fake:

1. deciding which asset is the update (the small one without `dat_archive`) and
   what its bytes should hash to -- GitHub publishes the digest, so a download
   can be called verified without trusting the wire;
2. unpacking it without letting a crafted name escape the target folder;
3. swapping `app/` and the three files beside it while the old exe is still
   running, which Windows forbids -- hence a detached applier that waits;
4. never touching `dat_archive`, `_mods_out` or `log`, which are the player's
   mods and data, not the build.

No network here: `release()` takes an `opener`, `_unpack` takes a real zip built
in a temp folder, and the swap is exercised on a fake install tree.
"""
import json
import os
import sys
import tempfile
import traceback
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

from aoe2mod import appversion as AV                      # noqa: E402
from aoe2mod import autoupdate as AU                     # noqa: E402
from aoe2mod import updates as UPD                       # noqa: E402

FAIL = []


def check(name, ok, detail=None):
    if ok:
        print("  ok   %s" % name)
        return
    FAIL.append(name + ("" if detail is None else " :: %s" % (detail,)))
    print("  FAIL %s%s" % (name, "" if detail is None else " :: %s" % (detail,)))


def opener_for(body):
    """An `opener` that answers `body` for any URL, and records the URLs."""
    seen = []

    def fetch(url, timeout=None):
        seen.append(url)
        if isinstance(body, Exception):
            raise body
        return body

    return fetch, seen


def release_doc(assets, tag="v9.9999", name="模组工坊 9.9999"):
    return json.dumps({"tag_name": tag, "name": name, "assets": assets})


def asset(size=1234, digest="sha256:" + "a" * 64, url=None, name=None):
    return {"name": name or AU.ASSET, "size": size, "digest": digest,
            "browser_download_url": url or ("https://github.com/x/y/releases/download/v9.9999/" + (name or AU.ASSET))}


# ---- 1. which asset, and what its bytes must hash to ----
fetch, seen = opener_for(release_doc([asset(name="AoE2DEModWorkshop.zip", size=367864513),
                                      asset(size=29791289)]))
rel = AU.release(opener=fetch)
check("the release is read once", len(seen) == 1, seen)
check("the update asset is the small one, not the 367 MB full zip",
      rel.get("ok") is True and rel["asset"]["name"] == AU.ASSET, rel)
check("its size is carried through, so the bar can say how far along it is",
      rel["asset"]["size"] == 29791289, rel["asset"])
check("the digest GitHub published is stripped to a bare sha256",
      rel["asset"]["sha256"] == "a" * 64, rel["asset"]["sha256"])
check("the direct URL is kept",
      rel["asset"]["url"].startswith("https://github.com/"), rel["asset"]["url"])
check("...and a proxied one is offered beside it, because the direct host times out here",
      rel["asset"]["fallback"].startswith(AU.PROXY), rel["asset"]["fallback"])
check("the version is the number the player reads",
      rel["version"] == "9.9999", rel["version"])

# A digest with no sha256: prefix, and a missing digest, must not be mistaken for
# "verified".
rel2 = AU.release(opener=opener_for(release_doc([asset(digest="")]))[0])
check("an asset with no digest is not silently called verified",
      rel2["asset"]["sha256"] == "", rel2["asset"]["sha256"])

# A release that predates the small archive has to say so in words.
rel3 = AU.release(opener=opener_for(release_doc([asset(name="AoE2DEModWorkshop.zip")]))[0])
check("a release without the update asset says which assets it does have",
      rel3.get("ok") is False and "AoE2DEModWorkshop.zip" in str(rel3.get("error")),
      rel3.get("error"))
check("...and names the archive it wanted",
      AU.ASSET in str(rel3.get("error")), rel3.get("error"))

rel4 = AU.release(opener=opener_for(RuntimeError("nope"))[0])
check("an unreachable API is a sentence, not an exception",
      rel4.get("ok") is False and "nope" in str(rel4.get("error")), rel4.get("error"))


# ---- 2. unpacking cannot escape the folder ----
WORK = tempfile.mkdtemp(prefix="aoe2mod-update-")


def make_zip(path, entries):
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in entries:
            zf.writestr(name, text)
    return path


flat = make_zip(os.path.join(WORK, "flat.zip"),
                [("app/runtime/manifest.json", "{}"), ("README.txt", "hi")])
into = os.path.join(WORK, "flat")
top = AU._unpack(flat, into)
check("a hand-made archive with app/ at the top unpacks to its own root",
      os.path.isdir(os.path.join(top, "app")), top)

wrapped = make_zip(os.path.join(WORK, "wrapped.zip"),
                   [("AoE2ModWorkshop-COMPLETE/app/runtime/manifest.json", "{}"),
                    ("AoE2ModWorkshop-COMPLETE/README.txt", "hi")])
into2 = os.path.join(WORK, "wrapped")
top2 = AU._unpack(wrapped, into2)
check("the released zip has one folder on top and the unpacker follows it",
      os.path.isdir(os.path.join(top2, "app")), top2)
check("...and it is that folder, not the outer one",
      os.path.basename(top2) == "AoE2ModWorkshop-COMPLETE", top2)

evil = make_zip(os.path.join(WORK, "evil.zip"),
                [("app/x.txt", "x"), ("../escaped.txt", "boom")])
into3 = os.path.join(WORK, "evil")
os.makedirs(into3, exist_ok=True)
try:
    AU._unpack(evil, into3)
    refused = False
except RuntimeError as exc:
    refused = "跳出目录" in str(exc)
check("a name that climbs out of the folder is refused before anything is written",
      refused, )
check("...so nothing landed outside it",
      not os.path.exists(os.path.join(WORK, "escaped.txt")))

empty = make_zip(os.path.join(WORK, "empty.zip"), [("README.txt", "hi")])
try:
    AU._unpack(empty, os.path.join(WORK, "empty"))
    said = ""
except RuntimeError as exc:
    said = str(exc)
check("an archive with no app/ is refused in words",
      "没有 app" in said, said)


# ---- 3. the install root: which copy am I, and can I be replaced? ----
check("running from the source tree is not an installed copy",
      AU.install_root(HERE) is None, AU.install_root(HERE))

FAKE = os.path.join(WORK, "install")
os.makedirs(os.path.join(FAKE, "app", "runtime"), exist_ok=True)
os.makedirs(os.path.join(FAKE, "app", "aoe2mod"), exist_ok=True)
with open(os.path.join(FAKE, "app", "runtime", "manifest.json"), "w") as fh:
    fh.write("{}")
check("a folder with app/runtime/manifest.json and app/aoe2mod is an install",
      AU.install_root(os.path.join(FAKE, "app")) == FAKE,
      AU.install_root(os.path.join(FAKE, "app")))
check("the engine runs with its cwd inside app/, so one level up is the install",
      AU.install_root(os.path.join(FAKE, "app")) == os.path.dirname(
          os.path.join(FAKE, "app")), )

os.environ["AOE2MOD_ROOT"] = FAKE
check("AOE2MOD_ROOT wins when a launcher sets it",
      AU.install_root(tempfile.gettempdir()) == FAKE,
      AU.install_root(tempfile.gettempdir()))
del os.environ["AOE2MOD_ROOT"]


# ---- 4. what the swap is allowed to touch ----
check("the archive is the small one, named once", AU.ASSET.endswith(".zip"), AU.ASSET)
check("the three files beside app/ are the build's, and they are named",
      set(AU.ROOT_FILES) == {"AoE2 DE Mod Workshop.exe", "WebView2Loader.dll", "README.txt"},
      AU.ROOT_FILES)
PLAYER_DIRS = ("dat_archive", "_mods_out", "log")
check("no player folder is in the list of things to replace",
      not (set(PLAYER_DIRS) & set(AU.ROOT_FILES)), AU.ROOT_FILES)
src = open(os.path.join(HERE, "aoe2mod", "autoupdate.py"), encoding="utf-8").read()
check("the applier copies app/ and the three files, and nothing else by name",
      "put_tree(fh, os.path.join(stage, \"app\")" in src)
# The module docstring mentions them on purpose (it says they are never taken).
# The applier is the code that could get it wrong, so it is what gets read.
check("...and the applier never spells dat_archive or _mods_out at all",
      "dat_archive" not in AU.APPLIER and "_mods_out" not in AU.APPLIER, )
check("the work folder is its own name, so a failed update can be read later",
      AU.WORK_DIR == "_update", AU.WORK_DIR)
check("progress goes to one job key, the one the page polls",
      AU.JOB_KEY == "update", AU.JOB_KEY)


# ---- 5. the swap itself, on a fake install ----


def fake_install():
    root = tempfile.mkdtemp(prefix="aoe2mod-inst-")
    os.makedirs(os.path.join(root, "app", "runtime"))
    with open(os.path.join(root, "app", "runtime", "marker.txt"), "w") as fh:
        fh.write("old")
    for name in AU.ROOT_FILES:
        with open(os.path.join(root, name), "w") as fh:
            fh.write("old-" + name)
    for d in ("dat_archive", "_mods_out"):
        os.makedirs(os.path.join(root, d))
        with open(os.path.join(root, d, "keep.txt"), "w") as fh:
            fh.write("player data")
    return root


stage = os.path.join(WORK, "stage")
os.makedirs(os.path.join(stage, "app", "runtime"))
with open(os.path.join(stage, "app", "runtime", "marker.txt"), "w") as fh:
    fh.write("new")
with open(os.path.join(stage, "app", "runtime", "extra.txt"), "w") as fh:
    fh.write("new file")
for name in ("AoE2 DE Mod Workshop.exe", "WebView2Loader.dll"):
    with open(os.path.join(stage, name), "w") as fh:
        fh.write("new-" + name)
# README.txt is deliberately absent from the stage: an older release may not
# carry it, and losing the player's copy would be worse than not updating it.

INST = fake_install()
NS = {"__name__": "applier"}
APPLY = {}
exec(compile(AU.APPLIER, "applier.py", "exec"), NS)
ok_app = NS["put_tree"](None, os.path.join(stage, "app"), os.path.join(INST, "app"))
ok_root = True
for name in AU.ROOT_FILES:
    ok_root = NS["put_file"](None, os.path.join(stage, name), os.path.join(INST, name)) and ok_root
check("a staged app/ replaces the old one", ok_app is True)
check("...and every file in it is the new one",
      open(os.path.join(INST, "app", "runtime", "marker.txt")).read() == "new")
check("...including files the old copy did not have",
      os.path.isfile(os.path.join(INST, "app", "runtime", "extra.txt")))
check("the exe and the dll are replaced",
      open(os.path.join(INST, "AoE2 DE Mod Workshop.exe")).read() == "new-AoE2 DE Mod Workshop.exe")
check("a file the stage does not have is left alone rather than deleted",
      open(os.path.join(INST, "README.txt")).read() == "old-README.txt")
check("the player's data folder is still there, untouched",
      open(os.path.join(INST, "dat_archive", "keep.txt")).read() == "player data")
check("...and so is the built-mods folder",
      open(os.path.join(INST, "_mods_out", "keep.txt")).read() == "player data")
check("no leftover .old- copy of app/ is kept once the new one is in",
      not [n for n in os.listdir(INST) if n.startswith("app.old-")],
      [n for n in os.listdir(INST) if n.startswith("app.old-")])

# The first real run left an `app.old-<stamp>` behind every time, because
# `rmtree(ignore_errors=True)` met a file whose write bit was clear (zipfile
# does not set one, and copy2 carries whatever it finds) and quietly gave up.
# A leftover is not cosmetic: it is a whole second copy of the build, and the
# next update would have had to move a folder that no longer fits.
RO = tempfile.mkdtemp(prefix="aoe2mod-ro-")
os.makedirs(os.path.join(RO, "deep", "deeper"))
ONE = os.path.join(RO, "deep", "deeper", "locked.txt")
with open(ONE, "w") as fh:
    fh.write("locked")
os.chmod(ONE, 0o444)
NS["drop"](RO)
check("an old tree is removed even when a file in it is read-only",
      not os.path.isdir(RO), os.path.isdir(RO))


# ---- 6. the applier is a script, not an import ----
check("the applier is source text, so it survives the folder it replaces",
      isinstance(AU.APPLIER, str) and "def main(argv)" in AU.APPLIER)
check("...and it imports nothing from aoe2mod",
      "aoe2mod" not in AU.APPLIER.split("def say(")[1].split("def alive(")[0])
check("it waits for both the shell and the engine before swapping",
      "wait_gone(fh, [engine, shell])" in AU.APPLIER)
check("it opens the new build when it is done",
      "launch(fh, root, exe)" in AU.APPLIER)
check("a failure it cannot undo reaches a person, not just a log",
      "MessageBoxW" in AU.APPLIER)


# ---- 7. the button and the sentence that shares it ----
got = {"ok": True, "reachable": True, "behind": True, "remote": "9.9999"}
# Three parts since 2026-11-26 (「以后都这样0.0.0写」; before that it was two decimals,
# and before that four, which put fourteen releases and nine gigabytes into five
# days).  What matters here is that the number is exactly TWO dots and three
# integers, because the 关于 page, the release tag, the installer name and the gist
# all repeat it verbatim.
check("the check answers with the number this build says it is",
      AV.VERSION.count(".") == 2
      and all(p.isdigit() for p in AV.VERSION.split(".")),
      AV.VERSION)
check("the version the player reads sorts above the one before it",
      UPD.ver_tuple(AV.VERSION) > UPD.ver_tuple("1.0"), AV.VERSION)
check("what this build changed is written down for the 关于 page",
      isinstance(AV.CHANGES, tuple) and len(AV.CHANGES) >= 1, AV.CHANGES)
check("...in Chinese, one line each",
      all(isinstance(x, str) and x.strip() for x in AV.CHANGES), AV.CHANGES)

try:
    AU.start(root=None)
    raised = ""
except RuntimeError as exc:
    raised = str(exc)
check("a source checkout is told it cannot replace itself, in words",
      "源码目录" in raised, raised)

if FAIL:
    print("")
    print("UPDATE INSTALL: %d CHECK(S) FAILED" % (len(FAIL),))
    for one in FAIL:
        print("  - " + one)
    sys.exit(1)
print("")
print("UPDATE INSTALL: THE SMALL ARCHIVE IS CHECKED AGAINST THE DIGEST GITHUB PUBLISHES, "
      "THE SWAP REPLACES app/ AND NEVER THE PLAYER'S DATA, AND A COPY THAT CANNOT BE "
      "REPLACED SAYS SO BEFORE THE BUTTON IS PRESSED")
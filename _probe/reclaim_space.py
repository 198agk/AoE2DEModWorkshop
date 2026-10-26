"""Find the build caches that are worth reclaiming, and prove each one is a cache.

The workspace has twice grown by half a gigabyte in a day without anyone noticing:
every probe that calls `tk.build(...)` leaves a 11.4 MB `.dat` behind, and the
suites that check those builds leave the whole mod folder.  On 2026-10-24 the total
was 10.7 GB before anyone looked.

The safe rule is not "delete the big directories".  Two kinds of directory look
identical from `du` and behave oppositely:

  * **regenerated** -- the suite that names it removes it and then builds into it
    (`shutil.rmtree(OUT)` followed by `tk.build(..., out_dir=OUT)`).  Deleting it
    costs one rebuild.  `_probe/test_new_unit_box.py`, `test_linked_group.py`,
    `test_availability_dat_half.py`, `test_tech_create.py`,
    `test_replace_on_map.py` are all of this kind.
  * **read** -- the suite only ever reads a prebuilt directory.  Five of those
    existed in October 2026 (`out_smoke6`, `out_smoke8`, `out_dshtest_v2`,
    `out_probe_bundle_dat_half`, `out_dshtest_v4`) and deleting them broke the
    suites rather than the tree; they were fixed to build their own, but the shape
    can come back.

So this tool reads the naming suite and only reclaims what it can *prove* is
regenerated: the file must both remove/create the directory and call a build.  A
directory that is merely mentioned, or only read, stays and says why.

Nothing is deleted.  The moves go through `recycle.ps1`, which uses the shell's
Recycle Bin verb -- recoverable, and the user asked for exactly that on
2026-10-26.

    <python> -X utf8 _probe/reclaim_space.py            # report only
    <python> -X utf8 _probe/reclaim_space.py --apply    # recycle the provable ones

`aoe2mod/tests/out/` is deliberately not a candidate: it is tracked in git and read
by `test_api.py` / `test_compiler.py` / `test_emit_mod.py`.  Its three 11.4 MB
`.dat` files are build products of those suites, but removing a tracked file is a
history decision, not cleanup.
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROBE = os.path.join(ROOT, "_probe")

# directory -> the suite expected to regenerate it.  The pairing is a hint: every
# row is re-checked against the source before anything moves, because a stale hint
# is exactly how the five read-only directories were once mistaken for caches.
CANDIDATES = [
    ("out_avail_dat_half", "test_availability_dat_half.py"),
    ("_group_out", "test_linked_group.py"),
    ("_box_out", "test_new_unit_box.py"),
    ("out_repaint", "test_repaint.py"),
    ("out_effect", "test_effect_walk.py"),
    ("out_effect_append", "test_effect_append.py"),
    ("out_carrier_pin", "test_dat_carrier.py"),
    ("out_carrier_pin_revoke", "test_dat_carrier.py"),
    ("out_tech_create", "test_tech_create.py"),
    ("out_tech_create_icon", "test_tech_create.py"),
    ("out_repl_bundle", "test_replace_on_map.py"),
    ("out_repl_agree", "test_replace_on_map.py"),
    ("_repair_replay", "test_replay.py"),
    ("out_probe_bundle_dat_half", "probe_bundle_dat_half.py"),
    ("out_smoke6", "build_smoke6.py"),
    ("out_smoke8", "build_smoke8.py"),
]

MIN_MB = 3.0


def size_of(path):
    total = 0
    for base, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(base, f))
            except OSError:
                pass
    return total


def verdict(suite_path, name):
    """Can this directory be proven regenerated, or is it an input?

    The distinction rests on two separate facts, and both must hold: the naming
    file removes or creates the path, AND that file builds something.  A file that
    only mentions the directory (a docstring, a report path) proves nothing.
    """
    if not os.path.isfile(suite_path):
        return False, "no such file: %s" % os.path.basename(suite_path)
    txt = io.open(suite_path, encoding="utf-8", errors="replace").read()
    if name not in txt:
        return False, "the named file never mentions it"
    window = []
    for m in re.finditer(re.escape(name), txt):
        lo = max(0, m.start() - 1200)
        window.append(txt[lo:m.end() + 1200])
    blob = "\n".join(window)
    makes = bool(re.search(r"rmtree|makedirs|mkdir", blob))
    builds = bool(re.search(r"build\(|build_bundle\(|emit_data_mod\(", txt))
    if not makes:
        return False, "nothing removes or creates it -- treat it as an input"
    if not builds:
        return False, "the named file never builds"
    return True, "removed and rebuilt by %s" % os.path.basename(suite_path)


def main():
    apply_changes = "--apply" in sys.argv
    reclaim = []
    kept = []
    total = 0.0

    for name, suite in CANDIDATES:
        d = os.path.join(PROBE, name)
        if not os.path.isdir(d):
            continue
        mb = size_of(d) / 1048576.0
        if mb < MIN_MB:
            continue
        ok, why = verdict(os.path.join(PROBE, suite), name)
        if ok:
            reclaim.append("_probe/%s" % name)
            total += mb
            print("RECLAIM %-26s %6.1f MB  %s" % (name, mb, why))
        else:
            kept.append((mb, name, why))
            print("  KEEP  %-26s %6.1f MB  %s" % (name, mb, why))

    print()
    print("reclaimable: %d directories, %.1f MB" % (len(reclaim), total))
    if not reclaim:
        return 0

    lst = os.path.join(HERE, "tmp_recycle_list.txt")
    io.open(lst, "w", encoding="utf-8", newline="\n").write(
        "\n".join(reclaim) + "\n")
    if not apply_changes:
        print("dry run -- pass --apply to move them to the Recycle Bin")
        return 0

    out = subprocess.run(
        ["powershell.exe", "-ExecutionPolicy", "Bypass", "-File",
         os.path.join(HERE, "recycle.ps1"), "-ListFile", lst],
        capture_output=True)
    print((out.stdout or b"").decode("utf-8", "replace"))
    err = (out.stderr or b"").decode("utf-8", "replace").strip()
    if err:
        print("stderr: " + err[:400])
    return 0 if out.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

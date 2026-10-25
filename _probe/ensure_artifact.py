"""Make a suite that reads a prebuilt artifact able to rebuild it.

Why this exists: on 2026-10-25 I cut the workspace from 10.7 GB to 476 MB.  The
safety check I wrote asked "does any tracked file mention this build directory",
and I read "mentioned by a suite" as "that suite rebuilds it".  Five suites only
READ their directory -- `test_smoke6_result.py` failed with `KeyError: 'BRITONS'`
because `out_smoke6` was gone, which reads like a data bug and was actually a
deleted folder.  The check answered a question about mentions when the question
was about building.

So the rule is: a suite that depends on a directory must be able to produce it.
This helper runs the builder when the directory is missing and says so out loud,
because a rebuild during a test run takes seconds and a false red costs an hour
of reading the wrong thing.

    from ensure_artifact import ensure
    ensure("out_smoke6", "build_smoke6.py")
"""
import io
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)


def ensure(dir_name, builder, required=None, quiet=False):
    """Make sure `_probe/<dir_name>` exists, running `builder` if it does not.

    `required` is an optional relative path inside the directory whose presence
    is the real test (a directory can exist and be half-written).  Returns the
    absolute directory path.  Raises SystemExit with a readable message if the
    builder fails -- a suite cannot honestly report on data it could not build.
    """
    target = os.path.join(HERE, dir_name)
    marker = os.path.join(target, required) if required else target
    if os.path.exists(marker):
        return target

    script = os.path.join(HERE, builder)
    if not os.path.isfile(script):
        print("CANNOT REBUILD %s: the builder %s is not on disk" % (dir_name, builder))
        raise SystemExit(1)

    print("REBUILDING %s (it is not on disk; it is an artifact, not a fixture)"
          % dir_name)
    print("  builder: %s" % builder)
    out = subprocess.run([sys.executable, "-X", "utf8", "-u", script],
                         cwd=PROJECT, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    text = out.stdout.decode("utf-8", "replace")
    tail = [l for l in text.splitlines() if l.strip()][-3:]
    if out.returncode != 0 or not os.path.exists(marker):
        print("CANNOT REBUILD %s: %s exited %d"
              % (dir_name, builder, out.returncode))
        for line in tail:
            print("  " + line)
        raise SystemExit(1)
    if not quiet:
        for line in tail:
            print("  " + line)
    return target


if __name__ == "__main__":
    # `python _probe/ensure_artifact.py <dir> <builder> [required]` for a manual check
    if len(sys.argv) < 3:
        print("usage: ensure_artifact.py <dir_name> <builder.py> [required_rel_path]")
        raise SystemExit(2)
    print(ensure(sys.argv[1], sys.argv[2],
                 sys.argv[3] if len(sys.argv) > 3 else None))

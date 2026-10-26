# -*- coding: utf-8 -*-
"""Entry point for the packaged build.

`tools/run_ui.py` is the entry when the repo is on disk.  This file is the entry
when the whole thing is one exe, and the difference is not cosmetic:

* a frozen build has no repository, so anything resolved relative to `__file__`
  inside the archive points at a temp folder that is deleted on exit;
* therefore `argv` must be passed through (the first packaging attempt dropped
  `--port` and the probe waited ten minutes on a socket nobody had bound);
* and the working directory must NOT be assumed -- a player double-clicking an
  exe has whatever cwd Explorer gave it.

Everything else is the same program.
"""
import os
import sys


def _bootstrap():
    """Make `aoe2mod` and `tools` importable, frozen or not."""
    here = os.path.dirname(os.path.abspath(__file__))
    if getattr(sys, "frozen", False):
        # One-file builds unpack to _MEIPASS; that folder is on sys.path already.
        roots = [getattr(sys, "_MEIPASS", here),
                 os.path.dirname(os.path.abspath(sys.executable))]
    else:
        roots = [os.path.dirname(here)]
    for root in roots:
        if root and root not in sys.path:
            sys.path.insert(0, root)


def main():
    _bootstrap()
    from tools import run_ui
    return run_ui.main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main() or 0)

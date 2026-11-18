# -*- coding: utf-8 -*-
"""Every place the product shows a logo shows THE SAME logo.

WHY THIS EXISTS
---------------
BRAND.md rule 5: the logo is one file -- `brand/app-icon.png` scaled down, no
redrawing, no recolouring, no second variant.  Two pages broke that rule by
drawing their own crest out of CSS: the Tauri shell page drew a gold
`clip-path` pentagon (72x84) and the Python loading page drew a blue one
(44x51).  Neither was the product's icon, and neither could be fixed by
changing the master, because neither read the master at all.

A second thing is pinned here that no screenshot can show: the shipped page and
the developer page must be the same page.  `desktop/ui/index.html` is INLINED by
tauri-codegen at compile time, so a build whose `ui/` was not synced ships a page
that does not exist in the repository -- measured 2026-11-01: the build tree held
a 1159-byte page from 2026-10-26 while the repo had 53825 bytes, and the exe
still showed the old gold pentagon.  So this also checks that
`build_shell_ascii.py` syncs `ui/`, and that the two copies agree when the tree
exists.

Run:  python -X utf8 _probe/test_splash_brand.py
"""
import base64
import hashlib
import io
import os
import re
import sys
import _paths as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SHELL = os.path.join(ROOT, "desktop", "ui", "index.html")
LOADING = os.path.join(ROOT, "aoe2mod", "ui", "loading.py")
PAGE = os.path.join(ROOT, "aoe2mod", "ui", "static", "index.html")
MASTER = os.path.join(ROOT, "brand", "app-icon.png")
BUILD_SHELL = os.path.join(HERE, "build_shell_ascii.py")
BUILD_PAGE = os.path.join(P.BUILD, "ui", "index.html")
PAGES = (("shell", SHELL), ("loading", LOADING), ("rail", PAGE))

FAILS = []


def check(label, ok, detail=""):
    print("  %s %s%s" % ("ok  " if ok else "FAIL", label,
                         (" :: " + detail) if (detail and not ok) else ""))
    if not ok:
        FAILS.append(label)
    return ok


def read(path):
    with io.open(path, encoding="utf-8") as fh:
        return fh.read()


def inline_pngs(text):
    """The inline PNG that sits in a logo slot (``class="mark"``).

    Not every inline image on a page is a logo.  The about page carries the
    sponsor's QR code as a second inline PNG, three hundred thousand bytes
    away from the brand slot, so counting every one of them made a rule about
    the brand fail for a reason that has nothing to do with the brand.  The
    rule is about the logo, so only the logo slot is counted.
    """
    same_tag = re.findall(
        r'<img[^>]*class="mark"[^>]*data:image/png;base64,([A-Za-z0-9+/=]+)',
        text)
    in_span = re.findall(
        r'<span class="mark"><img[^>]*data:image/png;base64,([A-Za-z0-9+/=]+)',
        text)
    return same_tag + in_span


def main():
    print("\n=== 1. no page draws its own crest any more ===")
    for name, path in PAGES:
        text = read(path)
        check("%s: no clip-path pentagon" % name, "clip-path" not in text,
              "a CSS crest is a second logo")
        check("%s: no .crest rule or class" % name,
              ".crest" not in text and 'class="crest"' not in text)

    print("\n=== 2. each page carries exactly one inline icon, on an <img> ===")
    pngs = {}
    for name, path in PAGES:
        text = read(path)
        found = inline_pngs(text)
        pngs[name] = found
        check("%s: exactly one inline PNG" % name, len(found) == 1,
              "found %d" % len(found))
        # Inline on purpose: the shipped shell serves only "/" and the /api/*
        # routes, so a separate /static/ asset is a 404 in the release while the
        # dev server serves it fine, and a single-file page cannot be broken by
        # a ship that copies the exe and forgets the assets.
        check("%s: it lives on an <img class=\"mark\">" % name,
              bool(re.search(r'<img[^>]*class="mark"[^>]*data:image/png', text))
              or bool(re.search(r'<span class="mark"><img[^>]*data:image/png',
                                text)))
        check("%s: decorative, so it is hidden from screen readers" % name,
              'alt=""' in text and "aria-hidden" in text)

    print("\n=== 3. the three icons are the same picture ===")
    blobs = {}
    for name, found in pngs.items():
        if not found:
            continue
        blobs[name] = base64.b64decode(found[0])
        print("  --   %-8s %6d bytes  sha %s" % (
            name, len(blobs[name]),
            hashlib.sha256(blobs[name]).hexdigest()[:16]))
    # The FILES differ between pages because the encoder's zlib choices differ,
    # so compare pixels.  A file-hash assertion would fail the day Pillow is
    # upgraded, for no reason at all.
    try:
        from PIL import Image, ImageChops
    except ImportError:                                  # pragma: no cover
        print("  SKIP pixel comparison: Pillow is not installed")
        Image = None
    if Image is not None and len(blobs) >= 2:
        imgs = {k: Image.open(io.BytesIO(v)).convert("RGBA")
                for k, v in blobs.items()}
        ref = imgs.get("rail") or list(imgs.values())[0]
        check("the rail icon is 128x128 (the master's working size)",
              ref.size == (128, 128), str(ref.size))
        for name, im in imgs.items():
            if im is ref:
                continue
            same = ImageChops.difference(im, ref).getbbox() is None
            check("%s icon is pixel-identical to the rail icon" % name, same,
                  "a different picture in the same slot")

        print("\n=== 4. and it is the master, not a retouched copy ===")
        check("brand/app-icon.png exists", os.path.isfile(MASTER))
        if os.path.isfile(MASTER):
            master = Image.open(MASTER).convert("RGBA")
            check("the master is 1024x1024", master.size == (1024, 1024),
                  str(master.size))
            want = master.resize((128, 128), Image.LANCZOS)
            for name, im in imgs.items():
                diff = ImageChops.difference(im, want)
                check("%s icon equals a fresh LANCZOS downscale of the master"
                      % name, diff.getbbox() is None,
                      "a retouch (sharpen / crop / recolour) shows up here")

    print("\n=== 5. the build tree syncs the page it inlines ===")
    src = read(BUILD_SHELL)
    m = re.search(r"(?m)^SYNC\s*=\s*\[([^\]]*)\]", src)
    check("build_shell_ascii.py has a SYNC list", m is not None)
    if m:
        synced = [x.strip().strip("\"'") for x in m.group(1).split(",") if x.strip()]
        # tauri-codegen inlines desktop/ui/index.html at compile time.  Without
        # `ui` in this list the build tree keeps whatever page it had, and the
        # exe ships a page the repository does not contain.
        check("`ui` is in it", "ui" in synced, str(synced))
    check("and the tree is verified by fingerprint, not by counting .rs files",
          "def fingerprint(" in src and "def diff_files(" in src,
          "count_rs() said ok while ui/ was a month old")

    if os.path.isfile(BUILD_PAGE):
        a, b = read(SHELL), read(BUILD_PAGE)
        eq = hashlib.sha256(a.encode("utf-8")).hexdigest() == \
            hashlib.sha256(b.encode("utf-8")).hexdigest()
        check("the build tree's page is the repo's page", eq,
              "%d vs %d bytes" % (len(a), len(b)))
    else:
        print("  --   no ASCII build tree yet, skipping the copy comparison")

    print()
    if FAILS:
        print("SPLASH BRAND: %d CHECK(S) FAILED -> %s" % (len(FAILS), FAILS))
        return 1
    print("SPLASH BRAND: ONE ICON FILE, THREE PLACES, AND THE BUILD INLINES THE "
          "REPO'S PAGE")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Pack a release folder into a zip next to it, plus a .sha256 sidecar.

Why zipfile and not the shell: this MSYS git-bash has no zip binary at all.
"""
import hashlib
import os
import shutil
import sys
import zipfile


def digest(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def build(folder, out_zip, skip=(), arcname=None):
    root = os.path.abspath(folder)
    parent = os.path.dirname(root)
    top = arcname or os.path.basename(root)
    names = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if os.path.join(dirpath, d) not in skip)
        if dirpath in skip:
            continue
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            if full in skip:
                continue
            names.append(full)
    if os.path.exists(out_zip):
        os.remove(out_zip)
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for full in names:
            rel = os.path.relpath(full, root)
            z.write(full, top + '/' + rel.replace(os.sep, '/'))
    with zipfile.ZipFile(out_zip) as z:
        bad = z.testzip()
        count = len(z.namelist())
        pyc = [n for n in z.namelist() if n.endswith('.pyc') or '__pycache__' in n]
    size = os.path.getsize(out_zip)
    sha = digest(out_zip)
    sidecar = out_zip + '.sha256'
    with open(sidecar, 'w', encoding='utf-8', newline='\n') as f:
        f.write(sha + '  ' + os.path.basename(out_zip) + '\n')
    print('%s' % top)
    print('  files   %d' % count)
    print('  bytes   %d' % size)
    print('  sha256  %s' % sha)
    print('  testzip %s' % ('OK' if bad is None else 'CORRUPT ' + str(bad)))
    print('  pyc     %d' % len(pyc))
    return 0 if bad is None and not pyc else 1


def main(argv):
    args = argv[1:]
    skip = []
    out_name = None
    arcname = None
    folders = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--without':
            i += 1
            skip.append(os.path.abspath(args[i].rstrip('\\/')))
        elif a == '--out':
            i += 1
            out_name = args[i]
        elif a == '--arcname':
            i += 1
            arcname = args[i]
        else:
            folders.append(a.rstrip('\\/'))
        i += 1
    if not folders:
        print('usage: pack_release_zip.py [--arcname TOPDIR] [--without DIR] [--out NAME.zip] FOLDER ...')
        return 2
    rc = 0
    for folder in folders:
        out = (os.path.join(os.path.dirname(folder), out_name) if out_name else folder + '.zip')
        rc |= build(folder, out, skip, arcname)
    return rc


if __name__ == '__main__':
    sys.exit(main(sys.argv))
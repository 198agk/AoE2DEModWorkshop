import json, os

G = r'D:\Games\Steam\steamapps\common\AoE2DE'
MODS = r'C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed'
TARGET = None
for _d in os.listdir(MODS):
    if _d.startswith('550412_'):
        TARGET = _d
        break
assert TARGET, 'mod not found'

mat = json.load(open(os.path.join(G, 'widgetui', 'materials.json'), encoding='utf-8-sig'))
filemap = {}
for a in mat['AtlasTextures']:
    ad = a['AtlasDef']
    for t in ad['Textures']:
        filemap.setdefault(t['FileName'].replace('\\', '/').lower(), []).append((ad['Name'], t['RefName']))
globals_ = {t['TextureDef']['FileName'].replace('\\', '/').lower() for t in mat['GlobalTextures']}

full = os.path.join(MODS, TARGET)
unmatched = []
for root, dirs, fs in os.walk(full):
    for f in fs:
        p = os.path.relpath(os.path.join(root, f), full).replace('\\', '/')
        if not p.lower().startswith('widgetui/textures/'):
            continue
        rel = p[len('widgetui/'):]
        k = rel.lower()
        if k in filemap or k in globals_:
            continue
        unmatched.append(rel)

print('UNMATCHED in %s : %d' % (TARGET, len(unmatched)))
print()
print('%-72s %-10s %s' % ('mod file', 'game has?', 'size'))
print('-' * 100)
for rel in sorted(unmatched):
    gp = os.path.join(G, 'widgetui', rel.replace('/', os.sep))
    exists = os.path.exists(gp)
    gs = os.path.getsize(gp) if exists else 0
    ms = os.path.getsize(os.path.join(full, 'widgetui', rel.replace('/', os.sep)))
    print('%-72s %-10s mod=%-9d game=%d' % (rel[:72], 'YES' if exists else 'no', ms, gs))

# Also: are there textures in the mod whose path exists in the game tree but with different names?
print()
print('=== how many game-side widgetui/textures files are referenced by materials.json? ===')
gtex = os.path.join(G, 'widgetui', 'textures')
allfiles = []
for root, dirs, fs in os.walk(gtex):
    for f in fs:
        if f.lower().endswith(('.png', '.jpg', '.dds')):
            allfiles.append(os.path.relpath(os.path.join(root, f), os.path.join(G, 'widgetui')).replace('\\', '/').lower())
refd = set(filemap) | globals_
print('game texture files on disk :', len(allfiles))
print('referenced by materials.json:', len(refd))
print('on disk but unreferenced    :', len([f for f in allfiles if f not in refd]))
print('referenced but missing      :', len([f for f in refd if f not in set(allfiles)]))

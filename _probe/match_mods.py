import json, os

G = r'D:\Games\Steam\steamapps\common\AoE2DE'
MODS = r'C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed'

mat = json.load(open(os.path.join(G, 'widgetui', 'materials.json'), encoding='utf-8-sig'))

filemap = {}
for a in mat['AtlasTextures']:
    ad = a['AtlasDef']
    for t in ad['Textures']:
        fn = t['FileName'].replace('\\', '/').lower()
        filemap.setdefault(fn, []).append((ad['Name'], t['RefName']))

globals_ = set()
for t in mat['GlobalTextures']:
    globals_.add(t['TextureDef']['FileName'].replace('\\', '/').lower())

print('atlas unique files:', len(filemap), '| global textures:', len(globals_))
print()

for d in sorted(os.listdir(MODS)):
    full = os.path.join(MODS, d)
    if not os.path.isdir(full):
        continue
    files = []
    for root, dirs, fs in os.walk(full):
        for f in fs:
            p = os.path.relpath(os.path.join(root, f), full).replace('\\', '/')
            if p.lower().startswith('widgetui/textures/'):
                # materials.json FileName is relative to widgetui/, not to the game root
                files.append(p[len('widgetui/'):])
    if not files:
        continue
    hit = miss = g_hit = 0
    ex = []
    for p in files:
        key = p.lower()
        if key in filemap:
            hit += 1
            if len(ex) < 3:
                ex.append((p, filemap[key][0]))
        elif key in globals_:
            g_hit += 1
        else:
            miss += 1
            if len(ex) < 6:
                ex.append((p, 'UNMATCHED'))
    print(d[:60])
    print('   widgetui/textures/ files: %d | atlas match: %d | global match: %d | unmatched: %d'
          % (len(files), hit, g_hit, miss))
    for p, v in ex:
        print('     ', p[:95], '->', v)
    print()

import json, os

G = r'D:\Games\Steam\steamapps\common\AoE2DE'
mat = json.load(open(os.path.join(G, 'widgetui', 'materials.json'), encoding='utf-8-sig'))

print('%-26s %6s %6s %6s %6s  %s' % ('atlas', 'MaxW', 'MaxH', 'files', 'uniq', 'sources'))
print('-' * 110)
tot_files = 0
rows = []
for a in mat['AtlasTextures']:
    ad = a['AtlasDef']
    fns = [t['FileName'] for t in ad['Textures']]
    uniq = len(set(fns))
    src = []
    if 'UHDSource' in ad: src.append('UHD')
    if 'HDSource' in ad: src.append('HD')
    if 'DefaultSource' in ad: src.append('SD')
    rows.append((ad['Name'], ad['MaxWidth'], ad['MaxHeight'], len(fns), uniq, '+'.join(src), ad.get('Cached')))
    tot_files += len(fns)
for r in sorted(rows, key=lambda x: -x[2]):
    print('%-26s %6d %6d %6d %6d  %-12s %s' % (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
print()
print('total texture entries across atlases:', tot_files)
print('atlas count:', len(mat['AtlasTextures']))
print('material count:', len(mat['Materials']))
print('global textures:', len(mat['GlobalTextures']))

print()
print('=== Material Type x Blend distribution ===')
from collections import Counter
c = Counter((m['MaterialDef']['Type'], m['MaterialDef']['Blend']) for m in mat['Materials'])
for k, v in c.most_common():
    print('  %-10s %-14s %d' % (k[0], k[1], v))

print()
print('=== GlobalTextures by extension ===')
ext = Counter(os.path.splitext(t['TextureDef']['FileName'])[1].lower() for t in mat['GlobalTextures'])
for k, v in ext.most_common():
    print('  %-8s %d' % (k, v))

print()
print('=== how many atlas entries are per-civ emblems, and their native sizes ===')
from PIL import Image
emb = [t for a in mat['AtlasTextures'] if a['AtlasDef']['Name'] == 'ingamepanels'
       for t in a['AtlasDef']['Textures'] if t['RefName'].startswith('CivEmblem')]
print('  CivEmblem entries in ingamepanels:', len(emb))
sizes = Counter()
for t in emb[:80]:
    p = os.path.join(G, 'widgetui', t['FileName'].replace('/', os.sep))
    if os.path.exists(p):
        try:
            with Image.open(p) as im:
                sizes[im.size] += 1
        except Exception as e:
            sizes[('ERR', str(e)[:30])] += 1
for k, v in sizes.most_common(10):
    print('   ', k, v)

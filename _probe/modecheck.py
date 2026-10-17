import json, os

G = r'D:\Games\Steam\steamapps\common\AoE2DE'
MODS = r'C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed'

print('=== mod-status.json ===')
st = json.load(open(os.path.join(os.path.dirname(MODS), 'mod-status.json'), encoding='utf-8-sig'))
for m in st['Mods']:
    print('  Priority %-2s Enabled %-5s  %s' % (m['Priority'], m['Enabled'], m['Title'][:60]))

mat = json.load(open(os.path.join(G, 'widgetui', 'materials.json'), encoding='utf-8-sig'))
filemap = {}
for a in mat['AtlasTextures']:
    ad = a['AtlasDef']
    for t in ad['Textures']:
        filemap.setdefault(t['FileName'].replace('\\', '/').lower(), []).append((ad['Name'], t['RefName']))
globals_ = {t['TextureDef']['FileName'].replace('\\', '/').lower() for t in mat['GlobalTextures']}

print()
print('=== Pompeii morematerials.json: does it reference the 3106 "unreferenced" files? ===')
mm = json.load(open(os.path.join(G, 'modes', 'Pompeii', 'widgetui', 'morematerials.json'), encoding='utf-8-sig'))
mm_files = {}
for a in mm['AtlasTextures']:
    ad = a['AtlasDef']
    for t in ad['Textures']:
        mm_files.setdefault(t['FileName'].replace('\\', '/').lower(), []).append((ad['Name'], t['RefName']))
mm_glob = {t['TextureDef']['FileName'].replace('\\', '/').lower() for t in mm['GlobalTextures']}
print('  morematerials atlases: %d  unique files: %d  global: %d'
      % (len(mm['AtlasTextures']), len(mm_files), len(mm_glob)))
print('  cached values:', sorted({a['AtlasDef'].get('Cached') for a in mm['AtlasTextures']}))
print('  base cached values:', sorted({a['AtlasDef'].get('Cached') for a in mat['AtlasTextures']}))
print('  overlap of morematerials files with base materials.json:',
      len(set(mm_files) & set(filemap)))

gtex = os.path.join(G, 'widgetui', 'textures')
allfiles = set()
for root, dirs, fs in os.walk(gtex):
    for f in fs:
        if f.lower().endswith(('.png', '.jpg', '.dds')):
            allfiles.add(os.path.relpath(os.path.join(root, f), os.path.join(G, 'widgetui')).replace('\\', '/').lower())

unref = allfiles - set(filemap) - globals_
print()
print('  unreferenced by BOTH base and mode: ', len(unref - set(mm_files) - mm_glob))
print('  unreferenced by base but in mode   :', len(unref & (set(mm_files) | mm_glob)))
print()
print('  sample of still-unreferenced:')
for f in sorted(unref - set(mm_files) - mm_glob)[:25]:
    print('    ', f)

print()
print('=== 8 files referenced by materials.json but missing on disk ===')
for f in sorted(set(filemap) | globals_):
    if f not in allfiles:
        print('    ', f, '->', filemap.get(f))

import sys
sys.path.insert(0, r'D:\Software\AI\帝国项目')
from aoe2mod.dat import parser as P
MOD = r'_probe\out_dshtest_v17\resources\_common\dat\empires2_x2_p1.dat'
raw, how = P.load_dat(MOD)
st = P.Parser(raw).parse()
techs, effs = st['techs'], st['effects']
for tid in (495, 508, 1350):
    t = techs[tid]
    eid = t['effect_id']
    print('tech %-5d %-32s eff=%-5d' % (tid, t['name'][:32], eid))
    for c in effs[eid]['commands'][-3:]:
        print('        cmd type=%d a=%d b=%d c=%d d=%s' % c)
print()
print('--- do the two new effects exist and end with the disable? ---')
for eid in (1500, 1501):
    if eid < len(effs):
        cmds = effs[eid]['commands']
        print('effect %d  name=%r  %d commands  last=%s' % (eid, effs[eid]['name'], len(cmds), cmds[-1]))
    else:
        print('effect %d MISSING' % eid)

import io, os, shutil, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))

# key page text -> raw_ai_* name
MAP = [
    ('txt_commands-index.txt',            'raw_ai_commands-index.txt'),
    ('txt_parameters-index.txt',          'raw_ai_parameters-index.txt'),
    ('txt_sn-index.txt',                  'raw_ai_sn-index.txt'),
    ('txt_sn-index-by-id.txt',            'raw_ai_sn-index-by-id.txt'),
    ('txt_objects.txt',                   'raw_ai_objects.txt'),
    ('txt_techs.txt',                     'raw_ai_techs.txt'),
    ('txt_res-index.txt',                 'raw_ai_res-index.txt'),
    ('txt_events-index.txt',              'raw_ai_events-index.txt'),
    ('txt_tables-index.txt',              'raw_ai_tables-index.txt'),
    ('txt_load-if.txt',                   'raw_ai_load-if.txt'),
    ('txt_bugs_LanguageSyntax.txt',       'raw_ai_bugs_LanguageSyntax.txt'),
    ('txt_guide_intro-to-commands.txt',   'raw_ai_guide_intro-to-commands.txt'),
    ('txt_guide_logical-operators.txt',   'raw_ai_guide_logical-operators.txt'),
    ('txt_guide_defconsts-goals-sns-1.txt','raw_ai_guide_defconsts-goals-sns-1.txt'),
    ('txt_guide_data-limits.txt',         'raw_ai_guide_data-limits.txt'),
    ('txt_guide_helpful-info.txt',        'raw_ai_guide_helpful-info.txt'),
    ('txt_guide_command-performance.txt', 'raw_ai_guide_command-performance.txt'),
    ('txt_guide_sn-defaults-to-change.txt','raw_ai_guide_sn-defaults-to-change.txt'),
    ('txt_guide_enmipho-intro-to-duc.txt','raw_ai_guide_enmipho-intro-to-duc.txt'),
    ('txt_guide_leif-duc-tutorial-intro.txt','raw_ai_guide_leif-duc-tutorial-intro.txt'),
    ('txt_guide_xs-for-tournaments.txt',  'raw_ai_guide_xs-for-tournaments.txt'),
    ('txt_guide_swgb-scripting.txt',      'raw_ai_guide_swgb-scripting.txt'),
    ('raw_ai_commands_full.txt',          None),   # already named
    ('raw_ai_parameters_full.txt',        None),
    ('raw_ai_sns_full.txt',               None),
    ('raw_ai_loadif_symbols.md',          None),
]

made, skipped, missing = 0, 0, 0
for src, dst in MAP:
    if dst is None:
        print(f"  [have] {src}")
        continue
    sp, dp = os.path.join(D, src), os.path.join(D, dst)
    if not os.path.exists(sp):
        print(f"  [MISS] {src}")
        missing += 1
        continue
    if os.path.exists(dp):
        skipped += 1
        continue
    shutil.copyfile(sp, dp)
    made += 1
    print(f"  [made] {dst}  <- {src}")

print(f"\nmade={made} already_present={skipped} missing_source={missing}")

print("\n=== raw_ai_*.txt inventory ===")
tot = 0
for f in sorted(os.listdir(D)):
    if f.startswith('raw_ai_') and f.endswith('.txt'):
        s = os.path.getsize(os.path.join(D, f))
        tot += s
        print(f"  {f:46} {s:>9,} bytes")
print(f"  {'TOTAL':46} {tot:>9,} bytes")
print(f"\n  (plus raw_ai_loadif_symbols.md "
      f"{os.path.getsize(os.path.join(D,'raw_ai_loadif_symbols.md')):,} bytes)")

import json, os
d = r"D:\Software\DeepSeek Harness\工作区2\aoe2docs"

def load(f):
    return json.load(open(os.path.join(d, f), encoding="utf-8-sig"))

def dump(f, wanted=None, key="raw"):
    j = load(f)
    ps = j.get("posts") or (j.get("post_stream") or {}).get("posts") or []
    tps = j.get("topics") or ((j.get("post_stream") or {}).get("topics")) or []
    print("#" * 95)
    print("FILE", f, " posts", len(ps))
    if tps:
        for t in tps:
            print(f"   TOPIC {t.get('id')} :: {t.get('title')} :: {t.get('posts_count')} posts")
    for p in ps:
        pn = p.get("post_number")
        if wanted and pn not in wanted:
            continue
        t = p.get("raw") or p.get("cooked") or p.get("blurb") or ""
        t = t.replace("\n", "\n      ")
        print(f"  --- p{pn} @{p.get('username')} ({p.get('created_at','')[:10]}) ---")
        print("      " + t[:4000])
    print()

dump("q_dds_mipmap_mod.json")
dump("forums_search_widgetui.json", wanted={1})
dump("topic_288998.json")
dump("topic_61109.json")

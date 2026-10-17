import json, os
d = r"D:\Software\DeepSeek Harness\工作区2\aoe2docs"

def load(f):
    return json.load(open(os.path.join(d, f), encoding="utf-8-sig"))

def dump(f, wanted=None):
    j = load(f)
    ps = j.get("posts") or (j.get("post_stream") or {}).get("posts") or []
    print("#" * 95)
    print("FILE", f, " posts", len(ps))
    for p in ps:
        pn = p.get("post_number")
        if wanted and pn not in wanted:
            continue
        t = p.get("raw") or p.get("cooked") or p.get("blurb") or ""
        print(f"  --- p{pn} @{p.get('username')} ({p.get('created_at','')[:10]}) ---")
        print("      " + t.replace("\n", "\n      ")[:3500])
    print()

dump("topic_91310.json")       # Modding the Icon atlas files
dump("topic_128141.json")      # Files not registered for Mod Support
dump("topic_114096.json")      # Some UI and TechTree modding queries
dump("topic_82973.json")       # UI Modding Widgetui
dump("topic_231422.json")      # Icons.json and materials json in new patch
dump("topic_212760.json")
dump("topic_72516.json", wanted={1})
dump("topic_117361.json")

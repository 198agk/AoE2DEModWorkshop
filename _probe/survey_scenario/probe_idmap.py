"""Round 5: reconcile ASP trigger type ids vs the game's key-value string ids,
and settle the message-slot question."""
import json
import os
import re
import warnings
warnings.filterwarnings("ignore")

SITE = r"C:\Users\26913\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\Lib\site-packages\AoE2ScenarioParser"
HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(HERE, "kv_all.json"), encoding="utf-8") as f:
    KV = {int(k): v for k, v in json.load(f).items()}

print("=== ASP effects.py enum name -> id (first 40) ===")
eff_src = open(os.path.join(SITE, "datasets", "effects.py"), encoding="utf-8").read()
pairs = re.findall(r"^\s{4}([A-Z][A-Z0-9_]*)\s*=\s*(\d+)\s*$", eff_src, re.M)
print("  count:", len(pairs))
for name, num in pairs[:40]:
    n = int(num)
    print(f"   {num:>4}  {name:<38} kv[11555+{num}]={KV.get(11555+n, '?')!r}")

print()
print("=== ASP conditions.py enum name -> id ===")
cond_src = open(os.path.join(SITE, "datasets", "conditions.py"), encoding="utf-8").read()
cpairs = re.findall(r"^\s{4}([A-Z][A-Z0-9_]*)\s*=\s*(\d+)\s*$", cond_src, re.M)
print("  count:", len(cpairs))
for name, num in cpairs[:45]:
    n = int(num)
    print(f"   {num:>4}  {name:<38} kv[10500+{n}]={KV.get(10500+n, '?')!r}")

print()
print("=== where does 11555+id stop matching? ===")
bad = [(int(n), name, KV.get(11555+int(n))) for name, n in pairs if KV.get(11555+int(n)) is None]
print("  effects with no kv match:", len(bad))
print("  ", [(n, nm) for n, nm, _ in bad][:20])

print()
print("=== reverse: kv 11555..11660 vs ASP effect names ===")
by_id = {int(n): nm for nm, n in pairs}
for k in range(11555, 11665):
    if k in KV:
        asp = by_id.get(k - 11555, "-")
        print(f"  {k}: {KV[k][:44]:<46} <- ASP {asp}")

print()
print("=== MESSAGE MODEL: search ASP for a message array ===")
msg_py = open(os.path.join(SITE, "managers", "message_manager.py"), encoding="utf-8").read()
print("  message_manager.py bytes:", len(msg_py))
for pat in ("def ", "self.messages", "_messages", "class ", "MAX", "512", "array"):
    print(f"   {pat!r}: {msg_py.count(pat)}")
print("  --- def lines ---")
for line in msg_py.splitlines():
    s = line.strip()
    if s.startswith("def ") or s.startswith("class ") or s.startswith("self.") and "=" in s:
        print("   ", s[:110])

print()
print("=== structure.json Messages section (v1.54) ===")
st = json.load(open(os.path.join(SITE, "versions", "DE", "v1.54", "structure.json"), encoding="utf-8"))
print(json.dumps(st["Messages"], indent=1)[:2600])

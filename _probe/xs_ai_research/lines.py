import io, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = os.path.dirname(os.path.abspath(__file__))

cur = io.open(os.path.join(D, 'AI_SCRIPTING_AIREF.md'), encoding='utf-8', newline='').read().split('\n')
old = io.open(os.path.join(D, 'AI_SCRIPTING_AIREF.corrupt.bak.md'), encoding='utf-8', newline='').read().split('\n')

def show(n):
    print(f"\n===== L{n} =====")
    print("  OLD:", repr(old[n-1]))
    print("  NEW:", repr(cur[n-1]))

for n in [1, 72, 85, 100, 114, 116, 118, 133, 137, 138, 154, 162, 164, 166,
          183, 194, 195, 199, 203, 215, 225, 227, 231, 235, 240, 250, 251,
          252, 253, 254, 256, 257, 258, 259, 260, 270]:
    show(n)

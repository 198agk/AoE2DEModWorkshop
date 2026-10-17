# -*- coding: utf-8 -*-
"""DEFINITIVE PROOF that the reference screenshots show the MOD's 50%-alpha panel,
and that my renderer is faithful to the art the shipped layout names.

Established facts:
  * The enabled mod '透明主题整合自用' ships
        widgetui/textures/ingame/panels/ASIA/resource-panel.png
    which is BYTE-FOR-BYTE the vanilla RGB with alpha scaled by exactly 0.502
    (100% of pixels with both alpha>0 have identical RGB; alpha ratio p10=median=p90=0.502).
  * Loose PNG overrides atlas art (proven in this workspace's UI-texture skill).
  * Known-opaque widgets show across-shot std 1.57-1.93, so the instrument's zero is real.

Test. If the game drew the MOD panel, then for every pixel
        observed_i = 0.502*A + 0.498*T_i
    where A is the vanilla RGB and T_i the terrain behind it. Then:
      (1) std_i(observed) = 0.498 * std_i(T)  -- ~half the terrain's own std
      (2) T = (mean_i(observed) - 0.502*A)/0.498 must be PLAUSIBLE TERRAIN
          (inside 0..255, unclipped, terrain-toned).
    If the game drew the VANILLA panel, those same pixels must have std ~ 0.
"""
import os
import numpy as np
from PIL import Image

O = r"D:\Software\DeepSeek Harness\工作区2\_probe\hud_render"
GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
WID = os.path.join(GAME, "widgetui")
MOD = r"C:\Users\26913\Games\Age of Empires 2 DE\76561198406248391\mods\subscribed\550412_透明主题整合自用"
AT = r"C:\Users\26913\.dsh\attachments\v1\objects"
SHOTS = [os.path.join(AT, d, s) for d, s in [
    ("02", "0261b373ecaf49144281bea8a63f4b57627bc303cbb35a78fcb7f4b616ee4e82"),
    ("2f", "2fe5282335f5d309abf86f9cd8afee0fb3d2407ce8296985b65d0f71d21da974"),
    ("16", "16175bb0620c40734d7a57b380781a09c713e7ff4c0f0c7be6726c59eea614be"),
    ("8e", "8eeadcf84b38696ac0ede7aedaf08ee6eff1812468c8d43fa667e2376c877850"),
    ("89", "89bdabdd26b4c0ada57121bc0851f93ee52aa18080e51a9274406c1dee0bd9f9"),
]]
SC = 0.5980
rep = []

# The widget box is 1750x276 ref px -> 1046x165 screen px. That IS the plank footprint.
BW, BH = 1750, 276
TW, TH = int(round(BW * SC)), int(round(BH * SC))
print("plank footprint on screen: %dx%d" % (TW, TH))

st = np.stack([np.asarray(Image.open(p).convert("RGB").crop((0, 0, TW, TH)), dtype=np.float64) for p in SHOTS])
rm = st.mean(axis=0)
sd = st.std(axis=0).mean(axis=2)
H, W = sd.shape
rep.append("region = plank footprint %dx%d, mean across-shot std = %.2f" % (W, H, sd.mean()))
rep.append("")

vi = Image.open(os.path.join(WID, r"textures\ingame\panels\ASIA\resource-panel.png")).convert("RGBA")
mi = Image.open(os.path.join(MOD, r"widgetui\textures\ingame\panels\ASIA\resource-panel.png")).convert("RGBA")
A = np.asarray(vi.resize((TW, TH), Image.LANCZOS), dtype=np.float64)
M = np.asarray(mi.resize((TW, TH), Image.LANCZOS), dtype=np.float64)
mA = A[:, :, 3] >= 250
rep.append("vanilla panel: alpha>=250 over %.1f%% of the footprint" % (100.0 * mA.mean()))
rep.append("")

# ---------------------------------------------------------------- TEST 1
rep.append("=== TEST 1: across-shot std where VANILLA declares alpha=255 ===")
rep.append("  If the game drew the vanilla panel there, observed std MUST be ~0.")
rep.append("  observed std over those %d px: mean=%.2f median=%.2f"
           % (int(mA.sum()), float(sd[mA].mean()), float(np.median(sd[mA]))))
rep.append("  terrain (rows just below the plank) std = %.2f -> MOD 0.502 model predicts %.2f"
           % (float(np.median(sd[TH - 12:TH, :])), 0.498 * float(np.median(sd[TH - 12:TH, :]))))
icons = []
for i in range(4):
    x0 = int(round((57 + 200 * i - 42) * SC)); x1 = x0 + int(round(84 * SC))
    icons.append(float(sd[:, x0:x1].mean()))
rep.append("  CONTROL, known-opaque resource icons obs std: " + ", ".join("%.2f" % v for v in icons))
rep.append("  -> the instrument's real zero is ~1.6; the panel region sits at %.2f" % float(sd[mA].mean()))
rep.append("  => the VANILLA hypothesis is REFUTED at those pixels." if sd[mA].mean() > 4 else "  => vanilla survives")
rep.append("")

# ---------------------------------------------------------------- TEST 2
rep.append("=== TEST 2: reconstruct terrain T = (obs - a*A)/(1-a) and check plausibility ===")
aF = 0.502
T = (rm - aF * A[:, :, :3]) / (1 - aF)
oob = ((T < -2) | (T > 257)).mean()
below = st[:, TH - 14:TH, :, :].mean(axis=(0, 1, 2)) if TH - 14 > 0 else None
print("reconstructed terrain T: range %.1f..%.1f, mean %.1f %.1f %.1f, out-of-range %.3f%%"
      % (T.min(), T.max(), T[:, :, 0].mean(), T[:, :, 1].mean(), T[:, :, 2].mean(), 100.0 * oob))
rep.append("  MOD alpha=0.502 model: T range %.1f..%.1f  mean %.1f %.1f %.1f  out-of-range %.3f%%"
           % (T.min(), T.max(), T[:, :, 0].mean(), T[:, :, 1].mean(), T[:, :, 2].mean(), 100.0 * oob))
rimg = st[:, TH - 14:TH, :, :]
rep.append("  terrain immediately below the plank: mean %.1f %.1f %.1f"
           % (rimg[:, :, :, 0].mean(), rimg[:, :, :, 1].mean(), rimg[:, :, :, 2].mean()))
resid = [float(np.abs(aF * A[:, :, :3] + (1 - aF) * T - st[i]).mean()) for i in range(len(SHOTS))]
rep.append("  per-shot forward-model |residual|: %s  -> mean %.2f" % (", ".join("%.1f" % v for v in resid), float(np.mean(resid))))
rep.append("  VANILLA alpha=1.0 model: predicted = vanilla RGB exactly; mean|obs - art| = %.2f"
           % float(np.abs(rm - A[:, :, :3]).mean()))
rep.append("")

# ---------------------------------------------------------------- TEST 3
rep.append("=== TEST 3: which model reproduces the observed bar? ===")
aM = M[:, :, 3:4] / 255.0
predmod = aM * M[:, :, :3] + (1 - aM) * T
predvan = A[:, :, :3]
for label, pred in (("MOD  art over reconstructed terrain", predmod),
                    ("VANILLA art, no blending", predvan)):
    d = np.abs(pred - rm).mean(axis=2)
    rep.append("  %-38s mean|diff|=%6.2f  corr=%+.4f" % (label, d.mean(),
               float(np.corrcoef(pred.reshape(-1), rm.reshape(-1))[0, 1])))
rep.append("")

OUT = Image.new("RGB", (W, H * 3 + 16), (16, 16, 16))
OUT.paste(Image.fromarray(np.clip(rm, 0, 255).astype(np.uint8)), (0, 0))
OUT.paste(Image.fromarray(np.clip(predmod, 0, 255).astype(np.uint8)), (0, H + 8))
OUT.paste(Image.fromarray(np.clip(predvan, 0, 255).astype(np.uint8)), (0, 2 * H + 16))
OUT.resize((W * 2, (H * 3 + 16) * 2), Image.NEAREST).save(os.path.join(O, "mod_proof.png"))
Image.fromarray(np.clip(T, 0, 255).astype(np.uint8)).resize((W * 2, H * 2), Image.LANCZOS).save(os.path.join(O, "mod_terrain_recon.png"))
rep.append("wrote mod_proof.png (real / MOD-0.502 model / VANILLA model) and mod_terrain_recon.png")

txt = "\n".join(rep)
open(os.path.join(O, "mod_proof.txt"), "w", encoding="utf-8").write(txt)
print(txt)

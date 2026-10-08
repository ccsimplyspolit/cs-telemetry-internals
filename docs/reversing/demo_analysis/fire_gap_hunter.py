"""Focused hunt for view-angle gaps / missing data at fire moments.

Target: pользователь наблюдал что trueview данные пропадают в момент выстрела.
Задача: verify — какие поля/тики имеют NaN/None/missing на fire moments.
"""
from demoparser2 import DemoParser
import json
import math
from pathlib import Path
from collections import defaultdict

DEMO = r"C:\Users\sshunko\AppData\Local\Temp\claude\C--vmp\027d448b-b19c-4803-9bd6-5149a97f488f\scratchpad\demo.dem"
OUT  = Path(r"C:\Users\sshunko\AppData\Local\Temp\claude\C--vmp\027d448b-b19c-4803-9bd6-5149a97f488f\scratchpad")

p = DemoParser(DEMO)

# 1. All fires
wf = p.parse_event("weapon_fire")
itz_fires = sorted(wf[wf['user_name']=='ItzJuego']['tick'].tolist())
print(f"[+] {len(itz_fires)} fires")

# 2. Props — everything that could be view-related
PROPS = [
    'CCSPlayerPawn.m_angEyeAngles',           # server post-apply eye
    'CCSPlayerPawn.m_iShotsFired',
    'CCSPlayerPawn.m_flTimeOfLastInjury',
    'CCSPlayerPawn.m_bIsScoped',
    'CCSPlayerPawn.CCSPlayer_WeaponServices.m_bIsLookingAtWeapon',
    'CCSPlayerPawn.CCSPlayer_WeaponServices.m_flNextAttack',
    'CCSPlayerPawn.CCSPlayer_MovementServices.m_arrForceSubtickMoveWhen',
    'CCSPlayerPawn.CCSPlayer_MovementServices.m_nButtonDownMaskPrev',
    'CCSPlayerPawn.CCSPlayer_MovementServices.m_nButtons',
    'CCSPlayerPawn.CCSPlayer_MovementServices.m_nQueuedButtonDownMask',
    'CCSPlayerPawn.m_flVelocityModifier',
    'CCSPlayerPawn.m_flHitHeading',
    'CCSPlayerPawn.m_flHitOffset',
    'CCSPlayerController.m_nTickBase',
    'CCSPlayerPawn.m_flSimulationTime',       # tick-based simulation
    'CCSPlayerPawn.m_flCreateTime',
    'CCSPlayerPawn.CCSPlayer_ItemServices.m_bHasHelmet',
    'CCSPlayerPawn.m_iShotsFired',
    'CCSPlayerPawn.m_vecPredictedBaseAngleVelSpring',   # aim punch from recoil
    'CCSPlayerPawn.m_bIsWalking',
]

# 3. Gather -5..+5 around each fire
windows = defaultdict(dict)  # {fire_tick: {tick: {prop: value}}}
for ft in itz_fires:
    ticks = list(range(ft-5, ft+6))
    df = p.parse_ticks(PROPS, ticks=ticks)
    itz = df[df['name']=='ItzJuego']
    for _, row in itz.iterrows():
        t = int(row['tick'])
        windows[ft][t] = {p: row[p] for p in PROPS if p in row.index}

# 4. Detect gaps: тики где ItzJuego НЕТ в replicated set во время fire window
gap_report = []
missing_replication = []
nan_report = []

for ft in itz_fires:
    for t in range(ft-5, ft+6):
        if t not in windows[ft]:
            missing_replication.append({'fire_tick': ft, 'missing_tick': t, 'offset': t - ft})
            continue
        row = windows[ft][t]
        for prop, val in row.items():
            # detect NaN
            try:
                if val is None:
                    nan_report.append({'fire_tick': ft, 'tick': t, 'prop': prop, 'val': None, 'reason': 'None'})
                elif isinstance(val, float) and math.isnan(val):
                    nan_report.append({'fire_tick': ft, 'tick': t, 'prop': prop, 'val': 'NaN', 'reason': 'NaN'})
                elif isinstance(val, (list, tuple)) and val:
                    for i, v in enumerate(val):
                        if v is None or (isinstance(v, float) and math.isnan(v)):
                            nan_report.append({'fire_tick': ft, 'tick': t, 'prop': prop,
                                               'val': f'[{i}]=NaN', 'reason': 'array-NaN'})
            except (TypeError, ValueError):
                pass

# 5. Eye angle time-series continuity check
print("\n[+] View angle continuity per fire:")
va_series = {}
for ft in itz_fires:
    ang = []
    for t in sorted(windows[ft].keys()):
        row = windows[ft][t]
        eye = row.get('CCSPlayerPawn.m_angEyeAngles')
        # eye may be [pitch, yaw, roll] list или dict
        if eye is not None:
            if hasattr(eye, '__len__') and len(eye) >= 3:
                p_, y_, r_ = float(eye[0]), float(eye[1]), float(eye[2])
                ang.append((t, p_, y_, r_))
            else:
                ang.append((t, None, None, None))
    va_series[ft] = ang

# Look for DISCONTINUOUS pitch jumps в -1..+1 tick
jumps = []
for ft, ang in va_series.items():
    ang_sorted = sorted(ang)
    for i in range(1, len(ang_sorted)):
        prev_t, prev_p, prev_y, prev_r = ang_sorted[i-1]
        cur_t, cur_p, cur_y, cur_r = ang_sorted[i]
        if prev_p is None or cur_p is None:
            continue
        d_pitch = abs(cur_p - prev_p)
        if d_pitch > 30.0:  # abnormal jump
            jumps.append({
                'fire': ft, 'prev_tick': prev_t, 'cur_tick': cur_t,
                'd_ticks': cur_t - prev_t,
                'prev_pitch': prev_p, 'cur_pitch': cur_p,
                'd_pitch': cur_p - prev_p,
                'is_fire_tick': cur_t == ft or prev_t == ft,
            })

# 6. Field of view / trueview:
#    trueview obscures view? Check m_bIsScoped, m_flNextAttack, etc.

# 7. Write summary
print(f"[+] Missing replication ticks: {len(missing_replication)}")
print(f"[+] NaN/None values total: {len(nan_report)}")
print(f"[+] Pitch jumps >30° in fire windows: {len(jumps)}")
print(f"    Of those on fire tick: {sum(1 for j in jumps if j['is_fire_tick'])}")

lines = [
    "# Fire-Gap Hunter Report\n\n",
    f"**Fires:** {len(itz_fires)}\n",
    f"**Missing replication ticks in windows:** {len(missing_replication)}\n",
    f"**NaN/None values:** {len(nan_report)}\n",
    f"**Abnormal pitch jumps (Δ>30° per tick):** {len(jumps)}\n\n",
]

lines.append("## 1. Per-fire view_angle series\n\n")
for ft in itz_fires:
    lines.append(f"### Fire tick {ft}\n\n")
    lines.append("| Δtick | tick | pitch | yaw | roll | shots_fired | m_flNextAttack | replicated? |\n")
    lines.append("|------:|-----:|------:|----:|-----:|------------:|---------------:|:-----------:|\n")
    for t in range(ft-5, ft+6):
        d = t - ft
        if t not in windows[ft]:
            lines.append(f"| {d:+d} | {t} | — | — | — | — | — | ❌ MISSING |\n")
            continue
        row = windows[ft][t]
        eye = row.get('CCSPlayerPawn.m_angEyeAngles')
        try:
            if eye is None:
                pitch_s, yaw_s, roll_s = 'None', 'None', 'None'
            elif hasattr(eye, '__len__') and len(eye) >= 3:
                pitch_s = f"{float(eye[0]):.2f}"
                yaw_s   = f"{float(eye[1]):.2f}"
                roll_s  = f"{float(eye[2]):.2f}"
            else:
                pitch_s, yaw_s, roll_s = str(eye), '-', '-'
        except Exception:
            pitch_s, yaw_s, roll_s = str(eye), '?', '?'
        sf = row.get('CCSPlayerPawn.m_iShotsFired')
        na = row.get('CCSPlayerPawn.CCSPlayer_WeaponServices.m_flNextAttack')
        lines.append(f"| {d:+d} | {t} | {pitch_s} | {yaw_s} | {roll_s} | {sf} | {na} | ✅ |\n")
    lines.append("\n")

lines.append("## 2. Missing replication ticks (server didn't have data)\n\n")
if missing_replication:
    lines.append("| Fire tick | Missing tick | Offset |\n|---:|---:|---:|\n")
    for m in missing_replication[:100]:
        lines.append(f"| {m['fire_tick']} | {m['missing_tick']} | {m['offset']:+d} |\n")
else:
    lines.append("_Нет missing ticks в 11-tick окнах вокруг fires._\n")

lines.append("\n## 3. Pitch jumps (server-observed 89°→179° pattern)\n\n")
if jumps:
    lines.append("| Fire | Prev tick | Cur tick | Δticks | Prev pitch | Cur pitch | Δpitch | Is fire-tick? |\n")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|:---:|\n")
    for j in jumps:
        marker = "🔥 FIRE" if j['is_fire_tick'] else ""
        lines.append(f"| {j['fire']} | {j['prev_tick']} | {j['cur_tick']} | "
                     f"{j['d_ticks']} | {j['prev_pitch']:.2f} | {j['cur_pitch']:.2f} | "
                     f"{j['d_pitch']:+.2f} | {marker} |\n")

lines.append("\n## 4. NaN/None findings\n\n")
if nan_report:
    lines.append("| Fire | Tick | Prop | Val | Reason |\n|---:|---:|-----|----|--------|\n")
    for n in nan_report[:200]:
        prop_short = n['prop'].split('.')[-1]
        lines.append(f"| {n['fire']} | {n['tick']} | {prop_short} | {n['val']} | {n['reason']} |\n")
else:
    lines.append("_Нет NaN/None._\n")

(OUT / 'fire_gap_hunter.md').write_text(''.join(lines), encoding='utf-8')
(OUT / 'fire_gap_hunter.json').write_text(json.dumps({
    'fires': [int(f) for f in itz_fires],
    'missing_replication': missing_replication,
    'nan_report': nan_report[:500],
    'pitch_jumps': jumps,
    'view_angle_series': {int(ft): [(int(t), p_, y_, r_) for t, p_, y_, r_ in ang]
                          for ft, ang in va_series.items()},
}, indent=2, default=str))

print(f"\n[+] Wrote {OUT / 'fire_gap_hunter.md'}")
print(f"[+] Wrote {OUT / 'fire_gap_hunter.json'}")

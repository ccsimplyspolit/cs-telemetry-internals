"""Comprehensive fire-pattern analysis for player 'ItzJuego'.
Extracts 30 ticks before + 30 after each weapon_fire event, computes:
  - view-angle deltas (pitch/yaw) frame-to-frame
  - jitter score (norm of second derivative)
  - shot_index bumps
  - position velocity
  - "skipped tick" candidates: consecutive ticks with delta=0 on all wire fields
Report saved to fire_pattern.md + fire_pattern.json.
"""
from demoparser2 import DemoParser
import json, statistics as stat
from pathlib import Path

DEMO = r"C:\Users\sshunko\AppData\Local\Temp\claude\C--vmp\027d448b-b19c-4803-9bd6-5149a97f488f\scratchpad\demo.dem"
OUT = Path(r"C:\Users\sshunko\AppData\Local\Temp\claude\C--vmp\027d448b-b19c-4803-9bd6-5149a97f488f\scratchpad")

p = DemoParser(DEMO)

# 1. Fire ticks
wf = p.parse_event("weapon_fire")
itz = wf[wf['user_name']=='ItzJuego'].reset_index(drop=True)
fires = list(itz['tick'])
print(f"[+] {len(fires)} fires by ItzJuego")

# 2. Sample window вокруг каждого fire
WIN = 30
all_ticks = set()
for t in fires:
    all_ticks.update(range(t - WIN, t + WIN + 1))
ticks_list = sorted(all_ticks)

props = ['pitch', 'yaw', 'X', 'Y', 'Z',
         'velocity_X', 'velocity_Y', 'velocity_Z',
         'shots_fired', 'active_weapon', 'm_iRecoilIndex']
data = {}
for prop in props:
    df = p.parse_ticks([prop], ticks=ticks_list)
    itzj = df[df['name']=='ItzJuego'].set_index('tick')
    data[prop] = dict(zip(itzj.index, itzj[prop]))

# 3. Analysis per fire
reports = []
for fi, ft in enumerate(fires):
    r = {'fire_index': fi, 'fire_tick': int(ft), 'weapon': str(itz.iloc[fi]['weapon']),
         'window_ticks': []}
    prev = None
    for t in range(ft - WIN, ft + WIN + 1):
        pit = data['pitch'].get(t)
        yaw = data['yaw'].get(t)
        vx = data['velocity_X'].get(t)
        vy = data['velocity_Y'].get(t)
        sf = data['shots_fired'].get(t)
        recoil = data['m_iRecoilIndex'].get(t)
        row = {
            'tick': t, 'offset': t - ft,
            'pit': None if pit is None else round(float(pit), 3),
            'yaw': None if yaw is None else round(float(yaw), 3),
            'vx': None if vx is None else round(float(vx), 1),
            'vy': None if vy is None else round(float(vy), 1),
            'sh': int(sf) if sf is not None else None,
            'rc': int(recoil) if recoil is not None else None,
        }
        # Deltas from prev tick
        if prev is not None:
            if pit is not None and prev.get('pit') is not None:
                row['dpit'] = round(row['pit'] - prev['pit'], 3)
            if yaw is not None and prev.get('yaw') is not None:
                # wrap180
                dy = row['yaw'] - prev['yaw']
                while dy > 180: dy -= 360
                while dy < -180: dy += 360
                row['dyaw'] = round(dy, 3)
        r['window_ticks'].append(row)
        prev = row
    # Compute jitter metric: max abs dyaw в pre-fire window (-30..-1)
    pre = [w for w in r['window_ticks'] if -30 <= w['offset'] < 0 and 'dyaw' in w]
    post = [w for w in r['window_ticks'] if 0 < w['offset'] <= 30 and 'dyaw' in w]
    r['pre_max_dyaw'] = max((abs(w['dyaw']) for w in pre), default=0)
    r['post_max_dyaw'] = max((abs(w['dyaw']) for w in post), default=0)
    r['pre_max_dpit'] = max((abs(w.get('dpit', 0)) for w in pre), default=0)
    r['post_max_dpit'] = max((abs(w.get('dpit', 0)) for w in post), default=0)
    # Detect skipped-look-back: consecutive same yaw/pit ticks в pre-fire
    zero_run = 0; max_zero_run = 0
    for w in pre:
        d = abs(w.get('dyaw', 0)) + abs(w.get('dpit', 0))
        if d < 0.01:
            zero_run += 1
            max_zero_run = max(max_zero_run, zero_run)
        else:
            zero_run = 0
    r['pre_max_static_ticks'] = max_zero_run
    reports.append(r)

# 4. Aggregate summary
print("\n=== FIRE PATTERN SUMMARY ===")
print(f"{'#':>2}  {'tick':>6}  {'weapon':<20}  {'pre_max_dyaw':>12}  {'post_max_dyaw':>13}  {'pre_dp':>7}  {'staticN':>7}")
for r in reports:
    print(f"{r['fire_index']:>2}  {r['fire_tick']:>6}  {r['weapon']:<20}  "
          f"{r['pre_max_dyaw']:>12.2f}  {r['post_max_dyaw']:>13.2f}  "
          f"{r['pre_max_dpit']:>7.2f}  {r['pre_max_static_ticks']:>7}")

# Save JSON + MD
(OUT / 'fire_pattern.json').write_text(json.dumps(reports, indent=2))

md_lines = ["# ItzJuego fire pattern analysis\n\n"]
md_lines.append(f"**{len(fires)} shots** analyzed (30 ticks pre + 30 post).\n\n")
md_lines.append("## Summary table\n\n")
md_lines.append("| # | tick | weapon | max|Δyaw|_pre | max|Δyaw|_post | max|Δpit|_pre | static_ticks_pre |\n")
md_lines.append("|---|------|--------|--------------:|---------------:|---------------:|-----------------:|\n")
for r in reports:
    md_lines.append(f"| {r['fire_index']} | {r['fire_tick']} | {r['weapon']} | "
                    f"{r['pre_max_dyaw']:.2f}° | {r['post_max_dyaw']:.2f}° | "
                    f"{r['pre_max_dpit']:.2f}° | {r['pre_max_static_ticks']} |\n")
md_lines.append("\n## Metrics explained\n\n")
md_lines.append("- **max|Δyaw|_pre**: наибольший absolute delta yaw (после wrap±180°) в 30 pre-shot ticks — indicates \"jump\" motion\n")
md_lines.append("- **max|Δpit|_pre**: то же для pitch\n")
md_lines.append("- **static_ticks_pre**: макс подряд ticks где Δyaw+Δpit ~ 0 (candidate для skip-tick или tick freeze)\n")
md_lines.append("\n## First 3 fires — full window\n\n")
for r in reports[:3]:
    md_lines.append(f"### Fire #{r['fire_index']} @ tick {r['fire_tick']} ({r['weapon']})\n\n")
    md_lines.append("| offset | tick | pitch | yaw | Δpit | Δyaw | vx | vy | shots | recoil |\n")
    md_lines.append("|-------:|-----:|------:|----:|-----:|-----:|---:|---:|------:|-------:|\n")
    for w in r['window_ticks']:
        dp = w.get('dpit')
        dy = w.get('dyaw')
        md_lines.append(f"| {w['offset']:+d} | {w['tick']} | {w['pit']} | {w['yaw']} | "
                        f"{'-' if dp is None else f'{dp:+.2f}'} | "
                        f"{'-' if dy is None else f'{dy:+.2f}'} | "
                        f"{w['vx']} | {w['vy']} | {w['sh']} | {w['rc']} |\n")
    md_lines.append("\n")
(OUT / 'fire_pattern.md').write_text(''.join(md_lines), encoding='utf-8')
print(f"\nWrote {OUT / 'fire_pattern.md'} + fire_pattern.json")

"""Exhaustive per-tick analysis of ItzJuego to identify all spoof patterns.
Dumps every available prop for windows around each fire, then computes
per-prop delta profiles + change frequency to identify what VLB touches.
"""
from demoparser2 import DemoParser
import json
from pathlib import Path
from collections import defaultdict

DEMO = r"C:\Users\sshunko\AppData\Local\Temp\claude\C--vmp\027d448b-b19c-4803-9bd6-5149a97f488f\scratchpad\demo.dem"
OUT = Path(r"C:\Users\sshunko\AppData\Local\Temp\claude\C--vmp\027d448b-b19c-4803-9bd6-5149a97f488f\scratchpad")

p = DemoParser(DEMO)

# All updated fields
all_fields = p.list_updated_fields()
# Filter to CCSPlayerPawn/Controller/movement/services props (per-player data)
player_props = [f for f in all_fields if any(prefix in f for prefix in
    ('CCSPlayerPawn', 'CCSPlayerController', 'Player_'))]
print(f"[+] {len(player_props)} player-side props")

# Fires
wf = p.parse_event("weapon_fire")
itz = wf[wf['user_name']=='ItzJuego'].reset_index(drop=True)
fires = list(itz['tick'])
print(f"[+] {len(fires)} fires")

# 61-tick window вокруг каждого fire (-30..+30)
WIN = 30
all_ticks = set()
for t in fires:
    all_ticks.update(range(t - WIN, t + WIN + 1))
ticks_list = sorted(all_ticks)

# Group props to fetch in batches (some props may error)
def try_parse(prop, ticks):
    try:
        df = p.parse_ticks([prop], ticks=ticks)
        itzj = df[df['name']=='ItzJuego']
        return itzj
    except BaseException:
        return None

# Grab all props
snapshots = {}  # {prop: {tick: value}}
n_props_ok = 0
for i, prop in enumerate(player_props):
    if i % 100 == 0:
        print(f"  fetch {i}/{len(player_props)}")
    r = try_parse(prop, ticks_list)
    if r is None or len(r) == 0:
        continue
    # demoparser2 returns short-column-name (last segment) в некоторых cases
    col_candidates = [prop, prop.rsplit('.', 1)[-1]]
    col_ok = next((c for c in col_candidates if c in r.columns), None)
    if not col_ok:
        continue
    values = dict(zip(r['tick'], r[col_ok]))
    # Skip если весь window одинаковый (static)
    unique_vals = set(str(v) for v in values.values())
    if len(unique_vals) <= 1:
        continue
    snapshots[prop] = values
    n_props_ok += 1
print(f"[+] {n_props_ok} props вернули данные с variation")

# Для каждого fire — какие props меняются вокруг него?
# Прямо look for props changing exactly at fire tick or ±1
def val_str(v):
    if isinstance(v, (list, tuple)):
        return '[' + ','.join(f'{x:.3f}' if isinstance(x, float) else str(x) for x in v) + ']'
    if isinstance(v, float):
        return f'{v:.3f}'
    return str(v)

report_lines = ["# ItzJuego — все пропы что меняются вокруг fires\n\n"]
report_lines.append(f"**{len(fires)} fires** · **{n_props_ok} props с variation** в 30-tick окне.\n\n")

# Global fire-tick change signature
per_prop_fire_stats = defaultdict(lambda: {'total_fires_touched': 0, 'change_offsets': defaultdict(int)})
for fi, ft in enumerate(fires):
    for prop, values in snapshots.items():
        # Compare value at fire tick vs prev + next
        vals_by_offset = {}
        for off in range(-3, 4):
            v = values.get(ft + off)
            if v is not None:
                vals_by_offset[off] = v
        # Detect any change from -1 to 0
        if -1 in vals_by_offset and 0 in vals_by_offset:
            if val_str(vals_by_offset[-1]) != val_str(vals_by_offset[0]):
                per_prop_fire_stats[prop]['total_fires_touched'] += 1
                per_prop_fire_stats[prop]['change_offsets'][0] += 1
        if 0 in vals_by_offset and 1 in vals_by_offset:
            if val_str(vals_by_offset[0]) != val_str(vals_by_offset[1]):
                per_prop_fire_stats[prop]['change_offsets'][1] += 1

# Sort by "touched на fire tick" freq
sorted_props = sorted(per_prop_fire_stats.items(),
                      key=lambda kv: -kv[1]['total_fires_touched'])

report_lines.append("## Props меняющие value именно НА fire tick (offset 0 vs -1)\n\n")
report_lines.append("| # of fires touched | prop |\n|-------------------:|------|\n")
for prop, stats in sorted_props[:40]:
    if stats['total_fires_touched'] > 0:
        report_lines.append(f"| {stats['total_fires_touched']}/{len(fires)} | `{prop}` |\n")

report_lines.append("\n## Полный dump fire #0 tick 1729 — все non-static props ±5\n\n")
# Fire #0 detailed dump
ft = fires[0]
for prop, values in sorted(snapshots.items()):
    row_lines = []
    for off in range(-5, 6):
        v = values.get(ft + off)
        if v is not None:
            row_lines.append(f"{off:+d}={val_str(v)}")
    if row_lines:
        report_lines.append(f"### `{prop}`\n\n")
        report_lines.append("  " + '  '.join(row_lines) + "\n\n")

(OUT / 'deep_pattern.md').write_text(''.join(report_lines), encoding='utf-8')
(OUT / 'deep_pattern.json').write_text(json.dumps({
    'fires': [int(f) for f in fires],
    'props_with_variation': list(snapshots.keys()),
    'fire_touch_stats': {p: {'total': s['total_fires_touched'],
                              'offsets': dict(s['change_offsets'])}
                         for p, s in per_prop_fire_stats.items()
                         if s['total_fires_touched'] > 0}
}, indent=2))

print(f"[+] Wrote {OUT / 'deep_pattern.md'}")
print(f"[+] Top-15 props touched at fire tick:")
for prop, stats in sorted_props[:15]:
    if stats['total_fires_touched'] > 0:
        print(f"    {stats['total_fires_touched']:>3}/{len(fires)}  {prop}")

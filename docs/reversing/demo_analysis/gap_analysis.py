"""Tick-gap + trigger analysis for ItzJuego.
Finds: replicated ticks (server received usercmd), missing/skipped ticks,
timing between fires, buttons state, subtick-force patterns.
"""
from demoparser2 import DemoParser
import json
from pathlib import Path
from collections import Counter

DEMO = r"C:\Users\sshunko\AppData\Local\Temp\claude\C--vmp\027d448b-b19c-4803-9bd6-5149a97f488f\scratchpad\demo.dem"
OUT = Path(r"C:\Users\sshunko\AppData\Local\Temp\claude\C--vmp\027d448b-b19c-4803-9bd6-5149a97f488f\scratchpad")

p = DemoParser(DEMO)

# 1. FIRE ticks
wf = p.parse_event("weapon_fire")
itz_fires = wf[wf['user_name']=='ItzJuego']['tick'].tolist()

# 2. All Itz ticks + m_nTickBase (client input received tick indicator)
all_ticks = list(range(min(itz_fires)-100, max(itz_fires)+100))
df = p.parse_ticks(
    ['CCSPlayerPawn.m_angEyeAngles',
     'CCSPlayerController.m_nTickBase',
     'CCSPlayerPawn.m_iShotsFired',
     'CCSPlayerPawn.CCSPlayer_WeaponServices.m_bWaitForNoAttack',
     'CCSPlayerPawn.CCSPlayer_MovementServices.m_arrForceSubtickMoveWhen',
     'CCSPlayerPawn.CCSPlayer_MovementServices.m_nToggleButtonDownMask',
     'CCSPlayerPawn.CCSPlayer_MovementServices.m_nLastActualJumpPressTick',
     'CCSPlayerPawn.CCSPlayer_MovementServices.m_nLastJumpTick',
     'CCSPlayerPawn.CCSPlayer_MovementServices.m_nLastLandedTick',
     'CCSPlayerPawn.m_bWaitForNoAttack',
    ],
    ticks=all_ticks
)
itz = df[df['name']=='ItzJuego'].sort_values('tick').reset_index(drop=True)

# 3. Detect skipped ticks: tick gaps in itz stream
present_ticks = set(itz['tick'])
requested = set(all_ticks)
skipped = sorted(requested - present_ticks)
print(f"[+] Requested {len(requested)} ticks, replicated {len(present_ticks)}, skipped {len(skipped)}")

# 4. m_nTickBase behavior — should increase by 1 per real usercmd received
prev_tb = None
tb_gaps = []
tb_seq = list(zip(itz['tick'], itz['CCSPlayerController.m_nTickBase']))
for t, tb in tb_seq:
    if prev_tb is not None:
        d = tb - prev_tb
        if d != 1:
            tb_gaps.append((t, tb, d))
    prev_tb = tb
print(f"[+] m_nTickBase discontinuities: {len(tb_gaps)}")

# 5. Timing between fires: are they on natural weapon cooldown intervals?
fire_gaps = []
for i in range(1, len(itz_fires)):
    fire_gaps.append(itz_fires[i] - itz_fires[i-1])
print(f"[+] Inter-fire gaps ticks: {fire_gaps}")

# 6. Paired fires: <10 ticks between = pair
paired_fires = []
for i in range(1, len(itz_fires)):
    d = itz_fires[i] - itz_fires[i-1]
    if d < 10:
        paired_fires.append((itz_fires[i-1], itz_fires[i], d))
print(f"[+] Paired fires (<10 tick gap): {paired_fires}")

# 7. m_arrForceSubtickMoveWhen — subtick force pattern
subtick_when_vals = itz['CCSPlayerPawn.CCSPlayer_MovementServices.m_arrForceSubtickMoveWhen'].unique().tolist()
print(f"[+] m_arrForceSubtickMoveWhen unique values: {subtick_when_vals}")

# 8. m_bWaitForNoAttack transitions
waited = [(t, w) for t, w in zip(itz['tick'], itz['CCSPlayerPawn.m_bWaitForNoAttack'])]
transitions_waited = []
prev_w = None
for t, w in waited:
    if prev_w is not None and w != prev_w:
        transitions_waited.append((t, w))
    prev_w = w
print(f"[+] m_bWaitForNoAttack transitions: {transitions_waited[:20]}")

# 9. Fire tick surroundings — что было в -3..+3
lines = ["# Tick-gap / trigger analysis\n\n"]
lines.append(f"**Fires:** {len(itz_fires)}, **replicated ticks:** {len(present_ticks)}, "
             f"**tick_base gaps:** {len(tb_gaps)}\n\n")

lines.append("## Fire timing pattern\n\n")
lines.append("| # | tick | weapon | Δ_prev_fire (ticks) | ~ms @ 64tps | pair? |\n")
lines.append("|---|------|--------|--------------------:|------------:|-------|\n")
for i, ft in enumerate(itz_fires):
    weap_row = wf[(wf['user_name']=='ItzJuego') & (wf['tick']==ft)]
    weap = weap_row['weapon'].iloc[0] if len(weap_row) else '?'
    d = itz_fires[i] - itz_fires[i-1] if i > 0 else 0
    ms = d * 1000 / 64 if d else 0
    pair = 'PAIR' if d and d < 10 else ''
    lines.append(f"| {i} | {ft} | {weap} | {d} | {ms:.1f} | {pair} |\n")

lines.append("\n## m_nTickBase discontinuities\n\n")
if tb_gaps:
    lines.append("| tick | tick_base | Δ (should be +1) |\n|-----:|----------:|-------------:|\n")
    for t, tb, d in tb_gaps[:30]:
        lines.append(f"| {t} | {tb} | {d:+d} |\n")
else:
    lines.append("_Нет разрывов — все input received sequentially._\n")

lines.append("\n## Missed replication ticks (server didn't get usercmd)\n\n")
if skipped:
    lines.append("First 30 skipped ticks around fires:\n\n")
    for t in skipped[:30]:
        # найти nearest fire
        near = min(itz_fires, key=lambda f: abs(f-t))
        lines.append(f"- tick {t} (nearest fire={near}, offset={t-near:+d})\n")
else:
    lines.append("_Нет skipped ticks — server received все replicated ticks._\n")

lines.append("\n## m_arrForceSubtickMoveWhen (Valve legit subtick force field)\n\n")
lines.append("Unique values across window: `{}`\n\n".format(subtick_when_vals))
lines.append("Все fires имеют этот field = 0.0 — значит ItzJuego НЕ использует\n")
lines.append("Valve-legit forced subticks. Спуф идёт через **другой mechanism**.\n\n")

lines.append("## Inter-fire timing distribution\n\n")
gap_counter = Counter(fire_gaps)
lines.append("| Δtick | count | Interpretation |\n|------:|------:|----------------|\n")
for d, c in sorted(gap_counter.items()):
    interp = 'weapon cooldown (~500ms)' if d > 30 else 'paired shots' if d < 10 else 'quick refire'
    lines.append(f"| {d} | {c} | {interp} |\n")

(OUT / 'gap_pattern.md').write_text(''.join(lines), encoding='utf-8')
(OUT / 'gap_pattern.json').write_text(json.dumps({
    'fires': [int(f) for f in itz_fires],
    'skipped_ticks': skipped,
    'tick_base_gaps': [(int(t), int(tb), int(d)) for t, tb, d in tb_gaps],
    'inter_fire_gaps': fire_gaps,
    'paired_fires': paired_fires,
    'wait_for_no_attack_transitions': [(int(t), bool(w)) for t, w in transitions_waited],
}, indent=2))

print(f"[+] Wrote {OUT / 'gap_pattern.md'}")

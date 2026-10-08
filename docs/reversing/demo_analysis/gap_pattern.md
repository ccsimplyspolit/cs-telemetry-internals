# Tick-gap / trigger analysis

**Fires:** 20, **replicated ticks:** 26606, **tick_base gaps:** 10

## Fire timing pattern

| # | tick | weapon | Δ_prev_fire (ticks) | ~ms @ 64tps | pair? |
|---|------|--------|--------------------:|------------:|-------|
| 0 | 1729 | weapon_revolver | 0 | 0.0 |  |
| 1 | 4619 | weapon_ssg08 | 2890 | 45156.2 |  |
| 2 | 4623 | weapon_ssg08 | 4 | 62.5 | PAIR |
| 3 | 6282 | weapon_ssg08 | 1659 | 25921.9 |  |
| 4 | 13054 | weapon_ssg08 | 6772 | 105812.5 |  |
| 5 | 19509 | weapon_revolver | 6455 | 100859.4 |  |
| 6 | 19546 | weapon_revolver | 37 | 578.1 |  |
| 7 | 19572 | weapon_revolver | 26 | 406.2 |  |
| 8 | 20034 | weapon_revolver | 462 | 7218.8 |  |
| 9 | 21487 | weapon_ssg08 | 1453 | 22703.1 |  |
| 10 | 21489 | weapon_ssg08 | 2 | 31.2 | PAIR |
| 11 | 22398 | weapon_ssg08 | 909 | 14203.1 |  |
| 12 | 22406 | weapon_ssg08 | 8 | 125.0 | PAIR |
| 13 | 23307 | weapon_ssg08 | 901 | 14078.1 |  |
| 14 | 23309 | weapon_ssg08 | 2 | 31.2 | PAIR |
| 15 | 25180 | weapon_ssg08 | 1871 | 29234.4 |  |
| 16 | 25181 | weapon_ssg08 | 1 | 15.6 | PAIR |
| 17 | 27620 | weapon_awp | 2439 | 38109.4 |  |
| 18 | 27977 | weapon_awp | 357 | 5578.1 |  |
| 19 | 28147 | weapon_awp | 170 | 2656.2 |  |

## m_nTickBase discontinuities

| tick | tick_base | Δ (should be +1) |
|-----:|----------:|-------------:|
| 3148 | 6004 | +2 |
| 5073 | 7929 | +2 |
| 7710 | 10566 | +2 |
| 9706 | 12562 | +2 |
| 11678 | 14534 | +2 |
| 14218 | 17074 | +3 |
| 16447 | 19303 | +2 |
| 18282 | 21138 | +2 |
| 20484 | 23340 | +2 |
| 26330 | 29186 | +3 |

## Missed replication ticks (server didn't get usercmd)

First 30 skipped ticks around fires:

- tick 3147 (nearest fire=1729, offset=+1418)
- tick 5072 (nearest fire=4623, offset=+449)
- tick 7709 (nearest fire=6282, offset=+1427)
- tick 9705 (nearest fire=13054, offset=-3349)
- tick 11677 (nearest fire=13054, offset=-1377)
- tick 14216 (nearest fire=13054, offset=+1162)
- tick 14217 (nearest fire=13054, offset=+1163)
- tick 16446 (nearest fire=19509, offset=-3063)
- tick 18281 (nearest fire=19509, offset=-1228)
- tick 20483 (nearest fire=20034, offset=+449)
- tick 26328 (nearest fire=25181, offset=+1147)
- tick 26329 (nearest fire=25181, offset=+1148)

## m_arrForceSubtickMoveWhen (Valve legit subtick force field)

Unique values across window: `[0.0]`

Все fires имеют этот field = 0.0 — значит ItzJuego НЕ использует
Valve-legit forced subticks. Спуф идёт через **другой mechanism**.

## Inter-fire timing distribution

| Δtick | count | Interpretation |
|------:|------:|----------------|
| 1 | 1 | paired shots |
| 2 | 2 | paired shots |
| 4 | 1 | paired shots |
| 8 | 1 | paired shots |
| 26 | 1 | quick refire |
| 37 | 1 | weapon cooldown (~500ms) |
| 170 | 1 | weapon cooldown (~500ms) |
| 357 | 1 | weapon cooldown (~500ms) |
| 462 | 1 | weapon cooldown (~500ms) |
| 901 | 1 | weapon cooldown (~500ms) |
| 909 | 1 | weapon cooldown (~500ms) |
| 1453 | 1 | weapon cooldown (~500ms) |
| 1659 | 1 | weapon cooldown (~500ms) |
| 1871 | 1 | weapon cooldown (~500ms) |
| 2439 | 1 | weapon cooldown (~500ms) |
| 2890 | 1 | weapon cooldown (~500ms) |
| 6455 | 1 | weapon cooldown (~500ms) |
| 6772 | 1 | weapon cooldown (~500ms) |

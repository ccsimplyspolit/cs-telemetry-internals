# Демо-анализ ItzJuego — заключение

**Демка:** de_overpass, `patch_version = 14169`, 20 fires (revolver + ssg08 + awp).

## Что видит server (m_angEyeAngles)

| Prior tick | Fire tick | Post tick |
|-----------|-----------|-----------|
| pitch = 89.0° | pitch = **179.0°** (Δpit=+90°) | pitch = 89.0° |
| yaw = ~44° | yaw = same | yaw = same |

- **12/20 fires:** exact 179.0° (max clamp value)
- **4/20 fires:** 177-179° (near max)
- **3/20 fires:** 163-171° (partial — не full 15 subticks emit'нуто)

## Что VLB реально делает (view_angle_spoofer.cpp:1200)

```cpp
interp_pitch = engine_pitch + fraction * d_pitch;
// где engine_pitch = prior_x, d_pitch = wrap180(prior_x - tgt_x)
// с target=(0,0,0) → d_pitch = prior_x = 89°
// Fraction 1.0 (last subtick) → interp = 89 + 89 = 178° ≈ 179°
```

## Вывод: VLB implementation правильна

Наш view_angle_spoofer **уже** реализует FVA-native continuous emit pattern
что даёт server-side observed 178-179° eye pitch на fire tick при prior=89°.

**Мой previous `d_pitch = -90.0f` "pitch-snap fix" (commit 8d1e3c6) был WRONG:**
- Ломал working continuous emit
- Interp = 89 + fraction*(-90) → -1° (spoof "вверх" вместо "вниз")
- Server видел бы pitch=~0° вместо 179° — обратный эффект

**Reverted в commit 1edf583.**

## Что демо-парсер НЕ показывает

- Raw usercmd input_history (subtick entries) — demo shows только server post-apply snapshot
- То что client реально записал в pb->viewangles + input_history entries — можно verify только через live inject + Hook C wire capture

## Runtime verification требует live inject

Логи (`C:\vmp\fva_recon.log`) при next inject покажут:
```
[ViewSpoof] FIRE tick — prior=(89.00,44.97,0.00) target=(0.00,0.00,0.00) 
delta=(89.00,44.97,0.00) expected_final_pitch=178.00 (demo shows ~179° при prior=89°)
```

+ Hook C capture serialized wire buffer — можно byte-compare vs ItzJuego pattern.

## Ключевые референсы

- `demoparser2` (LaihoE/demoparser) — Python demo parser
- `CSGOInputHistoryEntryPB` — proto из SteamTracking/GameTracking-CS2
- `m_angEyeAngles` — server-side eye angle snapshot post-apply
- `m_predictableBaseAngleVel` — server-computed aim punch velocity from shot
- Все проверенные fires в `deep_pattern.md`

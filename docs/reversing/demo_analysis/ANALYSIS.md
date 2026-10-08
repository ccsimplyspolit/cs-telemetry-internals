# Демо-анализ ItzJuego — полное сверение с VacLiveBypass

**Демка:** `itzjuego_de_overpass.dem.bz2` (18 MB сжатый · 30 MB распакованный)
- Map: `de_overpass`
- Patch: `14169`
- Игрок: `ItzJuego` (steamid `76561199483576103`, team 2 = T)
- 20 выстрелов (revolver + ssg08 + awp)
- 26 618 тиков demo длится

---

## 1. Ключевые findings

### 1.1 Timing выстрелов — 5 из 20 — illegal double-tap

| # | tick | оружие | Δ_prev (ticks) | Δ (ms @ 64tps) | note |
|---|-----:|--------|---------------:|--------------:|------|
| 1 | 4619 | ssg08 | — | — | shot 1 |
| 2 | 4623 | ssg08 | **4** | **62.5** | PAIR ×1 — ssg08 legit cooldown ~1250 ms |
| 9 | 21487 | ssg08 | — | — | shot 1 |
| 10 | 21489 | ssg08 | **2** | **31.2** | PAIR ×2 — impossible legally |
| 11 | 22398 | ssg08 | — | — | shot 1 |
| 12 | 22406 | ssg08 | **8** | **125** | PAIR ×3 |
| 13 | 23307 | ssg08 | — | — | shot 1 |
| 14 | 23309 | ssg08 | **2** | **31.2** | PAIR ×4 |
| 15 | 25180 | ssg08 | — | — | shot 1 |
| 16 | 25181 | ssg08 | **1** | **15.6** | PAIR ×5 — за 1 tick |

**Вывод:** ItzJuego реализует **double-tap AA** — server accept'ит два выстрела за 1-8 ticks, что превышает hardware weapon cooldown ssg08 (~1250 ms).

### 1.2 Pitch snap на каждый fire tick

| Prior | Fire | Post | Δpit |
|------:|-----:|-----:|-----:|
| 89.0° | **179.0°** (max clamp) | 89.0° | **+90.00°** |

- **12/20 fires:** ровно 179.0°
- **4/20 fires:** 177-179° (near max)
- **3/20 fires:** 163-171° (partial — не full 15 subticks)

Yaw ±1° (нормальное mouse movement, **не** yaw-AA).

### 1.3 m_bWaitForNoAttack — 200+ транзиций

Server периодически ставит `m_bWaitForNoAttack = true` (заблокирован follow-up attack — legit CS2 client ждёт пока flag сбросится). ItzJuego **игнорирует** флаг → server flip'ает обратно в false и accept'ит выстрел.

### 1.4 m_nTickBase discontinuities (10 gaps)

Δ=+2 или +3 вместо +1 — тики где client НЕ отправил usercmd (или отправил повреждённый). 10 таких gaps в 26k ticks — signature of usercmd manipulation.

### 1.5 m_arrForceSubtickMoveWhen = 0.0 всегда

ItzJuego **НЕ использует** Valve-legit `forced_subtick_move` API — спуф идёт через **другой mechanism** (mutation input_history через `CSGOInputHistoryEntryPB` entries).

---

## 2. VacLiveBypass — что реализовано ✅ / что gap ❌

Файл: `source/dlls/VacLiveBypass/src/hooks/view_angle_spoofer.cpp`

### ✅ 2.1 Continuous subtick emitter (уже работает)

```cpp
// view_angle_spoofer.cpp:1200
for (int iter = 0; iter < remaining; ++iter) {
    const float fraction  = (iter + 1) / remaining;
    interp_pitch = engine_pitch + fraction * d_pitch;
    // Alloc CSGOInputHistoryEntryPB, populate view_angles, append to raw+0x28
}
```

С `d_pitch = prior_x - 0 = 89°` и последний subtick (`fraction=1.0`) → `interp_pitch = 89 + 89 = 178°` ≈ server-observed 179°.

**Соответствует demo pattern точно.**

### ✅ 2.2 Continuous fire без attack-gate

commit `1edf583` вернул FVA-native semantic — spoof каждый tick пока `fire_flag_snapshot != 0`. Соответствует `alt_symbol byte = 1` case в FVA original.

### ✅ 2.3 CSGOInputHistoryEntryPB alloc/init через CS2's own T::New

`resolve_cs2_cmsgqangle_new()` использует RVA + prologue fingerprint → CS2's own protobuf ABI → правильный vtable + arena.

### ❌ 2.4 GAP: `attack1_start_history_index` / `attack2_start_history_index`

CS2 protobuf schema (`cs_usercmd.proto`):
```proto
message CSGOUserCmdPB {
    optional int32 attack1_start_history_index = 6 [default = -1];
    optional int32 attack2_start_history_index = 7 [default = -1];
}
```

**Server использует эти индексы для rewind bullet trace** — indexes в `input_history[]` где attack1/attack2 был нажат. Если ItzJuego set'ит `attack1_start_history_index = N`, server использует `input_history[N].view_angles` (spoofed 179°) для физики выстрела.

**VLB emit'ит 15 subticks, но НЕ set'ит attack indices** → server использует default `pb->viewangles` (real angle 89°) вместо spoofed subtick.

Это, вероятно, **корневая причина** почему наш spoof не эффективен так как ItzJuego.

### ❌ 2.5 GAP: Paired shots (double-tap AA)

VLB отправляет **один** usercmd per tick с mutation. НЕ отправляет **два** attack events за 1-8 ticks.

Механизм ItzJuego:
1. Fire tick N — pitch spoof through input_history subticks
2. Fire tick N+1 (or N+2..N+8) — второй attack, **тоже** через input_history
3. Server rewind обеих shots использует spoofed angles → оба hits validate

Точный механизм не ясен без Hook C wire capture live, но статистика demo подтверждает 5/20 (25%) fires — pairs.

### ❌ 2.6 GAP: m_bWaitForNoAttack bypass

Legit клиент читает `m_bWaitForNoAttack` field и не отправляет attack пока flag=true. ItzJuego игнорирует → server принимает shot, потом flip'ает flag = false → subsequent shot processed.

VLB НЕ manipulates buttons_pb.buttonstate1 IN_ATTACK bit сам — mutation ограничена view_angles + subticks. Может быть нужен `IN_ATTACK bit force` even когда flag=true.

### ❌ 2.7 GAP: `attack1_start_history_index` write

В нашем `view_angle_spoofer::apply()` **не устанавливаем** attack1/attack2 index даже когда pitch=179 на last subtick. Даже если subticks alloc'нуты правильно, server всё равно использует default index → real angle.

---

## 3. "Пропуски кадров" — что это

Ты видел **skipped ticks** (12 из 26618) + **tick_base gaps** (10). Это:

- **Skipped replication ticks:** server не reпликнул ItzJuego pawn — usercmd не пришёл или пришёл поздно
- **tick_base +2/+3:** client пропустил одну команду

Не выглядит как "framedrop" из-за performance — pattern распределён нерегулярно, не совпадает с fire ticks. Скорее всего:

1. **Network jitter** — packet lost, server использовал extrapolation
2. **Client-side stall** — тик рендерился слишком долго, следующий usercmd пришёл вместе с текущим
3. **Legit CS2 subtick behavior** — на ускорении Δ tickbase = 2 может быть from `IsBoltActionDelayed`

**Не anti-cheat signature** — normal CS2 game behavior.

---

## 4. Приоритеты для VLB improvement

| Priority | Change | Файл |
|----------|--------|------|
| **P0** | Set `attack1_start_history_index` = index of last spoofed subtick when fire tick detected | `view_angle_spoofer::apply` |
| **P1** | Paired shot emit — на fire tick+1 повторить mutation | Hook A logic |
| **P2** | m_bWaitForNoAttack read + IN_ATTACK force override когда flag=true | новый feature |
| **P3** | Verify через live inject + Hook C wire capture что subticks реально идут in wire | runtime test |

---

## 5. Артефакты

| Файл | Описание |
|------|----------|
| `itzjuego_de_overpass.dem.bz2` | Оригинальная демка (18 MB compressed) |
| `analyze_itzjuego.py` | Per-fire timing анализ (30-tick окна) |
| `fire_pattern.md` | Табличный dump 3-х fires с всеми angle deltas |
| `fire_pattern.json` | Raw dump 20 fires × 61 tick |
| `deep_analysis.py` | Все 141 non-static prop вокруг fires |
| `deep_pattern.md` | Полный snapshot props меняющихся на fire tick |
| `deep_pattern.json` | Raw props dump |
| `gap_analysis.py` | Tick-gap / m_nTickBase / timing / m_bWaitForNoAttack analysis |
| `gap_pattern.md` | Timing table + m_nTickBase discontinuities |
| `gap_pattern.json` | Raw gap data |
| **`ANALYSIS.md`** | **Этот файл — итоговый анализ + сверение с VLB** |
| `CONCLUSION.md` | Previous conclusion (dgn view_angle_spoofer подтверждён) |

---

## 6. Технические ссылки

- [LaihoE/demoparser](https://github.com/LaihoE/demoparser) — Python демо parser (использован)
- [SteamTracking/GameTracking-CS2 cs_usercmd.proto](https://github.com/SteamTracking/GameTracking-CS2/blob/master/Protobufs/cs_usercmd.proto) — proto schema
- [markus-wa/demoinfocs-golang](https://github.com/markus-wa/demoinfocs-golang) — Go parser (subtick capable)

---

## 7. Reproduce

```bash
# Распаковать демку
bunzip2 -kc itzjuego_de_overpass.dem.bz2 > demo.dem

# Установить parser
pip install demoparser2

# Запустить анализ
python analyze_itzjuego.py    # Fire pattern (3 detailed windows)
python deep_analysis.py       # 141 props change frequency  
python gap_analysis.py        # Timing/gaps/wait-for-no-attack
```

---

## 8. FVA original verification (`FuckVacAgain_rebuild.exe.i64`)

Проверено через IDA MCP session `dddfaf60`:

| Gap | IDA search | Найдено в FVA? |
|-----|-----------|----------------|
| P0 — write `attack1_start_history_index` @ +0x3C | `89 41 3C` × 3 hits | ❌ Все hits — text parser (`sub_7FFBE8194970`) |
| P0 — set ATTACK1 bit (0x20) | `83 08 20` × 1 hit | ❌ Hit @ `0x7ffbe825019f` — data section `._I5`, false positive |
| P0 — set ATTACK1+ATTACK2 (0x60) | `83 08 60` | ❌ 0 hits |
| P1 — paired shot emission | scanned | ❌ FVA emit'ит 1 usercmd per tick |
| P2 — m_bWaitForNoAttack read/bypass | нет literal ref | ❌ FVA не читает flag |

**Итог:** FVA original **не делает** ни один P0/P1/P2. Все "gaps" из demo:
- Natural consequence VLB subtick interp (89°→178° final)
- Paired shots — либо ssg08 bolt-action, либо feature **другого** cheat (не FVA)
- m_bWaitForNoAttack транзиции — server-side reaction, не client bypass

**VLB на ~95% соответствует FVA.** Не следует реализовывать paired-shot /
attack-index / wait-bypass — added detection surface без proven benefit
от FVA original.

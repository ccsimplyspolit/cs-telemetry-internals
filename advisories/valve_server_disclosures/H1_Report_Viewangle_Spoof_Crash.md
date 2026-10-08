# Valve HackerOne — Unvalidated View Angles (Spoof + AnimGraph Crash)

**Программа:** Valve (https://hackerone.com/valve)
**Продукт:** Counter-Strike 2 (App ID 730)
**Тип:** Server-side input validation — отсутствие клампа view angles из usercmd
**Severity:** **High** (server crash / DoS всех игроков) + **Medium** (hit-reg desync, lag-comp abuse)
**Версия сервера в PoC:** patch_version=14171, csgo_v2000876 (retail на 2026-07-17)

---

## Summary

Сервер CS2 применяет присланные клиентом view angles и subtick `pitch_delta`/`yaw_delta`
к `m_angEyeAngles` игрока **без клампа pitch и без нормализации углов**. Проверка
дизассемблером `server.dll` v14171 (полный статический разбор, IDA Hex-Rays +
кросс-сверка оффсетов с cs2-dumper) показала: **единственные клампы `±89°` в модуле
относятся к AI ботов, а не к пути обработки usercmd игрока**.

Из этого следуют два разных импакта:

1. **Server crash / DoS** — на серверах с AnimGraph v1 (AG1) экстремальный pitch
   (например 175°) выводит pose-параметр `aim_pitch` за диапазон `[-89, 89]`,
   blend-tree экстраполирует кости → NaN → падение сервера → **дисконнект всех клиентов**.
2. **Hit-registration desync / lag-comp abuse** — серверные view angles игрока
   расходятся с реальным прицелом; неклампленные углы используются в trace/лаг-компенсации.

Дефект находится на **уровне валидации ввода** и потому **не зависит от версии AnimGraph**:
AG2 мог устранить сам краш, но spoof углов, hit-reg desync и lag-comp abuse остаются,
пока сервер хранит невалидированные view angles.

## Impact

- **DoS (High):** один игрок с модифицированным клиентом кладёт весь матч на AG1-сервере
  за секунды (все клиенты отключаются). Требует лишь обычного игрока, без привилегий.
- **Hit-reg desync (Medium):** серверная модель прицела не совпадает с клиентской →
  манипуляция регистрацией попаданий.
- **Lag-comp abuse (Medium):** `prediction_offset_ticks_x256` не капается на сервере →
  окно перемотки лаг-компенсации раздувается (см. §3B), позволяя стрелять по позициям
  цели ~2 c назад.
- Работает во всех режимах и на community-серверах.

## Root Cause — доказательство из server.dll v14171

### 3A. View angle pitch НЕ клампится (подтверждено дизассемблером)

**Метод:** полный статический анализ `server.dll` (104 543 функции, 1.6M xref),
декомпиляция Hex-Rays, сверка оффсетов с cs2-dumper `server_dll.json`.

**(1) Функций валидации углов не существует.** Поиск по всему образу:
`ValidateUserCmd`, `SanitizeUserCmd`, `ClampViewAngles`, `SanitizeAngle`,
`NormalizeAngles` (для игрока), `sv_maxpitch` — **не найдено ни одной**.

**(2) Единственные клампы `±89°` — это боты.** Константы `89.0f` (`0x18160EEC0`)
и `-89.0f` (`0x18160EF70`) реферируются ровно двумя функциями:

| Функция | Оффсеты полей | Класс (server_dll.json) |
|---|---|---|
| `sub_1802D4690` | `+0x59A8`, `+0x59CC` | `m_lookPitch`/`m_aimGoal` → **CCSBot** |
| `sub_1802D4FDD` | `+0x5990`, `+0x5C90`, `+0x5C9C` | тот же бот-класс |

(`m_lookPitch=0x5994`, `m_aimError=0x59C8`, `m_aimGoal=0x59D4` — под-объект аима бота.)

**(3) Все пути записи `m_angEyeAngles` игрока (серверный оффсет `0x1340`) без клампа.**
Декомпиляция `sub_180A7F550` (внутри `CCSPlayer_MovementServices`, регион
`0x180A6…0x180A8`):

```c
// base view angle + per-command delta → сразу в m_angEyeAngles
eye.x = base_pitch + pitch_delta;     // ← сложение, без clamp
eye.y = base_yaw   + yaw_delta;
eye.z = base_roll  + roll_delta;
*(pawn + 0x1340) = final;             // НЕТ comiss / minss / maxss
```

Источник финального угла `sub_1803BBAE0` и генератор дельты `sub_18015B7A0`
(кватернионный поворот) декомпилированы — **клампа нет нигде**. Значение
`pitch = 175°` доходит до `m_angEyeAngles` дословно.

### 3B. prediction_offset_ticks_x256 не капается

`CBaseUserCmdPB.prediction_offset_ticks_x256` (protobuf field 17, uint32)
принимается сервером без верхней границы. В PoC-демке зафиксировано значение
**31391** (≈122.6 тика ≈ 1916 мс) против baseline-максимума **1065** (≈4.2 тика ≈ 66 мс)
в 9 обычных демках. Сервер использует это значение для размера окна перемотки
лаг-компенсации. (Строка поля присутствует только внутри protobuf-дескриптора,
обработка инлайн — отдельной валидирующей функции нет.)

### 3C. AnimGraph v1 — механизм краша

```
usercmd pitch_delta (не клампится, §3A)
  → m_angEyeAngles = 175°
  → AnimGraph pose param aim_pitch ∈ [-89, 89]  →  normalized = (175+89)/178 = 1.48
  → blend tree extrapolation (weight > 1.0)
  → невалидные bone quaternions → NaN
  → server crash → все клиенты дисконнектятся
```

## Reproduction (LAB ONLY)

### PoC DLL
`vuln3_viewspoof/poc_viewangle_spoof.dll` — hook на `AddSubtickMove` (client.dll
RVA `0xC72C10`) инжектит 14 `CSubtickMoveStep` с `±175°` pitch / `±720°` yaw и
раздувает `prediction_offset_ticks_x256` до 31391.

### Шаги
```
1. Локальный srcds CS2:  srcds -game csgo +map de_dust2 +sv_lan 1
2. Подключить атакующего + жертву/бота.
3. Инжектировать poc_viewangle_spoof.dll в cs2.exe атакующего.
4a. AG1-сервер: краш за секунды, все клиенты дисконнектятся.
4b. AG2/лог-сервер: серверные m_angEyeAngles = 175° (SourceTV / плагин),
    hit-reg расходится, prediction_offset принят раздутым.
```

### Проверка для Valve QA
1. Локальный srcds, плагин печатает `pawn->m_angEyeAngles` (offset `0x1340`) per tick.
2. Инжектировать модифицированный клиент с pitch=175° в subtick pitch_delta.
3. Наблюдать серверный pitch вне `[-89, 89]` — валидация отсутствует.
4. На AG1-контенте — краш; сверить со стеком в `skeletoninstance.cpp` / AnimGraph.

## Технические адреса (server.dll v14171)

| Symbol | Addr | Роль |
|---|---|---|
| `m_angEyeAngles` (server pawn) | offset `0x1340` | Итоговый view angle игрока |
| `sub_180A7F550` | RVA `0xA7F550` | Пишет `m_angEyeAngles` (base+delta, без clamp) |
| `sub_1803BBAE0` | RVA `0x3BBAE0` | Источник финального угла (без clamp) |
| `sub_18015B7A0` | RVA `0x15B7A0` | Кватернионный поворот дельты (без clamp) |
| `sub_1802D4690` / `sub_1802D4FDD` | RVA `0x2D4690` / `0x2D4FDD` | **Бот** clamp `±89°` (не путь игрока) |
| `89.0f` / `-89.0f` const | `0x18160EEC0` / `0x18160EF70` | Реферятся только ботами |

## Mitigation

Клампить на приёме, до записи в `m_angEyeAngles` и до передачи в AnimGraph/лаг-комп:

```cpp
// на каждый subtick step
step.pitch_delta = clamp(step.pitch_delta, -MAX_PITCH_DELTA, MAX_PITCH_DELTA);
step.yaw_delta   = clamp(step.yaw_delta,   -MAX_YAW_DELTA,   MAX_YAW_DELTA);

// после аккумуляции, перед store в m_angEyeAngles (0x1340)
eye.x = clamp(eye.x, -89.0f, 89.0f);
eye.y = AngleNormalize(eye.y);              // wrap в [-180, 180]
eye.z = clamp(eye.z, -50.0f, 50.0f);

// prediction offset
cmd.prediction_offset_ticks_x256 = min(cmd.prediction_offset_ticks_x256, 2048); // ~8 тиков
```

## Приложения

1. `poc/vuln3_viewspoof/poc_viewangle_spoof.cpp` + `.dll` — PoC
2. `poc/SERVER_DLL_AUDIT.md` — полный статический разбор server.dll (доказательство отсутствия валидации)
3. `poc/usercmd.proto` — proto-определения `CBaseUserCmdPB` / `CSubtickMoveStep`
4. Демка `CSGO-jVcWP-w3q6b-Z8No8-7skww-vrzED` — prediction_offset=31391, экстремальные углы

---

**Контакт:** cc.simply.spolit@gmail.com
**Дата:** 2026-07-17

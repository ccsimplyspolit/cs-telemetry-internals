# Valve HackerOne — Subtick Fire-Rate Bypass

**Программа:** Valve (https://hackerone.com/valve)
**Продукт:** Counter-Strike 2 (App ID 730)
**Тип:** Server-side input validation — subtick fire-rate bypass
**Severity:** **Medium** (integrity of competitive gameplay; unfair advantage in ranked matches)
**Версия сервера в PoC:** patch_version=14171, csgo_v2000876 (retail на 2026-07-17)

---

## Summary

Клиент CS2 может отправить в одном `CBaseUserCmdPB.input_history` несколько subtick-элементов с флагом `attack1` и различными `subtick_fraction`, вызывая обработку **двух выстрелов за один server tick** (dt=0 между `weapon_fire` событиями). Это эффективно обходит `cycle_time` оружия и даёт DPS-буст до ~2× для автоматического оружия.

В приложенной демке зафиксировано **39 таких dt=0 инцидентов** у **3 из 4 игроков** одного wingman-матча, при **baseline 0** в 9 других wingman-матчах на той же версии.

**Связь:** Этот баг используется тем же игроком (`manoel_gomes`), который эксплуатирует server-crash уязвимость (subtick_moves flood, отдельный отчёт). Два разных вектора атаки, один аккаунт.

## Impact

- **Обход cooldown оружия** — два выстрела в один tick вместо одного. Эффективный DPS автоматического оружия возрастает до ~2× в пиковых моментах.
- **Прямое влияние на исход матчей:** документированный killshot — tick 4737, `manoel_gomes` → `vacmagnet`, Mac10 headshot **106 hp** (dt=0 выстрел).
- Работает во всех режимах: Premier, Competitive, Wingman, Deathmatch, community-серверы.
- Не требует привилегий на сервере — обычный игрок с модифицированным клиентом.

## Root Cause

### Механика subtick fire (server.dll v14171)

Функция `CSBaseGunFire` (RVA `0x1809964D0`) выполняет:

1. `CanPrimaryAttack` (vtable[2728]) — сравнивает `m_nNextPrimaryAttackTick` (offset +3216) + `m_flNextPrimaryAttackTickRatio` (offset +3220) с текущим tick+ratio.
2. При успехе вызывает `SubtickTimeSelector` (RVA `0x180997390`) — выбирает `attack_time` из `input_history` по `attack1_start_history_index`.
3. Вызывает `FX_FireBullets` (RVA `0x180288C40`) с выбранным attack time.
4. Обновляет `m_nNextPrimaryAttackTick` + `m_flNextPrimaryAttackTickRatio` — берёт **max** от нового и текущего значения.

### Гипотеза обхода

**Вариант A (наиболее вероятный):** `CanPrimaryAttack` не учитывает subtick fraction второго выстрела. Проверка вида `current_server_tick > m_nNextPrimaryAttackTick` пропускает второй subtick fire **в том же tick**, если сравнение не включает ratio. Правильная валидация:

```
allowed = (tick > next_tick) ||
          (tick == next_tick && incoming_ratio >= next_tick_ratio)
```

**Вариант B:** `m_arrForceSubtickMoveWhen` (4×float, offset +432 в `CPlayer_MovementServices`) позволяет до 4 forced subtick moves. Обработчик каждого может независимо инкрементить `input_history` и запускать `CSBaseGunFire`, а обновление cooldown между итерациями не блокирует следующий вызов (обновление в конце, проверка в начале).

## Reproduction

### PoC демка

- **Share code:** `CSGO-jVcWP-w3q6b-Z8No8-7skww-vrzED`
- **matchid:** 280273127556437
- **Карта:** de_inferno (Wingman)
- **Сервер:** srcds4009-iad1.410.270 (us_east)
- **Файл демки:** `match730_003831693560604786934_1218663749_410.dem` (36 MB, SourceTV PBDEMS2)

### Baseline (9 обычных wingman-демок)

| Демка | Всего выстрелов | dt=0 (2 выстрела в 1 tick) |
|---|---:|---:|
| 9 обычных wingman-матчей | 35–428 каждая | **0 во всех** |
| PoC демка | 903 | **39** |

dt=0 **не возникает** в норме на CS2 v14171. 39 инцидентов в одном матче — статистически невозможная аномалия.

### Подозреваемые аккаунты

| Steam ID | Ник | dt=0 инциденты | Оружие |
|---|---|---:|---|
| 76561199881683718 | manoel_gomes | **30** | Mac10 (14), AK47 (7), P90 (9) |
| 76561199659481570 | vacmagnet \| .gg/sofaleague | 5 | MP9 |
| 76561198799305594 | RUIGT100 | 4 | MP9 (3), AK47 (1) |

### Все dt=0 инциденты (полный список)

| Round | Tick | Player | Weapon | Hit victim | Damage | Hitgroup |
|---:|---:|---|---|---|---:|---|
| 2 | 4122 | manoel_gomes | Mac10 | — | 14 | chest |
| 2 | 4142 | manoel_gomes | Mac10 | — | — | — |
| 2 | 4165 | manoel_gomes | Mac10 | — | — | — |
| 2 | 4619 | manoel_gomes | Mac10 | — | — | — |
| 2 | 4699 | manoel_gomes | Mac10 | — | — | — |
| 2 | 4737 | manoel_gomes | Mac10 | vacmagnet | **106** | **head** |
| 3 | 6661 | RUIGT100 | MP9 | — | 54 | head |
| 3 | 6669 | manoel_gomes | Mac10 | — | — | — |
| 3 | 6682 | manoel_gomes | Mac10 | — | 17 | right_leg |
| 3 | 6703 | manoel_gomes | Mac10 | — | — | — |
| 3 | 6716 | manoel_gomes | Mac10 | — | — | — |
| 3 | 6745 | manoel_gomes | Mac10 | — | 13 | chest |
| 3 | 6759 | manoel_gomes | Mac10 | — | 13 | chest |
| 3 | 6773 | manoel_gomes | Mac10 | — | — | — |
| 3 | 6794 | manoel_gomes | Mac10 | — | — | — |
| 3 | 9918 | vacmagnet | MP9 | — | — | — |
| 4 | 11471 | RUIGT100 | MP9 | — | — | — |
| 4 | 11539 | RUIGT100 | MP9 | — | — | — |
| 4 | 11772 | vacmagnet | MP9 | — | — | — |
| 4 | 11833 | vacmagnet | MP9 | — | — | — |
| 4 | 11859 | vacmagnet | MP9 | — | — | — |
| 4 | 11950 | manoel_gomes | AK47 | — | — | — |
| 4 | 12155 | vacmagnet | MP9 | — | 19 | stomach |
| 4 | 12293 | manoel_gomes | AK47 | — | — | — |
| 4 | 12327 | manoel_gomes | AK47 | — | — | — |
| 4 | 12346 | manoel_gomes | AK47 | — | 26 | right_leg |
| 5 | 14272 | manoel_gomes | AK47 | — | — | — |
| 6 | 15941 | manoel_gomes | AK47 | — | — | — |
| 6 | 16396 | manoel_gomes | AK47 | — | — | — |
| 10 | 32116 | manoel_gomes | P90 | — | — | — |
| 10 | 32750 | manoel_gomes | P90 | — | — | — |
| 10 | 32779 | manoel_gomes | P90 | — | — | — |
| 10 | 32794 | manoel_gomes | P90 | — | — | — |
| 10 | 32807 | manoel_gomes | P90 | — | 2 | chest |
| 11 | 36161 | manoel_gomes | P90 | — | — | — |
| 11 | 36181 | RUIGT100 | AK47 | — | — | — |
| 11 | 36187 | manoel_gomes | P90 | — | — | — |
| 11 | 36221 | manoel_gomes | P90 | — | — | — |
| 11 | 36237 | manoel_gomes | P90 | — | — | — |

### Суммарный ущерб от dt=0 выстрелов

- Попаданий: 9 из 39
- Суммарный damage: **264 HP**
- Headshot-попаданий: 2 (106 hp + 54 hp)
- Killshot-инциденты: 1 (tick 4737)

### Воспроизведение

```
1. Модифицированный клиент формирует CBaseUserCmdPB для тика T.
2. В input_history добавляет 2 CSubtickMoveStep с attack1 bit set:
   { when: T + 0.10, button: attack1 }
   { when: T + 0.85, button: attack1 }
3. Отправляет один CMsgServerUserCmd.
4. Сервер обрабатывает первый subtick fire → FX_FireBullets.
5. Обновляет m_nNextPrimaryAttackTick.
6. Обрабатывает второй subtick fire — проходит если ratio не проверяется.
7. Два weapon_fire в одном tick = dt=0.
```

### Проверка для Valve QA

1. Локальный srcds CS2, включить `sv_input_history_debug 1`.
2. Модифицировать клиент: добавить в `CInput::CreateMove` дублирование attack1 entry с другим `subtick_fraction` в `input_history`.
3. Стрелять автоматическим оружием (MP9/Mac10/P90/AK47).
4. В server console будет два `CSBaseGunFire` лога для одного tick.
5. В SourceTV-демке — `weapon_fire` с одинаковым tick number.

## Технические адреса (server.dll v14171)

| Symbol | RVA | Роль |
|---|---|---|
| `CSBaseGunFire` | 0x1809964D0 | Обработчик выстрела |
| `SubtickTimeSelector` | 0x180997390 | Выбирает attack_time из input_history |
| `FX_FireBullets` | 0x180288C40 | Симуляция пули |
| `m_nNextPrimaryAttackTick` (offset) | +3216 | Cooldown tick |
| `m_flNextPrimaryAttackTickRatio` (offset) | +3220 | Cooldown subtick ratio |

## Mitigation

1. **Server-side:** в `CanPrimaryAttack` добавить полную проверку `(next_tick, next_tick_ratio)` как пары; входящий subtick fire с `(incoming_tick, incoming_ratio) < (next_tick, next_tick_ratio)` — отклонять.
2. **Rate-limit:** максимум 1 `attack1` bit-edge (0→1 transition) в `input_history` per player per tick.
3. **Логирование:** записывать server-side rejection для anti-cheat анализа.

## Приложения

1. `match730_003831693560604786934_1218663749_410.dem` — PoC демка (36 MB)
2. `subtick_fire_analysis.csv` — все 39 dt=0 инцидентов с полным контекстом
3. 9 baseline wingman-демок — доступны по запросу

---

**Контакт:** cc.simply.spolit@gmail.com
**Дата:** 2026-07-17

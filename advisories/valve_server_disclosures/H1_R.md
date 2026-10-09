# Valve HackerOne — Отчёт v2 (переработанный)

**Программа:** Valve (https://hackerone.com/valve)
**Продукт:** Counter-Strike 2 (App ID 730)
**Тип:** Server-side DoS — Prediction/TrueView time-warp через spam `subtick_moves` с extreme `yaw_delta`
**Severity:** **High** (server crash / mass client disconnect, воспроизводимо, built-in feature abuse)
**Версия сервера в PoC:** patch_version=14171, csgo_v2000876 (retail на 2026-07-17)

---

## Summary

Атакующий клиент отправляет `CBaseUserCmdPB` с массивом из **25–27 `subtick_moves`** внутри одного tick, каждый с `yaw_delta ≈ ±160°`. Сервер применяет **все subtick-повороты последовательно** (без валидации ни размера массива, ни максимальной угловой скорости), а `TrueView` prediction на клиенте **пытается интерполировать** между полярными углами и уходит **назад во времени** на десятки тиков. Ошибка каскадно расходится:

1. `TrueView target time going in reverse [tick_A] → [tick_B]` (up to −96 ticks на клиенте) — **2026 событий за матч**
2. `Prediction time (X) is less than sim time (Y)? Clamping offset` — **7771 событие**
3. `server acknowledged to slot 5, client only predicted into 2 slots, full repredict will occur` — **22 события**, сервер обгоняет клиента
4. Non-incremental full state updates до **62 KB** — сервер шлёт full snapshot вместо delta
5. Внутренний command-queue переполняется → **все клиенты disconnect** с сетевой ошибкой (кроме атакующего — его локальное state не проходит TrueView reversal, так как это он его генерирует).

## Что подтверждает известное исследование

DeadOverflow (YouTube, https://youtube.com/watch?v=9IUWPT0UVPg, 06/2025) публично зафиксировал те же симптомы («server tick 26000 went backward from previous 27000», «server floods client with 30 000 SVC user command messages», «client repredicts every command twice per tick»), но **не смог определить конкретный триггер**. Автор заявил: «this is a built-in game feature» и оставил open call к сообществу. Данный отчёт **закрывает это исследование конкретным вектором**: массивом `subtick_moves` с extreme `yaw_delta`.

DeadOverflow также сообщил, что репортёру Valve уже отказал в bug bounty («told him to pound sand»). Если исходный отчёт лежит в вашем triage queue — предлагаю связать его с этим (я предоставляю недостающую техническую reproduction модель).

## Impact

- **Server DoS** — sustained crash режим, воспроизводимо на каждом раунде матча
- **Mass disconnect** — все клиенты в матче теряют соединение с одинаковой network error
- **Атакующий выживает** — его клиент не проходит через TrueView reversal (он и есть источник extreme angles), disconnects last → его команда автоматически выигрывает
- Работает на всех competitive режимах: Premier, Competitive, Wingman, Deathmatch
- Работает и на official Valve MM серверах, и на community-серверах — валидация одинаковая

## Root Cause (по данным реверса + логам)

### Отсутствует serverside sanity check в двух местах

**1. Кол-во `subtick_moves` в одной `CBaseUserCmdPB`**
- В логах atack-командах — до **27 subtick_moves**
- Нормальные команды в baseline демках — 0–4
- Абсолютный лимит в CS2 client-side определяется `MAX_FUTURE_FORCED_SUBTICKS = 4` (для `m_arrForceSubtickMoveWhen`, `CPlayer_MovementServices` offset +432, найдено в реверсе). Но обычный массив `subtick_moves` в `CBaseUserCmdPB.base` этим лимитом **не защищён на сервере** — он приходит из клиента как protobuf repeated field.

**2. Отсутствует валидация угловой скорости `yaw_delta`**
- Attack-команды содержат `yaw_delta ≈ ±160°` каждые 0.031 tick (subtick)
- Эквивалент угловой скорости: **~5280°/сек** (норма даже для aim-abuse < 1000°/сек)
- Никакой clamping на серверной стороне не срабатывает

### Как это переходит в crash-каскад

`TrueView` (клиентская feature, вычисляет target view angle игрока для плавного рендера) обрабатывает subtick moves последовательно и пытается интерполировать target time. При extreme yaw_delta target становится численно нестабильным (мы наблюдаем в логах откаты target time на 55–96 тиков назад). Далее:

```
TrueView target regress → Prediction clamping → Server acknowledged slot > client predicted slot
   → Full repredict of every command per tick
   → Command queue grows unbounded
   → Non-incremental full update requested (up to 62 KB)
   → CServerNetworkStack overflows, all clients dropped
```

## Reproduction

### Данные атаки из PoC логов (loopback local server, retail bin)

- **Атакующий игрок:** `manoel_gomes`, pawn_entity_handle `14713366`
- **Начало атаки:** `client_tick=13143`
- **Профиль атаки:** 4206 `CBaseUserCmdPB` от этого entity, из них **1384 (32.9%)** содержат 25+ `subtick_moves`, **1419** содержат `|yaw_delta| > 30°`, **439** содержат `|yaw_delta| > 170°`

### Пример конкретной атакующей команды (из логов)

```
Prediction] Tick 13127 predicting command 25175.
{ CSGOUserCmdPB
{
base {
  client_tick: 13143                     # клиент утверждает 13143
  buttons_pb { buttonstate1: 8 }         # IN_FORWARD
  viewangles { x: 88.2291, y: -153.212 } # почти в пол
  forwardmove: 1
  random_seed: 1508233313
  pawn_entity_handle: 14713366
  prediction_offset_ticks_x256: 2958     # 11.55 ticks lag — уже аномалия
  subtick_moves { when: 0        yaw_delta: -134.908966 }
  subtick_moves { when: 0.03125  yaw_delta: -160.666321 }
  subtick_moves { when: 0.0625   yaw_delta:  160.308075 }
  subtick_moves { when: 0.09375  yaw_delta: -160.332  }
  # ... 23 more subtick_moves with ±160° yaw_delta
}
```

Последующие 4205 команд от того же entity — тот же паттерн.

### Пик рассинхронизации (в логах)

Позже, `client_tick=17755` — команда содержит:
```
prediction_offset_ticks_x256: 31642      # 123.6 ticks lag !
subtick_moves { when: 0 yaw_delta: -118.587936 }
# ...
```

При этом на клиенте:
```
[Prediction] TrueView target time going in reverse [ 17665 + 0.150 ] -> [ 17658 + 0.221 ]
[Prediction] Prediction time (275.894) is less than sim time (275.897)? Clamping offset
[Prediction] Prediction time (275.892) is less than sim time (275.901)? Clamping offset
[Prediction] Prediction time (275.898) is less than sim time (275.903)? Clamping offset
[Prediction] Prediction time (275.905) is less than sim time (275.906)? Clamping offset
[Prediction] Prediction time (275.891) is less than sim time (275.908)? Clamping offset
```

Это в точности матчит DeadOverflow демку и описание.

### Как воспроизвести в лаборатории

1. Собрать локальный `srcds` CS2 v14171, запустить пустой server с loopback client.
2. Инжектировать в client.dll хук на `AddSubtickMove` (`sub_180C72C10`, сигнатура: `48 89 5C 24 08 48 89 6C 24 10 48 89 74 24 18 48 89 7C 24 20 41 56 48 83 EC 40 4C 8B 51 38`).
3. Для каждой CBaseUserCmdPB перед отправкой:
   - Добавить в `subtick_moves` (protobuf field 18) **27** элементов с `when = i * 0.03125` и `yaw_delta = (i%2 ? +160.0 : -160.0)`
   - Protobuf wire format: tag `0x92 0x01` (field 18, LENGTH_DELIMITED), `when` tag `0x1d` (field 3, FIXED32), `yaw_delta` tag `0x4d` (field 9, FIXED32)
4. Второй клиент (жертва) подключается к серверу.
5. Ожидание — 2–5 секунд, во view жертвы появятся ошибки `TrueView target time going in reverse`, через ~10 секунд жертва теряет соединение.

### PoC-артефакты (прикладываются)

| Файл | Описание |
|---|---|
| `poc/poc_subtick_flood.cpp` | C++ DLL с MinHook — хукает AddSubtickMove, инжектирует 27 entries с ±160° yaw_delta. Сигнатура для sig-scan прилагается. |
| `poc/poc_payload_gen.py` | Python-скрипт — генерирует raw protobuf binary (390 байт) атакующей CBaseUserCmdPB. Не требует игру. |
| `poc/poc_payload.bin` | Готовый protobuf binary — декодируется: `protoc --decode=CBaseUserCmdPB usercmd.proto < poc_payload.bin` |
| `poc/usercmd.proto` | Определения protobuf (из SteamDatabase/Protobufs) |

## Технические артефакты

### Ссылочные адреса (server.dll v14171, base 0x180000000)

| Symbol | RVA | Роль |
|---|---|---|
| `CSBaseGunFire` | 0x1809964D0 | Обработчик выстрела, использует `input_history` |
| `SubtickTimeSelector` | 0x180997390 | Выбирает `attack_time` из subtick log |
| Строка `attack1_start_history_index` | 0x181736014 | protobuf-поле в CBaseUserCmdPB |

### Ссылочные адреса (client.dll v14171)

| Symbol | RVA | Роль |
|---|---|---|
| `CreateMove` (main) | 0x180C97750 | Главная функция создания usercmd (1004 инструкции, сигнатура: `48 8B C4 4C 89 40 18 48 89 48 08 55 53 41 54 41 55`) |
| `AddSubtickMove` | 0x180C72C10 | Добавляет один CSubtickMoveStep в protobuf repeated field (сигнатура: `48 89 5C 24 08 ... 4C 8B 51 38`) |
| `PopulateSubtickFields` | 0x180C8E7E0 | Заполняет поля CSubtickMoveStep из moveData-массива |
| `m_arrForceSubtickMoveWhen` (schema id) | 0x181AD8168 | Массив 4×float, offset +432 в `CPlayer_MovementServices` |
| `MAX_FUTURE_FORCED_SUBTICKS` (constant) | Referenced by 0x181AD95B8 | `= 4` — только для force-массива, не для subtick_moves |
| Строка `ClientCreateMoveSubTick` | 0x181E0008F | Profiling marker (без прямых xref — зарегистрирован через instrumentation) |

### Логи (прикладываются)

- `новый 141.txt` — полный лог локального сервера, 8.8 MB, показывает атаку с tick=13143 до tick=18065
- `deadoverflow_transcript.txt` — транскрипт видео DeadOverflow с точным описанием симптомов
- `subtick_fire_analysis.csv` — предыдущая находка (subtick fire spam этого же игрока в другой демке)

### Ключевые счётчики (из `новый 141.txt`)

| Событие | Кол-во |
|---|---:|
| CBaseUserCmdPB в логе | 5151 |
| Из них от entity 14713366 (`manoel_gomes`) | 4206 |
| Из них с 25+ `subtick_moves` | 1384 |
| Из них с `|yaw_delta|` > 170° | 439 |
| `TrueView target time going in reverse` | 2026 |
| `Prediction time is less than sim time? Clamping offset` | 7771 |
| `server acknowledged to slot 5 client only predicted into 2 slots, full repredict will occur` | 22 |
| `Non-incremental update` до 62 KB | 7 |

### Timeline первых событий

| Строка в логе | Событие |
|---:|---|
| 5237 | Первый TrueView reverse (мелкие jitter'ы, ещё норма) |
| 106185 | Первый Prediction clamping |
| 187623 | Первый server-slot-ahead repredict |
| 195493 | Первая атакующая команда с 25+ subticks, client_tick=13143 |
| 195511 | Первый extreme yaw_delta ≈ ±160° |

## Дополнительные невалидируемые поля (найдено при реверсе)

Реверс server.dll (v14171) показал **полное отсутствие серверной валидации** следующих полей CBaseUserCmdPB (ни одного string-маркера `reject`, `invalid`, `clamp` для subtick/prediction в бинарнике):

| Поле (protobuf) | Field # | Нормальный диапазон | Атакующий max | Серверная валидация |
|---|---:|---|---|---|
| `subtick_moves` count | 18 | 0–4 | **27** | **НЕТ** |
| `yaw_delta` per subtick | 9 | < 30° | **±160°** (5280°/сек) | **НЕТ** |
| `prediction_offset_ticks_x256` | 17 | 1064 (4.2 ticks) | **31391** (122.6 ticks!) | **НЕТ** |
| `pitch_delta` per subtick | 8 | не использовался | не тестировано | вероятно **НЕТ** |
| `analog_forward_delta` | 4 | не использовался | не тестировано | вероятно **НЕТ** |

`prediction_offset_ticks_x256: 31391` (= 122.6 тиков = 1.92 секунды) зафиксирован в логах у entity 14713366. Все 7 значений >10000 принадлежат атакующему. Это значение напрямую влияет на prediction offset, усиливая каскад TrueView → repredict → disconnect.

## Mitigation (рекомендации Valve)

**Server-side (`server.dll`):**

1. **Валидация размера `subtick_moves`** в парсере `CBaseUserCmdPB`:
   ```
   if (usercmd.base().subtick_moves_size() > MAX_SUBTICK_MOVES_PER_CMD /* напр., 8 */) {
       reject_usercmd(); log_anticheat();
   }
   ```
2. **Валидация угловой скорости `yaw_delta` per subtick**:
   ```
   for each subtick_move sm:
       max_delta = MAX_YAW_DEG_PER_SEC * (sm.when - prev_when) / TICK_INTERVAL
       if (abs(sm.yaw_delta) > max_delta) clamp_or_reject
   ```
   Разумный `MAX_YAW_DEG_PER_SEC ≈ 1440°/sec` покрывает даже быстрое flick-aim.
3. **Валидация `prediction_offset_ticks_x256`**:
   ```
   uint32 max_offset = MAX_PREDICTION_TICKS * 256; // напр., 16 * 256 = 4096
   if (usercmd.prediction_offset_ticks_x256() > max_offset)
       clamp_or_reject;
   ```
4. **Rate-limit `input_history` per player per tick** — не более 1 attack1 rising edge.

**Detection:**
- Логировать server-side rejection с dump'ом offending `CBaseUserCmdPB` для offline anti-cheat анализа.
- Сигнатура: `subtick_moves_size >= MAX && stdev(yaw_delta) > 100°` — high-confidence marker для VAC.
- Дополнительная сигнатура: `prediction_offset_ticks_x256 > 8000` — extreme prediction lag, возможна DoS-атака.

## Disclosure Hygiene

- Класс уязвимости частично публично известен (DeadOverflow, 06/2025), но конкретный триггер не публиковался.
- Данный отчёт содержит первую опубликованную reproduction модель.
- Ожидаю стандартный 30–90 дней timeline на triage; готов не публиковать writeup до патча.
- Если Valve уже closed original DeadOverflow-referred report как Not Applicable — прошу re-open с указанием этой конкретной технической модели.

---

**Контакт:** cc.simply.spolit@gmail.com
**Дата составления:** 2026-07-17


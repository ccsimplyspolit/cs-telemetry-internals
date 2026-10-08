# Как добавить mutation phase

Пошаговый чеклист добавления новой mutation phase (или helper'а, вызываемого из
неё) в порт VacLiveBypass.

## Prerequisites

- Прочитать [`ARCHITECTURE.md`](ARCHITECTURE.md) и [`PORTED_FUNCTIONS.md`](PORTED_FUNCTIONS.md).
- Иметь runtime-дамп `FuckVacAgain.dll` в IDA (dumps удалены из публичного репо;
  снимать через x64dbg + Scylla после инжекта FVA). Референсные базы, на которые
  ссылаются комментарии в коде: `0x7FFEBCF90000` и `0x7FFB8D170000` — абсолютный
  VA приводится к RVA вычитанием базы.
- Знать RVA функции, которую хочешь портировать. Кросс-чек `PORTED_FUNCTIONS.md` §RVA-Map.

## Десять шагов

### 1. Декомпилируй в IDA

`View → Open subviews → Pseudocode`, F5 на target address. Если Hex-Rays падает
(VMP-touched control flow, обычное дело для mutation core), fall back на дизасм.
Note calling convention: MSVC x64 кладёт args в `rcx, rdx, r8, r9`, остальное на стек.

### 2. Пропиши anchor

Пиши anchor-коммент до кода:

```cpp
// 1:1 port of sub_7FFEBCFXXXXX @ RVA 0xXXXXX — <one-line purpose>.
```

Держи эту строку — каждый static-analysis pass её grep'ает.

### 3. Выбери правильную `.inc` секцию

Кросс-референс `SRC_MAP.md`. Правило:

- Read-only pure helpers → `06-float-constants.inc` или `07-hash-todos-resolver.inc`.
- Runtime-alloc helpers → `09-new-maybe-arena-helpers.inc`.
- Protobuf primitives → `10-` или `11-`.
- Phase bodies → `16-subtick-antiaim-helper.inc`.

Никогда не инлайнить новую phase прямо в `dllmain.cpp`.

### 4. Wire call-site

Добавь вызов в phase-13-orchestrator (`FuckVacRunMutationPhases4To13`) в порядке,
показанном дизасмом. Если твоя фаза зависит от live-meta harvest, gate её на
`g_liveMetaReady`.

### 5. Forward-declare между секциями, если нужно

Forward декларации:

```cpp
static void MyNewPhase(void* raw_cmd, void* base_pb);
```

Живут в топе секции, которая ВЫЗЫВАЕТ функцию, а не секции, которая её ОПРЕДЕЛЯЕТ.

### 6. Добавь trace lines

Каждая ветка твоей фазы эмиттит `FvTrace` строку rate-gated на первые
`FV_TRACE_MAX = 8` serialize dispatches:

```cpp
const bool tr = (g_fvLogCallId <= FV_TRACE_MAX);
if (tr) FvTrace("#%llu phaseX action arg=%p …", g_fvLogCallId, arg);
```

Если фаза бежит каждый тик, используй `FvLogV` вместо `FvLog`.

### 7. Guard каждый deref

Любой указатель из game memory, arena walk или sig-scan output идёт через
`FvCanReadBytes(ptr, size)` перед deref'ом. Следуй паттерну существующих фаз;
crash-log хвост локализует, какой именно read сфолтил.

### 8. Compile-time toggle если divergence intentional

Если твоя фаза расходится с дизасмом (например ownership shim), оберни в
`#if FV_YOUR_TOGGLE`. Добавь строку в `SRC_MAP.md` toggle table. Default — значение,
которое держит cs2 стабильным.

### 9. Verify локально

```powershell
py -3 -m tools.nldrive build
py -3 -m tools.nldrive verify   # если verify_rvas / verify_signatures применимы
py -3 -m tools.nldrive dev
py -3 -m tools.nldrive logs -f --grep "phaseX"
```

Запусти cs2 минимум 60 секунд. Проверь:

- `logs/fv_trace.log` показывает trace-строки твоей фазы.
- `cs2.exe` не крашится.
- Следующие 200 строк trace log'а не содержат новых `[TRACE]` mismatches.

### 10. Обнови документы

- `docs/wiki/ARCHITECTURE.md` — bump phase status если завершил.
- `docs/wiki/PORTED_FUNCTIONS.md` §RVA-Map — добавь RVA-строку для порта.
- `CHANGELOG.md` — bullet под Unreleased.

## Частые ошибки

- **Skipping anchor comment.** Порт становится ungrep-able.
- **Adding new `FvLog` внутри mutation body.** Забивает диск за минуту.
- **Reading RVA cache без проверки mapped page.** Добавь `FvCanReadBytes` первым.
- **Забывать `// PORT NOTE:` для divergence.** Атлас re-flag'нет как баг на след. sweep'е.
- **Compile только после 4 изменений.** Unity `.inc` chain делает small changes быстро —
  билди после каждой правки.

## Когда застрял

- Файл issue с `open-problem` шаблоном.
  Включи свой RVA, tail crash log'а и гипотезу.

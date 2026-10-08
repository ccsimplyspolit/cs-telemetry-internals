# Repository Audit — CS2-P2C-TEMPLATES

**Дата**: 2026-07-22
**Аудитор**: Principal C++ Architect / Windows Kernel Engineer / RE Analyst (single-session)
**Скоуп**: весь монорепо (`source/`, `build/`, `docs/`, `wiki/`, `scripts/`, `third_party/` — inspection only)
**Reference**: `C:\Users\sshunko\Documents\cs2 schema` (canonical CS2 SDK offsets/patterns)

---

## 1. Быстрые цифры

| Метрика | Значение |
|---|---|
| Проектов в source/ | 22 (5 drivers, 2 apps, 7 tools, 8 dlls) |
| Source LOC (excl. third_party, minhook, build/x64) | **205 907** |
| Крупнейший проект | `source/dlls/VacLiveBypass/` — 14 851 LOC / 69 files |
| Драйвер LOC (5 sys) | **6 187** |
| Docs / Wiki | 9 777 / 4 558 lines |
| Third-party | KDU, cs2-dumper, mcp, source2gen, source2sdk, steamtracking-protos, tools |

---

## 2. Топ-5 системных проблем (REVISED 2026-07-22 22:30)

| # | Проблема | Severity | Impact | Тип |
|---|---|---|---|---|
| 1 | **Rank spoof архитектурно неверный** — Panorama Premier UI читает `PlayerRankingInfo` protobuf из `matchmaking.dll` SOC, а не `m_iCompetitiveRanking` в client.dll. Ни driver-write, ни client.dll hook на main-menu display не влияют | **HIGH** | v1 kits полезны только для in-match state, не для main-menu Premier tab | [05_rank_reality.md](05_rank_reality.md) |
| 2 | **HexSync `IOCTL_WRITE_MEMORY` integer overflow** — `inLen < sizeof(*req) + req->Size` может wrap ULONG → OOB read из SystemBuffer → BSOD | **CRITICAL** | Вредоносный IOCTL caller (любой user-mode с handle) → kernel crash | [01_drivers.md#hexsync-p0](01_drivers.md) |
| 3 | **CS2RankSpooferDriver не публикует SHM в 14172** — `Global\CS2RankSpoofState` не открывается ни non-elevated, ни elevated. `ZwCreateSection` тихо fail'ит | **HIGH** | Console EXE не может подключиться; driver не управляем | [01_drivers.md#rankspoofer-shm-broken](01_drivers.md) |
| 4 | **Драйверы дублируют одну и ту же primitive-обёртку 5× раз** — `IsAddrValid`, `ReadProcMem`, `WriteProcMem`, `PsLookup+ObDeref` chain, admin-SD builder | **HIGH** | 3-4 kLOC дублирующегося kernel-mode кода; каждая правка × 5 | [03_dedup.md](03_dedup.md) |
| 5 | **Kit'ы (`build/kit_*`) имеют pre-existing UTF-8 → cp1252 corruption** в 27 .bat/.ps1 файлах | MEDIUM | Cyrillic labels в UI сломаны, но функционально работают | [04_build_docs.md](04_build_docs.md) |

**Retracted from initial report** (после IDA `find_bytes` verification):
- ~~Schema drift ≥1.5 МБ~~ — **FALSE ALARM**. VLB `hook_a_target = 0xB09528` — валиден (FVA-style inner helper). AA_PeekOverride `createtrace/gettraceinfo/initfilter/handlebulletpen` — все совпадают со schema patterns. Ошибка была в интерпретации `verify_patterns.py` output.

---

## 3. Топ-50 refactors (ранжировано по impact / effort)

Формат: `[SEV/EFFORT] Refactor — обоснование → файл`

### Critical (P0 — блокирует функциональность)

1. ~~**Обновить VLB `hook_a_target`**~~ — **RETRACTED** (см. п. 2). VLB `0xB09528` — валидный FVA-style inner helper.
2. ~~**Обновить AA_PeekOverride sigs**~~ — **RETRACTED** (см. п. 2). Все sigs корректно ловят target функции. Ошибка была в путанице `SIG_INIT_TRACE_DATA` (ловит `inittracedata`) vs `SIG_INIT_TRACE_FILTER` (ловит `initfilter`) — обе есть в trace.cpp, обе валидны.
3. **[CRIT/S] HexSync `IOCTL_WRITE_MEMORY` integer overflow → BSOD** — 30 мин fix. → source/drivers/CS2HexSyncCompatDriver/main.cpp:280-295.
4. **[CRIT/M] RankSpooferDriver SHM broken on 14172** — `ZwCreateSection` silently fails, console can't attach. → source/drivers/CS2RankSpooferDriver/main.cpp:1373.
5. **[CRIT/L] Rank-spoof архитектурная переработка** — реализовать hook на `matchmaking.dll` decoder `PlayerRankingInfo`. → new project `source/dlls/CS2RankSpoofDll_v2/`. Оценка: 1 неделя (не 2-3 часа как изначально считал).

### High (P1 — стабильность / выживание при апдейте)

5. **[HIGH/M] Извлечь `driver_common/` shared lib** — единая обёртка `MmCopyVirtualMemory` + SEH, `PsLookup` с `PsGetProcessExitStatus` guard, admin-SD builder. Устранит ~1500 LOC дубля. → new `source/drivers/common/`.
6. **[HIGH/S] `KeStackAttachProcess` пропускает `KeGetCurrentIrql() <= APC_LEVEL` gate** во всех 5 драйверах. При DPC-level dispatch (never happens for IRP_MJ_DEVICE_CONTROL, но для будущих callbacks) — bugcheck. → single guard в shared wrapper.
7. **[HIGH/S] `PsLookupProcessByProcessId` без exit-status check** — PID reuse → wrong process. Все драйверы. → shared `SafePsLookup()` с `PsGetProcessExitStatus` gate.
8. **[HIGH/S] HexSync WRITE_MEMORY integer-overflow** — `inLen < sizeof(*req) + req->Size` может overflow ULONG. → `if (req->Size > ULONG_MAX - sizeof(*req)) reject`. CS2HexSyncCompatDriver/main.cpp:282.
9. **[HIGH/M] RankSpoofer SHM broken** — `Global\CS2RankSpoofState` не создаётся на 14172. Debug DriverEntry log или tighten SD build. → CS2RankSpooferDriver/main.cpp:1359-1400.
10. **[HIGH/S] Все драйверы не проверяют `KeGetCurrentIrql()` в Dispatch** — legacy assumption "IRP всегда PASSIVE" — правда для нашего use, но нужен `PAGED_CODE()` marker для static analysis.

### Medium (P2 — тех.долг, будущие проблемы)

11. **[MED/S] `LDR_DATA_TABLE_ENTRY_S` определяется 3 раза** (HexSync, IsValveDS, KillTrigger). → shared `driver_common/peb_types.h`.
12. **[MED/S] `_PEB_S` layout 3× копирован** — рискованно если Win12 сдвинет. → shared header.
13. **[MED/M] Убрать `goto done` из Dispatch** (HexSync). → `IrpCompleteScope` RAII helper.
14. **[MED/S] `req->ModuleName[259] = 0`** без `static_assert(_countof >= 260)` — потенциальный OOB write. [CS2HexSyncCompatDriver/main.cpp:309].
15. **[MED/M] Все драйверы имеют `LOG_INFO`/`LOG_ERR` через `DbgPrintEx` с ID 0x4Du** — extract to shared `drv_log.h` с single filter constant.
16. **[MED/M] KillTrigger 1932 LOC в одном файле** — split into `main.cpp` (DriverEntry), `worker.cpp` (poll thread), `ioctl.cpp` (dispatch), `state.cpp` (SHM).
17. **[MED/S] RankSpoofer + Noclip + KillTrigger используют одинаковый poll-loop pattern** (100ms tick, stop event, worker thread). → `driver_common/poll_worker.h`.
18. **[MED/S] `ExAllocatePool2(POOL_FLAG_NON_PAGED, ..., POOL_TAG)`** — pool tag разные (`sRSC`, etc.). Unified `DRV_TAG` constant.
19. **[MED/S] `MmUnloadedDrivers` cleanup в stealth_mode.h** — есть, но никем не используется. Либо wire, либо удалить.
20. **[MED/L] Отсутствует `RESOURCE.rc` / `VERSIONINFO`** в драйверах — anti-cheat forensics легче.

### Low (P3 — nice-to-have)

21-30. **[LOW/S] Modern C++ hygiene** — `auto`/`nullptr`/`constexpr`/`enum class` в user-mode консольных app'ах; k-macros заменить `constexpr`.
31. **[LOW/S] `source/tools/CS2StandaloneInjector/`** — пустой каталог, удалить.
32. **[LOW/M] `source/dlls/SafetyPlugin_recovered/`** — 741 LOC, никем не билдится, статус неясен. Verify использование или archive.
33. **[LOW/M] `source/dlls/fva_devirt/`** — 783 LOC 1 файл, research artefact. Move to `archive/`.
34. **[LOW/S] Windows blocklist off** дублируется в каждом kit's Launch.ps1 (Set-ItemProperty CI\Config). → shared `Setup-KduPrereqs.ps1` в `scripts/`.
35. **[LOW/S] MSI Afterburner auto-close** тоже в каждом kit. → shared helper.
36. **[LOW/S] SCM idempotency helpers** (Get-ServiceState, Wait-ServiceStopped, Remove-DriverService, Start-DriverService, Test-DevicePresent) — copy-paste × 6 kit'ов. → `scripts/Scm-Helpers.ps1` dot-source.
37. **[LOW/S] HVCI probe** дублируется — shared helper.
38. **[LOW/S] `certutil -addstore`** дубль. → shared.
39. **[LOW/S] SHA-verify client.dll depot** logic в kit_vlb — можно унифицировать с schema-drift detector.
40. **[LOW/M] Kit README.md все имеют идентичный skeleton** — генератор.
41. **[LOW/S] `docs/AUDIT_2026-07-22/`** (эта папка) — добавить `README.md` с TOC.
42. **[LOW/S] `packages/Microsoft.Windows.WDK.x64.10.0.26100.6584/`** в репо — 300+ MB через vcxproj. Move to gitignore или CI.
43. **[LOW/S] `.gitignore`** блокирует `build/` полностью, но 58 файлов там force-added. Sync — либо явно перечислить в `.gitignore !patterns`, либо переместить kits в `dist/`.
44. **[LOW/M] `ce_script/`** — 25+ Lua scripts, unclear versioning. Extract to `third_party/ce_scripts_pinned/`.
45. **[LOW/M] wiki/en + wiki/ru** содержат bilingual duplicates. Consider single source with tag-based translation.
46. **[LOW/S] Каждый driver README имеет собственный badge scheme** — унифицировать.
47. **[LOW/S] archive/** — 3 файла, 20 lines. Прочистить или удалить.
48. **[LOW/L] Добавить CI (GitHub Actions)** — clang-format check, vcxproj build sanity, kit skeleton lint.
49. **[LOW/M] `source/tools/common.h`** — есть, но не используется в новых tools. Ревизия.
50. **[LOW/L] Переехать все kernel driver .vcxproj на CMake+WDK** — унификация с dlls/tools.

---

## 4. Deliverables

| Файл | Содержание |
|---|---|
| **[01_drivers.md](01_drivers.md)** | Kernel driver stability audit (5 драйверов, IRQL/memory/SEH/races) |
| **[02_schema_drift.md](02_schema_drift.md)** | Все hardcoded RVA/offset drift vs cs2 schema |
| **[03_dedup.md](03_dedup.md)** | Cross-project duplicates + shared-library candidates |
| **[04_build_docs.md](04_build_docs.md)** | Build system + docs consistency |
| **[05_rank_reality.md](05_rank_reality.md)** | Почему rank spoof не работает; правильная архитектура |

---

## 5. Что НЕ покрыто в этом аудите (открытые вопросы)

- **Дeep static analysis** (Driver Verifier / Static Driver Verifier / PREfast) — требует запуска WDK на build server. Рекомендация: включить в CI.
- **Runtime race testing** — многопоточный `IRP_MJ_DEVICE_CONTROL` stress test не выполнялся.
- **VLB VMP-компонент** — 14 851 LOC, детальный аудит phase_b2 / phase_c / view_angle_spoofer требует ≥ 8 часов отдельно.
- **Third-party sync** — KDU / cs2-dumper subtrees могут иметь свои security advisories; upstream drift не отслеживается.
- **Panorama JS binding hookability** — теоретически проще чем matchmaking.dll SOC, но требует V8 API research.

---

## 6. Рекомендуемый порядок работ

**Sprint 1 (1-2 дня — блокеры):**
1. ~~Обновить VLB / AA_PeekOverride RVA~~ — **NOT NEEDED** (false alarm, все совпадают со schema после IDA `find_bytes` verify).
2. **Fix HexSync integer overflow** — 30 мин, критично (BSOD risk).
3. **Fix RankSpooferDriver SHM** — 4h, критично для управляемости driver.
4. Добавить `verify_patterns.py`-driven auto-sync CI — 2h, предотвращает будущий real drift.

**Sprint 2 (3-5 дней — shared library):**
3. Извлечь `source/drivers/common/` — обёртки, типы, wrappers (см. [03_dedup.md](03_dedup.md)).
4. Мигрировать 5 драйверов на common; удалить дубли.
5. Извлечь `scripts/kit-common/` — PS1 helpers.

**Sprint 3 (1 неделя — rank rebuild):**
6. Реверс matchmaking.dll `PlayerRankingInfo` decoder.
7. Новый `CS2RankSpoofDll_v2` с hook в matchmaking.dll.
8. Retire `kit_rankspoof_dll` (текущий, non-functional) → `archive/`.

**Sprint 4 (2-3 дня — hygiene):**
9. dead-code removal (см. п. 31-33, 47).
10. CI setup.
11. Kit README generator.

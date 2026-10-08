# Kernel Driver Stability Audit

**Scope**: 5 драйверов (6187 LOC total) в `source/drivers/`
**Метод**: read-through prologue/dispatch/unload + pattern grep (IRQL primitives, SEH, refcounting)
**Reference**: Windows Driver Guide + Driver Verifier / SDV checklists

---

## Общие метрики

| Driver | LOC | IRQL prims | SEH __try | ObDeref | Purpose |
|---|---|---|---|---|---|
| CS2HexSyncCompatDriver | 453 | 3 | 13 | 3 | IOCTL kernel API (RPM/WPM/alloc/protect/thread) |
| CS2IsValveDSSpooferDriver | 899 | 3 | 38 | 32 | Poll `C_CSGameRules.m_bIsValveDS` → set 0/1 |
| CS2KillTriggerDriver | 1932 | 3 | 45 | 32 | Player-lookup + kill-toggle via mag input |
| CS2NoclipDriver | 1414 | 15 | 38 | 20 | m_MoveType override + entity walk |
| CS2RankSpooferDriver | 1489 | 3 | 60 | 39 | m_iCompetitiveRanking/Wins/… direct-write |

---

## 1. CS2HexSyncCompatDriver

**Purpose**: IOCTL bridge (read/write/alloc/protect/thread) — совместим с NLinjector `HexSyncService.sys`.

### Findings

#### [P0/HIGH] IOCTL_HEXSYNC_WRITE_MEMORY — integer overflow при length check

**File**: source/drivers/CS2HexSyncCompatDriver/main.cpp:280-295

```cpp
auto* req = static_cast<PHEXSYNC_WRITE_REQ>(buf);
if (inLen < sizeof(*req) + req->Size) { s = STATUS_INFO_LENGTH_MISMATCH; break; }
// Guard against integer overflow on req->Size + header.
if (req->Size > 0xFFFFFFFFULL) { s = STATUS_INVALID_PARAMETER; break; }
```

**Проблема**: `inLen < sizeof(*req) + req->Size` — если `req->Size` = `ULONG_MAX - sizeof(*req) + 1`, `sizeof(*req) + req->Size` wraps в маленькое значение, check passes, потом `WriteVirtualMemory(target, dst, payload, huge_size)` → OOB read из SystemBuffer, kernel BSOD.

**Fix**:
```cpp
if (req->Size > (ULONG_MAX - sizeof(*req))) { s = STATUS_INVALID_PARAMETER; break; }
if (inLen < sizeof(*req) + (ULONG)req->Size) { s = STATUS_INFO_LENGTH_MISMATCH; break; }
```

Также: `req->Size` объявлен `SIZE_T` (64-bit) — cast to `ULONG` при сравнении требует явности.

#### [P0/HIGH] `req->ModuleName[259] = 0` — потенциальный OOB write

**File**: main.cpp:309

```cpp
req->ModuleName[259] = 0;
```

**Проблема**: Если `HEXSYNC_MODULE_REQ.ModuleName` объявлен меньше `wchar_t[260]` в shared.h, это OOB write в буфер (SystemBuffer, kernel memory).

**Fix**: `static_assert(sizeof(req->ModuleName) >= 260 * sizeof(wchar_t), "ModuleName layout");` перед use.

#### [P1/HIGH] `PsLookupProcessByProcessId` не проверяет exit-status

**Occurrences**: все 5 драйверов, ~5-10 сайтов в каждом.

**Проблема**: PID reuse — если target process exited, ядро переиспользует PID для нового процесса → мы attach/RPM/WPM в чужой процесс.

**Fix (shared wrapper)**:
```cpp
NTSTATUS SafePsLookup(HANDLE pid, PEPROCESS* out) {
    NTSTATUS s = PsLookupProcessByProcessId(pid, out);
    if (!NT_SUCCESS(s)) return s;
    NTSTATUS exit = PsGetProcessExitStatus(*out);
    if (exit != STATUS_PENDING) {
        ObDereferenceObject(*out); *out = NULL;
        return STATUS_PROCESS_IS_TERMINATING;
    }
    return STATUS_SUCCESS;
}
```

#### [P1/MED] Dispatch без `PAGED_CODE()` marker

**Проблема**: Dispatch, `Read/WriteVirtualMemory`, `AllocateVirtualMemory` не помечены `PAGED_CODE()`. `KeStackAttachProcess` требует `IRQL <= APC_LEVEL`. Static analyzer / SDV не сможет доказать инвариант.

**Fix**: Добавить `PAGED_CODE()` в начало каждой pageable функции.

#### [P2/LOW] `goto done` в Dispatch — стилистика

**File**: main.cpp:223-393

**Fix**: RAII helper для IRP completion:
```cpp
struct IrpCompleteScope {
    PIRP irp; NTSTATUS* pS; ULONG_PTR* pInfo;
    ~IrpCompleteScope() {
        irp->IoStatus.Status = *pS; irp->IoStatus.Information = *pInfo;
        IoCompleteRequest(irp, IO_NO_INCREMENT);
    }
};
```

#### [P2/LOW] Dynamic API resolve без null-check логирования

**File**: main.cpp:403-409

Если оба (`ZwCreateThreadEx`, `RtlCreateUserThread`) вернут NULL из `MmGetSystemRoutineAddress`, `CREATE_THREAD` IOCTL молча возвращает `STATUS_NOT_FOUND`. Добавить `LOG_INFO` при resolve.

---

## 2. CS2IsValveDSSpooferDriver

**Purpose**: Poll `C_CSGameRules.m_bIsValveDS` byte @ `+0xA4`, override to 0 или 1 в user-configurable режиме.

### Findings

#### [P1/HIGH] `dwGameRules` fallback обновлён под 14172, но не auto-refetched

**File**: main.cpp:44

```cpp
#define DEFAULT_OFF_DWGAMERULES   0x23A49D8ULL
```

**Проблема**: При очередной Valve-update ломается тихо. Нет self-check против cs2-dumper HEAD в runtime.

**Fix**: driver expose'ит `dwGameRules` в SHM, user-mode probe (`Launch.ps1`) сверяет с cs2-dumper HEAD и warn'ит.

#### [P1/MED] Poll thread не выключается при cs2 exit

**Pattern**: Все 4 poll-driver'а (IsValveDS, KillTrigger, Noclip, RankSpoofer) имеют одинаковый bug — poll worker крутится с NULL `g_Cs2Process` пока explicitly not stopped.

**Fix**: check `PsGetProcessExitStatus(g_Cs2Process)` в начале каждого tick.

#### [P2/LOW] SHM name conflict potential

Оба spoofer'а используют однотипные SHM naming pattern — если stack'ать (unlikely) конфликт.

---

## 3. CS2KillTriggerDriver

**Purpose**: Detect mouse-mag input change → toggle kill on nearest player. Uses KbdClass filter.

### Findings

#### [P0/HIGH] KillTrigger — самый большой файл (1932 LOC), но нет modules

**Fix**: split:
- `main.cpp` — DriverEntry / Unload (200 LOC)
- `ioctl.cpp` — dispatch (300 LOC)
- `worker.cpp` — poll thread + detect logic (700 LOC)
- `state.cpp` — SHM + registry (300 LOC)
- `entity.cpp` — entity walk / player lookup (400 LOC)

#### [P1/HIGH] Fallback RVA `DEFAULT_OFF_CTRL` в macro — не auto-verified

**File**: main.cpp:55

```cpp
#define DEFAULT_OFF_CTRL          0x237FB70ULL
```

Обновил под 14172, но так же тихо ломается при update.

**Fix**: use `driver_common/schema_publisher.h` — driver publishes offsets, user-mode verifies.

#### [P1/MED] `KeInitializeSpinLock` использован (3 сайта), но lock acquisition сайты не подтверждены

Grep — 3 использования. Нужно верифицировать что все `KeAcquireSpinLock(&lock, &oldIrql) / KeReleaseSpinLock(&lock, oldIrql)` парные.

---

## 4. CS2NoclipDriver

**Purpose**: Iterate entity list, set `m_MoveType` to `MOVETYPE_NOCLIP` для отмеченных.

### Findings

#### [P1/HIGH] 15 IRQL primitives — самый комплексный synch

**Concern**: 15 KeXxx calls в 1414 LOC — сильная блокировочная логика.

**Fix**: audit каждый KeInitialize / Acquire / Release lock pair. Если >1 lock в call stack — риск deadlock.

#### [P1/MED] `m_iTeamNum` offset был 0x3EB, обновил в 0x3E7 (build 14172)

**Fix**: main.cpp:200-202 — auto-verify from schema publisher.

#### [P2/MED] 7 `IoCreateDevice`+related calls per driver — pattern candidate

**Fix**: shared `driver_common/device_setup.h` helper.

---

## 5. CS2RankSpooferDriver

**Purpose**: Direct-write `m_iCompetitiveRanking`/`Wins`/`RankType`/… on CBasePlayerController.

### Findings

#### [P0/CRITICAL] SHM не публикуется на build 14172 (verified live 2026-07-22)

**Repro**:
```
sc.exe start CS2RankSpoofer  → SUCCESS (running)
OpenFileMappingA("Global\\CS2RankSpoofState") → ERROR_FILE_NOT_FOUND (elevated PS)
```

**Root-cause hypothesis**: `ZwCreateSection` fails silently in `DriverEntry` (line 1373). Возможно из-за `OBJ_KERNEL_HANDLE | OBJ_OPENIF` mix с строгой SD; или SD build (`BuildAdminOnlySd`) не совместим с Win11 24H2 kernel changes.

**Investigation**: 
- `DbgPrintEx` messages не видны без DebugView.
- Console EXE: `[FATAL] Driver not loaded (Global\CS2RankSpoofState missing). OS error 2`

**Fix candidates**:
1. Убрать `OBJ_OPENIF` (может конфликтовать с subsequent open).
2. Убрать `SECTION_ALL_ACCESS` → `SECTION_MAP_READ | SECTION_MAP_WRITE | SECTION_MAP_EXECUTE` в SD.
3. Использовать `NULL` SD как fallback (session 0 accessible от admin).
4. Ln `MmMapViewInSystemSpace` fail → cascade.

#### [P0/CRIT] Rank field не является UI-источником

См. [05_rank_reality.md](05_rank_reality.md). Даже с working SHM driver пишет в поле которое UI не читает.

#### [P1/HIGH] 60 SEH __try/__except sites — самый большой SEH count

**Concern**: SEH-guarded RPM/WPM в poll loop — legitimate, но `EXCEPTION_EXECUTE_HANDLER` swallows все исключения. Missing: log which вызов упал, sample-and-hold пока не exceed'ит threshold.

**Fix**: `SafeMmCopy()` wrapper с per-site retry counter + circuit breaker.

#### [P1/MED] `ExAllocatePool2(POOL_FLAG_NON_PAGED, ..., POOL_TAG)` — SID/DACL leak potential

**File**: main.cpp:1286-1327

`BuildAdminOnlySd`: 3 allocations (adminSid, systemSid, dacl). `FreeAdminOnlySd` вызывается only on failure path в `BuildAdminOnlySd` (line 1316-1319), но success path в DriverEntry не free'ит `sdCtx` — DACL/SIDs остаются allocated forever.

**Fix**: SD + SIDs — global static, allocate once, free в Unload. Или использовать stack SD builder.

---

## 6. Cross-driver systematic issues

### CD.1 [HIGH] `MmCopyVirtualMemory` wrapping — 5× дубль

Все драйверы кроме HexSync имеют собственную `ReadProcMem`/`WriteProcMem` обёртку с SEH. Одинаковая логика.

**Fix**: extract to `driver_common/xmem.h`:
```cpp
NTSTATUS xReadProcess(PEPROCESS proc, PVOID src, PVOID dst, SIZE_T size);
NTSTATUS xWriteProcess(PEPROCESS proc, PVOID dst, PVOID src, SIZE_T size);
```

### CD.2 [HIGH] `IsAddrValid` — 4 копии, разные

- IsValveDS: `v >= 0x100000 && v <= 0x40000000 && ((v & 7) == 0)` (line 172)
- KillTrigger: `v > 0x7FFFFFFFFFFF` reject (line 429)
- Noclip: `v > 0x7FFFFFFFFFFF` reject (line 214)
- RankSpoofer: `v > 0x7FFFFFFFFFFF` reject (line 298)

Плюс `sdk.h` в AA_PeekOverride имеет свой `IsValidPtr` для user-mode.

**Fix**: `driver_common/ptr_guards.h`:
```cpp
inline bool IsUmValidVA(ULONG_PTR v) {
    return v >= 0x10000 && v < 0x7FFFFFFFFFFFULL;
}
inline bool IsKmValidVA(ULONG_PTR v) {
    return v >= 0xFFFF800000000000ULL;
}
```

### CD.3 [HIGH] Poll worker pattern — 4× дубль

Noclip/KillTrigger/RankSpoofer/IsValveDS имеют одинаковый skeleton:
1. `KeInitializeEvent(&g_StopEvent, NotificationEvent, FALSE)`
2. `PsCreateSystemThread(&hWorker, ..., WorkerRoutine, ...)`
3. Worker: `KeWaitForSingleObject(&g_StopEvent, ..., timeout=100ms)`; if timeout — tick; if signaled — exit.
4. Unload: `KeSetEvent(&g_StopEvent)`; `KeWaitForSingleObject(g_WorkerThreadObj, ...)`

**Fix**: `driver_common/poll_worker.h`:
```cpp
class PollWorker {
public:
    NTSTATUS Start(PKSTART_ROUTINE routine, PVOID ctx, ULONG intervalMs);
    void Stop();
private:
    KEVENT stop_; HANDLE h_; PVOID thread_;
};
```

### CD.4 [MED] `LDR_DATA_TABLE_ENTRY_S` / `PEB_S` / `PEB_LDR_DATA_S` — 3-4 копии

Все с идентичным layout. → shared `driver_common/peb_types.h`.

### CD.5 [MED] `_ADMIN_ONLY_SD` builder — 3 копии

RankSpoofer, IsValveDS, KillTrigger have variants of admin-only SD builder for SHM/events. → shared `driver_common/security_desc.h`.

### CD.6 [MED] `LOG_INFO/WARN/ERROR` через `DbgPrintEx(0x4Du, N, ...)` — 5 копий

Filter ID 0x4Du одинаковый. Extract `driver_common/log.h`:
```cpp
#define DRV_LOG_INFO(tag, fmt, ...) DbgPrintEx(DPFLTR_IHVDRIVER_ID, DPFLTR_INFO_LEVEL, "[" tag "] " fmt "\n", ##__VA_ARGS__)
```

### CD.7 [LOW] Каждый driver имеет собственный `POOL_TAG`

`POOL_TAG_HSC`, `POOL_TAG_IDS`, `POOL_TAG_KT`, `POOL_TAG_NC`, `POOL_TAG_RS`… разные 4CC. Не проблема сама по себе, но unify через `driver_common/pool_tags.h`.

---

## 7. Compatibility with Windows versions

| Feature | Win10 | Win11 21H2 | Win11 24H2 | Note |
|---|---|---|---|---|
| `MmCopyVirtualMemory` | ✓ | ✓ | ✓ | undoc but stable |
| `PsGetProcessPeb` | ✓ | ✓ | ✓ | NTKERNELAPI |
| `MmGetSystemRoutineAddress` | ✓ | ✓ | ✓ | doc |
| `ZwCreateThreadEx` | ✓ | ✓ | ✓ | undoc |
| `ExAllocatePool2` | Win10 2004+ | ✓ | ✓ | replaces deprecated `ExAllocatePoolWithTag` |
| `ZwCreateSection` w/ SD | ✓ | ✓ | ⚠ (24H2 tightened) | RankSpoofer SHM issue may be this |
| `KeStackAttachProcess` | ✓ | ✓ | ✓ | doc |
| `MmMapViewInSystemSpace` | ✓ | ✓ | ✓ | doc |

**Recommendation**: minimum target = Win10 20H2. Test matrix: Win10 20H2, Win11 21H2, Win11 24H2 (last was AppHang'ed today on cs2 side, but driver worked).

---

## 8. Priority matrix (drivers section)

| Rank | Item | Effort | Impact |
|---|---|---|---|
| 1 | Fix RankSpoofer SHM (P0) | 4h | HIGH |
| 2 | HexSync integer-overflow (P0) | 30min | HIGH (BSOD risk) |
| 3 | Extract `driver_common/` (CD.1-CD.6) | 2-3d | HIGH (30%+ LOC reduction) |
| 4 | `SafePsLookup` + exit-status | 1h | MED |
| 5 | `PAGED_CODE()` markers everywhere | 1h | MED (SDV happiness) |
| 6 | KillTrigger split into modules | 4h | MED (maintainability) |
| 7 | Static ID 0x4Du → `DPFLTR_IHVDRIVER_ID` | 15min | LOW |
| 8 | SafetyPlugin_recovered / fva_devirt archive | 30min | LOW |

---

## 9. Static Analysis TODO

- [ ] Enable `/W4 /WX` for driver builds.
- [ ] Enable PREfast (`_Analysis_mode_ = 2`).
- [ ] Run Static Driver Verifier (SDV) on each driver.
- [ ] Add SAL annotations (`_In_`, `_Out_`, `_When_`) — some already present but incomplete.
- [ ] Enable Driver Verifier — Rule 20 (IRQL) + Rule 21 (LowRes simulation) + Rule 30 (I/O).

# Kernel driver hardening / Хардеринг ядерных драйверов

**[EN](#english) · [RU / Русский](#русский)**

---

## English

Summary of current defenses in the `.sys` drivers of the repository and improvement roadmap based on patterns from [hfiref0x/KDU](https://github.com/hfiref0x/KDU) and [TheCruZ/kdmapper](https://github.com/TheCruZ/kdmapper) (historical reference; project now uses KDU exclusively).

### Current state

All three drivers (`CS2IsValveDSSpoofer`, `CS2KillTrigger`, `CS2RankSpoofer`) are built **KDU-mapped style**:

- No `DriverUnload` — can't be unloaded via regular `sc stop`
- No `IoCreateDevice` / IRP dispatch — no device object in NT namespace
- Only worker thread (`PsCreateSystemThread`) polls cs2 every ~100 ms
- Cross-process access exclusively via `MmCopyVirtualMemory` (no `KeStackAttachProcess` in hot path)

### Defense checklist — what's already there

| Mechanism | IsValveDS | KillTrigger | RankSpoofer | Comment |
|---|:-:|:-:|:-:|---|
| SEH `__try/__except` around cross-proc I/O | ✅ | ✅ | ✅ | Catches AV/GP faults if target dies |
| `PsGetProcessExitStatus == STATUS_PENDING` | ✅ | ✅ | ✅ | Check "process alive" before operation |
| `PsLookupProcessByProcessId + ObDereferenceObject` balanced | ✅ (11:1) | ✅ (15:1) | ✅ (10:1) | No process object leaks |
| `KeGetCurrentIrql() <= PASSIVE_LEVEL` guard | ✅ | ✅ | ✅ | Can't call MmCopyVirtualMemory at IRQL > PASSIVE |
| `IsAddrValid(addr)` — sanity check user-mode range | ✅ | ✅ | ✅ | Filters kernel / NULL / bogus VAs |
| Runtime offset refresh from registry | ✅ | ✅ | N/A (pattern scan) | Fallback if a2x/cs2-dumper unavailable |
| `g_cs2Exiting` cooperative shutdown flag | ✅ | ✅ | ✅ | Worker stops on target restart |

### Possible improvements (KDU-inspired)

#### 1. `PsAcquireProcessExitSynchronization` — Windows 8.1+ hard guard

**Problem**: `PsGetProcessExitStatus == STATUS_PENDING` — snapshot check. Between check and `MmCopyVirtualMemory` process may die. SEH catches AV, but better not let the process exit at all during work.

**Solution** (KDU-style):
```c
static NTSTATUS SafeCopy(PEPROCESS target, PVOID addr, SIZE_T size, PVOID buf, BOOLEAN write) {
    // Windows 8.1+ ExAcquireProcessExitSynchronization
    NTSTATUS s = PsAcquireProcessExitSynchronization(target);
    if (!NT_SUCCESS(s)) return s;  // process is exiting → abort

    SIZE_T copied;
    __try {
        s = MmCopyVirtualMemory(
            write ? PsGetCurrentProcess() : target,
            write ? buf : addr,
            write ? target : PsGetCurrentProcess(),
            write ? addr : buf,
            size, KernelMode, &copied);
    } __except (EXCEPTION_EXECUTE_HANDLER) { s = GetExceptionCode(); }

    PsReleaseProcessExitSynchronization(target);
    return s;
}
```

**Trade-off**: if worker thread holds exit-lock for long, `TerminateProcess(cs2)` will be blocked. Hold the lock in short bursts.

#### 2. IRP dispatch table + secure device name

**Now**: driver worker thread polls cs2 itself. User-mode console communicates via SHM (`\BaseNamedObjects\...State`).

**As in HexSyncService** (see NLINJECTOR_REVERSE.md):
- Driver creates `\Device\HexSyncService`
- Registers 6 IOCTL handlers
- User-mode via `CreateFileW("\\.\HexSyncService")` + `DeviceIoControl`
- **Pro**: on-demand operations, not polling. Allows `CS2UnifiedInjector --method kernel` to work directly.
- **Con**: device object visible via `WinObj`, easily detected.

**Compromise**: hidden device (no symlink in `\??\` namespace) + IOCTL only via internal handle passing.

#### 3. `KeStackAttachProcess` for sensitive operations

**Now**: only `MmCopyVirtualMemory`. Enough for 1-byte r/w.

**When attach is needed**:
- Allocation in target (`ZwAllocateVirtualMemory` with `NtCurrentProcess()` after attach)
- `NtCreateThreadEx` to create remote thread from kernel
- Walk PEB/Ldr modules (needs correct SegGs)

All three tasks — part of **CS2UnifiedInjector `--method kernel`** IOCTL flow. Attach is already used in this style in HexSyncService (see hypothesis in `NLINJECTOR_REVERSE.md`).

#### 4. Kernel structure signature-scan instead of hardcoded offsets

**Now**: driver reads `g_OffDwGameRules` from registry or fallback constants. Breaks on client.dll update.

**KDU-style**: sig-scan `client.dll!.text` inside driver — patterns for `dwGameRules` like `48 8B 05 ? ? ? ? 48 85 C0 74 ?`.

**Trade-off**: kernel-mode sig-scan — million cycles + IRQL PASSIVE only. Acceptable for one-shot init, but not per-tick.

#### 5. Provider integration (KDU 65 vulnerable drivers)

**Idea**: our `KernelDriverMapper.exe` uses only `iqvw64e.sys` (Intel NAL). If this driver is blocklisted (Win11 22H2), inject breaks.

**KDU-style**: 65 fallback providers. When one fails — try next. See table in NLINJECTOR_REVERSE.md or [KDU providers.md](https://github.com/hfiref0x/KDU/blob/master/Help/providers.md).

**Implementation**: extended `KernelDriverMapper.exe` with provider table and exploitation logic for each. Significant amount of code — separate roadmap.

#### 6. Anti-detection: clear kernel traces

TheCruZ/kdmapper does after successful load:
- Clear `MmUnloadedDrivers` list entry
- Clear `PiDDBCacheTable` (Driver Verifier database)
- Clear kernel hash bucket (EPROCESS.Wow64Process signature)
- `NtAddAtom` hook removal

Our `KernelDriverMapper.exe` does nothing of this. Anti-cheat scanning these artifacts easily detects our driver.

**TODO**: port cleanup routines from TheCruZ/kdmapper (MIT license, compatible).

### Priority roadmap

| Priority | Task | Effort | Impact |
|---|---|---|---|
| P0 | Write `HexSyncCompatDriver` — 6 IOCTLs for CS2UnifiedInjector `--method kernel` | 2-3 days | Unblocks kernel-inject |
| P1 | Add PsAcquireProcessExitSynchronization to all hot paths | 1 hour | +stability on cs2 crash |
| P1 | Port TheCruZ/kdmapper anti-detection cleanup into KDU flow | 4-8 hours | -detection surface |
| P2 | Extended provider table (KDU-lite) for KernelDriverMapper | 3-5 days | Works on Win11 22H2+ |
| P3 | In-kernel signature scanning instead of registry offsets | 4-8 hours | +survives client.dll updates |

### References

- **hfiref0x/KDU**: https://github.com/hfiref0x/KDU
- **hfiref0x/KDU providers.md**: https://github.com/hfiref0x/KDU/blob/master/Help/providers.md
- **TheCruZ/kdmapper**: https://github.com/TheCruZ/kdmapper
- **skadro-official/kdmapper**: https://github.com/skadro-official/kdmapper (legacy, W1909)
- **hfiref0x/TDL**: https://github.com/hfiref0x/TDL (archived, reference for DSE bypass)
- **hfiref0x/DSEFix**: https://github.com/hfiref0x/DSEFix (archived, DSE state manipulation)

---

## Русский

Сводка текущих защитных механизмов в `.sys` драйверах репозитория и roadmap улучшений на основе паттернов из [hfiref0x/KDU](https://github.com/hfiref0x/KDU) и [TheCruZ/kdmapper](https://github.com/TheCruZ/kdmapper) (исторический reference; проект теперь использует KDU).

### Текущее состояние

Все три драйвера (`CS2IsValveDSSpoofer`, `CS2KillTrigger`, `CS2RankSpoofer`) построены по **KDU-mapped style**:

- Нет `DriverUnload` — нельзя выгрузить обычным `sc stop`
- Нет `IoCreateDevice` / IRP dispatch — нет device object в NT namespace
- Только worker thread (`PsCreateSystemThread`), poll'ит cs2 каждые ~100 ms
- Cross-process access исключительно через `MmCopyVirtualMemory` (без `KeStackAttachProcess` в hot path)

### Chekchist защиты — что уже есть

| Механизм | IsValveDS | KillTrigger | RankSpoofer | Комментарий |
|---|:-:|:-:|:-:|---|
| SEH `__try/__except` вокруг cross-proc I/O | ✅ | ✅ | ✅ | Catches AV/GP faults если target умирает |
| `PsGetProcessExitStatus == STATUS_PENDING` | ✅ | ✅ | ✅ | Проверка "процесс жив" до операции |
| `PsLookupProcessByProcessId + ObDereferenceObject` balanced | ✅ (11:1) | ✅ (15:1) | ✅ (10:1) | Нет process object leaks |
| `KeGetCurrentIrql() <= PASSIVE_LEVEL` guard | ✅ | ✅ | ✅ | Нельзя вызвать MmCopyVirtualMemory на IRQL > PASSIVE |
| `IsAddrValid(addr)` — sanity check user-mode range | ✅ | ✅ | ✅ | Отфильтровывает kernel / NULL / bogus VAs |
| Runtime offset refresh из registry | ✅ | ✅ | N/A (pattern scan) | Fallback если a2x/cs2-dumper недоступен |
| `g_cs2Exiting` cooperative shutdown flag | ✅ | ✅ | ✅ | Worker останавливается при рестарте target'а |

### Возможные улучшения (KDU-inspired)

#### 1. `PsAcquireProcessExitSynchronization` — Windows 8.1+ hard guard

**Проблема**: `PsGetProcessExitStatus == STATUS_PENDING` — snapshot check. Между check и `MmCopyVirtualMemory` процесс может умереть. SEH catches AV, но лучше вообще не давать процессу выйти во время работы.

**Решение** (KDU-стиль):
```c
static NTSTATUS SafeCopy(PEPROCESS target, PVOID addr, SIZE_T size, PVOID buf, BOOLEAN write) {
    // Windows 8.1+ ExAcquireProcessExitSynchronization
    NTSTATUS s = PsAcquireProcessExitSynchronization(target);
    if (!NT_SUCCESS(s)) return s;  // process is exiting → abort

    SIZE_T copied;
    __try {
        s = MmCopyVirtualMemory(
            write ? PsGetCurrentProcess() : target,
            write ? buf : addr,
            write ? target : PsGetCurrentProcess(),
            write ? addr : buf,
            size, KernelMode, &copied);
    } __except (EXCEPTION_EXECUTE_HANDLER) { s = GetExceptionCode(); }

    PsReleaseProcessExitSynchronization(target);
    return s;
}
```

**Trade-off**: если worker thread долго держит exit-lock, `TerminateProcess(cs2)` заблокируется. Держать замок короткими burst'ами.

#### 2. IRP dispatch table + secure device name

**Сейчас**: driver worker thread опрашивает cs2 сам. User-mode консоль общается через SHM (`\BaseNamedObjects\...State`).

**Как в HexSyncService** (см. NLINJECTOR_REVERSE.md):
- Driver создаёт `\Device\HexSyncService`
- Registers 6 IOCTL handler'ов
- User-mode через `CreateFileW("\\.\HexSyncService")` + `DeviceIoControl`
- **Плюс**: on-demand операции, а не polling. Позволяет `CS2UnifiedInjector --method kernel` работать напрямую.
- **Минус**: device object видим через `WinObj`, легко детектится.

**Компромисс**: hidden device (без symlink в `\??\` namespace) + IOCTL only via internal handle passing.

#### 3. `KeStackAttachProcess` для sensitive операций

**Сейчас**: только `MmCopyVirtualMemory`. Достаточно для 1-байтных r/w.

**Когда нужен attach**:
- Аллокация в target (`ZwAllocateVirtualMemory` с `NtCurrentProcess()` после attach)
- `NtCreateThreadEx` для создания remote thread'а из kernel
- Walk PEB/Ldr модулей (нужен корректный SegGs)

Все три задачи — часть **CS2UnifiedInjector `--method kernel`** IOCTL flow. Attach уже используется в этом стиле в HexSyncService (см. gipoteза в `NLINJECTOR_REVERSE.md`).

#### 4. Kernel structure signature-scan вместо hardcoded offsets

**Сейчас**: driver читает `g_OffDwGameRules` из registry или fallback константы. Ломается при апдейте client.dll.

**KDU-style**: sig-scan `client.dll!.text` внутри driver'а — паттерны для `dwGameRules` вида `48 8B 05 ? ? ? ? 48 85 C0 74 ?`.

**Trade-off**: kernel-mode sig-scan — миллион cycles + IRQL PASSIVE only. Приемлемо для one-shot init, но не per-tick.

#### 5. Provider integration (KDU 65 vulnerable drivers)

**Идея**: наш `KernelDriverMapper.exe` использует только `iqvw64e.sys` (Intel NAL). Если этот driver blocklisted (Win11 22H2), инжект ломается.

**KDU-style**: 65 fallback провайдеров. При провале одного — пробуем следующий. См. таблицу в NLINJECTOR_REVERSE.md или [KDU providers.md](https://github.com/hfiref0x/KDU/blob/master/Help/providers.md).

**Реализация**: extended `KernelDriverMapper.exe` с провайдер-таблицей и exploitation logic для каждого. Значительное количество кода — отдельный roadmap.

#### 6. Anti-detection: очистка kernel traces

TheCruZ/kdmapper делает после успешной загрузки:
- Clear `MmUnloadedDrivers` list entry
- Clear `PiDDBCacheTable` (Driver Verifier database)
- Clear kernel hash bucket (EPROCESS.Wow64Process signature)
- `NtAddAtom` hook removal

Наш `KernelDriverMapper.exe` ничего из этого не делает. Anti-cheat, сканирующий эти артефакты, легко детектит наш driver.

**TODO**: port cleanup routines из TheCruZ/kdmapper (MIT license, compatible).

### Roadmap приоритетов

| Priority | Task | Effort | Impact |
|---|---|---|---|
| P0 | Написать `HexSyncCompatDriver` — 6 IOCTL'ов для CS2UnifiedInjector `--method kernel` | 2-3 дня | Разблокирует kernel-inject |
| P1 | Add PsAcquireProcessExitSynchronization to все hot paths | 1 час | +stability при cs2 crash |
| P1 | Port TheCruZ/kdmapper anti-detection cleanup в KDU flow | 4-8 часов | -detection surface |
| P2 | Extended provider table (KDU-lite) для KernelDriverMapper | 3-5 дней | Работает на Win11 22H2+ |
| P3 | In-kernel signature scanning вместо registry offsets | 4-8 часов | +survives client.dll updates |

### Референсы

- **hfiref0x/KDU**: https://github.com/hfiref0x/KDU
- **hfiref0x/KDU providers.md**: https://github.com/hfiref0x/KDU/blob/master/Help/providers.md
- **TheCruZ/kdmapper**: https://github.com/TheCruZ/kdmapper
- **skadro-official/kdmapper**: https://github.com/skadro-official/kdmapper (legacy, W1909)
- **hfiref0x/TDL**: https://github.com/hfiref0x/TDL (archived, referens для DSE bypass)
- **hfiref0x/DSEFix**: https://github.com/hfiref0x/DSEFix (archived, DSE state manipulation)

# NLinjector.exe — reverse analysis / реверс-анализ

**[EN](#english) · [RU / Русский](#русский)**

---

## English

Complete breakdown of `C:\Users\sshunko\Downloads\NLinjector(2).exe` — user-mode CS2 injector, using [hfiref0x/KDU](https://github.com/hfiref0x/KDU) + its own kernel-mode helper `HexSyncService.sys`.

### TL;DR — what it's made of

NLinjector is **not an original development**. It's a frontend assembled from **three components**:

1. **[hfiref0x/KDU](https://github.com/hfiref0x/KDU) v1.4.9** — Kernel Driver Utility. A public library exploiting one of 65 known vulnerabilities in signed drivers (RTCore64/MSI Afterburner, Zemana, gdrv/Gigabyte, WINIO, ASRock/ASUS utilities, etc.), to obtain arbitrary kernel r/w and disable DSE (Driver Signature Enforcement).
2. **HexSyncService.sys** — a custom unsigned kernel driver that is loaded via KDU (manual-map style) after DSE is disabled. Exposes 6 IOCTLs for user-mode.
3. **User-mode frontend** — orchestration: extract embedded resources → DSE off → load driver → inject via IOCTL → DSE restore.

Nothing exotic. Standard "manual-map driver → IOCTL injection" pipeline from scene injectors.

### File properties

| Field | Value |
|---|---|
| Path | `C:\Users\sshunko\Downloads\NLinjector(2).exe` |
| Size | 4 759 552 B (4.53 MB) |
| Type | PE32+, x64, console subsystem, 7 sections |
| Static strings count | ~245 800 |
| IDA session | `nlinj` |
| Language | Visual C++ 2022 (MSVC 17.x runtime) |

### Full pipeline (main → sub_140006FF0)

```
Step 1: Initializing DSE Manager (sub_14000D050)
    ├─ Admin token check (CheckTokenMembership)
    ├─ RtlGetVersion → dword_14005772C = build number
    ├─ if build >= 22621 (Win11 22H2): disable VulnerableDriverBlocklistEnable
    │       via HKLM\System\CurrentControlSet\Control\CI\Config
    └─ Extract embedded KDU + drv64.dll from PE resources → dispatch table

Step 2: Disabling Driver Signature Enforcement (KDU integration)
    ├─ Load vulnerable provider driver (RTCore64/Zemana/etc)
    ├─ Get arbitrary kernel R/W via provider vulnerability
    ├─ Locate ci.dll!g_CiOptions in kernel memory
    ├─ Save original value → write new value (0 = fully disabled, 6 = default)
    └─ Unload provider driver

Step 3: Loading HexSync driver (sub_140005190 / sub_140005390)
    ├─ Extract HexSyncService.sys to temp path
    ├─ OpenSCManagerW + OpenServiceW / DeleteService (cleanup previous)
    ├─ CreateServiceW: kernel-mode, DEMAND_START, ERROR_NORMAL
    ├─ StartServiceW (succeeds because DSE disabled)
    └─ Wait ≤5s for \\.\HexSyncService device (5×100ms retry)

Step 4: Running self-test (IOCTL 0x22200C)
    ├─ DeviceIoControl(hDev, 0x22200C, in[12], out[12])
    ├─ Expected: out[0..7] == 0x200008421ULL (magic)
    ├─ Fail codes: 20 (open fail), 21 (IOCTL fail), 22 (magic mismatch)
    └─ On pass: driver is alive

Step 5: Wait for cs2.exe (loop with 1s poll)
    ├─ CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)
    ├─ Process32FirstW/NextW → search "cs2.exe" case-insensitive
    ├─ Print "Waiting for cs2.exe..." if not found
    └─ Once found: th32ProcessID captured

Step 6: Open device + bypass user-mode hooks (sub_140006720)
    ├─ CreateFileW(\\.\HexSyncService)
    ├─ For each entry in xmmword_1400576D8 (hook table with N entries * 64 B):
    │   ├─ sub_140005B30(entry_name) — restore original bytes via IOCTL
    │   └─ Log "Unhook failed: %s!%s" if failed
    └─ Print stats: hooks bypassed/total

Step 7: DLL injection (sub_1400068D0) — main event
    ├─ IOCTL 0x222018 IOCTL_HexSync_ALLOCATE_MEMORY
    │       in:  { DWORD pid, PVOID addr=NULL, SIZE_T size=pathBytes,
    │              DWORD protect=PAGE_READWRITE }
    │       out: { addr filled with allocated remote VA }
    │
    ├─ IOCTL 0x222004 IOCTL_HexSync_WRITE_MEMORY
    │       buf: { DWORD pid, PVOID remote_addr, SIZE_T size, ...dll_path bytes... }
    │
    ├─ IOCTL 0x222000 IOCTL_HexSync_READ_MEMORY (verification)
    │       in:  { DWORD pid, PVOID addr, SIZE_T size }
    │       out: read back bytes → memcmp with expected → abort if diff
    │
    ├─ Resolve local kernel32!LoadLibraryW address (user-mode)
    │
    ├─ IOCTL 0x222008 IOCTL_HexSync_GET_MODULE_BASE
    │       in:  { DWORD pid, WCHAR name[MAX_PATH]="kernel32.dll" }
    │       out: { PVOID base }
    │
    ├─ Compute remote_LLW = local_LLW + (remote_k32 - local_k32)
    │
    └─ IOCTL 0x222020 IOCTL_HexSync_CREATE_THREAD
            in:  { DWORD pid, PVOID start_fn=remote_LLW, PVOID param=remote_path }
            (kernel driver calls NtCreateThreadEx / ZwCreateThreadEx on target)

Step 8: Verification loop (5s deadline)
    ├─ IOCTL 0x222008 GET_MODULE_BASE for injected DLL basename
    ├─ Wait 100ms between retries
    └─ Print "Module loaded at 0x%p" or "Injection appeared successful but DLL load not detected"

Step 9: User-mode hooks restore
    └─ For each entry: sub_140006310 restore

Step 10: Wait 5 seconds → restore DSE
    └─ (reverse path from Step 2: restore g_CiOptions original value)
```

### HexSyncService IOCTL table

| Code | Name | Direction | Format |
|---|---|---|---|
| `0x222000` | READ_MEMORY | out | in: `{pid, addr, size}` → out: `bytes` |
| `0x222004` | WRITE_MEMORY | in | `{pid, addr, size, ...bytes...}` |
| `0x222008` | GET_MODULE_BASE | out | in: `{pid, WCHAR name[MAX_PATH]}` → out: `{base}` |
| `0x22200C` | SELF_TEST | out | out: `{magic=0x200008421}` |
| `0x222018` | ALLOCATE_MEMORY | out | in: `{pid, addr=NULL, size, protect}` → out: `{addr}` |
| `0x222020` | CREATE_THREAD | in | `{pid, start_fn, param}` |

`FSCTL_HexSync_UNHOOK` (no code seen in decompile) — also present, restores user-mode API prologue bytes.

### Kernel-side implementation (hypothesis, driver not in dump)

From IOCTL patterns the kernel-side can be reconstructed:

```c
// ALLOCATE_MEMORY (0x222018)
NTSTATUS HandleAllocate(HS_AllocReq* req) {
    PEPROCESS proc; PsLookupProcessByProcessId((HANDLE)req->pid, &proc);
    KeStackAttachProcess(proc, &apc);
    NTSTATUS s = ZwAllocateVirtualMemory(NtCurrentProcess(),
        &req->addr, 0, &req->size, MEM_COMMIT | MEM_RESERVE, req->protect);
    KeUnstackDetachProcess(&apc);
    ObDereferenceObject(proc);
    return s;
}

// WRITE_MEMORY (0x222004)
NTSTATUS HandleWrite(HS_WriteReq* req, void* data) {
    PEPROCESS proc; PsLookupProcessByProcessId((HANDLE)req->pid, &proc);
    SIZE_T copied;
    NTSTATUS s = MmCopyVirtualMemory(PsGetCurrentProcess(), data,
                                     proc, req->addr, req->size,
                                     KernelMode, &copied);
    ObDereferenceObject(proc);
    return s;
}

// GET_MODULE_BASE (0x222008)
NTSTATUS HandleGetModule(HS_ModReq* req) {
    PEPROCESS proc; PsLookupProcessByProcessId((HANDLE)req->pid, &proc);
    KeStackAttachProcess(proc, &apc);
    PPEB peb = PsGetProcessPeb(proc);
    for (LIST_ENTRY* e = peb->Ldr->InLoadOrderModuleList.Flink; ...) {
        LDR_DATA_TABLE_ENTRY* ldr = ...;
        if (RtlEqualUnicodeString(&ldr->BaseDllName, &req->name, TRUE)) {
            req->out_base = ldr->DllBase; break;
        }
    }
    KeUnstackDetachProcess(&apc);
    ObDereferenceObject(proc);
    return STATUS_SUCCESS;
}

// CREATE_THREAD (0x222020)
NTSTATUS HandleCreateThread(HS_ThreadReq* req) {
    PEPROCESS proc; PsLookupProcessByProcessId((HANDLE)req->pid, &proc);
    HANDLE hProc;
    ObOpenObjectByPointer(proc, 0, NULL, PROCESS_ALL_ACCESS, *PsProcessType,
                          KernelMode, &hProc);
    OBJECT_ATTRIBUTES oa; InitializeObjectAttributes(&oa, ...);
    HANDLE hThread;
    ZwCreateThreadEx(&hThread, THREAD_ALL_ACCESS, &oa, hProc, req->start_fn,
                     req->param, 0, 0, 0, 0, NULL);
    ZwClose(hThread); ZwClose(hProc);
    ObDereferenceObject(proc);
    return STATUS_SUCCESS;
}
```

### References to identified functions

| Address | Function | What it does |
|---|---|---|
| `0x140007b20` | `main` | Entry point, orchestrator |
| `0x140006FF0` | `sub_140006FF0` | Step 3-8: load driver → find cs2 → inject |
| `0x14000D050` | `sub_14000D050` | Step 1: DSE Manager init |
| `0x140006720` | `sub_140006720` | Step 6: user-mode hooks bypass loop |
| `0x1400068D0` | `sub_1400068D0` | Step 7: inject via 6 IOCTLs |
| `0x1400057D0` | `sub_1400057D0` | Wrapper around IOCTL 0x222008 GET_MODULE_BASE |
| `0x140005190` | `sub_140005190` | Extract HexSyncService.sys to disk |
| `0x140005390` | `sub_140005390` | Install/open SCM service |

### What is NOT unique

- **Nothing.** Every component is documented in OSS.
- KDU pipeline — `hfiref0x/KDU/Source/` open source.
- HexSyncService — standard manual-map pattern (see [`TheCruZ/kdmapper`](https://github.com/TheCruZ/kdmapper) for historical reference).
- IOCTL flow — same as in multiple public scene injectors.

### How this is implemented in our repo

**CS2UnifiedInjector** `--method kernel` — user-mode client to the identical IOCTL API (same 6 codes, same structures).

For a full functional analog of NLinjector one needs:
1. Write `HexSyncService.sys` — kernel driver with 6 IOCTL handlers (template in this document above)
2. Use `kdu.exe -map` (our KDUEMB build, `third_party/KDU`) to load — 65 embedded vulnerable providers with auto-fallback
3. ~~Or use legacy `KernelDriverMapper.exe` via `iqvw64e.sys`~~ (retired; replaced by KDU `-map`)

The `.sys` driver — TODO for future releases. IOCTL client is already ready and compatible with any such implementation.

### Legal

NLinjector, KDU, HexSyncService — all tools for **security research / educational** purposes. Use against Valve services = VAC ban. See [`docs/ETHICS.md`](ETHICS.md).

---

## Русский

Полный разбор `C:\Users\sshunko\Downloads\NLinjector(2).exe` — user-mode CS2 инжектора, использующего связку [hfiref0x/KDU](https://github.com/hfiref0x/KDU) + собственный kernel-mode helper `HexSyncService.sys`.

### TL;DR — из чего собран

NLinjector — **не оригинальная разработка**. Это frontend, собранный из **трёх компонентов**:

1. **[hfiref0x/KDU](https://github.com/hfiref0x/KDU) v1.4.9** — Kernel Driver Utility. Публичная библиотека, эксплуатирующая одну из 65 известных уязвимостей в подписанных драйверах (RTCore64/MSI Afterburner, Zemana, gdrv/Gigabyte, WINIO, ASRock/ASUS утилиты, и т.д.), чтобы получить arbitrary kernel r/w и отключить DSE (Driver Signature Enforcement).
2. **HexSyncService.sys** — собственный неподписанный kernel driver, который загружается через KDU (manual-map style) уже с отключённым DSE. Экспозит 6 IOCTL'ов для user-mode.
3. **User-mode фронтенд** — оркестрация: extract embedded resources → DSE off → load driver → inject via IOCTL → DSE restore.

Ничего экзотического. Стандартный "manual-map driver → IOCTL injection" pipeline из scene-инжекторов.

### Файл и характеристики

| Поле | Значение |
|---|---|
| Path | `C:\Users\sshunko\Downloads\NLinjector(2).exe` |
| Size | 4 759 552 B (4.53 MB) |
| Type | PE32+, x64, console subsystem, 7 sections |
| Static strings count | ~245 800 |
| IDA session | `nlinj` |
| Language | Visual C++ 2022 (MSVC 17.x runtime) |

### Полный pipeline (main → sub_140006FF0)

```
Step 1: Initializing DSE Manager (sub_14000D050)
    ├─ Admin token check (CheckTokenMembership)
    ├─ RtlGetVersion → dword_14005772C = build number
    ├─ if build >= 22621 (Win11 22H2): disable VulnerableDriverBlocklistEnable
    │       via HKLM\System\CurrentControlSet\Control\CI\Config
    └─ Extract embedded KDU + drv64.dll from PE resources → dispatch table

Step 2: Disabling Driver Signature Enforcement (KDU integration)
    ├─ Load vulnerable provider driver (RTCore64/Zemana/etc)
    ├─ Get arbitrary kernel R/W via provider vulnerability
    ├─ Locate ci.dll!g_CiOptions in kernel memory
    ├─ Save original value → write new value (0 = fully disabled, 6 = default)
    └─ Unload provider driver

Step 3: Loading HexSync driver (sub_140005190 / sub_140005390)
    ├─ Extract HexSyncService.sys to temp path
    ├─ OpenSCManagerW + OpenServiceW / DeleteService (cleanup previous)
    ├─ CreateServiceW: kernel-mode, DEMAND_START, ERROR_NORMAL
    ├─ StartServiceW (succeeds because DSE disabled)
    └─ Wait ≤5s for \\.\HexSyncService device (5×100ms retry)

Step 4: Running self-test (IOCTL 0x22200C)
    ├─ DeviceIoControl(hDev, 0x22200C, in[12], out[12])
    ├─ Expected: out[0..7] == 0x200008421ULL (magic)
    ├─ Fail codes: 20 (open fail), 21 (IOCTL fail), 22 (magic mismatch)
    └─ On pass: driver is alive

Step 5: Wait for cs2.exe (loop with 1s poll)
    ├─ CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)
    ├─ Process32FirstW/NextW → search "cs2.exe" case-insensitive
    ├─ Print "Waiting for cs2.exe..." if not found
    └─ Once found: th32ProcessID captured

Step 6: Open device + bypass user-mode hooks (sub_140006720)
    ├─ CreateFileW(\\.\HexSyncService)
    ├─ For each entry in xmmword_1400576D8 (hook table with N entries * 64 B):
    │   ├─ sub_140005B30(entry_name) — restore original bytes via IOCTL
    │   └─ Log "Unhook failed: %s!%s" if failed
    └─ Print stats: hooks bypassed/total

Step 7: DLL injection (sub_1400068D0) — main event
    ├─ IOCTL 0x222018 IOCTL_HexSync_ALLOCATE_MEMORY
    │       in:  { DWORD pid, PVOID addr=NULL, SIZE_T size=pathBytes,
    │              DWORD protect=PAGE_READWRITE }
    │       out: { addr filled with allocated remote VA }
    │
    ├─ IOCTL 0x222004 IOCTL_HexSync_WRITE_MEMORY
    │       buf: { DWORD pid, PVOID remote_addr, SIZE_T size, ...dll_path bytes... }
    │
    ├─ IOCTL 0x222000 IOCTL_HexSync_READ_MEMORY (verification)
    │       in:  { DWORD pid, PVOID addr, SIZE_T size }
    │       out: read back bytes → memcmp with expected → abort if diff
    │
    ├─ Resolve local kernel32!LoadLibraryW address (user-mode)
    │
    ├─ IOCTL 0x222008 IOCTL_HexSync_GET_MODULE_BASE
    │       in:  { DWORD pid, WCHAR name[MAX_PATH]="kernel32.dll" }
    │       out: { PVOID base }
    │
    ├─ Compute remote_LLW = local_LLW + (remote_k32 - local_k32)
    │
    └─ IOCTL 0x222020 IOCTL_HexSync_CREATE_THREAD
            in:  { DWORD pid, PVOID start_fn=remote_LLW, PVOID param=remote_path }
            (kernel driver вызывает NtCreateThreadEx / ZwCreateThreadEx на target'е)

Step 8: Verification loop (5s deadline)
    ├─ IOCTL 0x222008 GET_MODULE_BASE for injected DLL basename
    ├─ Wait 100ms between retries
    └─ Print "Module loaded at 0x%p" or "Injection appeared successful but DLL load not detected"

Step 9: User-mode hooks restore
    └─ For each entry: sub_140006310 restore

Step 10: Wait 5 seconds → restore DSE
    └─ (обратный path из Step 2: восстановить g_CiOptions original value)
```

### IOCTL таблица HexSyncService

| Code | Name | Direction | Формат |
|---|---|---|---|
| `0x222000` | READ_MEMORY | out | in: `{pid, addr, size}` → out: `bytes` |
| `0x222004` | WRITE_MEMORY | in | `{pid, addr, size, ...bytes...}` |
| `0x222008` | GET_MODULE_BASE | out | in: `{pid, WCHAR name[MAX_PATH]}` → out: `{base}` |
| `0x22200C` | SELF_TEST | out | out: `{magic=0x200008421}` |
| `0x222018` | ALLOCATE_MEMORY | out | in: `{pid, addr=NULL, size, protect}` → out: `{addr}` |
| `0x222020` | CREATE_THREAD | in | `{pid, start_fn, param}` |

`FSCTL_HexSync_UNHOOK` (без code видимого в decompile) — тоже присутствует, восстанавливает user-mode API prologue bytes.

### Kernel-side реализация (гипотеза, driver не в дампе)

Из паттернов IOCTL можно восстановить kernel-side:

```c
// ALLOCATE_MEMORY (0x222018)
NTSTATUS HandleAllocate(HS_AllocReq* req) {
    PEPROCESS proc; PsLookupProcessByProcessId((HANDLE)req->pid, &proc);
    KeStackAttachProcess(proc, &apc);
    NTSTATUS s = ZwAllocateVirtualMemory(NtCurrentProcess(),
        &req->addr, 0, &req->size, MEM_COMMIT | MEM_RESERVE, req->protect);
    KeUnstackDetachProcess(&apc);
    ObDereferenceObject(proc);
    return s;
}

// WRITE_MEMORY (0x222004)
NTSTATUS HandleWrite(HS_WriteReq* req, void* data) {
    PEPROCESS proc; PsLookupProcessByProcessId((HANDLE)req->pid, &proc);
    SIZE_T copied;
    NTSTATUS s = MmCopyVirtualMemory(PsGetCurrentProcess(), data,
                                     proc, req->addr, req->size,
                                     KernelMode, &copied);
    ObDereferenceObject(proc);
    return s;
}

// GET_MODULE_BASE (0x222008)
NTSTATUS HandleGetModule(HS_ModReq* req) {
    PEPROCESS proc; PsLookupProcessByProcessId((HANDLE)req->pid, &proc);
    KeStackAttachProcess(proc, &apc);
    PPEB peb = PsGetProcessPeb(proc);
    for (LIST_ENTRY* e = peb->Ldr->InLoadOrderModuleList.Flink; ...) {
        LDR_DATA_TABLE_ENTRY* ldr = ...;
        if (RtlEqualUnicodeString(&ldr->BaseDllName, &req->name, TRUE)) {
            req->out_base = ldr->DllBase; break;
        }
    }
    KeUnstackDetachProcess(&apc);
    ObDereferenceObject(proc);
    return STATUS_SUCCESS;
}

// CREATE_THREAD (0x222020)
NTSTATUS HandleCreateThread(HS_ThreadReq* req) {
    PEPROCESS proc; PsLookupProcessByProcessId((HANDLE)req->pid, &proc);
    HANDLE hProc;
    ObOpenObjectByPointer(proc, 0, NULL, PROCESS_ALL_ACCESS, *PsProcessType,
                          KernelMode, &hProc);
    OBJECT_ATTRIBUTES oa; InitializeObjectAttributes(&oa, ...);
    HANDLE hThread;
    ZwCreateThreadEx(&hThread, THREAD_ALL_ACCESS, &oa, hProc, req->start_fn,
                     req->param, 0, 0, 0, 0, NULL);
    ZwClose(hThread); ZwClose(hProc);
    ObDereferenceObject(proc);
    return STATUS_SUCCESS;
}
```

### Ссылки на разобранные функции

| Address | Function | Что делает |
|---|---|---|
| `0x140007b20` | `main` | Entry point, orchestrator |
| `0x140006FF0` | `sub_140006FF0` | Step 3-8: load driver → find cs2 → inject |
| `0x14000D050` | `sub_14000D050` | Step 1: DSE Manager init |
| `0x140006720` | `sub_140006720` | Step 6: user-mode hooks bypass loop |
| `0x1400068D0` | `sub_1400068D0` | Step 7: инжект через 6 IOCTL'ов |
| `0x1400057D0` | `sub_1400057D0` | Wrapper над IOCTL 0x222008 GET_MODULE_BASE |
| `0x140005190` | `sub_140005190` | Extract HexSyncService.sys to disk |
| `0x140005390` | `sub_140005390` | Install/open SCM service |

### Что НЕ является уникальным

- **Ничего**. Каждый компонент задокументирован в OSS.
- KDU pipeline — `hfiref0x/KDU/Source/` открытый исходник.
- HexSyncService — стандартный manual-map pattern (см. [`TheCruZ/kdmapper`](https://github.com/TheCruZ/kdmapper) для исторической справки).
- IOCTL flow — тот же, что в multiple public scene-инжекторах.

### Как это реализовано в нашем репо

**CS2UnifiedInjector** `--method kernel` — user-mode клиент к идентичному IOCTL API (те же 6 codes, те же структуры).

Для полного функционального аналога NLinjector нужно:
1. Написать `HexSyncService.sys` — kernel driver с 6 IOCTL handler'ами (шаблон в этом документе выше)
2. Использовать `kdu.exe -map` (наш KDUEMB build, `third_party/KDU`) для загрузки — 65 embedded vulnerable providers с auto-fallback
3. ~~Или legacy `KernelDriverMapper.exe` через `iqvw64e.sys`~~ (retired; заменён на KDU `-map`)

Драйверный `.sys` — TODO для будущих релизов. IOCTL-клиент уже готов и совместим с любой такой реализацией.

### Legal

NLinjector, KDU, HexSyncService — все инструменты для **security research / educational** целей. Использование против сервисов Valve = VAC ban. См. [`docs/ETHICS.md`](ETHICS.md).

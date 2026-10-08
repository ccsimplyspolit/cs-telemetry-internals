# 04 — IsValveDS Spoofer

Kernel-mode one-byte spoofer for `C_CSGameRules::m_bIsValveDS`. Two components:

- **CS2IsValveDSSpooferDriver.sys** — kernel driver (~17.9 KB, KDU-mapped).
- **CS2IsValveDSSpooferConsole.exe** — user-mode SHM controller (~206 KB, VT100 TUI).

Source:
- Driver: [`source/drivers/CS2IsValveDSSpooferDriver/`](../../source/drivers/CS2IsValveDSSpooferDriver/)
- Console: [`source/apps/CS2IsValveDSSpooferConsole/`](../../source/apps/CS2IsValveDSSpooferConsole/)
- Kit: [`build/kit_isvalveds/`](../../build/kit_isvalveds/)

Version: **v1.14-claude** — protocol v2 with Freeze mode (2026-07-15).

---

## What it does

`C_CSGameRules::m_bIsValveDS` is a single byte in CS2 memory that tells the client whether the connected dedicated server is an official Valve DS (1) or a community server (0). Several features read this: MOTD tab, official-server icon, some UI toggles. It is **not** networked from the server side — the server sends its identity, the client sets the byte based on that identity, then the byte is available for local reads.

The driver rewrites this byte every 200 ms while the worker thread is alive. From the client's perspective the server has whatever type you tell it.

---

## Architecture

```
User console ─────► SHM Global\IsValveDSState ◄───── Driver worker (200 ms)
       │                                                     │
       │                                                     ▼
       │                                           KeStackAttachProcess(cs2)
       │                                                     │
       │                                                     ▼
       │                                        Read pointer [client_base + dwGameRules]
       │                                                     │
       │                                                     ▼
       │                                        Write 1 byte at [*gr + m_bIsValveDS]
       │                                                     │
       │                                                     ▼
       │                                              KeUnstackDetachProcess
       │
       ├── freeze_enabled=1 ─────────────────► driver rewrites every tick, ignores request_id
       │
       └── Global\IsValveDSStop event ────────► worker exits, signals Global\IsValveDSStopped
```

Named objects:

| Type | Win32 name | NT path |
|---|---|---|
| SECTION | `Global\IsValveDSState` | `\BaseNamedObjects\IsValveDSState` |
| EVENT | `Global\IsValveDSStop` | `\BaseNamedObjects\IsValveDSStop` |
| EVENT | `Global\IsValveDSStopped` | `\BaseNamedObjects\IsValveDSStopped` |

Definitions in [`shared.h`](../../source/drivers/CS2IsValveDSSpooferDriver/shared.h) (identical copy in the console).

Protocol version: **2** (`protocol_version = 2` in SHM header).

---

## Offsets (fallback defaults, build 14169)

| Symbol | Offset | Comment |
|---|---|---|
| `DEFAULT_OFF_DWGAMERULES` | `0x23A0C58` | `client.dll!dwGameRules` (was `0x2340FE8` on 14167) |
| `DEFAULT_OFF_ISVALVEDS` | `0xA4` | `C_CSGameRules::m_bIsValveDS` (stable) |

Registry `HKLM\SOFTWARE\IsValveDS` overrides these constants. `Load-Spoofer.ps1` from the kit auto-fetches fresh offsets from `a2x/cs2-dumper` HEAD via WinHTTPS and writes them to the registry before every driver load.

---

## Driver worker loop (every 200 ms)

```c
if (freeze_enabled) {
    desired = freeze_value;
} else if (write_request_id != last_write_id) {
    desired = desired_value;
    last_write_id = write_request_id;
} else {
    continue;  // nothing to do
}

status = PsLookupProcessByProcessId(cs2_pid, &proc);
if (!NT_SUCCESS(status)) continue;

KeStackAttachProcess(proc, &apc);
__try {
    // Read pointer to C_CSGameRules
    MmCopyVirtualMemory(proc, client_base + OffDwGameRules, kern, &gr_ptr, 8, KernelMode, &copied);
    if (gr_ptr) {
        // Write 1 byte
        byte val = (byte)desired;
        MmCopyVirtualMemory(kern, &val, proc, gr_ptr + OffMIsValveDS, 1, KernelMode, &copied);
    }
} __except (EXCEPTION_EXECUTE_HANDLER) { /* SEH guard */ }
KeUnstackDetachProcess(&apc);
ObDereferenceObject(proc);
```

Uses `PsAcquireProcessExitSynchronization` (Windows 8.1+ hard guard) to prevent cs2 exit racing the write. Details: [`docs/DRIVER_HARDENING.md`](../../docs/DRIVER_HARDENING.md) §1.

---

## Console TUI (v1.14)

Full-frame VT100:

- Colored current-value badge (green **VALVE DS** / red **COMMUNITY**).
- Freeze banner (cyan when ON), re-apply counter live.
- Presets:
  1. Valve DS locked.
  2. Community locked.
  3. Free (no freeze).
  4. Auto-toggle every 5 s (console-side thread).

Config save/load: `%LOCALAPPDATA%\CS2IsValveDSSpoofer\config.json`.

CLI flags:

- `--freeze-on VAL` — set freeze_value + freeze_enabled=1
- `--freeze-off` — clear freeze
- `--set-value VAL` — one-shot write via write_request_id ping-pong
- `--print-state` — dump current SHM snapshot
- `--unload` — signal driver stop event, wait for stopped, exit

Interactive session (v1.13-style):

```
> h        # help
> 0        # set m_bIsValveDS = 0 (community server)
> 1        # set m_bIsValveDS = 1 (Valve DS)
> s        # status
> q        # quit (signal worker stop)
```

---

## Registry keys (populated by Load-Spoofer.ps1)

Registry root: `HKLM\SOFTWARE\F20Driver` (legacy path shared with KillTrigger, or `HKLM\SOFTWARE\IsValveDS` in v1.14).

| Value | Type | Purpose |
|---|---|---|
| `OffDwGameRules` | REG_QWORD | `client.dll::dwGameRules` RVA |
| `OffMIsValveDS` | REG_QWORD | `C_CSGameRules::m_bIsValveDS` offset (usually `0xA4`) |

Driver reads these at DriverEntry. Fallback: hardcoded `0x23A0C58` + `0xA4` (build 14169).

Load-Spoofer script does WinHTTPS GET on:

```
https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json
```

Reads `client.dll::dwGameRules` and writes it to `OffDwGameRules`. `-OffGameRules 0x23A0C58` CLI flag overrides.

---

## Usage

Load:
```
double-click Load-Spoofer.bat
# or manually:
.\Load-Spoofer.ps1 -OffGameRules 0x23A0C58
```

Unload (driver + clean registry):
```
double-click Unload-Spoofer.bat
# or:
.\Unload-Spoofer.ps1
# keep the registry keys:
.\Unload-Spoofer.ps1 -KeepRegistry
```

Load flags:

| Flag | Meaning |
|---|---|
| `-OffGameRules <hex>` | Override GitHub auto-fetch (e.g. `0x23A0C58`) |
| `-OffMIsValveDS <hex>` | Override m_bIsValveDS offset (default `0xA4`) |
| `-KduProvider 0\|1` | KDU provider (1 = RTCore64 default, 0 = Intel NAL) |
| `-WithFallback` | Try alternate KDU provider on failure |
| `-SkipConsole` | Load driver only, don't start console |

---

## Debug

Driver logs with prefix `[IsVDS]` in DebugView with "Capture Kernel" enabled.

---

## Requirements

- Windows 10 / 11 x64.
- Administrator.
- MSI Afterburner auto-closed by Load-Spoofer (holds `RTCore64` exclusive).
- HVCI (Memory Integrity) off, OR use `-KduProvider 0` (Intel NAL).

---

## Cross-refs

- [`source/drivers/CS2IsValveDSSpooferDriver/README.md`](../../source/drivers/CS2IsValveDSSpooferDriver/README.md)
- [`source/apps/CS2IsValveDSSpooferConsole/README.md`](../../source/apps/CS2IsValveDSSpooferConsole/README.md)
- [`build/kit_isvalveds/README.txt`](../../build/kit_isvalveds/README.txt)
- Release notes: [`docs/RELEASE_NOTES_v1.14-claude.md`](../../docs/RELEASE_NOTES_v1.14-claude.md)

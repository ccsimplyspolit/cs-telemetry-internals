# 07 — Build / install / usage

Everything you need to build any of the 12 projects, unpack the prebuilt kits, and use the shipping scripts.

---

## Requirements

| Component | Version | Purpose |
|---|---|---|
| Windows | 10 / 11 x64 build 22621+ | Target platform |
| Visual Studio | 2022 (v145 toolset) | C++20 |
| Windows SDK | 10.0.26100+ | User-mode headers |
| Windows WDK | 10.0.26100 | Kernel driver targets |
| CMake | 3.20+ | VLB build system |
| CS2 | depot 24134959, build 14169 or 14170 | Runtime target |
| MSI Afterburner | any | Auto-closed by launchers (holds `RTCore64` exclusive) |

Verify:

```powershell
cmake --version
msbuild -version
"C:\Program Files\Microsoft Visual Studio\2022\*\VC\Tools\MSVC\*\bin\Hostx64\x64\cl.exe" | Select-String Version
```

---

## Clone

```powershell
git clone --recursive https://github.com/ccsimplyspolit/CS2-P2C-TEMPLATES.git
cd CS2-P2C-TEMPLATES
```

The `--recursive` matters — pulls the `third_party/KDU` submodule.

---

## Build: VLB DLL

Two gate modes, three depot targets:

```powershell
cd source\dlls\VacLiveBypass

# Attack mode (fire-gated, ~10% ticks emit, minimal detection)
cmake -B build -A x64 -DFVA_TARGET_DEPOT=24134959 -DFVA_GATE_MODE=attack
cmake --build build --config Release --target fva_recon

# Byte mode (FVA-original 1:1, always-on when armed)
cmake -B build_byte -A x64 -DFVA_TARGET_DEPOT=24134959 -DFVA_GATE_MODE=byte
cmake --build build_byte --config Release --target fva_recon

# Baseline depot 14167 (regression)
cmake -B build_14167 -A x64 -DFVA_TARGET_DEPOT=14167
cmake --build build_14167 --config Release --target fva_recon

# Verbose H1 for reverse-dev
cmake -B build_verbose -A x64 -DFVA_TARGET_DEPOT=24134959 -DFVA_VERBOSE_H1=ON
cmake --build build_verbose --config Release --target fva_recon
```

Artefacts: `build/Release/fva_recon.dll`, `build_byte/Release/fva_recon.dll`, `build_14167/Release/fva_recon.dll` (~82 KB each).

---

## Build: Injector

```powershell
cd source\tools\CS2UnifiedInjector
msbuild CS2UnifiedInjector.vcxproj /p:Configuration=Release /p:Platform=x64
```

Output: `source/tools/CS2UnifiedInjector/x64/Release/CS2UnifiedInjector.exe` (~273 KB, 8 methods including kernel).

---

## Build: kernel drivers

Requires WDK.

```powershell
# CS2HexSyncCompatDriver (companion for --method kernel)
cd source\drivers\CS2HexSyncCompatDriver
msbuild CS2HexSyncCompatDriver.vcxproj /p:Configuration=Release /p:Platform=x64

# CS2IsValveDSSpooferDriver
cd ..\CS2IsValveDSSpooferDriver
msbuild CS2IsValveDSSpooferDriver.vcxproj /p:Configuration=Release /p:Platform=x64

# CS2KillTriggerDriver
cd ..\CS2KillTriggerDriver
msbuild CS2KillTriggerDriver.vcxproj /p:Configuration=Release /p:Platform=x64

# CS2RankSpooferDriver
cd ..\CS2RankSpooferDriver
msbuild CS2RankSpooferDriver.vcxproj /p:Configuration=Release /p:Platform=x64
```

Artefacts: `x64/Release/*.sys` in each driver dir.

---

## Build: consoles + tools

```powershell
# Consoles
cd source\apps\CS2IsValveDSSpooferConsole
msbuild CS2IsValveDSSpooferConsole.vcxproj /p:Configuration=Release /p:Platform=x64

cd ..\CS2RankSpooferConsole
msbuild CS2RankSpooferConsole.vcxproj /p:Configuration=Release /p:Platform=x64

# Tools
cd ..\..\tools\CS2MemoryTool
msbuild CS2MemoryTool.vcxproj /p:Configuration=Release /p:Platform=x64

cd ..\KbdClassAnalyzer
msbuild KbdClassAnalyzer.vcxproj /p:Configuration=Release /p:Platform=x64

cd ..\KernelDriverMapper
msbuild KernelDriverMapper.vcxproj /p:Configuration=Release /p:Platform=x64

cd ..\KernelDriverUnmapper
msbuild KernelDriverUnmapper.vcxproj /p:Configuration=Release /p:Platform=x64
```

---

## Build: fva_devirt

```powershell
cd source\dlls\fva_devirt
msbuild fva_devirt.vcxproj /p:Configuration=Release /p:Platform=x64
```

Output: `source/dlls/x64/Release/fva_devirt.exe`.

---

## Prebuilt kits

`build/kit_*/` directories contain ready-to-run kits. Each includes a signed CS2HexSyncCompatDriver.sys, KDU (`kdu.exe`), launcher scripts, and the relevant payload.

### kit_vlb_attack_gated — VLB fire-gated

```
build/kit_vlb_attack_gated/
├── CS2HexSyncCompatCert.cer      code-signing cert
├── CS2HexSyncCompatDriver.sys    signed driver (16688 B)
├── CS2UnifiedInjector.exe        injector (273408 B)
├── fva_recon_14167.dll           VLB payload for baseline depot (83456 B)
├── fva_recon_24134959.dll        VLB payload for current depot (82944 B)
├── GATE_MODE.txt                 human-readable "attack" marker
├── kdu.exe                       KDU standalone with 65 embedded providers (2477568 B)
├── Launch-Inject.bat             bat wrapper with UAC elevate
├── Launch-Inject.ps1             main pipeline (~19 KB)
└── README.txt                    instructions
```

### kit_vlb_byte_gated

Same layout as kit_vlb_attack_gated, `GATE_MODE.txt` marks it as `byte`.

### kit_vlb_default

Base VLB inject without an external gate condition. Section-J spoof activates when `engine_stable == true` AND local pawn alive+HP > 0. Same layout as `kit_vlb_attack_gated`, `GATE_MODE.txt` not set (default path).

### kit_isvalveds

```
build/kit_isvalveds/
├── CS2IsValveDSSpooferConsole.exe
├── CS2IsValveDSSpooferDriver.sys
├── Launch-Spoofer.bat / .ps1     kdu.exe -map path — in-memory driver load
├── kdu.exe                       KDU with 65 embedded providers (DSE off/on + driver map)
└── README.md
```

### kit_rankspoof

```
build/kit_rankspoof/
├── CS2HexSyncCompatCert.cer
├── CS2RankSpooferConsole.exe
├── CS2RankSpooferDriver.sys
├── Load-Spoofer.bat / .ps1
├── Unload-Spoofer.bat / .ps1
├── kdu.exe
└── README.txt
```

---

## Launch-Inject.ps1 pipeline (12 steps)

Used by kit_vlb_attack_gated / kit_vlb_byte_gated / kit_vlb_default. 1:1 reimplementation of NLinjector's flow (verified in IDA session `nlinj`).

```
Step 1   Admin check
Step 2   Disable VulnerableDriverBlocklistEnable (Win11 22H2+)
           HKLM\System\...\CI\Config\VulnerableDriverBlocklistEnable = 0
Step 3   Wait for cs2.exe (poll 1s)
Step 4   SHA client.dll → pick fva_recon_<depot>.dll
Step 4.5 Auto-close MSI Afterburner + RTSS + Encoder Server
           (they hold RTCore64 exclusive)
           Wait up to 15s for RTCore64 service to enter Stopped
Step 5   Install code-signing cert to TrustedRoot + TrustedPublisher
Step 6   Cleanup zombie KDU-provider services
           auto-fallback to prv=0 (Intel NAL) if RTCore64 stuck in StopPending
Step 7   kdu.exe -prv 1 -dse 0 (RTCore64 → patch g_CiOptions in CI.dll)
           fallback: -prv 0 -dse 0
Step 8   sc create + sc start CS2HexSyncCompatSvc
Step 9   Open \\.\CS2HexSyncCompat + SELF_TEST IOCTL magic 0x200008421
Step 10  CS2UnifiedInjector --method kernel:
           10a. BypassUserHooks — 17 API inline hooks
                (kernel32 / ntdll / KernelBase)
           10b. ALLOCATE_MEMORY (IOCTL 0x222018) — remote alloc
           10c. WRITE_MEMORY (0x222004) — DLL path in remote
           10d. READ_MEMORY (0x222000) — verify write
           10e. GET_MODULE_BASE (0x222008) — remote kernel32.dll
           10f. CREATE_THREAD (0x222020) — remote LoadLibraryW
           10g. Poll GET_MODULE_BASE up to 5s — verify DLL loaded
           10h. RestoreUserHooks — restore original hook bytes
Step 11  kdu.exe -prv <prv> -dse 6 (restore DSE)
Step 12  sc stop + sc delete cleanup (try/finally guaranteed)
```

Cleanup helpers in the launcher: `Get-ServiceState`, `Wait-ServiceStopped`, `Wait-ServiceRemoved`, `Test-DevicePresent`, `Start-DriverService` with bounded retry on error 183.

Each step is color-coded: `[+]` green, `[!]` yellow, `[-]` red. Any failure stops the pipeline with a clear next-step message.

---

## Launch-Inject.ps1 optional flags

| Flag | Meaning |
|---|---|
| `-Dll fva_recon_14167.dll` | Manual DLL selection |
| `-KduProvider 0` | Use Intel NAL instead of RTCore64 |
| `-WithFallback` | Allow fallback prv 1 → prv 0 |
| `-NoDbg` | Minimum output |

---

## Load-Spoofer.ps1 (IsValveDS + RankSpoofer)

Same DSE-off / KDU / SCM pattern but simpler:

```
1. Admin check
2. Blocklist off
3. Fetch offsets from a2x/cs2-dumper HEAD via WinHTTPS
     → HKLM\SOFTWARE\IsValveDS (or CS2RankSpoofer) registry values
4. Kill MSI Afterburner if running
5. KDU DSE off
6. sc create + sc start driver service
7. DSE restore
8. Launch console (unless -SkipConsole)
```

Flags:

| Flag | Meaning |
|---|---|
| `-OffGameRules <hex>` | Override GitHub auto-fetch |
| `-OffMIsValveDS <hex>` | Override m_bIsValveDS offset (default `0xA4`) |
| `-KduProvider 0\|1` | KDU provider (1 = RTCore64 default, 0 = Intel NAL) |
| `-WithFallback` | Try alternate provider on failure |
| `-SkipConsole` | Load driver only |

---

## Runtime debug

**VLB:** default is quiet. Enable via `set FVA_DEBUG=1` OR create `C:\vmp\.fva_debug`. Log: `C:\vmp\fva_recon.log`.

**RankSpoofer / IsValveDS drivers:** DebugView with "Capture Kernel" enabled. Prefixes `[RASX]` and `[IsVDS]` respectively.

Monitoring:

```powershell
Get-Content C:\vmp\fva_recon.log -Wait -Tail 30
```

---

## Unload

- **VLB:** press **END** key in the CS2 window. VLB worker thread uninstalls hooks and calls `FreeLibrary` on itself.
- **RankSpoofer:** press `U` in the console (or `--unload` CLI). Signals `Global\CS2RankSpoofStop*`.
- **IsValveDS:** press `q` in the console (or `--unload` CLI). Signals `Global\IsValveDSStop`.

After console signals stop event, drivers can be removed by their `Unload-Spoofer.ps1` companion.

Kernel drivers loaded via `kdu.exe -map` stay in memory until reboot — they have no `DriverUnload` and no `IoCreateDevice`. This is intentional (KDU-style hardening). See [`docs/DRIVER_HARDENING.md`](../docs/kernel_driver_hardening.md).

---

## Troubleshooting

**`KDU DSE off failed (provider 1)`**
- MSI Afterburner did not fully close → kill via Task Manager.
- Or try `-KduProvider 0 -WithFallback` (Intel NAL).

**`cs2.exe not running (60s wait)`**
- Steam launched CS2 as `SteamService.exe` shim? Launch CS2 directly.
- Not running in Compatibility mode.

**`[fva_recon] FATAL: install_all failed`**
- Verify client.dll MD5. Expected `16917fce6c15715434f6604e8086d38a` for depot 24134959.
- If depot 14167 → use `fva_recon_14167.dll` (launcher SHA check switches automatically).

**Cs2 crashes on map change**
- Rebuild with `-DFVA_STRICT_FINGERPRINT=ON` to abort injection on fingerprint mismatch.
- Check `fva_recon.log` last lines for exact crash point.

**BSOD 0x50 loading driver**
- DSE bypass timing or cert install race. Reboot, retry with `-KduProvider 0`.

---

## Cross-refs

- Deep dive per project: [02_vlb.md](02_vlb.md), [03_rankspoofer.md](03_rankspoofer.md), [04_isvalveds.md](04_isvalveds.md).
- Depot survival: [09_depot_updates.md](09_depot_updates.md).
- Live parity proof: [08_runtime_verification.md](08_runtime_verification.md).
- Older wiki INSTALL: `docs/wiki/INSTALL.md`.

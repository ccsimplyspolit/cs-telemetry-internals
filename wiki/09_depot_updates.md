# 09 — Depot updates

How each product in the repo survives a CS2 patch, and what to do when it doesn't.

CS2 depots update on `24134959` roughly every 1-2 weeks; build numbers bump within the depot (e.g. 14167 → 14169 → 14170). Most bumps are byte-level with no offset movement. Sometimes classes move fields around, sometimes RVAs drift.

---

## Auto-update matrix

From [`docs/wiki/BUILD_AUDIT.md`](../../docs/wiki/BUILD_AUDIT.md).

| Category | Projects |
|---|---|
| Full (GitHub HEAD auto-fetch) | — (none fully self-updating) |
| Partial (registry / SHM / sig-scan) | VacLiveBypass, CS2IsValveDSSpooferDriver, CS2KillTriggerDriver, CS2RankSpooferDriver, KbdClassAnalyzer, the two consoles |
| None (rebuild required) | CS2HexSyncCompatDriver, CS2UnifiedInjector, CS2MemoryTool, KernelDriverMapper, KernelDriverUnmapper |

The three "rebuild required" projects don't touch CS2 offsets and only need a rebuild when the injector wire protocol, IOCTL API, or kernel API surface changes — which is rare.

---

## VLB — auto-fetch offsets

VLB does WinHTTPS GET to `raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json` at DLL init with a 5-second timeout. Reads:

- `engine2!dwNetworkGameClient` + `signOnState` offset
- `client!dwLocalPlayerPawn` + `dwLocalPlayerController`
- `client!dwCSGOInput` · `dwGlobalVars` · `dwGameRules`

Falls back to hardcoded values on network failure. Log line at DLL init prints source of values.

For **hook targets** VLB does not use RVAs — it does pattern-scan with wildcards. Even RVA drift of +0x960 (H4) is handled without a code change.

The only thing that needs manual work on a new depot: `version_manifest.h` fingerprint (client.dll MD5 + size). Wrong fingerprint aborts injection with `install_all failed`.

---

## RankSpoofer / IsValveDS drivers — registry-driven offsets

Both drivers read their offsets from `HKLM` at `DriverEntry`:

| Driver | Registry root |
|---|---|
| CS2IsValveDSSpooferDriver | `HKLM\SOFTWARE\IsValveDS` (or `HKLM\SOFTWARE\F20Driver` legacy) |
| CS2RankSpooferDriver | `HKLM\SYSTEM\CurrentControlSet\Services\CS2RankSpoofer` |
| CS2KillTriggerDriver | `HKLM\SOFTWARE\F20Driver` |

`Load-Spoofer.ps1` fetches fresh offsets from `a2x/cs2-dumper` HEAD and writes them into the registry BEFORE `sc start`. If the network is down, the driver falls back to hardcoded values.

For RankSpoofer this is a **22-offset schema push**; see [`shared.h`](../../source/drivers/CS2RankSpooferDriver/shared.h) v2 for the layout.

---

## Depot state file

Current snapshot of offsets: [`DEPOT_STATE.md`](../../DEPOT_STATE.md).

Fields on 2026-07-11 (build 14169 / depot 24134959):

Client.dll:
- `dwGameRules` = `0x23A0C58` (+0x5FC70 vs 14167)
- `dwLocalPlayerController` = `0x237BD60` (+0x5B7F0 vs 14167)
- `dwLocalPlayerPawn` = `0x23A14B8`
- `dwEntityList` = `0x254CE20`
- `dwGlobalVars` = `0x209A5A0`
- `dwCSGOInput` = `0x23B69B0`
- `dwGlowManager` = `0x23A0688`

Class fields:
- `C_CSGameRules::m_bIsValveDS` = `0xA4`
- `CCSPlayerController::m_pActionTrackingServices` = `0x820` (was `0x818`)
- `CCSPlayerController_ActionTrackingServices::m_iNumRoundKills` = `0x128`

Engine2.dll:
- `dwBuildNumber` = `0x60F714`
- `dwNetworkGameClient` = `0x90D9B0`

---

## When a new depot lands

### Step 1 — quick MD5 check

```powershell
$new = (Get-FileHash 'D:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\bin\win64\client.dll' -Algorithm MD5).Hash
# Expected on 24134959 / build 14169: 16917FCE6C15715434F6604E8086D38A
if ($new -eq '16917FCE6C15715434F6604E8086D38A') { 'SAME BUILD' } else { "NEW BUILD $new" }
```

Same → nothing to do.

### Step 2 — runtime verify the 4 hooks

Launch CS2, wait for main menu:

```powershell
Start-Process 'scripts\runtime_verify\rt_verify_task_wrapper.cmd' -Verb RunAs -Wait
Get-Content docs\rt_verify_all_hooks_result.json | ConvertFrom-Json | ForEach-Object { $_.hooks | Select name, hits }
```

- 4 × `hits=1` → VLB works; no rebuild needed.
- Anyone `hits=0` or `hits>1` → proceed to step 3.

### Step 3 — regenerate offsets

Two paths.

**Path A: cs2-dumper (fast, complete):**

```powershell
cd C:\vmp\cs_dumper
cargo run --release -- -v -o output_fresh

# Copy for VLB consumption (VLB reads live from GitHub, so:)
# just wait until a2x/cs2-dumper PR is merged — 5 minutes typically.
```

**Path B: `auto_adapt_new_depot.ps1` (targeted, VLB only):**

```powershell
cd source\dlls\VacLiveBypass
powershell -ExecutionPolicy Bypass -File scripts\auto_adapt_new_depot.ps1
```

Script does:
1. Reads MD5 of current client.dll.
2. If it's a new depot (not 14167 and not 24134959):
   - Snapshots binary into `depot_snapshots/depot_<build>_<date>/`.
   - Sig-scans Hook A / B / C, ArenaStringPtr::Set, 5x protobuf T::New, arena allocator.
   - Prints RVA drift vs 24134959.
   - Emits a ready-to-paste `#elif FVA_TARGET_DEPOT == <new>` block for `version_manifest.h`.

### Step 4 — patch version_manifest.h + rebuild

```powershell
# Paste block into src/version_manifest.h after existing #elif chains
# Update fingerprint namespace with new MD5 + size

cmake -B build -DFVA_TARGET_DEPOT=<new_buildid>
cmake --build build --config Release --target fva_recon
```

### Step 5 — Load-Spoofer scripts (IsValveDS / RankSpoofer)

They auto-pull offsets on every run. If a2x/cs2-dumper hasn't updated yet:

```powershell
# Override manually:
.\Load-Spoofer.ps1 -OffGameRules 0x23A0C58
```

Or edit the `-OffGameRules` fallback constant in `Load-Spoofer.ps1`.

---

## SHA whitelist (Launch-Inject.ps1)

The launcher SHA-checks client.dll before selecting which VLB payload to inject. On unknown SHA (new build) it now emits a **Warn**, not a silent default — that changed in v1.15-claude.

Whitelist source: hardcoded array at the top of `Launch-Inject.ps1`. Add new SHA when depot bumps:

```powershell
$KnownGoodSHAs = @(
    '16917fce6c15715434f6604e8086d38a',   # 14169
    '<new md5 here>'                       # 14170
)
```

Log line when a known SHA hits:
```
[+] client.dll SHA matches build 14170 — using fva_recon_24134959.dll
```

On unknown:
```
[!] client.dll SHA <hex> not in whitelist — defaulting to fva_recon_24134959.dll
[!] If injection fails, this depot needs a rebuild — see wiki/en/09_depot_updates.md
```

---

## Sig-scan philosophy

VLB pattern-scans with wildcards because RVAs drift on every depot. Sig criteria:

- 16-30 bytes long.
- Anchor on function prologue (`48 89 5C 24 XX 55 56 57 …`) — MSVC callee-save is stable.
- 4-8 wildcards where the compiler emits RIP-relative displacements (`48 8B 0D ? ? ? ?`).
- Verify uniqueness on both baseline (14167) and current (24134959) depot.

If a sig loses uniqueness on a new depot, tighten with additional anchor bytes from the target function's body. Never add wildcards to fix uniqueness — that broadens matches, not narrows them.

Sigs live in [`source/dlls/VacLiveBypass/src/hooks/*.cpp`](../../source/dlls/VacLiveBypass/src/hooks/) as `constexpr std::string_view k_target_sig` literals.

---

## What breaks on major depot bumps

Rare, but happens (e.g. big engine rewrite, protobuf schema break):

- New field added to `CSGOInputHistoryEntryPB` → `MergeFrom` mask changes → protobuf serialization corrupts → cs2 crashes on subtick emit.
- New protobuf message class inserted before `CSGOInputHistoryEntryPB` in vtable table → VLB's vtable RVA `0x1A1E028` is wrong → wrong New() function called.
- Anti-cheat backports a new self-scan pattern → user-mode inline hooks detected in seconds → kernel-inject becomes mandatory.

Response: bump `FVA_STRICT_FINGERPRINT=ON`, aggressive fingerprint-mismatch abort, do full IDA session on the new client.dll to re-derive: RTTI descriptor xrefs for message classes → New() RVAs → vtable RVAs.

See [`source/dlls/VacLiveBypass/docs/DEPOT_UPDATE_PLAYBOOK.md`](../../source/dlls/VacLiveBypass/docs/DEPOT_UPDATE_PLAYBOOK.md) for the full 30-minute playbook (baseline snapshot, cs2-dumper run, IDA MCP session, T::New via RTTI, vtable RVAs).

---

## Cross-refs

- Current snapshot: [`DEPOT_STATE.md`](../../DEPOT_STATE.md)
- Detailed VLB playbook: [`source/dlls/VacLiveBypass/docs/DEPOT_UPDATE_PLAYBOOK.md`](../../source/dlls/VacLiveBypass/docs/DEPOT_UPDATE_PLAYBOOK.md)
- Runtime verification: [08_runtime_verification.md](08_runtime_verification.md)
- Offset feed: [github.com/a2x/cs2-dumper](https://github.com/a2x/cs2-dumper)
- Auto-adapt script: [`source/dlls/VacLiveBypass/scripts/auto_adapt_new_depot.ps1`](../../source/dlls/VacLiveBypass/scripts/)

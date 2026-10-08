# 02 — VacLiveBypass (VLB)

Source root: [`source/dlls/VacLiveBypass/`](../../source/dlls/VacLiveBypass/)
Product binary: `fva_recon.dll` (~82 KB)
Origin: 1:1 reimplementation of `FuckVacAgain.dll` (VMP 3.6+), reversed via Hex-Rays over the Scylla-unpacked rebuild.

VLB is the flagship of this repository. It is the only project that lives inside `cs2.exe` as an injected DLL — everything else (RankSpoofer, IsValveDS, KillTrigger) operates from kernel mode via `MmCopyVirtualMemory`.

---

## What VLB does per tick

Every tick (64 Hz) the CS2 client builds a `CSGOUserCmdPB` protobuf holding the player's input: viewangles, buttons, subtick state, movement axes. VLB detours three CS2 functions and, when armed, injects fabricated `CSGOInputHistoryEntryPB` entries into `input_history` (proto tag 2 on the CSGOUserCmdPB). The server's rewind step reads these entries to time-align hit registration; falsified entries move the server-side aim reconstruction away from the real click position, producing an anti-aim effect.

The mutation is ~30 lines in [`src/hooks/phase_b2.cpp::run_fva_section_j_emitter`](../../source/dlls/VacLiveBypass/src/hooks/phase_b2.cpp). Everything else is scaffolding, sig-scan, gate logic, arena bookkeeping, crash protection.

---

## Four hooks

All four verified in live cs2 memory on 2026-07-16 (PID 53000, build 14170):

| # | Target | Module | Live RVA (14170) | Purpose |
|---|---|---|---|---|
| H1 | `CBaseUserCmd::CreateMove` inner | client.dll | `0xB09528` | Main entry — mutation happens here |
| H2 | `IGameSystem::LevelInit` | client.dll | `0xB3A600` | Reset state on map load (force_reresolve + alt_symbol_reset) |
| H3 | `CBaseUserCmdPB::SerializePartialToArray` | client.dll | `0x11AD520` | Diagnostic: capture the final wire buffer |
| H4 | `ShouldUpdateSequences` | animationsystem.dll | `0x14F950` | Adjacent animation gate hook (FVA parity) |

Install method: **5-byte inline JMP rel32** (`E9 XX XX XX XX`) via MinHook. Same install pattern FVA uses (see `docs/reversing/fulldiff_client_dll.csv` rows 2/3/4 in the sibling repo).

Runtime JSON proof: [`docs/rt_verify_all_hooks_result.json`](../../docs/rt_verify_all_hooks_result.json).

---

## The gate

A single byte controls whether Section-J (the viewangle wrap + input_history reconstruction) runs.

- **FVA original:** `byte_7FFBE823A9A0` at FVA image + `0x23A9A0`. Init at `0x7FFBE80CA00B` (FNV1a-64 key `0xB6E8F068409FEF6C` decrypts `dword_7FFBE823A9CC`, result → gate byte). Check at `0x7FFBE80CA6B4` (`cmp cs:byte_7FFBE823A9A0, r13b(=0); jz loc_7FFBE80CAA2F`). Non-zero → armed.
- **VLB equivalent:** [`FVA_GATE_MODE`](../../source/dlls/VacLiveBypass/CMakeLists.txt) compile-time flag:
  - `byte` — reads FVA gate semantics (equivalent to armed byte).
  - `attack` — additional policy: only emit on fire (LMB/RMB detected via dual-path CUserCmd raw+0x60 OR CInButtonStatePB protobuf).

Byte mode = FVA-original 1:1. Attack mode = minimal detection surface (~10 % ticks emit). Detailed semantics: [`source/dlls/SafetyPlugin_recovered/docs/gate_byte_logic.md`](../../source/dlls/SafetyPlugin_recovered/docs/gate_byte_logic.md).

---

## Section-J emitter (the mutation)

Location: [`src/hooks/phase_b2.cpp::run_fva_section_j_emitter`](../../source/dlls/VacLiveBypass/src/hooks/phase_b2.cpp)

Per emit (up to 15 subticks per tick):

```
step   = CS2_CSGOInputHistoryEntryPB_New(subs.arena)   // 120 B via CS2's protobuf T::New
qangle = CS2_CMsgQAngle_New(nullptr)                   // 40 B, heap
qangle.{x,y,z} = prior + fraction * delta               // interpolate along wrap180(prior - target)
step[+0x18] = qangle                                     // step.view_angles
step[+0x60..0x68] = tick / fraction                     // FVA constants
step->has_bits |= 0x1E01                                 // presence flags
AddAllocated fast-path OR add_allocated_slow_path
```

Interpolation formula (1:1 from FVA helper `sub_7FFBE80C95B4`, IDA session `0edfdfab`):

```
interp = reference_cache_from_prev_tick + fraction * (prior - reference)
```

- Tick 1 (fresh, ref=0, prior=89°): last subtick = `0 + 1.0 * 89 = 89°` (single spoof)
- Tick N idle (ref=prev, prior=prev): last subtick = `prev + 0` (self-echo, NO append — write delta=0 into existing entry, per memory `fva-no-hotkey`)
- Tick N mouse move (ref=89, prior=95): last subtick = `89 + 1.0 * 6 = 95°` (smooth)

`s_reference_bits[3]` (line 1611 in the port) holds the reference cache; updated after emit (line 1806-1808) to `prior`. Emit call passes `tgt_x/y/z` (= reference cache) as base, `d_pitch/yaw/roll` (= prior - tgt) as delta.

---

## Protobuf schema targets

Recovered from the descriptor blob at FVA `0x7FFBE8210A00..0x7FFBE82163xx`. Method-name strings (`SerializeToArray`, `MergeFrom`, `ParseFrom`) have **zero code xrefs** in FVA rebuild — they are stripped/inlined. Pinning must be done via vtable pointer table around `0x7FFBE8215F2C`.

`CSGOInputHistoryEntryPB` (Section-J target, descriptor @ FVA `0x7FFBE8210A3A`):

| Tag | Field | Type | Notes |
|-----|---|---|---|
| 2 | view_angles | CMsgQAngle | ← Section-J target |
| 4 | render_tick_count | int32 | |
| 5 | render_tick_fraction | float | |
| 6 | player_tick_count | int32 | |
| 7 | player_tick_fraction | float | |
| 12-15 | interp fields | CSGOInterpolationInfoPB | |
| 64-69 | frame_number, target_ent_index, shoot_position, target_head/abs/ang_check | int32 / CMsgVector / CMsgQAngle | |

Factory: `CSGOInputHistoryEntryPB::New` @ FVA RVA `0x742730`, size **120 B**. Signature `B9 78` is NOT unique — must disambiguate via RTTI ("`?AVCSGOInputHistoryEntryPB@@`" descriptor xref) per memory `fva-targets-input-history`. Byte 4 of the ctor sled is `0x10`, not `0x08` (memory `cs2-t-new-rva-hardcoded`).

Full schema table: [`source/dlls/SafetyPlugin_recovered/docs/protobuf_schema.md`](../../source/dlls/SafetyPlugin_recovered/docs/protobuf_schema.md).

**Not touched by Section-J:** `subtick_moves` (proto tag 18 on `CBaseUserCmdPB`). Any VLB code path that mutates subtick_moves is a parity divergence.

---

## FNV1a-64 hashes (game_state resolver)

VLB uses 4 hashes to look up CS2 globals, 1:1 with FVA:

- `k_alt_symbol_field_hash` — FVA alt_symbol byte
- `k_subobj_base_hash` — protobuf sub-object base
- `k_fire_flag_byte_hash` — the fire-flag byte (memory `FVA no hotkey`)
- `k_live_subtick_counter_hash` — subtick counter

The main gate hash is FNV1a-64 `0xB6E8F068409FEF6C` (decrypts `dword_7FFBE823A9CC` at FVA gate init). Source: [`source/dlls/VacLiveBypass/src/hooks/game_state_resolver.cpp`](../../source/dlls/VacLiveBypass/src/hooks/game_state_resolver.cpp).

---

## Arena and ArenaStringPtr

CS2 uses Google Protobuf 3.21.8 with per-message arena allocation. Two critical ABI details VLB must get right:

**Arena word untag** (from FVA `sub_7FFBE80DC5A8`):
```cpp
auto untag_msg_arena = [](std::uint8_t* msg) -> std::uint64_t {
    const auto raw = *reinterpret_cast<std::uint64_t*>(msg + 8);
    if (raw & 2) return 0;                        // null arena tag
    auto untagged = raw & ~std::uint64_t{3};
    if (raw & 1) untagged = *reinterpret_cast<std::uint64_t*>(untagged);
    return untagged;
};
```

**`ArenaStringPtr::Set` this-pointer bug** (task #84): `move_crc` is a tagged-pointer field (bit 0 = kAllocated, bit 1 = kMutableArena, bit 2 = kDefault). You MUST pass `&move_crc` (address of slot), not `move_crc` (value). Passing value crashes cs2 in ~10 seconds.

Details: [`source/dlls/VacLiveBypass/README.md`](../../source/dlls/VacLiveBypass/README.md) §2.

---

## RepeatedPtrField grow / append / recycle

FVA `sub_7FFBE80CB348` (VLB `add_allocated_slow_path`) has 3 branches:

- **A: grow** — `!rep || current == total` → allocate new `Rep` via `IMemAlloc::Alloc`, copy elements, `subs->rep = new`.
- **B: swap-append** — `allocated < total` → `elements[allocated] = elements[current]; elements[current++] = step; allocated++`.
- **C: recycle** — `allocated == total && current < total && arena == 0` → overwrite `elements[current]` without alloc. Old element "leaks" — CS2's arena reclaims on next reset.

Early port bug: forcing branch C to grow crashed cs2 after ~200 ticks (subs->rep replaced, subs->total_size not reset → OOB in networksystem).

---

## Multi-depot support

[`src/version_manifest.h`](../../source/dlls/VacLiveBypass/src/version_manifest.h) has `#if FVA_TARGET_DEPOT == …` blocks:

| Depot buildid | client.dll MD5 | Size |
|---|---|---|
| 14167 (baseline) | `b0fd08261be12cceb8e5636500e5a1d0` | 37 272 728 B |
| 24134959 (current) | `16917fce6c15715434f6604e8086d38a` | 37 419 160 B |

RVA drift 14167 → 24134959:

```
Hook A CreateMove:      +0x3A598  (0xACEF90  → 0xB09528)
Hook B LevelInit:       +0x3C650  (0xAFDFB0  → 0xB3A600)
Hook C Serialize:       +0x23BB0  (0x1189930 → 0x11AD4E0 nominal, +0x40 at 14170 runtime → 0x11AD520)
CBaseUserCmdPB::New:    +0x30120
CSubtickMoveStep::New:  +0x30120
CInButtonStatePB::New:  +0x30120
CMsgQAngle::New:        -0x28F00
CSGOInputHistoryEntry:  +0x34CE0
CBaseUserCmdPB vtable:  +0x3FE40
ArenaStringPtr::Set:    +0x23BB0
```

VLB pattern-scan handles up to +0x960 drift automatically. See [09_depot_updates.md](09_depot_updates.md) for the update procedure.

---

## Build

```powershell
cd source\dlls\VacLiveBypass

# attack mode (fire-gated, minimal detection)
cmake -B build -DFVA_TARGET_DEPOT=24134959 -DFVA_GATE_MODE=attack
cmake --build build --config Release --target fva_recon

# byte mode (FVA-original 1:1, always-on when armed)
cmake -B build_byte -DFVA_TARGET_DEPOT=24134959 -DFVA_GATE_MODE=byte
cmake --build build_byte --config Release --target fva_recon

# baseline depot 14167
cmake -B build_14167 -DFVA_TARGET_DEPOT=14167
cmake --build build_14167 --config Release --target fva_recon

# with verbose H1 logging (for reverse-dev)
cmake -B build_verbose -DFVA_TARGET_DEPOT=24134959 -DFVA_VERBOSE_H1=ON
```

Artefacts:
- `build/Release/fva_recon.dll` (~82 KB)
- `build_byte/Release/fva_recon.dll`
- `build_14167/Release/fva_recon.dll`

Also shipped in `releases/` under the source root and in `build/kit_*` for double-click use.

---

## Runtime debug

Default is quiet in retail. Enable via:

- `set FVA_DEBUG=1` in the shell, OR
- Create the marker file `C:\vmp\.fva_debug`.

Log path: `C:\vmp\fva_recon.log`.

Key log lines:

```
[fva_recon][offsets] LIVE-fetched cs2-dumper HEAD OK (body 1890 bytes)
[fva_recon][engine2] signon read: ptr=… value=6 (FULL) ok=1
[State] CCSGOInput @ … (RVA 0x23B95F0) vft=…
[Hook-A] tick=N SpoofEmit fired #M mode=attack engine=1 alive=1 fire=1
[ViewSpoof] FIRE tick — prior=(89..) delta=(89..) expected_final_pitch=178
subtick_moves.size N → 15
[MOVE_CRC] set ok via ArenaStringPtr::Set
```

Metric summary interpretation: [`source/dlls/VacLiveBypass/docs/VERIFICATION_TABLE.md`](../../source/dlls/VacLiveBypass/docs/VERIFICATION_TABLE.md).

---

## Injection

VLB does not ship an injector; use `source/tools/CS2UnifiedInjector/` (8 methods) or the standalone kits (`build/kit_vlb_attack_gated/`, `build/kit_vlb_byte_gated/`, `build/kit_vlb_default/`) which use kernel-IOCTL inject via `CS2HexSyncCompatDriver`.

Kernel injection is preferred: FVA's 5.6 kHz `NtReadVirtualMemory` self-scan detects user-mode inline hooks within seconds. Kernel-side hooks bypass the syscall path entirely.

Details: [07_build_install_usage.md](07_build_install_usage.md).

---

## Cross-refs

- Rebuild source of truth: `C:\vmp\fva_livedump\FuckVacAgain_rebuild.exe`
- FVA-side pseudo-C: [`source/dlls/SafetyPlugin_recovered/hooks/create_move_hook.pseudo.cpp`](../../source/dlls/SafetyPlugin_recovered/hooks/create_move_hook.pseudo.cpp) — 173 lines, banner "unverified"
- Runtime verification pipeline: [08_runtime_verification.md](08_runtime_verification.md)
- Parity check vs FVA: [`source/dlls/SafetyPlugin_recovered/docs/vlb_gap.md`](../../source/dlls/SafetyPlugin_recovered/docs/vlb_gap.md)
- Full port notes: [`source/dlls/VacLiveBypass/docs/FVA_FULL_PORT_2026-07-10.md`](../../source/dlls/VacLiveBypass/docs/FVA_FULL_PORT_2026-07-10.md)
- VMP protection dissection: [`docs/VMP_PROTECTION_MECHANICS_FULL.md`](../../docs/VMP_PROTECTION_MECHANICS_FULL.md)

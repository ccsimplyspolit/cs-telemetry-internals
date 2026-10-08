# 05 — SafetyPlugin_recovered

Reconstructed source-code skeleton of `FuckVacAgain.dll` (internal name: **SafetyPlugin-Unprotected**, confirmed from leaked source paths + strings). Extracted via bulk Hex-Rays decompilation of the Scylla-unpacked runtime dump (`rebuild.i64`).

**Not for build.** Every `.pseudo.cpp` carries an "unverified" banner and preserves the original decompiled body inline as reference. This tree is a research artefact meant to sit side-by-side with VLB source when diffing for parity.

Source root: [`source/dlls/SafetyPlugin_recovered/`](../../source/dlls/SafetyPlugin_recovered/)

---

## Layout

```
SafetyPlugin_recovered/
├── README.md                                    bilingual overview
├── DEVIRT_STATUS.md                             per-module recovery confidence
├── hooks/
│   ├── create_move_hook.pseudo.cpp              H1 body (Section A–K state atlas)
│   ├── level_init_hook.pseudo.cpp               H2 body
│   └── serialize_to_array_hook.pseudo.cpp       H3 body
├── core/
│   ├── dllmain.pseudo.cpp                       DllMain / TLS_Callback_0 / OEP
│   ├── gate_check.pseudo.cpp                    byte_7FFBE823A9A0 gate init + check
│   └── input_history_spoof.pseudo.cpp           Section-J angle-fixup / input_history reconstruction
└── docs/
    ├── playbook.md                              6-day devirt playbook (consolidated from 16 deob_docs)
    ├── hook_map.json                            structured hook_targets_found / critical_functions
    ├── protobuf_schema.md                       CSGOUserCmdPB / CSGOInputHistoryEntryPB / CInButtonStatePB
    ├── gate_byte_logic.md                       semantics of byte_7FFBE823A9A0
    └── vlb_gap.md                               FVA ↔ VLB parity gap analysis
```

Total: 13 files, 1332 lines.

---

## Anchors

Values relative to the rebuild image base `0x7FFBE8000000` (`C:\vmp\fva_livedump\FuckVacAgain_rebuild.exe`).

| Item | Value |
|---|---|
| OEP RVA | `0x122C` |
| Packer entry | `0x3ED6D9` |
| TLS_Callback_0 RVA | `0x374254` |
| Shared VMP dispatcher | `sub_7FFF424EE1C0` (RVA `0x43E1C0`) |
| Tail-return handler | `sub_7FFF424D44B7` (RVA `0x4244B7`) |
| IAT `NtProtectVirtualMemory` | RVA `0x23B020` |
| Rebuild image base (live) | `0x7FFBE8000000` |
| Gate byte | `byte_7FFBE823A9A0` |
| Hook A body | `sub_7FFBE80C9D8C` |
| VMP dynamic import resolver | `sub_7FFBE82ED25E` (1.7 MB, VMP-blocked) |

---

## Devirt confidence per hook

| Module | Target | Confidence | VLB counterpart |
|---|---|---|---|
| H1 CreateMove | client.dll +0xACEF90 live / +0xB09528 current | **CONFIRMED** (runtime-verified 2026-07-16) | `create_move_hook.cpp` |
| H2 LevelInit | client.dll +0xAFDFB0 / +0xB3A600 | **CONFIRMED** (runtime-verified) | `level_init_hook.cpp` |
| H3 SerializePartialToArray | client.dll +0x1189930 / +0x11AD520 (+0x40 drift on 14170) | **CONFIRMED** (runtime-verified) | `serialize_to_array_hook.cpp` |
| H4 ShouldUpdateSequences | animationsystem.dll +0x14F950 (+0x960 drift) | **CONFIRMED** (runtime-verified) | `animation_hook.cpp` |
| H_DynamicResolver_Internal | FVA-internal `sub_7FFBE82ED25E` | **VMP-BLOCKED** | n/a (opaque `fva_resolve_import()` boundary) |

Details: [`DEVIRT_STATUS.md`](../../source/dlls/SafetyPlugin_recovered/DEVIRT_STATUS.md).

Legend:
- **CONFIRMED** — decompiled body matches live-install site AND semantics are cross-validated against VLB port.
- **PLAUSIBLE** — signature/behavioral match but at least one cross-check missing.
- **UNCONFIRMED** — no live-install evidence and/or Hex-Rays failed on containing function.
- **VMP-BLOCKED** — function body still virtualized in `.#I5` / `.#?n`; only I/O boundary known.

---

## Gate byte (`byte_7FFBE823A9A0`)

The single ENABLE flag for Section-J. Full write-up in [`docs/gate_byte_logic.md`](../../source/dlls/SafetyPlugin_recovered/docs/gate_byte_logic.md).

Init site (`0x7FFBE80CA00B`):
```asm
call    sub_7FFBE80FB1C4               ; FNV1a decrypt of dword_7FFBE823A9CC
                                       ; with key 0xB6E8F068409FEF6C
mov     cl, [rax+rdi]                  ; rax = decoded RVA table base, rdi = index
mov     cs:byte_7FFBE823A9A0, cl       ; populate gate byte from manifest
mov     [rax+rbx], dil                 ; dil == 0 -> zero companion slot at rbx
```

Check site (`0x7FFBE80CA6B4`):
```asm
cmp     cs:byte_7FFBE823A9A0, r13b     ; r13b = 0 (xor r13d, r13d earlier)
jz      loc_7FFBE80CAA2F               ; skip ~900 B of Section-J
```

- `byte == 0` → `JZ` taken → skip Section-J code.
- `byte != 0` → fall through into view-angle wrap + input_history reconstruction path.

No hotkey, no `g_target_armed` — only this single byte gates whether the reconstruction runs.

---

## Protobuf schema (recovered)

Descriptor blob at `0x7FFBE8210A00..0x7FFBE82163xx`. Method-name strings (`SerializeToArray`, `MergeFrom`, `ParseFrom`, `CopyFrom`, `SerializePartialToArray`) have **zero code xrefs** in the rebuild — stripped/inlined. Pinning must go through the vtable pointer table around `0x7FFBE8215F2C`.

`CSGOInputHistoryEntryPB` (Section-J target):
- Factory: `CSGOInputHistoryEntryPB::New` @ RVA `0x742730`, size **120 B**.
- Sig `B9 78` is NOT unique — disambiguate via RTTI descriptor xref.
- Byte 4 of the ctor sled is `0x10`, not `0x08`.
- `MergeFrom` @ `0x7FFBE80F8B4C` (usercmd.pb.cpp:879), mask `0x7F` copies 7 fields (qword@+24, byte@+32, 5 dwords @ +36..+52).

`CSGOUserCmdPB` (outer message):
- `MergeFrom` @ `0x7FFBE80F853C` (usercmd.pb.cpp:507), 3 qword pointer fields @ +0x18 / +0x20 / +0x28.
- vtable RVA FVA targets for input_history: **`0x1A1E028`**.

`CInButtonStatePB` (button-state message):
- dtor / vtable install: `sub_7FFBE80F80F0` (usercmd.pb.cpp:350).
- 3 uint64 tags (buttonstate1/2/3).

`CSubtickMoveStep`: descriptor @ `0x7FFBE8215FE2`. **Not touched by Section-J.** Any VLB code path mutating `subtick_moves` is a parity divergence.

Full table: [`docs/protobuf_schema.md`](../../source/dlls/SafetyPlugin_recovered/docs/protobuf_schema.md).

---

## Reconstruction workflow (6-day playbook)

Consolidated from 16 VMP-Deob docs. Full text: [`docs/playbook.md`](../../source/dlls/SafetyPlugin_recovered/docs/playbook.md).

**Day 1** — OEP capture + Scylla dump + VMEntry site scan.
- Attach to cs2 via `mydbg --stealth`, INT3/HW BP at `image_base + 0x122C`, deferred `bpdll FuckVacAgain.dll` BEFORE inject.
- Scylla dump of unpacked FVA (IAT lands in `.=ly` @ RVA 0x23B000).
- VMEntry pattern scan across the rebuild.

**Day 2** — Handler taxonomy scan across `.#I5` and `.#?n` using 10 canonical handler names (`vEntry_Prologue`, `vDispatcher_JmpR9`, `vTapeFetch`, `vValueCryptor_Chain`, etc.). Output: `day2_handlers.json`.

**Day 3** — Live trace through the shared dispatcher `sub_7FFF424EE1C0` (17+ callers) with per-caller chunking on the tail-return canary at RVA `0x4244B7`.

**Days 4–6** — Symbolic p-code emission per handler → Z3-driven simplification → JIT-friendly reassembly of `.#I5` / `.#?n` → parity diff against VLB → emit final pseudo-C to `SafetyPlugin_recovered/`.

Blocking constraint: **5.6 kHz `NtReadVirtualMemory` self-scan on `.text`** kills user-mode inline hooks in seconds. Options are kernel-mode shadow (via `km_driver.c` lazy IOCTL) or HW breakpoints only.

---

## VLB parity gaps

From [`docs/vlb_gap.md`](../../source/dlls/SafetyPlugin_recovered/docs/vlb_gap.md):

**H1 CreateMove:** MATCH. FVA installs 5-byte JMP at `client.dll+0xACEF90`. VLB `create_move_hook.cpp` is a monolithic 1:1 port of `sub_7FFBE80C9D8C` with explicit +offset comments (A.1..K.2, section D `alt_symbol`, section J viewangle wrap). VLB additions not present in FVA: SEH gates, `engine2_stable` gate, `FVA_GATE_MODE_ATTACK` / `FVA_GATE_MODE_BYTE` toggle. Observable side-effects match: cvar zero, alt-byte zero, subtick emit, viewangle echo, scratch mirror, move_crc regen.

**H2 LevelInit:** MATCH. VLB calls `g_original` FIRST (matches FVA order), then `game_state::force_reresolve`, `alt_symbol_reset`, `engine2::notify_level_init_complete`.

**H3 SerializePartialToArray:** MATCH. VLB is capture-only, vtable-RVA fingerprint distinguishes `CBaseUserCmdPB` from siblings (LazyString wrapper broke `GetTypeName`). Corpus proof of target message family: `CInButtonStatePB` dtor, `CSGOUserCmdPB::MergeFrom` @ line 507, `CSGOInputHistoryEntryPB::MergeFrom` @ line 879.

**H4 ShouldUpdateSequences:** CONFIRMED via runtime memory read. Legacy RVA `0x14EFF0` no longer contains the sig on 14170 (+0x960 drift). VLB pattern-scanner resolves to `0x14F950` automatically. FVA-side install could not be confirmed statically (livedump lacks animationsystem.dll CSV; FVA install lives inside `sub_7FFBE82ED25E` VMP blob) — but the TARGET FUNCTION exists exactly where VLB expects.

**Section-J targets `CSGOInputHistoryEntryPB.view_angles` (proto tag 2) via vtable RVA `0x1A1E028`. It does NOT touch `subtick_moves` (proto tag 18 on CBaseUserCmdPB).** Any VLB path that mutates subtick_moves is a divergence.

**Per memory `fva-no-hotkey`:** reconstruction code MUST NOT reintroduce a `g_target_armed` variable; self-echo is a **delta=0 write into the existing entry**, NOT an append.

---

## Cross-cutting risks

- **NtReadVirtualMemory self-scan @ 5.6 kHz** — forbids user-mode inline hooks in FVA `.text`; kernel shadow or HW BPs only.
- **VMP dynamic import resolver** `sub_7FFBE82ED25E` (1.7 MB) is the only site referencing `SetThreadContext` / `SuspendThread` / `Thread32First` / `Thread32Next`. IAT slots `NtProtectVirtualMemory` / `VirtualProtect` / `NtAllocateVirtualMemory` have **zero direct xrefs** — must be resolved through this VMP blob. Not decompilable without full VMP unwind.
- **Protobuf method-name strings stripped/inlined** — no code xrefs from `CSGOUserCmdPB`, `SerializeToArray`, `MergeFrom`. Descriptor blobs present at `0x7FFBE8210A00..0x7FFBE82163xx` but init function must be pinned by pointer-table scan, not string xref.

---

## Cross-refs

- FVA rebuild binary: `C:\vmp\fva_livedump\FuckVacAgain_rebuild.exe` (Scylla-unpacked, Hex-Rays works)
- FVA immutable original: `C:\vmp\FuckVacAgain.dll` (VMP-locked, static disasm shows all-zero `.text`)
- Sibling repo tooling: [ccsimplyspolit/VMP-Deob](https://github.com/ccsimplyspolit/VMP-Deob) v2.0
- Standalone VMP static analyzer: [06_fva_devirt.md](06_fva_devirt.md)
- VMP mechanics: [`docs/VMP_PROTECTION_MECHANICS_FULL.md`](../../docs/VMP_PROTECTION_MECHANICS_FULL.md)

# CS2-P2C-TEMPLATES — English Wiki Index

Security-research templates for Counter-Strike 2. VMProtect devirtualization, kernel-driver spoofing, live payload injection. Windows 10/11 x64 only.

> **Not for use on Valve live servers.** Injecting into matchmaking violates Steam SSA and CS2 EULA. Everything here is scoped to `-insecure` local dedicated servers, bug-bounty work, and academic reversing.

---

## Reading order

1. [01 Project overview](01_project_overview.md) — the three products at a glance.
2. [07 Build / install / usage](07_build_install_usage.md) — get a working DLL out the door.
3. [02 VLB deep dive](02_vlb.md) — the core anti-VAC payload, hook by hook.
4. [08 Runtime verification](08_runtime_verification.md) — prove the hooks landed on live memory.
5. [09 Depot updates](09_depot_updates.md) — how to keep everything working when Valve patches CS2.

The rest can be read as reference:

- [03 RankSpoofer](03_rankspoofer.md) — client-side visual rank/profile spoof.
- [04 IsValveDS](04_isvalveds.md) — one-byte spoofer for `C_CSGameRules::m_bIsValveDS`.
- [05 SafetyPlugin_recovered](05_safetyplugin_recovered.md) — reconstructed FVA source-code skeleton (research only, does not build).
- [06 fva_devirt](06_fva_devirt.md) — self-contained VMP static analyzer.
- [10 Glossary](10_glossary.md) — terms and abbreviations.

---

## Repo map (top level)

```
MyDriver23/
├── README.md                     bilingual root readme (RU + EN)
├── ARCHITECTURE.md               how the 12 projects wire together
├── CLAUDE.md                     Claude Code development notes
├── DEPOT_STATE.md                current CS2 offsets snapshot
├── LICENSE                       research-only
├── docs/                         reversing notes, release notes, VMP mechanics
│   ├── VMP_PROTECTION_MECHANICS_FULL.md   6-layer VMP 3.6+ dissection
│   ├── FVA_PROTECTION_STATE.md            FVA-specific analysis
│   ├── VLB_VERIFICATION_AGAINST_VMP_CONTRACT.md
│   ├── DRAFT_VM_PAYLOAD_CORRELATION_REVIEW.md
│   ├── RELEASE_NOTES_v1.14-claude.md
│   ├── RELEASE_NOTES_v1.15-claude.md
│   ├── MORNING_REPORT_2026-07-16.md
│   ├── NLINJECTOR_REVERSE.md              reverse of NLinjector(2).exe
│   ├── DRIVER_HARDENING.md
│   ├── VULNERABLE_DRIVERS.md              KDU 65-provider catalog
│   ├── ETHICS.md                          legal boundaries
│   └── wiki/                              older wiki (INSTALL / WORKFLOW / etc.)
├── source/
│   ├── apps/                     CS2IsValveDSSpooferConsole, CS2RankSpooferConsole
│   ├── dlls/                     VacLiveBypass, SafetyPlugin_recovered, fva_devirt
│   ├── drivers/                  CS2HexSyncCompatDriver, CS2IsValveDSSpooferDriver,
│   │                             CS2KillTriggerDriver, CS2RankSpooferDriver
│   ├── lua_reverse/              Aimware VACLiveGuard.lua devirt
│   └── tools/                    CS2UnifiedInjector, KernelDriverMapper/Unmapper,
│                                  CS2MemoryTool, KbdClassAnalyzer
├── build/
│   ├── kit_vlb_attack_gated/               ready-to-ship VLB payload, fire-gated
│   ├── kit_vlb_byte_gated/                 ready-to-ship VLB payload, always-on
│   ├── kit_vlb_default/        kernel-driven variant of kit_vlb_attack_gated
│   ├── kit_isvalveds/            IsValveDS spoofer standalone
│   └── kit_rankspoof/            RankSpoofer standalone
├── scripts/
│   └── runtime_verify/           H1–H4 live-memory verification pipeline
├── third_party/                  KDU submodule
└── wiki/                         (you are here)
```

---

## Version and target

| Field | Value |
|---|---|
| CS2 build number | **14170** (also verified on 14169) |
| Depot ID | 24134959 |
| Baseline depot | 14167 (for regression) |
| client.dll SHA256 change | tolerated — 32/32 globals + 3189/3189 schema fields identical between 14169 and 14170 |
| VLB gate mode | `attack` (fire-only) or `byte` (always-on), pick at CMake time |
| Verification date | 2026-07-16 (live memory read) |

---

## Runtime parity tally (from `docs/RELEASE_NOTES_v1.15-claude.md`)

| Hook | Module | Live RVA (14170) | Sig hits | Verdict |
|---|---|---|---|---|
| H1 CreateMove | client.dll | `0xB09528` | 1 unique | verified |
| H2 LevelInit | client.dll | `0xB3A600` | 1 unique | verified |
| H3 SerializePartialToArray | client.dll | `0x11AD520` | 1 unique | verified (+0x40 drift, sig-scan handles it) |
| H4 ShouldUpdateSequences | animationsystem.dll | `0x14F950` | 1 unique | verified (+0x960 drift, sig-scan handles it) |

Raw JSON: `../../docs/rt_verify_all_hooks_result.json`.

---

## Cross-refs

- Sibling repo (VMP mechanics + Python devirt tools): [ccsimplyspolit/VMP-Deob](https://github.com/ccsimplyspolit/VMP-Deob)
- Offset feed: [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper) — HEAD is auto-fetched by VLB and Load-Spoofer scripts.
- FVA original (immutable): `C:\vmp\FuckVacAgain.dll` (2 224 128 B, SHA256 `af02612545e4f849…eb6d319`).
- Rebuild dump (readable): `C:\vmp\fva_livedump\FuckVacAgain_rebuild.exe` — Hex-Rays works, VMP unpacked in memory.

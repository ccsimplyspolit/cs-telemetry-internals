# 01 — Project overview

CS2-P2C-TEMPLATES is a security-research repository. It publishes source and pre-built kits for three CS2-adjacent products plus one reference project:

| # | Product | Kind | What it does |
|---|---|---|---|
| 1 | **VacLiveBypass** (VLB) | injected DLL (`fva_recon.dll`) | 1:1 native-layer reimplementation of `FuckVacAgain.dll` — mutates `CBaseUserCmdPB.input_history` before wire-serialization to spoof viewangles across subticks. |
| 2 | **RankSpoofer** | kernel driver + TUI console | Client-side visual spoof of rank / wins / losses / profile fields via `KeStackAttachProcess` + `MmCopyVirtualMemory` writes into `CCSPlayerController`. |
| 3 | **IsValveDS** | kernel driver + console | One-byte spoof of `C_CSGameRules::m_bIsValveDS` so the client thinks it is (or isn't) on an official Valve dedicated server. |
| 4 | **SafetyPlugin_recovered** | pseudo-C reconstruction | Reference-only decompiled skeleton of `FuckVacAgain.dll` (13 files, 1332 lines). Diff target for VLB parity work. **Does not build.** |

Plus the tooling:

| Tool | Kind | Purpose |
|---|---|---|
| CS2UnifiedInjector | user EXE | 8 DLL injection methods including kernel-IOCTL via CS2HexSyncCompatDriver. |
| CS2HexSyncCompatDriver | kernel .sys | Byte-for-byte reimplementation of NLinjector's HexSyncService.sys IOCTL API. |
| CS2KillTriggerDriver | kernel .sys | Kill-hotkey via kbdclass callback injection on round-kill increment. |
| CS2MemoryTool | user EXE | Read/write/scan any process memory via 4 backends (RPM, NtRPM, IOCTL, KDU). |
| KernelDriverMapper / Unmapper | user EXE | KDU-style loader/unloader for unsigned `.sys` via vulnerable driver exploit. |
| KbdClassAnalyzer | user EXE | Native PE + PDB analyzer for `kbdclass.sys`, feeds KillTrigger driver via registry. |
| fva_devirt | user EXE | Standalone C++ VMP static analyzer (this repo, `source/dlls/fva_devirt/`). |
| lua_reverse | Lua | Byte-for-byte devirt of Luraph v14.2 VM used by Aimware `VACLiveGuard.lua`. |

---

## Which do I want?

- **You want an anti-VAC helper for local testing.** VLB. Use `build/kit_vlb_attack_gated/` (fire-gated, ~10 % of ticks emit) or `build/kit_vlb_byte_gated/` (always-on).
- **You want to display any rank / profile in your CS2 UI.** RankSpoofer. Use `build/kit_rankspoof/`.
- **You want your client to report Valve DS = 1 to itself.** IsValveDS. Use `build/kit_isvalveds/`.
- **You are reverse-engineering FVA.** Read `source/dlls/SafetyPlugin_recovered/` for pseudo-C bodies, then `source/dlls/fva_devirt/` for the static analyzer.
- **You are researching the VMP protection stack itself.** Read `docs/VMP_PROTECTION_MECHANICS_FULL.md` (the 6-layer dissection) then `docs/FVA_PROTECTION_STATE.md` and the sibling repo [VMP-Deob](https://github.com/ccsimplyspolit/VMP-Deob).

---

## How the products interact

They are independent. They can all be loaded at once and none of them shares in-process state with any other:

- VLB injects `fva_recon.dll` into `cs2.exe`. RankSpoofer and IsValveDS drivers live in the kernel and reach into `cs2.exe` via `MmCopyVirtualMemory`. No shared handles, no shared allocations.
- The only user-mode ↔ kernel-mode contract for the spoofer drivers is SHM (`\BaseNamedObjects\...State` sections) + named events (`...Stop` / `...Stopped`).

Injection tooling (CS2UnifiedInjector + CS2HexSyncCompatDriver) is optional. The prebuilt kits already carry a launcher (`Launch-Inject.ps1`) that wraps 12 steps: DSE off via KDU → driver load → API-hook bypass → allocate/write DLL path → remote thread → DSE restore → service cleanup.

---

## Why native reimplementation instead of unpacking FVA?

`FuckVacAgain.dll` is a VMProtect 3.6+ VM-obfuscated binary. Its `.text` section is zeroed on disk; a p-code tape in `._I5` and a handler executor in `._?n` reconstruct it in memory at runtime. Only two options to defeat this:

1. **Devirtualize** the p-code → clean PE. Estimated 2–3 weeks with the VMPAttack/NoVmp toolchain, and public tooling only covers VMP 3.5.1 fully — 3.6+ needs manual work on the delta (AddGate mutation, post-VMEntry AntiDebug injection, paired-route CRC).
2. **Reimplement** the observable behavior on the native CS2 layer. VLB does this. It never touches FVA's VM state, VM code, or handler executor. It hooks the same native CS2 functions that FVA's decrypted callbacks eventually reach.

Reimplementation is:

- **Depot-portable** — VLB auto-fetches offsets from `a2x/cs2-dumper` HEAD via WinHTTPS at DLL init. FVA has offsets baked into its VM and needs a rebuild per depot.
- **Debuggable** — everything is in un-obfuscated C++.
- **Cheap** — a single-digit KLOC codebase vs multi-week symbolic execution.

Trade-off: reimplementation does **not** reproduce FVA's anti-tamper self-scan silhouette. If the anti-cheat learns to detect specifically FVA's 5.6 kHz `NtReadVirtualMemory` scan pattern via kernel telemetry, VLB will lack that fingerprint. Not observed as of 2026-07-16.

---

## Reference source of truth

- **FVA immutable original:** `C:\vmp\FuckVacAgain.dll` (2 224 128 B, SHA256 `af02612545e4f849…eb6d319`). VMP-locked, static disasm shows all-zeros in `.text`.
- **FVA rebuild dump:** `C:\vmp\fva_livedump\FuckVacAgain_rebuild.exe` — Scylla-unpacked. Hex-Rays works on this. 4776 functions, 92 named, 3025 strings. IDA session id `dddfaf60`.
- **CS2 live memory:** used for hook target verification (see [08_runtime_verification.md](08_runtime_verification.md)).

Any RVA or symbol claim in this wiki should be cross-referenced against one of the three.

---

## Legal boundary in one paragraph

Injecting VLB, RankSpoofer, or IsValveDS into `cs2.exe` while it connects to Valve matchmaking is unauthorized modification of a running service. That violates the Steam Subscriber Agreement, CS2 EULA, and computer-misuse statutes in most jurisdictions (US CFAA § 1030, UK Computer Misuse Act 1990 § 3, Germany StGB § 303a/303b). Test only on:

- Local `-insecure` dedicated servers with `map de_dust2` + bots.
- CTF-style controlled infrastructure.
- Your own CS2 shard (unlikely — but VLB has been used against private CS2 mods).

See `../../docs/ETHICS.md` for the full legal writeup.

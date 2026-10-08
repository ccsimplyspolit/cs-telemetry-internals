# 10 — Glossary

Terms, abbreviations, and CS2/reversing jargon used across the wiki.

---

## Products in this repo

**VLB (VacLiveBypass)** — the flagship injected DLL, `fva_recon.dll`. 1:1 native-layer reimplementation of FVA.

**FVA (FuckVacAgain)** — the original VMProtect-obfuscated anti-VAC helper DLL (`FuckVacAgain.dll`, SHA256 `af02612545…`, internal name "SafetyPlugin-Unprotected"). VLB reimplements its observable behavior.

**RankSpoofer** — kernel driver + TUI console for client-side visual spoof of rank / profile / matchmaking fields.

**IsValveDS** — kernel driver + console for one-byte spoof of `C_CSGameRules::m_bIsValveDS`.

**KillTrigger** — kernel driver for kill-hotkey via kbdclass callback on round-kill increment.

**HexSyncCompatDriver** — kernel driver reimplementing NLinjector's HexSyncService.sys IOCTL API for `--method kernel` DLL injection.

**SafetyPlugin_recovered** — pseudo-C reconstruction of FVA (research only, does not build).

**fva_devirt** — standalone C++ VMP static analyzer.

---

## Anti-cheat and injection

**VAC** — Valve Anti-Cheat. Server-side detection; VLB targets *bypass*, but publisher will not answer support tickets about it.

**Section-J** — the subtick emitter in FVA `sub_7FFBE82E8C32`. Ports to VLB `phase_b2.cpp::run_fva_section_j_emitter`. Iterates 15 subticks per tick, emits `CSGOInputHistoryEntryPB` entries into `input_history` (proto tag 2) via CS2's protobuf `T::New`.

**Gate byte** — FVA `byte_7FFBE823A9A0`, single-byte ENABLE flag. Init at `0x7FFBE80CA00B`, check at `0x7FFBE80CA6B4`. Non-zero → Section-J armed.

**Attack mode / Byte mode** — VLB `FVA_GATE_MODE` compile-time flag. `attack` = fire-gated (LMB/RMB detect). `byte` = FVA-original 1:1 (armed byte only).

**FNV1a-64** — hash function used by FVA for game_state resolver. Main gate hash: `0xB6E8F068409FEF6C`.

**T::New (protobuf)** — CS2's per-message-class arena allocator entry point. VLB uses CS2's own T::New to allocate `CSGOInputHistoryEntryPB` (RVA `0x742730`, 120 B).

**Rep grow / swap-append / recycle** — three branches of protobuf `RepeatedPtrField::add_allocated_slow_path` (FVA `sub_7FFBE80CB348`). A = grow, B = swap+append, C = recycle.

**ArenaStringPtr** — protobuf tagged-pointer field type (3 bits: kAllocated, kMutableArena, kDefault). `move_crc` in `CSGOUserCmdPB` uses this. Must pass address-of-slot to Set(), not value.

**Signon-latch** — VLB's engine2 signon-state readback (crash fix from memory `FVA no hotkey`).

**Self-echo** — write delta=0 into the existing entry, NOT an append. Applies when tick idle and reference cache equals prior.

---

## Injection / kernel

**KDU** — Kernel Driver Utility ([hfiref0x/KDU](https://github.com/hfiref0x/KDU)). 65 vulnerable driver providers for DSE bypass and manual-map.

**kdmapper** — Manual-map loader for unsigned drivers via `iqvw64e.sys` exploit. Both TheCruZ and skadro variants used as historical references. **Retired** — the project now uses `kdu.exe -map` (`third_party/KDU`) exclusively.

**iqvw64e.sys** — Intel NAL driver (CVE-2015-2291). Provides arbitrary kernel R/W via IOCTL.

**RTCore64** — MSI Afterburner core driver (CVE-2019-16098). KDU's default provider.

**DSE** — Driver Signature Enforcement. Windows requires signed kernel drivers. DSE-off = KDU patches `ci.dll!g_CiOptions` in kernel memory.

**HVCI** — Hypervisor-protected Code Integrity (Windows 10/11 Memory Integrity). If enabled, RTCore64 is blocklisted; use Intel NAL via `-KduProvider 0`.

**KDU providers.md** — [full catalog of 65 vulnerable drivers](https://github.com/hfiref0x/KDU/blob/master/Help/providers.md).

**Vulnerable Driver Blocklist** — Microsoft's blocklist that disables known-vulnerable drivers. Toggled off in HKLM by Load-Spoofer / Launch-Inject scripts on Win11 22H2+.

**MmCopyVirtualMemory** — Windows kernel API for cross-process memory copy without OpenProcess handle. Used by all spoofer drivers.

**KeStackAttachProcess** — attach current thread to another process's address space. Required for cross-proc allocations and PEB walks.

**PsAcquireProcessExitSynchronization** — Windows 8.1+ hard guard preventing target process exit during our writes. See [`docs/DRIVER_HARDENING.md`](../../docs/DRIVER_HARDENING.md) §1.

**SCM / SC** — Service Control Manager. Standard Windows driver loading path (`sc create` + `sc start`).

**SHM** — Shared memory. Used for user↔kernel contract in spoofer drivers via `\BaseNamedObjects\...State` sections.

---

## VMProtect

**VMP** — VMProtect. Commercial code protector by VMPSoft. Versions 3.5.1 (leaked sources at `C:\vmp\vmp-3.5.1-src\`) and 3.6+ (used by FVA).

**vtAdvanced / vtClassic** — VMP virtualization modes. Advanced uses register-indirect dispatch; Classic uses 0x100-entry jump table. FVA has BOTH mixed (34 Advanced sites + 1 Classic).

**p-code** — VMP's virtual machine bytecode. FVA's p-code lives (encrypted) in `.#?n` section, decrypted at runtime into `.#I5` (652 KB decrypted tape).

**Handler executor** — the x86 code in `.#?n` that walks the p-code tape and dispatches to handlers.

**AddGate** — VMP's VM entry stub emitter. 3.5.1 outputs 2 instructions (`push imm; call vm_entry`). 3.6+ outputs 15+ with MBA obfuscation → FVA is 3.6+.

**MBA (Mixed Boolean Arithmetic)** — obfuscation technique. `add + sub + xor` chains that reduce to a constant but resist symbolic analysis.

**VMExit tail** — universal return point from VM to native. In FVA: `add rsp, 138h; retn` at `0x18023d25e` — exactly 1 occurrence.

**jmp_registr / crypt_registr / pcode_registr / stack_registr** — 4 randomly picked anchor registers per build. FVA build: `jmp = R10`, `crypt = RDI`, `pcode = RBP` (hypothesis), `stack = RSP`.

**OpcodeCryptor** — VMP's rolling-key opcode decryption. In 3.5.1: hardcoded XOR (`ccXor`), not random.

**ValueCryptor** — per-operand crypt chain. 3-100 random ops (XOR/ADD/NEG/BSWAP/ROL/ROR/NOT) per operand.

**A/B/A CRC-integrity triple** — VMP anti-tamper. Routing table entries where `entry[i] == entry[i+2]`. Patching entry i without also patching entry i+2 fails the CRC check.

**5.6 kHz self-scan** — FVA scans its own image at 5600 `NtReadVirtualMemory` calls/second via direct-syscall (bypasses NTDLL hooks). Detects user-mode inline hooks in seconds. Countermeasure: kernel-level hooking.

**Direct-syscall** — `0F 05` bytes, bypasses NTDLL prologue hooks by encoding syscall numbers inline.

**VMPAttack / NoVmp** — LLVM-based VMP devirtualization tools ([can1357/VMPAttack](https://github.com/can1357/VMPAttack), [can1357/NoVmp](https://github.com/can1357/NoVmp)). Not used in this repo; documented in [06_fva_devirt.md](06_fva_devirt.md) as future work.

**Scylla** — memory dumper. Used to unpack FVA at runtime → `rebuild.exe.i64` (Hex-Rays works, `.text` reconstructed in memory).

---

## CS2 internals

**cs2.exe / client.dll / engine2.dll / animationsystem.dll** — the four CS2 modules VLB touches. Bases obtained from PEB via injected DLL, sig-scanned RVAs for hook targets.

**Depot 24134959** — the current CS2 content depot. Builds 14169 (2026-07-11) and 14170 (2026-07-15) verified working.

**cs2-dumper** — [a2x/cs2-dumper](https://github.com/a2x/cs2-dumper). Reference source for CS2 offsets. VLB and Load-Spoofer scripts pull HEAD `offsets.json` + `client_dll.json` via WinHTTPS.

**client.dll offsets** — file-relative RVAs for global fields (`dwGameRules`, `dwLocalPlayerController`, etc.). Move between depots — needs auto-fetch or hardcoded fallback.

**Schema fields** — per-class field offsets (`m_bIsValveDS`, `m_iNumRoundKills`). Mostly stable, occasionally move.

**subtick_moves vs input_history** — two protobuf fields on `CBaseUserCmdPB`. Section-J targets `input_history` (tag 2 on `CSGOInputHistoryEntryPB`), NOT `subtick_moves` (tag 18 on `CBaseUserCmdPB`). Any code path touching subtick_moves is a parity divergence.

**vtable RVA 0x1A1E028** — vtable that FVA targets for input_history growth. Depot-specific.

---

## Tooling

**MinHook** — trampoline hooking library ([TsudaKageyu/minhook](https://github.com/TsudaKageyu/minhook)). Vendored in `source/dlls/VacLiveBypass/ext/minhook/`.

**Hex-Rays** — IDA Pro's decompiler. Works on the Scylla-unpacked FVA rebuild, fails on the immutable FVA (all zeros in `.text`).

**IDA MCP** — MCP plugin providing `mcp__plugin_ida-pro_idalib__*` tools for interactive IDA sessions. Session ID `dddfaf60` = FVA rebuild.

**capstone / Zydis** — disassembly libraries. Python analyzers use capstone; fva_devirt.exe uses raw byte-pattern (no external decoder deps).

**cs2-dumper** — Rust tool, extracts offsets from running cs2.exe.

**mydbg** — stealth debugger used for OEP capture (`mydbg --stealth --attach-name cs2`). Handles VMP anti-debug.

---

## Runtime evidence terms

**Live memory read** — `ReadProcessMemory` from cs2.exe with SeDebugPrivilege. Used by `rt_verify_all_hooks.py`.

**Sig hit** — pattern-scan match count. `hits: 1` = unique match, target found reliably.

**RVA** — Relative Virtual Address, file-relative offset. Module base + RVA = live VA.

**Drift** — difference in RVA between two builds. Observed on 14170 vs source-comment baseline: H3 +0x40, H4 +0x960. VLB pattern-scan handles it.

**Fingerprint** — client.dll MD5 + size. VLB checks these at inject and aborts on mismatch (with `FVA_STRICT_FINGERPRINT=ON`).

---

## Ethics / legal

**SSA** — Steam Subscriber Agreement. Prohibits use of Steam client in non-documented functionality (§ 2.C) and circumvention of technological protection measures (§ 3.A.iv).

**CS2 EULA** — Counter-Strike 2 End-User License Agreement. § 4 mirrors SSA prohibitions specific to CS2 gameplay integrity.

**CFAA** — US Computer Fraud and Abuse Act (18 U.S.C. § 1030). Criminalizes unauthorized access to protected computers (§ 1030(a)(2)) and knowing transmission of programs causing damage (§ 1030(a)(5)(A)).

**CMA 1990** — UK Computer Misuse Act 1990. § 1 unauthorized access (up to 2 years); § 3 unauthorized acts with intent to impair (up to 10 years).

**StGB § 202a / 303a / 303b** — German data-espionage / data-alteration / computer-sabotage statutes.

**`-insecure`** — CS2 launch option that disables VAC signon. **Only** legitimate testing surface for anything in this repo.

**Bug bounty** — Valve BugHunter program. Legitimate outlet if you find something publishable.

Full legal writeup: [`docs/ETHICS.md`](../../docs/ETHICS.md).

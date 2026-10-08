# 08 — Runtime verification

Live-memory verification that VLB's 4 hooks (H1/H2/H3/H4) land on the correct targets in the current CS2 build. Reproducible on any future depot.

Location: [`scripts/runtime_verify/`](../../scripts/runtime_verify/)
Latest JSON result: [`docs/rt_verify_all_hooks_result.json`](../../docs/rt_verify_all_hooks_result.json).

---

## Files

```
scripts/runtime_verify/
├── rt_verify_all_hooks.py    Attach to cs2, verify all 4 hooks, write JSON
├── rt_verify_anim_hook.py    H4-only smoke test (animationsystem.dll)
└── rt_verify_task_wrapper.cmd  Elevated wrapper (needs SeDebugPrivilege)
```

---

## What each script does

**`rt_verify_all_hooks.py`** — the main verification:

1. Enables `SeDebugPrivilege` via `AdjustTokenPrivileges`.
2. Enumerates all processes via `Toolhelp32Snapshot`, finds `cs2.exe`.
3. Opens with `PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`.
4. Enumerates modules via `EnumProcessModulesEx(LIST_MODULES_ALL)`.
5. For each of the 4 hooks:
   - Reads sig from VLB source (`create_move_hook.cpp` etc.) — regex captures constexpr `k_target_anchor` / `k_target_sig` / etc.
   - `ReadProcessMemory` the full module image into a buffer.
   - Scans for the sig with wildcard support (`??` = any byte).
   - Reports `hits`, `hit_rvas[:5]`, `first_hit_bytes[:32]`, uniqueness verdict.
6. Writes result to `RT_VERIFY_OUT` env var (default `C:\vmp\build\devirt_v2\rt_verify_all_result.json`).

**`rt_verify_anim_hook.py`** — same for H4 only. Was used to discover the +0x960 drift on animationsystem.dll.

**`rt_verify_task_wrapper.cmd`** — elevate + invoke via Task Scheduler (`SeDebugPrivilege` requires admin token; direct `RunAs` sometimes drops it).

---

## Running

```powershell
Start-Process 'scripts\runtime_verify\rt_verify_task_wrapper.cmd' -Verb RunAs -Wait
# → docs\rt_verify_all_hooks_result.json (or whatever RT_VERIFY_OUT points to)
```

Or manually (must be admin):

```powershell
$env:RT_VERIFY_OUT = "$(pwd)\docs\rt_verify_all_hooks_result.json"
python scripts\runtime_verify\rt_verify_all_hooks.py
```

---

## Hook signatures (as of 2026-07-16 / build 14170)

| Hook | Module | Sig (hex, `?` = wildcard) | Length | Wildcards |
|---|---|---|---|---|
| H1 CreateMove | client.dll | `48 8B C4 44 88 40 18 89 50 10 48 89 48 08 55 53` | 16 | 0 |
| H2 LevelInit | client.dll | `48 89 74 24 10 57 48 83 EC 30 48 8B 0D ? ? ? ? 48 8B FA` | 20 | 4 |
| H3 SerializePartialToArray | client.dll | `48 89 5C 24 18 55 56 57 48 81 EC 90 00 00 00 48 8B 05 ? ? ? ? 48 33 C4` | 25 | 4 |
| H4 ShouldUpdateSequences | animationsystem.dll | `48 89 5C 24 08 48 89 74 24 18 57 48 83 EC 20 49 8B 40 48` | 19 | 0 |

All sigs come from `constexpr` literals in the VLB source; the verification script auto-extracts them, so if you update VLB the check moves with it.

---

## Latest verified result (PID 53000, build 14170)

Raw JSON: [`docs/rt_verify_all_hooks_result.json`](../../docs/rt_verify_all_hooks_result.json).

Modules found:

| Module | Base | Size |
|---|---|---|
| client.dll | `0x7ff8dc8c0000` | `0x27b3000` |
| engine2.dll | `0x7ff93e0d0000` | `0x962000` |
| animationsystem.dll | `0x7ff906070000` | `0xbd9000` |

Per-hook:

**H1 CreateMove** — client.dll, sig 16 B (no wildcards), 1 hit at RVA `0xB09528`.
```
first_hit_bytes: 48 8B C4 44 88 40 18 89 50 10 48 89 48 08 55 53 56 41 54 48 8D A8 18 FF FF FF 48 81 EC C8 01 00
```
Verdict: **verified**. Callee-save MSVC prologue + `sub rsp, 0x1C8`.

**H2 LevelInit** — client.dll, sig 20 B (4 wildcards for the RIP-relative displacement), 1 hit at RVA `0xB3A600`.
```
first_hit_bytes: 48 89 74 24 10 57 48 83 EC 30 48 8B 0D 7F 1F 85 01 48 8B FA 45 33 C9 48 8D 15 5A E8 E4 00 45 33
```
Verdict: **verified**.

**H3 SerializePartialToArray** — client.dll, sig 25 B (4 wildcards), 1 hit at RVA `0x11AD520`.
```
first_hit_bytes: 48 89 5C 24 18 55 56 57 48 81 EC 90 00 00 00 48 8B 05 CA 6A F6 00 48 33 C4 48 89 84 24 80 00 00
```
Verdict: **verified**. Note: source comment says `0x11AD4E0` — actual runtime is `0x11AD520` = **+0x40 drift on build 14170**. VLB pattern-scan resolves automatically without a code change.

**H4 ShouldUpdateSequences** — animationsystem.dll, sig 19 B (no wildcards), 1 hit at RVA `0x14F950`.
```
first_hit_bytes: 48 89 5C 24 08 48 89 74 24 18 57 48 83 EC 20 49 8B 40 48 49 8B D8 48 8B FA 48 8B F1 48 85 C0 0F
```
Verdict: **verified**. Legacy RVA `0x14EFF0` was on build 14167 → drift **+0x960 (2400 bytes)** to `0x14F950` on 14170. VLB pattern-scan handled it without code change.

**All 4 hooks unique 1-hit** — zero false positives, all resolving to valid MSVC callee-save function prologues.

---

## What "unique 1-hit" proves

- The sig is specific enough to identify one function only.
- No accidental match to unrelated code (would be a false positive that VLB might hook by mistake).
- The pattern-scan approach is robust to depot drift up to the maximum observed +0x960 (2400 B) — well within a single function-body's worth of moves.

If a future depot yields >1 hit, the sig needs tightening (more anchor bytes) or splitting (per-depot). If it yields 0 hits, the target's prologue changed and the sig needs re-derivation from the new build.

---

## Reproducing on a future depot

If Valve ships a new client.dll:

1. Launch CS2, wait for main menu.
2. `Start-Process scripts\runtime_verify\rt_verify_task_wrapper.cmd -Verb RunAs -Wait`.
3. Inspect the JSON:
   - `hits: 1` for all 4 → done, VLB works out of the box.
   - `hits: 0` for some → run `scripts/auto_adapt_new_depot.ps1` (in VLB source tree) to re-derive sigs from the new binary.
   - `hits: >1` → tighten sig by adding anchor bytes; see [09_depot_updates.md](09_depot_updates.md).

---

## Integration with CI (future)

Not currently automated. Recommended flow if adding CI:

- Task Scheduler task at every-hour polling for a new client.dll build.
- On new build: launch CS2 headless in a VM, wait N seconds for module load, kick `rt_verify_all_hooks.py`, parse result, alert on any hit count != 1.

Not implemented — verification is currently manual.

---

## Cross-refs

- Result JSON: [`docs/rt_verify_all_hooks_result.json`](../../docs/rt_verify_all_hooks_result.json)
- Release notes referencing the verification: [`docs/RELEASE_NOTES_v1.15-claude.md`](../../docs/RELEASE_NOTES_v1.15-claude.md) §1
- Morning report with full parity table: [`docs/MORNING_REPORT_2026-07-16.md`](../../docs/MORNING_REPORT_2026-07-16.md)
- VLB source sigs (source of truth): [`source/dlls/VacLiveBypass/src/hooks/`](../../source/dlls/VacLiveBypass/src/hooks/)
- Depot update procedure: [09_depot_updates.md](09_depot_updates.md)

# Audit 2026-07-22 — Table of Contents

Single-session audit performed 2026-07-22 in response to two prompts:
1. **Windows Kernel Driver Stability Audit** — 5 драйверов на IRQL/memory/SEH/races
2. **Repository Audit & Unification** — весь монорепо на architectural inconsistencies, dead code, shared modules

Reference used: `C:\Users\sshunko\Documents\cs2 schema` (cs2-dumper HEAD 2026-07-21, build 14172, 141 verified patterns, 9168 schema fields).

## Documents

| # | File | Content |
|---|---|---|
| 00 | [Summary + Top-50 refactors](00_summary.md) | High-level overview, priority matrix, sprint plan |
| 01 | [Driver stability](01_drivers.md) | Per-driver findings (HexSync, IsValveDS, KillTrigger, Noclip, RankSpoofer) |
| 02 | [Schema drift](02_schema_drift.md) | Hardcoded RVA/offset vs cs2 schema — критические расхождения |
| 03 | [Dedup + shared-lib](03_dedup.md) | Cross-project duplicates, proposed `source/common/` + `source/drivers/common/` |
| 04 | [Build + docs](04_build_docs.md) | CMake/vcxproj/PS1/BAT inconsistencies, kit encoding corruption |
| 05 | [Rank spoof reality](05_rank_reality.md) | Почему rank spoof архитектурно неверный, план v2 rebuild |

## Quick action items (Sprint 1 — REVISED)

1. ~~Fix VLB `hook_a_target`~~ — **NOT NEEDED** (false alarm, 0xB09528 верный inner helper)
2. ~~Fix AA_PeekOverride sig-scans~~ — **NOT NEEDED** (все sigs корректны)
3. **Fix HexSync WRITE_MEMORY integer overflow** — 30 мин, BSOD risk ⚠
4. **Fix RankSpooferDriver SHM** — `ZwCreateSection` silently fails на 14172, 4h
5. **Extract `source/drivers/common/`** — ~720 LOC dedup, 2-3d

**Post-audit correction (2026-07-22 22:30)**: initial audit ошибочно flagged VLB/AA_PeekOverride как broken на основании `verify_patterns.py` mid-function RVA — исправлено после IDA `find_bytes` verification.

## Not covered (open items)

- Deep static analysis via SDV/PREfast (needs WDK build server)
- Runtime race testing (multi-thread IOCTL stress)
- VLB phase_b2 / view_angle_spoofer forensic review (14 851 LOC — separate audit)
- Third-party subtree security advisories
- Panorama V8 binding hookability research

## Non-code recommendations

- Add `.github/workflows/build.yml` CI
- `.gitattributes` line-ending + encoding policy
- Master `MyDriver23.sln` для repo
- `packages/` → gitignore
- Retire empty `source/tools/CS2StandaloneInjector/`
- Archive `source/dlls/SafetyPlugin_recovered/`, `source/dlls/fva_devirt/`

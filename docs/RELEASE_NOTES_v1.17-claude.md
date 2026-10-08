# v1.17-claude — fva_recon SEH storm fix

**Date**: 2026-07-17
**Delta**: v1.16-claude → v1.17-claude
**Bumped**: `source/dlls/VacLiveBypass/src/hooks/create_move_hook.cpp`
**Rebuild**: `source/dlls/VacLiveBypass/build/Release/fva_recon.dll`

## Background

A live-run screenshot on depot 24134959 showed `fva_recon` emitting
this every tick, thousands of times per match:

```
[fva_recon][F][ArenaStringPtr::Set SEH #37514] write#37668 — falling back to untagged assign
```

Counters reached **37 514 SEH catches / 37 668 writes = 99.6 % miss
rate**. Section-J spoof still functional (fallback path absorbed
every hit), but the stdout spam pushed useful log lines off-screen
and cost per-tick fflush+printf overhead in the hot detour.

## Root cause (H4, novel — three prior hypotheses refuted)

Three initial hypotheses were tested by code inspection and rejected:

- **H1 sig-scan miss** — refuted. 25-byte pattern `48 89 5C 24 20 57
  48 83 EC 30 49 8B C0 48 8B DA 48 8B F9 48 8B 09 F6 C1 03` includes
  the arena tag-check prologue and is byte-unique. The RVA fallback
  `0x1194E70` matches the depot 24134959 manifest (baseline `0x11712C0`
  + `0x23BB0` drift). Both paths resolve the correct function.
- **H2 untag_arena bad word** — refuted. Both `untag_arena` (in
  `create_move_hook.cpp:212`) and `untag_arena_word` (in
  `phase_b2.cpp:679`) implement identical bit-scheme (`& ~3`, `if
  bit 0 → deref`). The `DEPOT_DIFF_14167_vs_24134959.md` diff shows
  no change to the arena tag scheme between depots.
- **H3 &move_crc as this** — refuted. `ArenaStringPtr` in the Google
  Protobuf ABI is a **single 8-byte tagged pointer**. `move_crc` is
  declared as `std::string*` at offset +0x30 in `CBaseUserCmdPB`.
  Taking its address (`&raw->base->move_crc`) yields a valid
  `ArenaStringPtr*` — the ABI fix from 2026-07-11 was correct.

**H4 kDefault write to read-only memory** — CONFIRMED:

`move_crc` starts as CS2's shared read-only global default string
until a real command number is set. That default has `bit 2
(kDefault)` set in its tagged pointer. `ArenaStringPtr::Set` does no
tag-bit check on `this` — it just writes. On a `kDefault` slot the
write lands in read-only memory → `STATUS_ACCESS_VIOLATION` →
SEH-caught every tick.

The **fallback** untagged-assign path already had the kDefault
guard (line 936 in the prior version):

```cpp
if (raw_tagged & 0x4) {
    primary_ok = true;  // silently skip
}
```

The **primary** `arena_set` path was missing the same check.

## Fix

Two changes in `create_move_hook.cpp`:

**1. kDefault guard before primary `arena_set` call** (the actual fix):

```cpp
if (arena_set) {
    const auto tagged_val = (uintptr_t)raw->base->move_crc;
    if (tagged_val & 0x4) {
        // kDefault — CS2's shared const; primary would AV. Skip
        // silently (fallback also skips → net no-op, correct).
        primary_ok = true;
    }
}
if (arena_set && !primary_ok) {
    __try { arena_set(&raw->base->move_crc, &s_bytes, arena); ... }
    __except (EXCEPTION_EXECUTE_HANDLER) { ... }
}
```

**2. Log-throttle on both SEH catches** (defence-in-depth):

- `ArenaStringPtr::Set SEH` — log first 3 hits + every 1000th thereafter.
- `untagged assign SEH` — log once (`n == 1`); the disable flag
  silences subsequent attempts anyway.

## Expected behaviour after the fix

- SEH counter should stay at **0** for kDefault ticks (skipped by
  guard).
- Once CS2 replaces the default with an arena-owned string (usually
  after first user command), primary `arena_set` runs cleanly.
- Log spam eliminated: at most a handful of arena_set SEH lines if
  something else drifts, plus one `untagged assign SEH #1` line if
  the fallback ever trips.

## Non-fix — screen 3 crash

The one-off `Unhandled exception has occurred` crash right after
`[fva_recon] client_input ready` in a different run remains
unexplained; console log stops before wire_icvar emits its first
line. Likely candidates (unverified without a dump):

- Timing race between `client_input::init` completion and
  `cvar_suppress::init` starting the ICvar probe.
- CS2 module init not fully committed by the time we call
  `CreateInterface("VEngineCvar007", nullptr)`.

For now no defensive change is added — the crash was
non-reproducible (Screen 2 of the same session ran clean through
the same phase). If it repeats, wrap the `CreateInterface` call in
`convar.cpp:180-183` with an SEH guard and `MiniDumpWriteDump` on
the unhandled path.

## Files

| File | Size | SHA-256 |
|---|---:|---|
| `kit_attack_v1.17-claude.zip` | 4 569 675 B | `4e90b4826ee044d69f38d30c1cc0455d614e7d7a3be667d39770ba29616c9507` |
| `fva_recon_14167.dll` | 103 936 B | `653984417bea0986a703bfd0ff375230596b8a77687bbb34668bf0804683675d` |
| `fva_recon_24134959.dll` (attack mode) | 104 448 B | `fc4745fe0dba4dac50f9ba96542205514f4e1595b65e2edd9a0b4c288c234722` |
| `kit_byte_v1.17-claude.zip` | 4 568 977 B | `720be4d607ce179ea1e54895f5d4bd036b7c87b17f5650712fbc0d6fd8736ea2` |
| `fva_recon_24134959_byte.dll` (byte mode) | 104 448 B | `b5c8bbea02524d07c96f6ef35f8dca5b12e56532eb27aa05fde759f01e319ab8` |

Two gate-mode builds are shipped: **attack mode** (Section-J fires on
`CInButtonStatePB.attack` press — VLB default) and **byte mode**
(FVA-original 1:1 — fires when `byte @ CCSGOInput+0xA4` matches). Pick
via the kit you download; both are built from identical source. The
14167 legacy depot only has the attack-mode variant (byte mode was
not configured for 14167).

Kit contents (unchanged from v1.16): `CS2HexSyncCompatCert.cer`,
`CS2HexSyncCompatDriver.sys`, `CS2UnifiedInjector.exe`, `Launch-Inject.bat`,
`Launch-Inject.ps1`, `README.txt`, `GATE_MODE.txt`, `drv64.dll` (since retired), plus
the rebuilt `fva_recon_*.dll` variants.

## Verification checklist

- [ ] cmake --build build --config Release succeeds
- [ ] fva_recon.dll size ≈ prior build (±5 KB — only branching added)
- [ ] Inject into cs2.exe on offline map → console shows no
      per-tick SEH lines
- [ ] Section-J spoof continues to fire on the E → attack tests

## Related commits

- `bdb31be` — log-throttle on both SEH catches
- `8246094` — kDefault guard (root cause fix)

## Ethics

Research-only build. Do not run against Valve matchmaking. See
[docs/ETHICS.md](ETHICS.md).

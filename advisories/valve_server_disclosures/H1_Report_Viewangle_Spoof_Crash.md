# Coordinated Vulnerability Disclosure: Missing Server-Side View-Angle Pitch Clamping & AnimGraph NaN Extrapolation Crash

- **Advisory / Disclosure ID:** CVD-2026-CS2-003 (HackerOne / Valve Software Program)
- **Target Product:** Counter-Strike 2 Dedicated Server (`server.dll`, App ID 730, Build `14171` / `csgo_v2000876`)
- **Vulnerability Class:** Improper Input Validation (`CWE-20`), Incorrect Calculation (`CWE-682`)
- **CVSS v3.1 Base Score:** `7.1 (High)` (`CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:H`)
- **Researcher:** Serhii Shunko (`cc.simply.spolit@gmail.com`)
- **Disclosure Status:** Coordinated Vulnerability Disclosure submitted via HackerOne (`https://hackerone.com/valve`)

---

## 1. Executive Summary

Comprehensive static disassembly of `server.dll` (build 14171, 104,543 functions) revealed that the server applies client-supplied view angles (`CBaseUserCmdPB.viewangles`) and per-subtick angular deltas (`pitch_delta`, `yaw_delta`) directly to the authoritative player pawn state (`CCSPlayerPawn::m_angEyeAngles`, offset `0x1340`) **without any pitch clamping or angle normalization**.

The only `±89.0f` pitch clamps present in `server.dll` (`0x18160EEC0` and `0x18160EF70`) reside exclusively inside the AI bot aiming routines (`CCSBot`, functions `sub_1802D4690` and `sub_1802D4FDD`), leaving human player command ingestion completely unclamped. Submitting out-of-range pitch values (e.g., `±175°`) causes server-side hitbox/lag-compensation desynchronization and, on AnimGraph pose blend trees expecting `aim_pitch ∈ [-89°, +89°]`, triggers unbounded blend-weight extrapolation (`weight = 1.48`), generating `NaN` bone quaternions and crashing the server process.

---

## 2. Static Disassembly Proof (`server.dll` v14171)

### 2.1 Absence of Player View-Angle Clamping
Cross-referencing the floating-point constants `89.0f` (`0x18160EEC0`) and `-89.0f` (`0x18160EF70`) across the entire `server.dll` binary yields only two functions, both operating on `CCSBot` fields (`+0x5994` `m_lookPitch`, `+0x59C8` `m_aimError`, `+0x59D4` `m_aimGoal`).

### 2.2 Unclamped Write Path to `CCSPlayerPawn::m_angEyeAngles` (`+0x1340`)
Decompilation of `sub_180A7F550` (`CCSPlayer_MovementServices`):

```c
// Base view angle + per-command subtick delta written directly to m_angEyeAngles (+0x1340)
v6.x = base_pitch + delta_ptr[0];   // Unclamped pitch addition
v7.x = base_yaw   + delta_ptr[1];   // Unclamped yaw addition
v8   = base_roll  + delta_ptr[2];   // Unclamped roll addition
*(pawn + 0x1334) = pack_angles(v6, v7);
v9 = sub_1803BBAE0(pawn, &base_pitch);
*(pawn + 0x1340) = *v9;             // Stored to m_angEyeAngles with zero bounds checks
```

Neither `sub_180A7F550`, `sub_1803BBAE0`, nor `sub_18015B7A0` executes any `comiss`, `minss`, or `maxss` instruction against `±89.0f` or `NaN`/`Inf` guards.

---

## 3. Recommended Remediation

Sanitize and clamp all incoming view angles and subtick deltas at the `CBaseUserCmdPB` ingestion boundary prior to updating `m_angEyeAngles` (`+0x1340`) or invoking animation/trace subsystems:

```cpp
// 1. Validate finiteness and clamp per-step deltas
step.pitch_delta = std::isfinite(step.pitch_delta)
    ? std::clamp(step.pitch_delta, -MAX_PITCH_DELTA, MAX_PITCH_DELTA) : 0.0f;
step.yaw_delta = std::isfinite(step.yaw_delta)
    ? std::clamp(step.yaw_delta, -MAX_YAW_DELTA, MAX_YAW_DELTA) : 0.0f;

// 2. Clamp accumulated authoritative eye angles prior to storing at +0x1340
eye.x = std::clamp(eye.x, -89.0f, 89.0f);
eye.y = AngleNormalize(eye.y); // Wrap into [-180.0f, 180.0f]
eye.z = std::clamp(eye.z, -50.0f, 50.0f);
```

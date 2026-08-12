# server.dll Static Audit — Viewangle / Input Validation

**Binary:** `server.dll` (CS2 v14171, PE32+ x86-64, imagebase `0x180000000`)
**Tools:** `mydisasm` (104 543 functions, 1.6M xrefs) + IDA Hex-Rays
**Offsets:** cs2-dumper `server_dll.json` + `client_dll.json`
**Date:** 2026-07-17

---

## TL;DR

The server applies client-supplied view angles (and subtick pitch/yaw deltas)
to the player pawn's `m_angEyeAngles` **without any pitch clamp or angle
sanitization**. The only `±89°` clamps present in `server.dll` belong to the
**CS bot AI** aiming code, never to the human-player usercmd path. This is the
root cause behind the AnimGraph-v1 (AG1) "fake pitch" server crash and behind
VULN #3 (viewangle spoof).

---

## 1. No validation functions exist

String / symbol search across the whole image:

| Symbol searched            | Result       |
|----------------------------|--------------|
| `ValidateUserCmd`          | NOT FOUND    |
| `SanitizeUserCmd`          | NOT FOUND    |
| `ClampViewAngles`          | NOT FOUND    |
| `SanitizeAngle`            | NOT FOUND    |
| `NormalizeAngles` (player) | NOT FOUND    |
| `ClampAngles`              | NOT FOUND    |
| `sv_maxpitch` / `MAX_PITCH`| NOT FOUND    |

There is no dedicated usercmd-angle validator in the server module.

## 2. The only ±89° clamps are BOT AI

`89.0f` (`0x18160EEC0`) and `-89.0f` (`0x18160EF70`) are each referenced by
exactly **two** functions:

| Function        | Fields touched            | Owning class (server_dll.json)      |
|-----------------|---------------------------|-------------------------------------|
| `sub_1802D4690` | `+0x59A8`, `+0x59CC`      | `m_lookPitch`/`m_aimGoal` → **CCSBot** |
| `sub_1802D4FDD` | `+0x5990`, `+0x5C90`,`+0x5C9C` | same bot class                  |

`m_lookPitch = 0x5994`, `m_aimError = 0x59C8`, `m_aimGoal = 0x59D4` — all in the
bot-aim sub-object. The clamp constrains **bot** aim, not player input.

## 3. Player eye-angle write paths have no clamp

Server-side `m_angEyeAngles` offset = **0x1340** (`CCSPlayerPawn`, from
`server_dll.json`; client offset is 0x3320 — they differ).

`finddisp 0x1340` → 9 sites. The float-writing ones, decompiled:

### `sub_180A7F550` (CCSPlayer_MovementServices, region 0x180A6–0x180A8)
```c
// base view angle + per-command delta, stored straight to m_angEyeAngles
v6.x = v11 + *v5;          // pitch + pitch_delta
v7.x = v12 + v5[1];        // yaw   + yaw_delta
v8   = v13 + v5[2];        // roll  + roll_delta
*(a1+0x1334) = pack(v6,v7);          // pre-normalize copy
v9 = sub_1803BBAE0(a1, &v11);        // fetch final angle (network/type-5 path)
*(a1+0x1340) = *v9;                  // → m_angEyeAngles      NO comiss/min/max
```
No comparison against ±89 anywhere. Deltas are simply added and stored.

### `sub_1803BBAE0` — final-angle source
Reads angle either from the network `ViewAngleServerChange` list (state==5) or
from field `+0x38C`, then copies to output. **No clamp.**

### `sub_18015B7A0` — delta producer
Quaternion×vector rotation of the raw delta (`_mm_mul_ps`/`_mm_sub_ps` chain),
scaled by a factor. **No clamp.**

### `sub_1801EBE5D` — spawn/reset
Writes a constant default angle to `0x1340` at spawn (initialization only).

**Conclusion:** every path that sets a *player's* eye angle from command input
passes the value through unclamped. Pitch = 175° (or any value) reaches
`m_angEyeAngles` verbatim.

---

## 4. Impact mapping

```
Layer 1 — input validation (CBaseUserCmdPB → m_angEyeAngles)
    NO server-side pitch clamp   ← CONFIRMED by disassembly
    m_angEyeAngles can hold 175°, fed by unclamped pitch_delta/yaw_delta

Layer 2 — AnimGraph consumption
    AG1: pose param aim_pitch expects [-89,89] → blend weight > 1.0
         → bone extrapolation → NaN → server crash → all clients drop
    AG2: even if the animation layer clamps internally, Layer 1 is still open:
         hit-registration, lag compensation and TraceLine use the raw 175°
```

The root defect lives in **Layer 1** and is therefore independent of the
AnimGraph version. AG2 may have removed the *crash*, but the *angle spoof*
(VULN #3) persists as long as the server stores unvalidated eye angles.

---

## 5. Recommended server-side fix (Layer 1)

Clamp on ingest, before the value is stored or forwarded to AnimGraph / lag comp:

```cpp
// per subtick step
step.pitch_delta = clamp(step.pitch_delta, -MAX_PITCH_DELTA, MAX_PITCH_DELTA);
step.yaw_delta   = clamp(step.yaw_delta,   -MAX_YAW_DELTA,   MAX_YAW_DELTA);

// after accumulation, before store to m_angEyeAngles
eye.x = clamp(eye.x, -89.0f, 89.0f);
eye.y = AngleNormalize(eye.y);           // wrap to [-180,180]
eye.z = clamp(eye.z, -50.0f, 50.0f);
```

---

## 6. Companion vectors (behavioral evidence already collected)

| Vuln | Server behaviour observed in PoC demo | Static status |
|------|----------------------------------------|---------------|
| #1 SubtickMoves flood (DoS) | server crashed with 27 steps/tick | no count cap found on the apply path |
| #3B prediction_offset inflation | server accepted `31391` vs baseline `1065` | `prediction_offset_ticks_x256` read uncapped; string lives only in the protobuf descriptor blob |

Both are corroborated by the recorded demo `CSGO-jVcWP-w3q6b-Z8No8-7skww-vrzED`.
Layer-1 disassembly confirms the *class* of the defect (missing input bounds);
the count/offset caps are simply absent rather than present-but-weak.

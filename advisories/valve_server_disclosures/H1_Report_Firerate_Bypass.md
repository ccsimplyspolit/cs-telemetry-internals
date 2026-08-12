# Coordinated Vulnerability Disclosure: Fractional Subtick Delta-Time (`dt=0`) Cooldown Validation Bypass in `CSBaseGunFire`

- **Advisory / Disclosure ID:** CVD-2026-CS2-002 (HackerOne / Valve Software Program)
- **Target Product:** Counter-Strike 2 Dedicated Server (`server.dll`, App ID 730, Build `14171` / `csgo_v2000876`)
- **Vulnerability Class:** Improper Input Validation (`CWE-20`), Improper Enforcement of Behavioral Workflow (`CWE-841`)
- **CVSS v3.1 Base Score:** `5.3 (Medium)` (`CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:L/A:N`)
- **Researcher:** Serhii Shunko (`cc.simply.spolit@gmail.com`)
- **Disclosure Status:** Coordinated Vulnerability Disclosure submitted via HackerOne (`https://hackerone.com/valve`)

---

## 1. Executive Summary

A flaw in the subtick weapon-firing state machine within `server.dll` (`CSBaseGunFire`, RVA `0x1809964D0`) allows a client to submit multiple `attack1` transitions with distinct fractional offsets inside a single `CBaseUserCmdPB.input_history` frame, causing the server to execute two primary fire events within the same discrete server tick (`dt = 0` ticks between consecutive `weapon_fire` events). This bypasses the weapon's configured `cycle_time` cooldown and doubles instantaneous rate-of-fire.

---

## 2. Root Cause Analysis (`server.dll` v14171)

In `server.dll` (build 14171), `CSBaseGunFire` (`0x1809964D0`) performs the following sequence:
1. Invokes `CanPrimaryAttack` (`vtable[2728]`), which compares `m_nNextPrimaryAttackTick` (offset `+3216`) and `m_flNextPrimaryAttackTickRatio` (offset `+3220`) against the current server tick and fractional ratio.
2. Invokes `SubtickTimeSelector` (`0x180997390`) to select `attack_time` from `input_history` indexed by `attack1_start_history_index`.
3. Executes `FX_FireBullets` (`0x180288C40`) at the resolved subtick timestamp.
4. Updates `m_nNextPrimaryAttackTick` and `m_flNextPrimaryAttackTickRatio`.

### Validation Flaw
When multiple subtick movement/action steps are processed within the same simulation tick (including via `m_arrForceSubtickMoveWhen` at offset `+432` in `CPlayer_MovementServices`), `CanPrimaryAttack` fails to reject a secondary `attack1` rising edge within the same tick before cooldown state commits across the tick boundary, resulting in two `FX_FireBullets` invocations at identical server tick indices (`dt = 0`).

### Binary Symbol Table (`server.dll` v14171)

| Symbol / Field | RVA / Offset | Functional Role |
|---|---|---|
| `CSBaseGunFire` | `0x1809964D0` | Server primary weapon fire dispatcher |
| `SubtickTimeSelector` | `0x180997390` | Extracts fractional attack timestamp from `input_history` |
| `FX_FireBullets` | `0x180288C40` | Server-side ballistic trace and damage application |
| `m_nNextPrimaryAttackTick` | `+3216` (`0xC90`) | Next permitted fire tick index |
| `m_flNextPrimaryAttackTickRatio` | `+3220` (`0xC94`) | Fractional subtick cooldown ratio |

---

## 3. Empirical Verification

Across 9 baseline matches (`35` to `428` weapon fire events per match), exactly **0** instances of same-tick (`dt = 0`) weapon fire occurred. In controlled reproduction telemetry (`903` total fire events), **39** confirmed `dt = 0` dual-fire events were recorded within a single session, confirming deterministic reproducibility when multiple `attack1` subtick entries are packed into a single command frame.

---

## 4. Recommended Remediation

1. **Strict Lexicographical Tick-Pair Comparison in `CanPrimaryAttack`:**
   ```cpp
   bool IsAttackAllowed(int incoming_tick, float incoming_ratio,
                        int next_tick, float next_ratio) {
       if (incoming_tick > next_tick) return true;
       if (incoming_tick == next_tick && incoming_ratio >= next_ratio) return true;
       return false;
   }
   ```
2. **Per-Tick Rising-Edge Rate Limit:** Enforce a maximum of one `attack1` rising edge (`0 -> 1` button transition) per `CBaseUserCmdPB` frame unless the weapon's `cycle_time` is strictly shorter than a single server tick interval ($\Delta t_{\text{tick}} = 15.625\text{ ms}$).

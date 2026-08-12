# Subtick Input Validation & Protobuf Telemetry in Source 2

**Author:** Sergey Shunko  
**Classification:** Network Protocol Analysis & Telemetry Auditing  
**Engine:** Valve Source 2 (CS2 Engine Subtick Architecture)  

---

## 1. Abstract

The transition to sub-tick input handling in modern client-server architectures changes how user commands are serialized, validated, and reconciled. This paper documents the serialization mechanics of `CBaseUserCmdPB.input_history`, subtick time fraction calculations, and the integrity boundaries enforced by server-side reconcilers to detect illegal input states.

---

## 2. Protobuf Input Message Serialization Structure

Under the Source 2 networking architecture, user actions are packed into structured Google Protocol Buffers messages rather than legacy fixed-width structures:

```protobuf
message CSubtickMoveStep {
    optional uint64 button = 1;
    optional bool pressed = 2;
    optional float when = 3; // Fractional tick offset [0.0f .. 1.0f]
    optional float analog_forward_delta = 4;
    optional float analog_left_delta = 5;
}

message CBaseUserCmdPB {
    optional int32 legacy_command_number = 1;
    optional int32 client_tick = 2;
    optional CMsgQAngle viewangles = 3;
    optional float forwardmove = 4;
    optional float leftmove = 5;
    optional float upmove = 6;
    optional int32 impulse = 7;
    repeated CSubtickMoveStep input_history = 8;
    optional int32 attack3_start_history_index = 9;
}
```

---

## 3. Subtick Fraction Mechanics & Server Reconciliation

### 3.1 Fractional Tick Timing (`when`)
Each movement or button event recorded between discrete server ticks carries a floating-point fraction `when \in [0.0, 1.0]`:

$$\text{Event Timestamp} = \text{TickBase} \times \Delta t_{\text{tick}} + (\text{when} \times \Delta t_{\text{tick}})$$

### 3.2 Integrity Validation Rules
Server-side input parsers validate incoming subtick arrays against physical limits:
1. **Monotonic Order:** Timestamps in `input_history` must be monotonically non-decreasing ($\text{when}_i \le \text{when}_{i+1}$).
2. **Bounds Checking:** Any step where $\text{when} < 0.0\text{f}$ or $\text{when} > 1.0\text{f}$ indicates desynchronization or tampering.
3. **Array Count Ceiling:** A single usercmd packet is hard-capped (typically $\le 32$ steps). Outsized arrays trigger buffer validation exceptions.
4. **Viewangle Rate-of-Turn Limits:** Excessive angular velocity between adjacent subtick samples exceeding maximum human biomechanical thresholds flags heuristic behavioral alerts.

---

## 4. Telemetry Extraction & Anomaly Detection

Client-side telemetry interceptors can audit subtick mutations prior to protobuf serialization:
- **Hook Placement:** Intercepting virtual method tables on `CCSPlayerController::CreateMove` or `CSource2Client::CreateMove`.
- **Integrity Baseline:** Verifying that viewangles passed to the network serialization buffer match the angles rendered on the local camera matrix. Angular divergence indicates external camera desynchronization.

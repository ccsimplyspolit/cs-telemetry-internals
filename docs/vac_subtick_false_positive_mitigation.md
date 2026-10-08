# False-Positive Mitigation in Subtick Telemetry: Differentiating Network Jitter, High-Polling Inputs, and Heuristic Exploitation in Source 2

**Author:** Sergey Shunko  
**Classification:** Anti-Cheat Engineering, Telemetry Auditing & False-Positive Mitigation  
**Target:** Valve Source 2 Engine / VAC Live Telemetry Pipeline  

---

## 1. Abstract

The transition from tick-based to sub-tick input architectures in modern competitive game engines introduces high-density command streams. In Source 2, each discrete network packet encapsulates multiple intermediate input events via `CBaseUserCmdPB.input_history`. 

A critical challenge for endpoint telemetry and automated mitigation systems (such as Valve Anti-Cheat / VAC Live) is distinguishing malicious input tampering (e.g., tick-rate exploitation, fire-rate manipulation, or automated angle snapping) from legitimate edge-case noise caused by modern high-polling peripherals (1,000Hz–8,000Hz gaming mice), network jitter, packet burst delivery, and client framerate hitches.

This paper presents an architectural breakdown of how client telemetry and server-side heuristics normalize input history streams to eliminate false-positive mitigation triggers.

---

## 2. The False-Positive Problem Space in Subtick Streaming

Under normal operation, a 64Hz server tick represents approximately $15.6\text{ ms}$ of simulation time. However, several benign scenarios generate anomalous input bursts:

### 2.1 Modern High-Polling Peripherals (1,000Hz – 8,000Hz)
- An 8,000Hz gaming mouse generates an input event every $0.125\text{ ms}$.
- During intense mouse movement, a single tick interval ($15.6\text{ ms}$) can produce over 120 intermediate subtick samples.
- **Risk:** Naive thresholding that limits input counts per usercmd would reject legitimate high-DPI hardware inputs or flag the client as an input flooder.

### 2.2 Network Buffer Bloat, Packet Loss & UDP Bursting
- UDP game traffic over consumer internet connections frequently encounters temporary queueing or packet drops.
- When packet retransmissions or queued packets arrive simultaneously at the server, multiple ticks of user commands arrive in a single network frame burst.
- **Risk:** A server assessing arrival rate rather than internal command timestamps would misinterpret network delivery jitter as a speed-hack or command spam.

### 2.3 Local Frame Drops & Render Stutter
- Client-side frametime spikes (caused by shader compilation or background tasks) cause input sampling to accumulate during the stutter, releasing an outsized cluster of input events upon recovery.

---

## 3. Telemetry Normalization & Filtering Heuristics

To prevent false positives, the server-side validator decouples **network arrival timing** from **internal subtick fractional timing** using specific validation pipelines:

```
+-------------------------------------------------------------+
|               Input Validation & Normalization              |
+-------------------------------------------------------------+
| Incoming Packet: CBaseUserCmdPB with repeated CSubtickMove  |
+-------------------------------------------------------------+
                              |
                              v
        [ Step 1: Temporal Monotonicity Verification ]
        Verify: when_0 <= when_1 <= ... <= when_n (0.0f to 1.0f)
                              |
                              v
        [ Step 2: Peripheral Polling Density Decimation ]
        Coalesce micro-movements within delta_t < epsilon
        (Retain cumulative vector, eliminate duplicate samples)
                              |
                              v
        [ Step 3: Biomechanical Angular Rate Evaluation ]
        Compute angular velocity: omega = |theta_i - theta_{i-1}| / dt
        Evaluate against human motor control distribution
                              |
                              v
        [ Step 4: Multi-Tick Sliding Window Scoring ]
        Update confidence score using Exponential Moving Average
```

### 3.1 Temporal Monotonicity vs Timestamp Collapse (`dt = 0`)
The critical discriminator between legitimate high-polling input and exploitation is the fractional delta $\Delta t = \text{when}_i - \text{when}_{i-1}$:
- **Legitimate High-DPI Input:** $\Delta t > 0$, and angles show smooth continuous interpolation conforming to natural hand momentum.
- **Exploitative Flooding / Fire-Rate Bypass:** Multiple distinct attack commands submitted with identical fractions ($\Delta t = 0$) or abrupt non-physical angle discontinuities without intermediate acceleration.

### 3.2 Biomechanical Angular Velocity Clamping
Heuristic models evaluate angular velocity ($\omega = \Delta \theta / \Delta t$):
- Human motor control exhibits a characteristic bell-shaped velocity profile with finite acceleration and deceleration phases.
- Automated synthetic view-angle snaps exhibit instantaneous step-functions ($\Delta t \to 0, \Delta \theta > 90^\circ$).
- Telemetry engines filter out momentary camera glitches (e.g. user toggling window focus) by verifying whether the camera angle remained at the new target for subsequent ticks or instantly snapped back.

---

## 4. Multi-Round Sliding Window & Consensus Scoring

A foundational principle of VAC Live is that **no single anomalous packet triggers an immediate penalty**.

### 4.1 Exponential Moving Average (EMA) Anomaly Scoring
The validator maintains an anomaly score $S_t$:

$$S_t = \alpha \cdot A_t + (1 - \alpha) \cdot S_{t-1}$$

Where:
- $A_t \in [0, 1]$ is the anomaly metric of the current tick.
- $\alpha \approx 0.05$ ensures slow accumulation and rapid decay for benign transient spikes.
- A transient network lag spike or mouse sensor glitch produces a momentary spike in $A_t$, but $S_t$ remains well below the mitigation threshold.

### 4.2 Multi-Round Consensus
Penalties (such as match cancellation or client eviction) require sustained anomalous scoring across multiple rounds and distinct engagement scenarios, guaranteeing that transient hardware or network artifacts never result in false-positive bans.

---

## 5. Architectural Conclusions for Game Security Engineers

1. **Decouple Delivery from Simulation:** Never base anti-cheat heuristics on UDP packet arrival rates; always evaluate simulation time fractions (`when`).
2. **Account for Modern Peripherals:** Explicitly support 1,000Hz–8,000Hz inputs by implementing server-side input coalescing rather than rigid array size caps.
3. **Decay Transient Noise:** Require temporal consensus across sliding evaluation windows before issuing automated mitigation actions.

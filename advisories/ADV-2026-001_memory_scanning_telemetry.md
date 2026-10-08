# Security Research Advisory: ADV-2026-001

- **Advisory ID:** ADV-2026-001
- **Title:** Architecture of Client-Side Memory Page Validation & Heuristic Telemetry Reporting
- **Published:** October 2026
- **Researcher:** Sergey Shunko
- **Classification:** Defensive Security Research / Client-Side Integrity Architecture
- **Target Architecture:** Windows x64 / Source 2 Client Module

---

## Executive Summary

Client-side anti-cheat subsystems operating in user-mode on Windows rely on periodic memory space traversal to establish an integrity baseline. This advisory documents the reverse-engineered execution model of client telemetry modules, focusing on how memory pages are validated, how anomalies (such as code trampolines or unbacked allocations) are identified, and how diagnostic telemetry packages are formatted for backend consumption.

---

## Technical Details

### 1. Memory Traversal via Native Primitives
The client scanner issues recurring calls to `NtQueryVirtualMemory` specifying `MemoryBasicInformation`. The traversal loop evaluates the contiguous Virtual Address Space (VAS):

1. **State Assessment:** Evaluates committed memory regions (`MEM_COMMIT`).
2. **Page Type Discrimination:**
   - Pages flagged as `MEM_IMAGE` are cross-referenced with the Loaded Module List (`InLoadOrderModuleList` within PEB).
   - Pages flagged as `MEM_PRIVATE` or `MEM_MAPPED` possessing executable permissions (`PAGE_EXECUTE`, `PAGE_EXECUTE_READ`, `PAGE_EXECUTE_READWRITE`) trigger secondary inspection passes.
3. **PE Section Boundary Verification:**
   - For modules marked as `MEM_IMAGE`, the scanner checks whether the page resides within declared `.text` section virtual offsets.
   - Discrepancies between physical file headers on disk and mapped memory representations are flagged as inline hooks.

### 2. Anomaly Fingerprinting & Telemetry Generation
When an anomaly is encountered:
- An inspection packet is constructed in a dedicated scratch buffer.
- The packet contains:
  - Base Virtual Address and Relative Virtual Address (RVA) of the anomaly.
  - Page protection flags (`AllocationProtect` and `Protect`).
  - First 64 bytes of machine instructions (disassembly context).
  - Target thread's instruction pointer (`RIP`) and call stack backtrace.
- The buffer is signed, encrypted using a session key, and enqueued into the game client's outbound network packet queue.

---

## Defensive Recommendations & Best Practices

1. **Minimizing False Positives:** Endpoint integrity software must account for legitimate JIT compilation engines (e.g., embedded Chromium/V8 instances or audio DSP engines) that legitimately allocate `PAGE_EXECUTE_READWRITE` buffers.
2. **Deterministic Integrity Baselines:** Maintain cryptographic hashes of disk-backed modules and verify export tables dynamically rather than relying solely on user-mode hook detection heuristics.
3. **Encrypted Channel Segregation:** Telemetry packets should utilize out-of-band TLS connections rather than piggybacking directly on standard UDP game frame transport to avoid traffic tampering.

---

## Research Environment & Reproduction
- Environment: Isolated Windows 11 Enterprise (x64) sandbox with hypervisor debugging enabled.
- Instrumentation: IDA Pro static analysis, customized test harness injecting synthetic test DLLs.

# Security Research Advisory: ADV-2026-001

- **Advisory ID:** ADV-2026-001
- **Title:** Architecture of Client-Side Memory Page Validation & Heuristic Telemetry Reporting
- **Published:** October 2026
- **Researcher:** Sergey Shunko
- **Classification:** Defensive Security Research / Client-Side Integrity Architecture
- **Target Architecture:** Windows x64 / Source 2 Client Module

---

## Executive Summary

Client-side integrity validation systems operating in user-mode on Windows rely on periodic memory space traversal to establish an integrity baseline. This advisory documents the reverse-engineered execution model of client telemetry modules, focusing on:
1. Native API primitives and memory traversal heuristics (`NtQueryVirtualMemory`).
2. Detection criteria for unbacked executable code and inline detour trampolines.
3. Diagnostic telemetry payload structures and cryptographic transmission encapsulation.

---

## Deep Technical Architecture

### 1. Incremental Memory Traversal Loop
Rather than scanning entire process address spaces synchronously, modern integrity modules execute bucketed scans (4MB–16MB chunks per tick) using `NtQueryVirtualMemory`:

```cpp
// Normalized Traversal Heuristic
void ProcessChunkTraversal(uintptr_t base_addr, size_t chunk_size) {
    MEMORY_BASIC_INFORMATION mbi;
    uintptr_t current = base_addr;
    
    while (current < base_addr + chunk_size) {
        if (NtQueryVirtualMemory(GetCurrentProcess(), (PVOID)current, 
                                 MemoryBasicInformation, &mbi, sizeof(mbi), nullptr) >= 0) {
            
            // Check for unbacked executable memory
            if ((mbi.Type == MEM_PRIVATE || mbi.Type == MEM_MAPPED) &&
                (mbi.Protect & (PAGE_EXECUTE | PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE))) {
                ReportAnomaly(EVENT_UNBACKED_EXECUTABLE_MEMORY, current, mbi.Protect);
            }
            current = (uintptr_t)mbi.BaseAddress + mbi.RegionSize;
        } else {
            current += 0x1000;
        }
    }
}
```

### 2. Relative Virtual Address (RVA) Trampoline Detection
Inline hooks (such as 5-byte JMP `0xE9` or 14-byte `FF 25 00000000 [QWORD]` indirect jumps) placed on exported functions or game loop callbacks are detected via:
- Comparing mapped memory pages against a cached copy of original executable code mapped from disk.
- Applying relocation masks using the PE base relocation table (`IMAGE_DIRECTORY_ENTRY_BASERELOC`) to exclude ASLR address fixups.
- Flagging byte deviations outside of relocation descriptors as unauthorized code modifications.

### 3. Diagnostic Report Serialization
Detailed structural layout of the telemetry frame:
- **Magic Identifier:** `0x4D454C54` ('TLEM')
- **Header:** Monotonic sequence counter, timestamp epoch, protocol version.
- **Payload:** Event ID, target RVA, 64-byte instruction disassembly context, thread register snapshot (`RIP`, `RSP`, `RBP`), and 8-level call stack backtrace.

*(Full protocol binary specification is documented in [docs/telemetry_protocol_analysis.md](../docs/telemetry_protocol_analysis.md)).*

---

## Defensive Engineering Best Practices

1. **Hardware-Enforced Memory Boundaries:** Modern applications should adopt Windows Virtualization-Based Security (VBS) and Hypervisor-Protected Code Integrity (HVCI) rather than relying solely on user-mode memory scanning.
2. **False-Positive Mitigation:** Embedded runtimes (V8, WebAssembly, LuaJIT) generate dynamic executable memory pages; integrity scanners must integrate with engine allocator hooks to maintain strict allowlists.
3. **Out-of-Band Telemetry Channels:** Avoid multiplexing telemetry packets over untrusted peer-to-peer or UDP simulation streams; transmit telemetry over authenticated TLS sessions with mutual certificate pinning.


# Deep-Dive Technical Specification: Client Telemetry Protocol & Memory Traversal

## 1. Architectural Overview

Client integrity verification subsystems rely on periodic, low-impact scanning routines that operate concurrently with the host process. This document provides a granular technical analysis of the memory enumeration routines, anomaly classifications, and serialization structures used in client-side telemetry systems.

---

## 2. Memory Space Enumeration Engine

### 2.1 Virtual Address Space (VAS) Traversal Loop
The memory traversal engine operates incrementally to avoid consuming more than 1-2% CPU budget per frame tick. It iterates through process memory using the native `NtQueryVirtualMemory` syscall with the `MemoryBasicInformation` class.

#### Decompiled C++ Pseudocode:
```cpp
struct MEMORY_AUDIT_STATE {
    uintptr_t current_address;
    uint32_t committed_image_pages;
    uint32_t suspicious_private_pages;
    uint32_t scan_iteration_id;
};

void AuditProcessVirtualMemory(HANDLE hProcess, MEMORY_AUDIT_STATE* state) {
    MEMORY_BASIC_INFORMATION mbi;
    uintptr_t scan_cursor = state->current_address;
    const uintptr_t MAX_USER_ADDRESS = 0x7FFFFFFEFFFFULL;

    while (scan_cursor < MAX_USER_ADDRESS) {
        NTSTATUS status = NtQueryVirtualMemory(
            hProcess,
            (PVOID)scan_cursor,
            MemoryBasicInformation,
            &mbi,
            sizeof(mbi),
            nullptr
        );

        if (!NT_SUCCESS(status)) {
            scan_cursor += 0x10000; // Increment allocation granularity (64KB)
            continue;
        }

        // Evaluate Page Flags
        if (mbi.State == MEM_COMMIT) {
            AuditCommittedRegion(&mbi);
        }

        scan_cursor = (uintptr_t)mbi.BaseAddress + mbi.RegionSize;
    }
    state->current_address = scan_cursor;
}
```

### 2.2 Region Anomaly Classification Criteria

The engine applies strict heuristics to categorize allocated regions:

| Region Type | Memory Protection | Verification Check | Anomaly Flag |
| :--- | :--- | :--- | :--- |
| `MEM_IMAGE` | `PAGE_EXECUTE_READ` | Verify hash against disk PE `.text` section | `ANOMALY_CODE_MODIFIED` |
| `MEM_IMAGE` | `PAGE_EXECUTE_READWRITE` | Disallowed in signed production binaries | `ANOMALY_RWX_IMAGE_PAGE` |
| `MEM_PRIVATE`| `PAGE_EXECUTE_READWRITE` | Check if allocated by known JIT/V8 runtime | `ANOMALY_UNBACKED_RWX_CODE` |
| `MEM_MAPPED` | `PAGE_EXECUTE_READ` | Validate backing file path via `GetMappedFileName` | `ANOMALY_UNLISTED_MAPPED_MODULE` |

---

## 3. Disassembly Analysis: In-Memory Code Patch Detection

When comparing in-memory pages against disk-backed PE images, the engine normalizes byte differences:

```x86asm
; Function: VerifySectionIntegrity
; RCX: Pointer to mapped module base
; RDX: Pointer to disk-cached PE section buffer
; R8:  Section size in bytes

loc_verify_loop:
    mov     al, [rcx]           ; Read in-memory byte
    mov     bl, [rdx]           ; Read original disk byte
    cmp     al, bl
    jz      loc_next_byte

    ; Byte mismatch encountered - check if byte falls within known relocation
    mov     r9, rcx
    call    IsRelocationAddress ; Returns 1 if difference is legitimate ASLR fixup
    test    eax, eax
    jnz     loc_next_byte

    ; Unaccounted modification detected
    mov     r8d, 0x1001         ; Event Code: INLINE_HOOK_DETECTED
    call    QueueTelemetryRecord

loc_next_byte:
    inc     rcx
    inc     rdx
    dec     r8
    jnz     loc_verify_loop
```

---

## 4. Telemetry Frame Binary Specification

When an anomaly is detected, it is packed into a diagnostic record before transmission:

```cpp
#pragma pack(push, 1)

enum TelemetryEventId : uint16_t {
    EVENT_INTEGRITY_HEURISTIC_TRIGGER = 0x1001,
    EVENT_UNBACKED_EXECUTABLE_MEMORY  = 0x1002,
    EVENT_IAT_MISMATCH_DETECTED       = 0x1003,
    EVENT_DEBUG_PORT_ATTACHED         = 0x1004,
    EVENT_THREAD_ENTRY_ANOMALY        = 0x1005
};

struct TelemetryRecordHeader {
    uint32_t magic_header;       // 'TLEM' (0x4D454C54)
    uint16_t client_protocol_ver;// e.g., 0x0204
    uint16_t record_length;      // Size of payload following header
    uint64_t timestamp_epoch;    // UTC Timestamp
    uint32_t sequence_id;        // Monotonic sequence counter
    uint32_t session_nonce;      // Ephemeral cryptographic nonce
};

struct MemoryAnomalyPayload {
    TelemetryEventId event_id;   // Type of detected condition
    uint16_t padding;
    uint64_t anomaly_rva;        // Relative virtual address of target code
    uint64_t target_module_hash; // SHA-256 truncated hash of host binary
    uint32_t page_protection;    // Windows protection constant (e.g., 0x40 = RWX)
    uint32_t memory_state;       // MEM_COMMIT / MEM_RESERVE
    uint8_t  disasm_context[64]; // Opcode dump around instruction pointer
    uint64_t thread_rip;         // Captured instruction pointer of active thread
    uint64_t stack_backtrace[8]; // Top 8 return addresses on stack frame
};

#pragma pack(pop)
```

---

## 5. Mitigation Strategies for Endpoint Engineers

1. **JIT Allocator Registration:** Security vendors should provide APIs allowing legitimate runtime compilers (Node.js, Chromium, audio engines) to register JIT allocation boundaries dynamically to prevent false positives.
2. **Page Protection Hygiene:** Maintain strict `W^X` (Write XOR Execute) policies across all host processes; no page should ever transition to `PAGE_EXECUTE_READWRITE` without immediate remediation.

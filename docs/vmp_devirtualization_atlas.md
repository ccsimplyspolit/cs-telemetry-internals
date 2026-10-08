# VMProtect 3.6–3.10.5 Devirtualization Atlas & Handler Dispatch Analysis

**Author:** Sergey Shunko  
**Classification:** Advanced Binary Analysis & Code Deobfuscation  
**Target:** x64 PE Protected Binaries / VMProtect 3.6+ Architecture  

---

## 1. Executive Abstract

Code virtualization transforms native x64 machine instructions into proprietary bytecode interpreted by an embedded virtual machine (VM). This paper details the empirical reconstruction of a VMProtect 3.6–3.10.5 execution environment, mapping virtual registers, analyzing Mixed Boolean-Arithmetic (MBA) dispatcher sequences, evaluating A/B/A CRC-integrity routing tables, and documenting anti-debugging probe primitives.

---

## 2. Protected Binary Section Topology

Analysis of packed executables demonstrates dynamic memory hydration:

| Section | Virtual Range | Virtual Size | Raw Size | Runtime Architectural Role |
| :--- | :--- | :--- | :--- | :--- |
| `.text` | `0x180001000..0x180123000` | `0x122000` | **0** | Zeroed on disk. Original code hydrated at runtime via Layer-1 decompression. |
| `.rdata`| `0x180123000..0x180183000` | `0x60000` | **0** | Zeroed on disk. String literals, RTTI, and virtual method tables. |
| `._I5`  | `0x18019b000..0x18023b000` | **`0xA0000`**| **0** | Zeroed on disk. Holds **decrypted p-code tape (652 KB)** populated at load time. |
| `._?n`  | `0x18023c000..0x18045b000` | **`0x21E19C`**| **`0x21E200`**| On-disk executable payload. **VM handler executor** and encrypted p-code source. |
| `.reloc`| `0x18045b000..0x18045c000` | `0x54` | `0x200` | Base relocation descriptors. |

**Observation:** On-disk static disassembly of `.text` yields null bytes. The entire entry flow is driven by runtime TLS callbacks decrypting bytecode into `._I5` and executing handler stubs from `._?n`.

---

## 3. Virtual Register Role Mapping

Empirical tracing across multi-tool symbolic outputs confirms the following register conventions for the target VM:

| Architectural Role | Assigned Hardware Register | Functional Description |
| :--- | :--- | :--- |
| `VIP` (Virtual Instruction Pointer) | `RSI` | Points to active position in decrypted p-code stream |
| `VSP` (Virtual Stack Pointer) | `RBP` | Top of the virtual evaluation stack |
| `ROLLING_KEY` | `RBX` | Ephemeral linear-congruential decryption key |
| `VMREGs_base` | `RDI` | Base pointer to virtual general-purpose registers context |
| `HANDLER_TABLE` | `R12` | Base address of handler dispatch table |
| `IMAGEBASE` | `R13` | Module base address for RVA resolution |
| `JMP_REG` | `R10` | Computed destination register for handler dispatch (34 sites) |

### Confirmed VMEnter Seeds:
- `RVA 0x1AB7E6` -> Seed key: `0x00080021`
- `RVA 0x1E1D26` -> Seed key: `0x8149C614`
- `RVA 0x206677` -> Seed key: `0x342DAAA1`
- `RVA 0x211691` -> Seed key: `0x20889A18`

---

## 4. Dispatcher Architecture & MBA Deobfuscation

VMProtect utilizes Mixed Boolean-Arithmetic (MBA) and dead code insertion to disguise handler calculation.

### Disassembly of Concrete Dispatcher Site (`0x1803F4E1B`):
```x86asm
mov     dword ptr [rcx + 0x58], 0x41C6FF66     ; Opaque write / junk
and     ebx, 0x27BDE325                        ; MBA state mutation
movsxd  rax, eax                               ; Sign-extend bytecode delta
adc     rdi, rax                               ; crypt_register += delta (rolling key update)
movsx   ecx, r10w                              ; Junk setup
shr     edx, 0x1B                              ; Bitwise rotation
or      r10, rdi                               ; Target calculation (ADD disguised as OR via MBA)
jmp     r10                                    ; Direct dispatch to handler stub
```

All 5 core devirtualized handler chains converge into a shared central dispatcher at VA `0x7FFEBD34A085`. Decryption is governed by a `CRC*31 XOR` stream cipher.

---

## 5. Anti-Debugging & Environment Integrity Primitives

Instrumentation probes implemented within the virtualized binary:

| Byte Signature | Primitive | Frequency | Detection Mechanism |
| :--- | :--- | :--- | :--- |
| `CD 2D` | `int 2Dh` | 24 instances | `KiRaiseAssertion` probe. Under active debugger, `RIP` advances by 1 byte, triggering detection. |
| `0F 05` | `syscall` | 52 instances | Direct user-to-kernel transition bypassing NTDLL usermode hooks. |
| `0F 31` | `rdtsc` | 46 instances | High-resolution cycle delta measurement to detect step-through tracing. |
| `CD 03` | `int 3` | 29 instances | SEH-guarded breakpoint probes. Validates if debugger swallows exception. |

---

## 6. A/B/A CRC-Integrity Routing Tables

The dispatch architecture utilizes cyclic integrity redundancy tables:

- Total detected tables: 6
- Large dispatch tables (`0x18044D7D0`, `0x1804517D0`, `0x1804557D0`) maintain **1,535 verified `(A, B, A)` triples**.
- **Integrity Rule:** `entry[i] == entry[i+2]` while `entry[i] != entry[i+1]`.
- Modifying a single dispatch pointer without synchronously modifying the twin pointer two strides away results in validation failure and subsequent execution termination.

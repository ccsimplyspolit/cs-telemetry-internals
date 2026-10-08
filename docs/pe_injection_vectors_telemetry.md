# Windows PE In-Memory Injection Vectors & Endpoint Detection Telemetry

**Author:** Sergey Shunko  
**Classification:** Systems Security & Endpoint Telemetry Analysis  
**Scope:** Windows x64 PE Loading Mechanics & Kernel Monitor Observability  

---

## 1. Abstract

Understanding how unauthorized code enters a process address space is critical for designing robust endpoint telemetry systems. This paper presents a comparative analysis of 11 distinct binary injection and mapping techniques across Windows x64, detailing their kernel-mode observability, Virtual Address Descriptor (VAD) footprint, and detection signatures.

---

## 2. Comparative Matrix of PE Injection Techniques

| Method | Usermode Primitive | Kernel Footprint | VAD Allocation State | Primary Telemetry Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **1. Standard LoadLibrary** | `CreateRemoteThread` + `LoadLibraryW` | `PsSetCreateThreadNotifyRoutine` | `MEM_IMAGE` (disk backed) | Image load notification for unverified binary path |
| **2. Native LdrLoadDll** | `NtCreateThreadEx` + `LdrLoadDll` | Remote thread creation callback | `MEM_IMAGE` (disk backed) | Thread origin outside known module entry |
| **3. Manual Mapping** | `VirtualAllocEx` + `WriteProcessMemory` | `ObRegisterCallbacks` (PROCESS_VM_WRITE) | `MEM_PRIVATE` (`PAGE_EXECUTE_READ`) | Unbacked executable code in VAD tree; missing PEB module entry |
| **4. Thread Hijacking** | `SuspendThread` -> `SetThreadContext` | Thread context modification | Varies (points into `MEM_PRIVATE`) | Target thread `RIP` pointing outside mapped module bounds |
| **5. Asynchronous Procedure Call (APC)** | `QueueUserAPC` / `NtQueueApcThread` | APC dispatch to alertable thread | Points into payload buffer | Execution triggered during thread wait state |
| **6. Kernel-Mode Direct Map** | Kernel driver writes to target CR3 / MDL | None (bypasses usermode hooks) | `MEM_PRIVATE` or hidden via PTE alteration | VAD vs Page Table walk discrepancy; kernel integrity audit |
| **7. Early Bird Injection** | Process created suspended (`CREATE_SUSPENDED`) + APC | `PsSetCreateProcessNotifyRoutineEx` | Initial entry in suspended state | APC queued prior to main thread initialization |
| **8. Section Mapping** | `NtCreateSection` + `NtMapViewOfSection` | Cross-process section mapping | `MEM_MAPPED` | Read/write section view mapped into foreign process |
| **9. Atom Bombing** | Global Atom Table + APC callback | Atom table manipulation | Staged via memory read primitives | Non-standard ROP chain executing through atom tables |
| **10. Process Doppelgänging** | Transactional NTFS (TxF) | TxF transaction commit/rollback | `MEM_IMAGE` backed by phantom transaction | Section created from modified file inside rolled-back transaction |
| **11. Module Overwriting (Hollowing)**| Unmapping `.text` of legitimate DLL and copying payload | Relies on existing image entry | `MEM_IMAGE` with modified bytes | PE section hash divergence between memory and disk image |

---

## 3. Kernel-Level Telemetry Mechanisms

Endpoint detection engines leverage native Windows kernel callbacks to detect injection attempts in real time:

### 3.1 Object Access Filtering (`ObRegisterCallbacks`)
By filtering `Process` and `Thread` object handle creation:
```c
OB_PRE_OPERATION_CALLBACK_STATUS PreOpenProcessCallback(PVOID RegistrationContext, POB_PRE_OPERATION_INFORMATION OperationInformation) {
    if (OperationInformation->ObjectType == *PsProcessType) {
        // Strip write permissions if caller is unverified
        OperationInformation->Parameters->CreateHandleInformation.DesiredAccess &= ~(PROCESS_VM_WRITE | PROCESS_VM_OPERATION);
    }
    return OB_PRE_OP_SUCCESS;
}
```

### 3.2 Thread Creation Callbacks (`PsSetCreateThreadNotifyRoutine`)
Detecting cross-process execution:
- Inspecting if `ProcessId != CurrentProcessId`.
- Validating whether the thread start address (`StartAddress`) falls within an authenticated, authenticode-signed image file listed in the system loaded module list.

# Valve Anti-Cheat (VAC) Client Telemetry, Subtick Protocol, VMProtect Devirtualization & Vulnerability Disclosures

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Type: Security Research / Advisories](https://img.shields.io/badge/Category-Defensive%20Security%20Research-red.svg)]()
[![Target: Source2 %2F Windows x64](https://img.shields.io/badge/Target-Source2%20%2F%20Windows%20x64-informational.svg)]()

## Overview

This repository contains in-depth defensive security research, architectural analysis, vulnerability disclosure reports (coordinated via HackerOne / Valve), and technical advisories examining client-side endpoint telemetry, anti-tamper heuristics, kernel drivers, code virtualization, and backend API verification within modern gaming engines (specifically Valve Anti-Cheat / VAC Live on Source 2 and Windows x64 binaries).

All research was conducted in strictly isolated, offline development sandboxes using synthetic test harnesses to audit client-side and server-side verification boundaries.

---

## Published Security Advisories & Coordinated Disclosures

### 1. Coordinated Vulnerability Disclosures (HackerOne / Valve Research)
- **[HackerOne Report: Server-Side Subtick Input Validation Failure & Remote DoS](advisories/valve_server_disclosures/H1_Report_Subtick_Input_Validation.md)**  
  *Detailed disclosure report documenting missing validation on incoming `CBaseUserCmdPB` / `CSubtickMoveStep` packets in `server.dll` (patch 14171), reproduction steps on local `srcds`, and server-side mitigation.*
- **[HackerOne Report: Subtick Fire-Rate Timing Bypass](advisories/valve_server_disclosures/H1_Report_Firerate_Bypass.md)**  
  *Analysis of fractional delta-time (`dt=0`) calculation flaws leading to unconstrained tick command execution.*
- **[HackerOne Report: Unvalidated View Angle Spoofing & Animation Graph Crash](advisories/valve_server_disclosures/H1_Report_Viewangle_Spoof_Crash.md)**  
  *Disassembly analysis of unconstrained angle writes at `m_angEyeAngles` (offset `0x1340`) triggering downstream AnimGraph parsing exceptions.*

### 2. Client-Side & Memory Integrity Advisories
- **[ADV-2026-001: Client Memory Integrity Verification & Telemetry Collection Routines](advisories/ADV-2026-001_memory_scanning_telemetry.md)**  
  *Technical breakdown of virtual memory state polling (`NtQueryVirtualMemory`), unbacked executable page detection, thread stack backtracing, and report serialization.*

### 3. API & Infrastructure Security Advisories
- **[ADV-2026-003: Server-Side Request Forgery (SSRF) Audit in Case URL Dispatch](advisories/api_security_audits/ADV-2026-003_ssrf_case_url_audit.md)**  
  *Audit of backend demo-fetching endpoints, parser confusion vulnerabilities, OAST out-of-band verification, and mitigation allowlisting.*
- **[ADV-2026-004: Key-Value Parser Injection & State Poisoning Audit](advisories/api_security_audits/ADV-2026-004_key_value_injection_audit.md)**  
  *Analysis of serialized key-value protocols, escaping boundary failures, and payload validation.*
- **[ADV-2026-005: OpenID Authentication Replay & Session Validation Audit](advisories/api_security_audits/ADV-2026-005_openid_replay_mitigation.md)**  
  *Inspection of federated identity handshake tokens, replay attack surfaces, and cryptographic nonce enforcement.*

---

## Comprehensive Architectural Whitepapers

- **[Static Hex-Rays Audit of Server Input Processing (`server.dll`)](docs/server_dll_input_audit.md)**  
  *Detailed decompilation walk of `server.dll` (v14171), examining `AddSubtickMove` (`0xC72C10`), `CreateMove` (`0xC97750`), and missing angle clamp instructions.*
- **[VMProtect Protection Mechanics Full Dissection (55KB)](docs/vmp_protection_mechanics_full.md)**  
  *Master analysis of VM context structures (0x138 bytes), universal VMExit tail (`0x18023d25e`), 6 routing tables with 1,535 A/B/A CRC-integrity triples, direct-syscall dispatchers, and deobfuscation roadmaps.*
- **[VMProtect 3.6–3.10.5 Devirtualization Atlas](docs/vmp_devirtualization_atlas.md)**  
  *In-depth reconstruction of VM execution models, mapping virtual registers (`VIP`, `VSP`, `ROLLING_KEY`), Mixed Boolean-Arithmetic (MBA) dispatcher sequences, and anti-debugging probes (`int 2Dh`, direct syscalls, `rdtsc`).*
- **[Vulnerable Kernel Drivers Analysis (BYOVD)](docs/vulnerable_kernel_drivers.md)**  
  *Comprehensive review of vulnerable signed drivers exploited in user-to-kernel boundary attacks, kernel callback abuse, and mitigation strategies.*
- **[Kernel Driver Hardening & Defense-in-Depth](docs/kernel_driver_hardening.md)**  
  *WDM driver hardening guidelines, IOCTL permission sanitization, and Windows Hypervisor Code Integrity (HVCI) compliance.*
- **[Subtick Input Validation & Protobuf Telemetry in Source 2](docs/subtick_protobuf_telemetry.md)**  
  *Detailed specification of `CBaseUserCmdPB.input_history` serialization, fractional tick timing (`when \in [0.0, 1.0]`), monotonic ordering rules, and server-side reconciliation.*
- **[Windows PE Injection Vectors & Endpoint Detection Telemetry](docs/pe_injection_vectors_telemetry.md)**  
  *Comparative analysis of 11 distinct binary injection techniques and their kernel-mode observability (`ObRegisterCallbacks`, `PsSetCreateThreadNotifyRoutine`, VAD traversal).*
- **[Client Telemetry Protocol & Memory Traversal Specification](docs/telemetry_protocol_analysis.md)**  
  *Granular binary layout of diagnostic telemetry frames (`TelemetryRecordHeader`, `MemoryAnomalyPayload`) and decompiler pseudocode.*

---

## Tooling & Static Analysis Automation

- **`tools/vmp_atlas/build_atlas.py`**: Automated VMProtect handler merger combining 16 symbolic execution tool outputs into machine-readable `atlas.json` and `hook_manifest.json` (PE-sieve dump of 108 hooks).
- **`tools/kbdclass_analyzer/analyze_kbdclass.cpp`**: C++ static and dynamic analysis utility for locating `kbdclass!KeyboardClassServiceCallback` in Windows kernel memory.
- **`tools/vac_module_analyzer.py`**: Automated IDAPython script for locating native memory inspection primitives and annotating disassembly call sites with defensive audit bookmarks.

---

## Author & Verification

- **Lead Researcher:** Sergey Shunko
- **Contact:** `cc.simply.spolit@gmail.com`
- **Role:** Independent Binary Security Researcher
- **Scope:** Client-side endpoint telemetry, Windows x64 memory analysis, reverse engineering.

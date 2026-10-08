# Valve Anti-Cheat (VAC) Client Telemetry, Subtick Protocol, VMProtect Devirtualization & API Security Audits

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Type: Security Research / Advisories](https://img.shields.io/badge/Category-Defensive%20Security%20Research-red.svg)]()
[![Target: Source2 %2F Windows x64](https://img.shields.io/badge/Target-Source2%20%2F%20Windows%20x64-informational.svg)]()

## Overview

This repository contains in-depth defensive security research, architectural analysis, and technical advisories examining client-side endpoint telemetry, anti-tamper heuristics, kernel drivers, code virtualization, and backend API verification within modern gaming engines (specifically Valve Anti-Cheat / VAC Live on Source 2 and Windows x64 binaries).

All research was conducted in strictly isolated, offline development sandboxes using synthetic test harnesses to audit client-side verification boundaries.

---

## Published Security Advisories & Technical Papers

### 1. Client-Side & Memory Integrity Advisories
- **[ADV-2026-001: Client Memory Integrity Verification & Telemetry Collection Routines](advisories/ADV-2026-001_memory_scanning_telemetry.md)**  
  *Technical breakdown of virtual memory state polling (`NtQueryVirtualMemory`), unbacked executable page detection, thread stack backtracing, and report serialization.*

### 2. API & Infrastructure Security Advisories
- **[ADV-2026-003: Server-Side Request Forgery (SSRF) Audit in Case URL Dispatch](advisories/api_security_audits/ADV-2026-003_ssrf_case_url_audit.md)**  
  *Audit of backend demo-fetching endpoints, parser confusion vulnerabilities, OAST out-of-band verification, and mitigation allowlisting.*
- **[ADV-2026-004: Key-Value Parser Injection & State Poisoning Audit](advisories/api_security_audits/ADV-2026-004_key_value_injection_audit.md)**  
  *Analysis of serialized key-value protocols, escaping boundary failures, and payload validation.*
- **[ADV-2026-005: OpenID Authentication Replay & Session Validation Audit](advisories/api_security_audits/ADV-2026-005_openid_replay_mitigation.md)**  
  *Inspection of federated identity handshake tokens, replay attack surfaces, and cryptographic nonce enforcement.*

### 3. Comprehensive Architectural Whitepapers
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
  *Comparative analysis of 11 distinct binary injection techniques (LoadLibrary, LdrLoadDll, ManualMap, ThreadHijack, APC, Kernel, EarlyBird, Section, Atom, Process Doppelgänging, Module Overwrite) and their kernel-mode observability (`ObRegisterCallbacks`, `PsSetCreateThreadNotifyRoutine`, VAD traversal).*
- **[Client Telemetry Protocol & Memory Traversal Specification](docs/telemetry_protocol_analysis.md)**  
  *Granular binary layout of diagnostic telemetry frames (`TelemetryRecordHeader`, `MemoryAnomalyPayload`) and decompiler pseudocode.*

---

## Tooling & Static Analysis Automation

- **`tools/vmp_atlas/build_atlas.py`**: Automated VMProtect handler merger combining 16 symbolic execution tool outputs into machine-readable `atlas.json` and `hook_manifest.json` (PE-sieve dump of 108 hooks).
- **`tools/kbdclass_analyzer/analyze_kbdclass.cpp`**: C++ static and dynamic analysis utility for locating `kbdclass!KeyboardClassServiceCallback` in Windows kernel memory.
- **`tools/vac_module_analyzer.py`**: Automated IDAPython script for locating native memory inspection primitives and annotating disassembly call sites with defensive audit bookmarks.

---

## Research Scope & Ethics

All experiments were performed on locally hosted dummy modules and offline test binaries without connecting to live Valve matchmaking or production game servers. The primary goal of this research is educational: documenting client integrity models, helping endpoint defenders understand memory telemetry, and improving detection engineering for modern operating systems.

---

## Author & Verification

- **Lead Researcher:** Sergey Shunko
- **Role:** Independent Binary Security Researcher
- **Scope:** Client-side endpoint telemetry, Windows x64 memory analysis, reverse engineering.

# Source 2 Network Protocol Auditing, Server Input Validation & Endpoint Telemetry Research

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23640494.svg)](https://doi.org/10.5281/zenodo.23640494)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Type: Security Research / Advisories](https://img.shields.io/badge/Category-Defensive%20Security%20Research-red.svg)]()
[![Target: Source2 %2F Windows x64](https://img.shields.io/badge/Target-Source2%20%2F%20Windows%20x64-informational.svg)]()

## Overview

This repository contains defensive security research, static binary audits (`server.dll` / `client.dll`), coordinated vulnerability disclosure reports, and technical advisories examining server-side protobuf input validation, network deserialization bounds, backend API security, and endpoint memory-integrity verification on Windows x64.

All research and reproduction verification were conducted strictly in isolated, offline laboratory environments (`srcds -insecure +sv_lan 1`) to identify missing server-side validation boundaries and provide actionable remediation patches.

---

## Published Security Advisories & Coordinated Disclosures

### 1. Server-Side Input Validation Disclosures (Source 2 Dedicated Server / `server.dll`)
- **[CVD-2026-CS2-001: Unbounded Protobuf `subtick_moves` Deserialization & Angular Velocity Validation Failure (Server-Side DoS)](advisories/valve_server_disclosures/H1_Report_Subtick_Input_Validation.md)**  
  *Static disassembly and root-cause analysis of missing cardinality and angular-velocity bounds on incoming `CBaseUserCmdPB` / `CSubtickMoveStep` protobuf messages (`CWE-20`, `CWE-400`, `CWE-1284`), local `srcds` reproduction telemetry, and server-side C++ mitigation patches.*
- **[CVD-2026-CS2-002: Fractional Subtick Delta-Time (`dt=0`) Cooldown Validation Bypass in `CSBaseGunFire`](advisories/valve_server_disclosures/H1_Report_Firerate_Bypass.md)**  
  *Analysis of fractional tick-ratio comparison flaws in `CanPrimaryAttack` (`0x1809964D0`) permitting duplicate primary fire execution within a single server simulation tick (`CWE-20`, `CWE-841`).*
- **[CVD-2026-CS2-003: Missing Server-Side View-Angle Pitch Clamping & AnimGraph NaN Extrapolation Crash](advisories/valve_server_disclosures/H1_Report_Viewangle_Spoof_Crash.md)**  
  *Full static audit across 104,543 functions in `server.dll` proving that `±89.0f` pitch clamps exist only on AI bot entities (`CCSBot`), leaving player `m_angEyeAngles` (`+0x1340`) unclamped (`CWE-20`, `CWE-682`).*

### 2. Endpoint Integrity & Memory Verification Advisories
- **[ADV-2026-001: Architecture of Client-Side Memory Page Validation & Heuristic Telemetry Reporting](advisories/ADV-2026-001_memory_scanning_telemetry.md)**  
  *Defensive breakdown of virtual address space traversal (`NtQueryVirtualMemory`), relocation-masked `.text` verification, and diagnostic telemetry serialization.*

### 3. Backend API & Authentication Security Advisories
- **[ADV-2026-003: Server-Side Request Forgery (SSRF) & URL Parser Confusion in Automated Replay Ingestion Pipelines](advisories/api_security_audits/ADV-2026-003_ssrf_case_url_audit.md)**  
  *Analysis of asynchronous replay-fetching workers (`CWE-918`), DNS rebinding vectors, and post-resolution IP allowlisting.*
- **[ADV-2026-004: Valve Data Format (VDF / KeyValues) Serializer Injection & Recursive Parser Exhaustion](advisories/api_security_audits/ADV-2026-004_key_value_injection_audit.md)**  
  *Structural delimiter breakout (`CWE-943`), unbounded recursion (`CWE-674`), and Unicode digit normalization flaws (`CWE-178`) in VDF parsers.*
- **[ADV-2026-005: Authentication Bypass & Assertion Replay Vulnerabilities in Custom OpenID 2.0 Relying Parties](advisories/api_security_audits/ADV-2026-005_openid_replay_mitigation.md)**  
  *Audit of custom OpenID 2.0 callback verifiers (`CWE-290`, `CWE-294`), `openid.op_endpoint` pinning, and single-use nonce enforcement.*

---

## Technical Whitepapers & Static Disassembly Audits

- **[Static Hex-Rays Audit of Server Input Processing (`server.dll` v14171)](docs/server_dll_input_audit.md)**  
  *Decompilation walk of `sub_180A7F550`, `sub_1803BBAE0`, and `sub_18015B7A0` demonstrating unclamped write paths to `CCSPlayerPawn::m_angEyeAngles` (`+0x1340`).*
- **[Subtick Input Validation & Protobuf Telemetry in Source 2](docs/subtick_protobuf_telemetry.md)**  
  *Wire-format specification of `CBaseUserCmdPB` and `CSubtickMoveStep` fractional tick reconciliation rules.*
- **[False-Positive Mitigation in Subtick Telemetry: Differentiating Network Jitter & 8000Hz Peripherals](docs/vac_subtick_false_positive_mitigation.md)**  
  *Mathematical model of temporal monotonicity verification, biomechanical velocity clamping, and Exponential Moving Average (EMA) consensus scoring.*
- **[Client Telemetry Protocol & Memory Traversal Specification](docs/telemetry_protocol_analysis.md)**  
  *Specification of `MEMORY_BASIC_INFORMATION` region anomaly classification and relocation-aware section integrity checks.*
- **[Windows PE In-Memory Injection Vectors & Kernel Telemetry Observability](docs/pe_injection_vectors_telemetry.md)**  
  *Comparative matrix of 11 PE mapping vectors and their observability via `ObRegisterCallbacks` and `PsSetCreateThreadNotifyRoutine`.*
- **[VMProtect 3.6–3.10.5 Devirtualization Atlas & Handler Dispatch Analysis](docs/vmp_devirtualization_atlas.md)**  
  *Reconstruction of virtual register conventions, Mixed Boolean-Arithmetic (MBA) dispatchers, and A/B/A CRC-integrity tables for static binary auditing.*

---

## Defensive Analysis Tooling & Audit Package

- **[Audit Preparation & Architecture Package (`AUDIT_PREP.md`)](AUDIT_PREP.md)** — Trail of Bits-style review goals, scope, data-flow diagram, and automated unit test suite (`3/3 PASS`).
- **[`tools/vac_module_analyzer.py`](tools/vac_module_analyzer.py)** — Dual-mode (IDA Pro IDAPython + standalone CLI) static analysis script for locating and annotating virtual memory inspection primitives (`NtQueryVirtualMemory`, `VirtualQueryEx`, `K32GetMappedFileNameW`).
- **[`ccsimplyspolit/protobuf-bounds-auditor`](https://github.com/ccsimplyspolit/protobuf-bounds-auditor)** — Companion static security analyzer for `.proto` definitions (`CWE-1284` unbounded repeated sub-messages and `CWE-20` unvalidated float/double wire fields).

---

## Author & Contact

- **Lead Researcher:** Serhii Shunko
- **Contact:** `cc.simply.spolit@gmail.com`
- **Scope:** Application & Binary Security Research, Protocol Input Validation, Static Disassembly Auditing

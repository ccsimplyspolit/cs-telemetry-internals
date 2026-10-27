# Source 2 Network Protocol Auditing, Server Input Validation & Endpoint Telemetry Research

[![CI](https://github.com/ccsimplyspolit/cs-telemetry-internals/actions/workflows/ci.yml/badge.svg)](https://github.com/ccsimplyspolit/cs-telemetry-internals/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23640494.svg)](https://doi.org/10.5281/zenodo.23640494)
[![Type: Security Research / Whitepapers](https://img.shields.io/badge/Category-Defensive%20Security%20Research-red.svg)](AUDIT_PREP.md)
[![Target: Source2 %2F Windows x64](https://img.shields.io/badge/Target-Source2%20%2F%20Windows%20x64-informational.svg)](AUDIT_PREP.md)

## Overview

This repository contains defensive security research, static binary audits (`server.dll` / `client.dll`), and technical whitepapers examining server-side protobuf input validation, network deserialization bounds, and endpoint memory-integrity verification on Windows x64, paired with a dual-mode IDAPython/CLI static analyzer (`tools/vac_module_analyzer.py`).

All research and verification were conducted strictly in isolated, offline laboratory environments (`srcds -insecure +sv_lan 1`) to analyze server-side validation boundaries and memory inspection primitives.

---

## Technical Whitepapers & Static Disassembly Audits (`docs/`)

1. **[Static Hex-Rays Audit of Server Input Processing (`server.dll` v14171)](docs/server_dll_input_audit.md)**  
   *Decompilation walk of `sub_180A7F550`, `sub_1803BBAE0`, and `sub_18015B7A0` demonstrating unclamped write paths to `CCSPlayerPawn::m_angEyeAngles` (`+0x1340`).*
2. **[Subtick Input Validation & Protobuf Telemetry in Source 2](docs/subtick_protobuf_telemetry.md)**  
   *Wire-format specification of `CBaseUserCmdPB` and `CSubtickMoveStep` fractional tick reconciliation rules.*
3. **[False-Positive Mitigation in Subtick Telemetry: Differentiating Network Jitter & 8000Hz Peripherals](docs/vac_subtick_false_positive_mitigation.md)**  
   *Mathematical model of temporal monotonicity verification, biomechanical velocity clamping, and Exponential Moving Average (EMA) consensus scoring.*
4. **[Client Telemetry Protocol & Memory Traversal Specification](docs/telemetry_protocol_analysis.md)**  
   *Specification of `MEMORY_BASIC_INFORMATION` region anomaly classification and relocation-aware section integrity checks.*
5. **[Windows PE In-Memory Injection Vectors & Kernel Telemetry Observability](docs/pe_injection_vectors_telemetry.md)**  
   *Comparative matrix of 11 PE mapping vectors and their observability via `ObRegisterCallbacks` and `PsSetCreateThreadNotifyRoutine`.*
6. **[VMProtect 3.6–3.10.5 Devirtualization Atlas & Handler Dispatch Analysis](docs/vmp_devirtualization_atlas.md)**  
   *Reconstruction of virtual register conventions, Mixed Boolean-Arithmetic (MBA) dispatchers, and A/B/A CRC-integrity tables for static binary auditing.*

---

## Defensive Analysis Tooling & Audit Package

- **[Audit Preparation & Architecture Package (`AUDIT_PREP.md`)](AUDIT_PREP.md)** — Trail of Bits-style review goals, scope, data-flow diagram, and automated unit test suite (`3/3 PASS`).
- **[`tools/vac_module_analyzer.py`](tools/vac_module_analyzer.py)** — Dual-mode (IDA Pro IDAPython + standalone CLI) static analysis script for locating and annotating virtual memory inspection primitives (`NtQueryVirtualMemory`, `VirtualQueryEx`, `K32GetMappedFileNameW`).
- **[`test_vac_module_analyzer.py`](test_vac_module_analyzer.py)** — Automated unit test suite verifying standalone ASCII/UTF-16LE binary scanning, primitive list completeness, and CLI execution (`3/3 PASS`).
- **[`ccsimplyspolit/protobuf-bounds-auditor`](https://github.com/ccsimplyspolit/protobuf-bounds-auditor)** — Companion static security analyzer for `.proto` definitions (`CWE-1284` unbounded repeated sub-messages and `CWE-20` unvalidated float/double wire fields).

### Running the Unit Test Suite

```bash
python -m unittest discover -v
```

---

## Author & Contact

- **Lead Researcher:** Serhii Shunko (`@sshunko` / `@ccsimplyspolit`, ORCID [`0009-0002-4183-0361`](https://orcid.org/0009-0002-4183-0361))
- **Contact:** `cc.simply.spolit@gmail.com`
- **Scope:** Application & Binary Security Research, Protocol Input Validation, Static Disassembly Auditing

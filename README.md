# Valve Anti-Cheat (VAC) Client Telemetry & Memory Verification Internals

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Type: Security Advisory / Research](https://img.shields.io/badge/Category-Defensive%20Security%20Advisory-red.svg)]()
[![Target: Client Telemetry](https://img.shields.io/badge/Target-Source2%20%2F%20VAC-informational.svg)]()

## Overview

This repository contains independent defensive security research, architectural analysis, and security advisories examining client-side telemetry, memory auditing mechanisms, and anti-tamper heuristics within modern client integrity systems (specifically Valve Anti-Cheat / VAC and VAC Live on the Source 2 engine).

All research was conducted in strictly isolated, offline development sandboxes using synthetic test harnesses to audit client-side verification boundaries.

---

## Published Security Advisories & Disclosures

- **[ADV-2026-001: Client Memory Integrity Verification & Telemetry Collection Routines](advisories/ADV-2026-001_memory_scanning_telemetry.md)**  
  *Technical breakdown of virtual memory state polling (`NtQueryVirtualMemory`), unbacked executable page detection, thread stack backtracing, and report serialization.*

---

## Research Scope & Ethics

All experiments were performed on locally hosted dummy modules and offline test binaries without connecting to live Valve matchmaking or production game servers. The primary goal of this research is educational: documenting client integrity models, helping endpoint defenders understand memory telemetry, and improving detection engineering for modern operating systems.

---

## Repository Structure

```
├── advisories/
│   └── ADV-2026-001_memory_scanning_telemetry.md  # Formal security research advisory
├── docs/
│   └── telemetry_protocol_analysis.md             # Breakdown of packet structures & report fields
├── tools/
│   └── vac_module_analyzer.py                     # Static analysis tool for scanning inspection primitives
├── LICENSE                                        # MIT License
└── SECURITY.md                                    # Responsible disclosure guidelines
```

---

## Author & Verification

- **Lead Researcher:** Sergey Shunko
- **Role:** Independent Binary Security Researcher
- **Scope:** Client-side endpoint telemetry, Windows x64 memory analysis, reverse engineering.

#!/usr/bin/env python3
"""
vac_module_analyzer.py
Defensive static analysis utility for enumerating virtual memory inspection primitives
(VirtualQuery, NtQueryVirtualMemory, K32GetMappedFileNameW) in Windows x64 PE binaries.
Supports both interactive IDA Pro (IDAPython) annotation and standalone CLI/unit-test analysis.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List

try:
    import idaapi  # type: ignore
    import idautils  # type: ignore
    import idc  # type: ignore

    HAS_IDA = True
except ImportError:
    HAS_IDA = False

INTEGRITY_PRIMITIVES: List[str] = [
    "VirtualQuery",
    "VirtualQueryEx",
    "NtQueryVirtualMemory",
    "ZwQueryVirtualMemory",
    "CreateToolhelp32Snapshot",
    "GetMappedFileNameW",
    "K32GetMappedFileNameW",
]


def scan_binary_bytes(data: bytes) -> Dict[str, List[int]]:
    """Locate ASCII/UTF-16LE import symbol occurrences and offsets in a raw PE image."""
    results: Dict[str, List[int]] = {}
    for primitive in INTEGRITY_PRIMITIVES:
        ascii_pat = re.escape(primitive.encode("ascii"))
        utf16_pat = re.escape(primitive.encode("utf-16le"))
        offsets = [m.start() for m in re.finditer(ascii_pat, data)]
        offsets.extend(m.start() for m in re.finditer(utf16_pat, data))
        if offsets:
            results[primitive] = sorted(set(offsets))
    return results


def scan_integrity_xrefs() -> int:
    """Scan and annotate integrity primitives inside an active IDA Pro database."""
    if not HAS_IDA:
        print("[!] IDAPython runtime not detected; use CLI file mode: python vac_module_analyzer.py <binary.dll>")
        return 0

    print("[*] Scanning IDA database for memory integrity audit primitives...")
    found_calls = 0

    for primitive in INTEGRITY_PRIMITIVES:
        ea = idc.get_name_ea_simple(primitive)
        if ea == idaapi.BADADDR:
            continue

        print(f"[+] Found API import: {primitive} at 0x{ea:X}")
        for ref in idautils.CodeRefsTo(ea, 0):
            func = idaapi.get_func(ref)
            caller_name = idaapi.get_func_name(func.start_ea) if func else "unknown"
            print(f"    -> Referenced at 0x{ref:X} inside {caller_name}")
            idc.set_cmt(ref, f"[AUDIT] Integrity check routine invoking {primitive}", 1)
            found_calls += 1

    print(f"[*] Analysis complete. Found {found_calls} integrity call sites.")
    return found_calls


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Static analyzer for Windows x64 memory-integrity inspection primitives"
    )
    parser.add_argument("binary", nargs="?", help="Optional path to PE binary (.dll / .exe) for standalone scan")
    args = parser.parse_args(argv)

    if args.binary:
        data = Path(args.binary).read_bytes()
        hits = scan_binary_bytes(data)
        for prim, offsets in hits.items():
            hex_offs = ", ".join(f"0x{o:X}" for o in offsets)
            print(f"[+] {prim}: {hex_offs}")
        return 0

    scan_integrity_xrefs()
    return 0


if __name__ == "__main__":
    sys.exit(main())

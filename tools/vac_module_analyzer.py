#!/usr/bin/env python3
"""
vac_module_analyzer.py
Static analysis tool for reverse-engineering memory auditing routines in client binaries.
Targeted at IDA Pro Python API.
"""

import idaapi
import idautils
import idc

INTEGRITY_PRIMITIVES = [
    "VirtualQuery",
    "VirtualQueryEx",
    "NtQueryVirtualMemory",
    "ZwQueryVirtualMemory",
    "CreateToolhelp32Snapshot",
    "GetMappedFileNameW",
    "K32GetMappedFileNameW"
]

def scan_integrity_xrefs():
    print("[*] VAC Module Analyzer: Scanning for memory integrity audit primitives...")
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

if __name__ == "__main__":
    scan_integrity_xrefs()

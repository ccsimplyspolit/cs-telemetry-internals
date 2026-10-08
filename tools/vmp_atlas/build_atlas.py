#!/usr/bin/env python3
"""Consolidate all 14 devirt-worker outputs into single machine-readable atlas.

Reads outputs from t02/t03/t04/t06/t07/t08/t09/t12/t13/t18/t19/t20 + Rasetsuu +
Mergen + devirt_vmprotect3 under C:/Users/sshunko/source/repos/tools/, produces
atlas.json keyed by RVA with union of every tool's findings.

Run: py -3 docs/vmp_atlas/build_atlas.py
"""
from __future__ import annotations
import json, os, sys, re, glob
from pathlib import Path

TOOLS = Path("C:/Users/sshunko/source/repos/tools")
OUT = Path(__file__).parent / "atlas.json"

atlas: dict[str, dict] = {}

def ensure(rva_int: int) -> dict:
    key = f"0x{rva_int:x}"
    return atlas.setdefault(key, {
        "rva": rva_int,
        "section": None,
        "seed_key": None,
        "handler_class": None,
        "sources": [],
        "decrypted_bytes": {},
        "llvm_ir": [],
        "next_hops": [],
        "extras": {},
    })

def add_source(entry: dict, tool: str, note: str = ""):
    entry["sources"].append({"tool": tool, "note": note})

# --- Rasetsuu diag JSON — decrypted VIP streams
p = Path("C:/tmp/rasetsuu/vmp_out.json.diag.json")
if p.exists():
    try:
        d = json.loads(p.read_text())
        for im in d.get("push_immediates", []) if isinstance(d, dict) else []:
            rva = im if isinstance(im, int) else int(str(im), 0)
            e = ensure(rva)
            add_source(e, "rasetsuu", "push imm captured")
        for s in d.get("decrypted_streams", []) if isinstance(d, dict) else []:
            if not isinstance(s, dict): continue
            vip = s.get("vip", 0)
            e = ensure(vip - 0x180000000 if vip >= 0x180000000 else vip)
            e["section"] = s.get("section", e["section"])
            e["decrypted_bytes"]["rasetsuu"] = {
                "vip_va": vip,
                "enc": s.get("enc_hex", "")[:128],
                "dec": s.get("dec_hex", "")[:128],
                "cipher": "CRC*31 XOR",
            }
            add_source(e, "rasetsuu", f"CRC*31 decrypt window at {s.get('section')}")
    except Exception as ex:
        print(f"  rasetsuu diag: {ex}", file=sys.stderr)

# --- Mergen LLVM IR outputs
for lp in sorted(TOOLS.glob("Mergen/build_iced/output*.ll")):
    m = re.search(r"0x([0-9a-fA-F]+)", lp.name)
    if m:
        rva = int(m.group(1), 16)
    elif "no_opts" in lp.name and "_" not in lp.stem.replace("output_no_opts", ""):
        rva = 0x1AB7E6
    else:
        continue
    e = ensure(rva)
    txt = lp.read_text(errors="ignore")
    # scan for `store i64 <key>, ptr %<n>` — VMP push imm
    for mkey in re.finditer(r"store i64 (\d+), ptr", txt):
        k = int(mkey.group(1))
        if 0x1000 < k < 0xFFFFFFFF:
            e["seed_key"] = k
            break
    e["llvm_ir"].append({"tool": "Mergen", "path": str(lp), "size": lp.stat().st_size})
    add_source(e, "Mergen", "LLVM 18.1.8 lifted")

# --- t04 eversinc33 pseudo-LLVM
p = TOOLS / "t04_eversinc33_llvm_devirt" / "vmenter_1AB7E6.ll.txt"
if p.exists():
    for m in re.finditer(r"@vmenter_0x([0-9A-Fa-f]+)", p.read_text(errors="ignore")):
        rva = int(m.group(1), 16)
        e = ensure(rva)
        e["llvm_ir"].append({"tool": "t04_eversinc33", "path": str(p)})
        add_source(e, "t04_eversinc33", "pseudo-LLVM lifted")

# --- t07 hackyboiz LLVM handlers
for lp in sorted((TOOLS / "t07_triton_vmp" / "lifted").glob("handler_*.ll")):
    m = re.search(r"handler_([0-9a-fA-F]+)", lp.name)
    if not m: continue
    rva = int(m.group(1), 16)
    e = ensure(rva)
    e["llvm_ir"].append({"tool": "t07_hackyboiz_triton", "path": str(lp)})
    txt = lp.read_text(errors="ignore")
    if "bswap" in txt and "udiv" in txt:
        e["handler_class"] = "bswap+udiv (MBA collapse)"
    add_source(e, "t07_hackyboiz_triton", "Triton→LLVM IR")

# --- t09 Thalium per-VMEnter traces
for jp in sorted(TOOLS.glob("t09_thalium_devirt/thalium_devirt_*.json")):
    m = re.search(r"thalium_devirt_([0-9A-Fa-f]+)", jp.name)
    if not m: continue
    rva = int(m.group(1), 16)
    e = ensure(rva)
    e["extras"].setdefault("triton_traces", []).append({"tool": "t09_thalium", "path": str(jp), "size": jp.stat().st_size})
    add_source(e, "t09_thalium", "Triton symbolic execution trace")

# --- devirt_vmprotect3 fvac_run — VA-keyed
for d in sorted((TOOLS / "devirt_vmprotect3" / "fvac_run").glob("hdl_*")):
    m = re.search(r"hdl_([0-9a-fA-F]+)", d.name)
    if not m: continue
    va = int(m.group(1), 16)
    rva = va - 0x7FFEBCF90000
    e = ensure(rva)
    ll = list(d.glob("*.ll"))
    if ll:
        txt = ll[0].read_text(errors="ignore")
        mret = re.search(r"ret i64 (\d+)", txt)
        if mret:
            e["next_hops"].append({
                "tool": "devirt_vmprotect3",
                "next_va": int(mret.group(1)),
                "next_rva_hex": f"0x{int(mret.group(1)) - 0x7FFEBCF90000:x}",
            })
        e["llvm_ir"].append({"tool": "devirt_vmprotect3", "path": str(ll[0])})
    add_source(e, "devirt_vmprotect3", "Triton PE-direct loader")

# --- Pushan flat_cfg per VMEnter (blocks+handlers)
for jp in sorted(TOOLS.glob("pushan_proto/run_*/flat_cfg.json")):
    m = re.search(r"run_([0-9a-fA-F]+)", str(jp))
    if not m: continue
    rva = int(m.group(1), 16)
    e = ensure(rva)
    try:
        d = json.loads(jp.read_text())
        e["extras"]["pushan"] = {
            "blocks": len(d.get("blocks", d)) if isinstance(d, (dict, list)) else 0,
            "vpc_register": d.get("vpc") if isinstance(d, dict) else None,
            "path": str(jp),
        }
    except Exception:
        pass
    add_source(e, "pushan", "Stage-1 VPC-sensitive flat CFG")

# --- t02 CFG signature scanner (dump run)
p = Path("C:/Users/sshunko/source/repos/tools/t02_cfg_sig/out.json")
if p.exists():
    try:
        d = json.loads(p.read_text())
        for s in d.get("vmenter_verified", []):
            rva = int(s.get("rva", 0), 16) if isinstance(s.get("rva"), str) else s.get("rva", 0)
            if rva:
                e = ensure(rva)
                e["section"] = s.get("section", e["section"])
                if s.get("push_imm"):
                    v = s["push_imm"]
                    e["seed_key"] = int(v, 16) if isinstance(v, str) else v
                add_source(e, "t02_cfg_sig", "push-imm+jmp verified")
    except Exception as ex:
        print(f"  t02 out: {ex}", file=sys.stderr)

# --- Known VMEnter seeds from workflow reports (belt-and-suspenders)
KNOWN_SEEDS = {
    0x1AB7E6: 0x80021,
    0x1E1D26: 0xFFFFFFFF8149C614 & 0xFFFFFFFF,
    0x206677: 0x342DAAA1,
    0x211691: 0x20889A18,
}
for rva, seed in KNOWN_SEEDS.items():
    e = ensure(rva)
    if e["seed_key"] is None:
        e["seed_key"] = seed
    e["section"] = e["section"] or ".#I5"

# --- t20 IAT
p = Path("C:/Users/sshunko/AppData/Local/Temp/claude/C--Users-sshunko-source-repos-MyDriver23/d5a2e702-17c2-4214-a997-cee0079b5f54/scratchpad/fuckvacv2_iat.tsv")
iat_entries = 0
if p.exists():
    for line in p.read_text().splitlines():
        if line.startswith("0x00007ffebd"):
            iat_entries += 1

atlas["_meta"] = {
    "generated_from": "docs/vmp_atlas/build_atlas.py",
    "target": {
        "static_dll": "C:/Users/sshunko/source/repos/MyDriver23/source/dlls/FuckVacV2.dll (2224128B)",
        "dump_dll": "C:/Users/sshunko/source/repos/MyDriver23/source/dlls/FuckVacV2_dump.dll (4546560B)",
        "image_base_dump": "0x7FFEBCF90000",
        "image_base_static": "0x180000000",
        "vmp_version": "3.6-3.10.5",
    },
    "totals": {
        "vmenters_catalogued": sum(1 for k, v in atlas.items() if isinstance(v, dict) and v.get("seed_key")),
        "handlers_devirt": sum(1 for k, v in atlas.items() if isinstance(v, dict) and v.get("llvm_ir")),
        "iat_entries_from_t20": iat_entries,
    },
    "confirmed_facts": {
        "cipher": "CRC*31 XOR stream (Rasetsuu src/decrypt.rs::OpcodeCryptor)",
        "register_roles": {
            "VIP": "RSI",
            "VSP": "RBP",
            "ROLLING_KEY": "RBX",
            "VMREGs_base": "RDI",
            "HANDLER_TABLE": "R12",
            "IMAGEBASE": "R13",
        },
        "shared_dispatcher_va": "0x7FFEBD34A085 (all 5 devirt'd handlers converge here)",
        "on_disk_section": ".#?n (backs everything; .#I5 raw=0 in packed, VMP decrypts at TLS callback)",
    },
    "sources": [
        "t02_cfg_sig", "t03_ida_vmp_hunter", "t04_eversinc33_llvm_devirt",
        "t06_hackyboiz", "t07_hackyboiz_triton", "t08_ticklingvmp",
        "t09_thalium_devirt", "t12_oasif", "t13_ticklingvmp_part23",
        "t18_hadengue", "t19_0xnobody", "t20_vmp_imports",
        "rasetsuu (vmprotect-research)", "Mergen", "devirt_vmprotect3",
        "pushan_proto",
    ],
}

OUT.write_text(json.dumps(atlas, indent=2))
print(f"[+] wrote {OUT} ({OUT.stat().st_size} bytes)")
print(f"    VMEnters catalogued: {atlas['_meta']['totals']['vmenters_catalogued']}")
print(f"    Handlers with LLVM IR: {atlas['_meta']['totals']['handlers_devirt']}")
print(f"    IAT entries (t20): {atlas['_meta']['totals']['iat_entries_from_t20']}")

# also emit a human-readable summary
summary = OUT.with_suffix(".md")
lines = ["# VMP Handler Atlas — consolidated 2026-07-06", "",
         f"Sources: {len(atlas['_meta']['sources'])} tools", "",
         "## Catalogued VMEnters + handlers", "",
         "| RVA | Section | Seed key | Class | Sources | LLVM IR? | Next-hop? |",
         "|---|---|---|---|---|---|---|"]
for k, v in sorted(atlas.items()):
    if not k.startswith("0x"): continue
    src_count = len(v.get("sources", []))
    ir = "yes" if v.get("llvm_ir") else "-"
    nh = "yes" if v.get("next_hops") else "-"
    seed = f"0x{v['seed_key']:x}" if v.get("seed_key") else "-"
    lines.append(f"| {k} | {v.get('section','?')} | {seed} | {v.get('handler_class','-')} | {src_count} | {ir} | {nh} |")
summary.write_text("\n".join(lines))
print(f"[+] wrote {summary}")

# 06 — fva_devirt (standalone VMP static analyzer)

Single-translation-unit C++ x64 tool that reproduces (without IDA) the VMP invariants documented in `docs/FVA_PROTECTION_STATE.md` and `docs/DRAFT_VM_PAYLOAD_CORRELATION_REVIEW.md`. Point of this tool is **repeatability**: any future FVA build or any other VMP 3.5/3.6+ target can be dropped in and get the same analysis without an IDA license or Hex-Rays.

Source root: `source/dlls/fva_devirt/`
Binary: `x64\Release\fva_devirt.exe` (~700 lines, no runtime deps other than kernel32 + bcrypt).

---

## What it produces

Given `fva_devirt.exe C:\vmp\FuckVacAgain.dll`, writes next to the input:

- `<basename>_devirt_data.json` — machine-readable inventory.
- `<basename>_devirt_report.md` — human-readable summary.

Both contain:

- Payload identity (SHA-256, image base, file/image size).
- Section map with sanitized names for VMP-renamed sections (`.#I5` → `._I5`, `.#?n` → `._?n`).
- **VMP version pinning** (3.5.1 vs 3.6+) from AntiDebug primitive counts.
- Universal VMExit tail localization (must be unique for a clean VMP wrapper).
- Dispatcher site inventory: `jmp r10`, `jmp r9`, `jmp qword ptr [rcx*8+K]`.
- Per-dispatch-site preambles (32 raw bytes preceding each dispatcher, ready for a symbolic decoder).
- AntiDebug primitive counts: `int 2Dh`, direct `syscall`, `rdtsc`, `int 3`.
- Candidate routing tables with **A/B/A CRC-integrity triple detection**.

## What it does NOT produce (yet)

Honestly documented in the emitted report:

- **Decoded p-code stream** — requires `entry_cryptor` initial key recovery (per-build fixup in the entry stub). Solving that would need either a 3.6 leak (public sources are 3.5.1) or manual constraint solving on the entry stub bytes.
- **Handler-body symbolic lift** — requires an x86 decoder + IR + full CFG walk per VM segment. The preamble bytes this tool emits are the raw input to such a lifter; the lifter itself is Ghidra-scale.
- **Compilable source-equivalent output** — needs both of the above plus a code generator.

If you need a compilable reimplementation of FVA behavior, look at the sibling project VLB — a from-scratch native-layer reimplementation via CS2 hooks, not a devirtualization.

---

## Build

```powershell
$m = 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe'
& $m 'C:\Users\sshunko\source\repos\MyDriver23\source\dlls\fva_devirt\fva_devirt.vcxproj' `
    /p:Configuration=Release /p:Platform=x64 /m /nologo /v:minimal /t:Rebuild
```

Output: `source/dlls/x64/Release/fva_devirt.exe`.

---

## Usage

```powershell
fva_devirt.exe C:\vmp\FuckVacAgain.dll
```

Produces:

- `C:\vmp\FuckVacAgain_devirt_data.json`
- `C:\vmp\FuckVacAgain_devirt_report.md`

Optional `--out <dir>` to redirect output.

---

## Expected results on the reference FVA

`C:\vmp\FuckVacAgain.dll` (SHA-256 `af02612545e4f849…eb6d319`):

| Metric | Expected |
|---|---|
| SHA-256 | `af02612545e4f84920bad38b9fe5ec6c60d6bce656931afe215e42821eb6d319` |
| Image base | `0x180000000` |
| Sections with RX | 3 (`.text`, `._I5`, `._?n`) |
| VMExit tail hits | **exactly 1** at `0x18023d25e` |
| `jmp r10` sites | 34 |
| `jmp r9` sites | 2 |
| `jmp [rcx*8+K]` | 1 |
| `int 2Dh` hits | ≥ 20 |
| `syscall` hits | ≥ 30 |
| `rdtsc` hits | ≥ 30 |
| Verdict | **VMP 3.6+** |
| Routing table | at `0x18045a028` (or near) with A/B/A triples > 0 |

If any of these diverge → either the DLL has changed (new FVA release) or the scanner has a bug. Inspect `_devirt_data.json` first.

---

## Section layout on the reference FVA

Per `docs/VMP_PROTECTION_MECHANICS_FULL.md` §2:

| Section | VA range | vsize | raw_size | Role |
|---|---|---|---|---|
| `.text` | `0x180001000..0x180123000` | `0x122000` | **0** | ZEROED on disk. Original code lives here at runtime after LAYER 1 decompression. |
| `.rdata` | `0x180123000..0x180183000` | `0x60000` | **0** | ZEROED. Read-only data (strings, RTTI, tables). |
| `.data` | `0x180183000..0x18018d000` | `0xa000` | **0** | ZEROED. Writeable data. |
| `.pdata` | `0x18018d000..0x18019a000` | `0xd000` | **0** | ZEROED. SEH unwind info. |
| `.fptable` | `0x18019a000..0x18019b000` | `0x1000` | **0** | ZEROED. |
| `._I5` | `0x18019b000..0x18023b000` | **`0xa0000`** | **0** | ZEROED on disk. At runtime holds **decrypted p-code tape** (652 KB). |
| `.=ly` | `0x18023b000..0x18023c000` | `0x755` | `0x800` | On-disk, VMP metadata. |
| `._?n` | `0x18023c000..0x18045b000` | **`0x21e19c`** | **`0x21e200`** | On-disk, FULL 2.2 MB. **Handler executor** + encrypted p-code source. |
| `.reloc` | `0x18045b000..0x18045c000` | `0x54` | `0x200` | Base relocations (minimal). |

Key insight: everything the DLL "does" originates from `._?n` on disk. `.text` on disk is empty; VMP's unpacker in `._?n` reconstructs `.text` in memory at runtime. This is why static disassembly of `.text` shows all zeros.

---

## Dispatcher shape (Advanced VM)

From FVA at site `0x1803f4e1b`:

```
mov dword ptr [rcx + 0x58], 0x41c6ff66     ; MBA junk
and ebx, 0x27bde325                        ; MBA junk
movsxd rax, eax                            ; sign-extend delta
adc rdi, rax                               ; crypt_registr += delta (running key)
movsx ecx, r10w                            ; setup / junk
shr edx, 0x1b                              ; MBA junk
or r10, rdi                                ; jmp_registr += delta (ADD obfuscated to OR via MBA)
jmp r10                                    ; dispatch
```

Empirical register roles for this build:
- `jmp_registr = R10` (34 dispatch sites vs 2 for R9 — proved statistically)
- `crypt_registr = RDI` (`or r10, rdi` before dispatch)
- `pcode_registr = RBP` (hypothesis)
- `stack_registr = ?` (candidate RSP)

Randomized per build per source (intel.cc:28593-28636).

---

## AntiDebug primitives (VMP 3.6+ signals)

| Bytes | Instruction | Count | Role |
|---|---|---|---|
| `CD 2D` | `int 2Dh` | 24 | KiRaiseAssertion — under debugger, EIP advances by 1 byte, VMP catches it. Absent in 3.5.1 sources. |
| `0F 05` | `syscall` | 52 | Direct-syscall — bypass usermode NTDLL hooks. Same primitive used by FVA's 5.6 kHz self-scan. |
| `0F 31` | `rdtsc` | 46 | Timing check. Step-through / BP slow execution → VMP detects. |
| `CD 03` | `int 3` | 29 | SEH-guarded BP probes. If SEH handler runs → no debugger; if not → debugger swallowed the event. |

Some hits are false positives (bytes inside other-instruction operands), but 24 + 52 + 46 + 29 is too large for coincidence — especially `0F 05` which needs rax setup for a syscall number.

Combined with the 15+ instruction MBA-obfuscated DllEntryPoint (3.5.1 AddGate emits only 2 instructions), verdict: **VMP 3.6+**.

---

## Routing table detection (A/B/A CRC-integrity triples)

`fva_devirt.exe` output shows 6 routing tables:

| Table VA | Entries | A/B/A triples |
|---|---|---|
| `0x180338DC4` | 12 | 0 |
| `0x180374220` | 13 | 2 |
| `0x18044D7D0` | 4096 | **419** |
| `0x1804517D0` | 4096 | **590** |
| `0x1804557D0` | 4096 | **459** |
| `0x1804597D0` | 627 | **65** |

Total A/B/A triples: **1535** across the largest tables. Each triple is `(A, B, A)` where `entry[i] == entry[i+2]` and `entry[i] != entry[i+1]`. Tampering with A in position i without also tampering with position i+2 fails the integrity check.

Practical implication: if you patch a routing table entry (say to redirect a handler to your own code), you must also patch the DUPLICATE entry two positions later. Naive single-entry patches are detected.

---

## Reproducibility on any future FVA build

The scanner produces its full output on the immutable `FuckVacAgain.dll` alone (no runtime dump needed for observational layer). Full pipeline:

```powershell
# 1. Build
$m = 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe'
& $m 'C:\Users\sshunko\source\repos\MyDriver23\source\dlls\fva_devirt\fva_devirt.vcxproj' `
    /p:Configuration=Release /p:Platform=x64

# 2. Run against target
source\dlls\fva_devirt\x64\Release\fva_devirt.exe C:\vmp\FuckVacAgain.dll

# 3. Run Python analyzers (in sibling VMP-Deob repo)
python C:\vmp\build\devirt_v2\static_task_bundle.py       # tasks 21-25
python C:\vmp\build\devirt_v2\preamble_decoder.py         # capstone decode of preambles
python C:\vmp\build\devirt_v2\segment_lifter.py           # VM segment walker
python C:\vmp\build\devirt_v2\analyze_vtable_poisoning.py # host DLL diff analysis
```

---

## What the JSON is for

The `_devirt_data.json` is machine-readable input for the next stages of devirtualization (not implemented in this tool, sketched here):

1. **Entry-cryptor recovery** — take preamble bytes at each `jmp r10` site + entry-stub bytes at `entry_rva`, run through a constraint solver to identify the rolling-key initial value. Biggest missing piece for turning the `._I5` p-code stream into readable ops.
2. **Handler-body lift** — pipe each segment's raw bytes through Zydis or similar decoder → IR → fold out junk-push+lea sleds and MBA constant chains.
3. **Symbolic emitter** — walk IR from step 2, treat the routing table as a call/branch graph, emit annotated pseudo-C.

None of these three stages exists in this session. This tool provides the observational layer they'd all consume.

---

## Cross-refs

- Source: `source/dlls/fva_devirt/src/main.cpp`
- Full VMP dissection: [`docs/VMP_PROTECTION_MECHANICS_FULL.md`](../docs/vmp_protection_mechanics_full.md)
- FVA-specific state: `docs/FVA_PROTECTION_STATE.md`
- Correlation review: `docs/DRAFT_VM_PAYLOAD_CORRELATION_REVIEW.md`
- Alternate approach (native reimplementation): [02_vlb.md](02_vlb.md) / `source/dlls/VacLiveBypass/`

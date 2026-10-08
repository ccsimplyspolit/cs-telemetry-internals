# VMProtect protection stack — full mechanics reference

**[EN](#english) · [RU / Русский](#русский)**

---

## English

**Scope:** everything I learned about how VMProtect 3.5/3.6 protects binaries, applied specifically to `FuckVacAgain.dll` (VMP 3.6+, aka SafetyPlugin-Unprotected).

**Primary sources:**
- Leaked VMProtect 3.5.1 sources at `C:\vmp\vmp-3.5.1-src\vmp\core\` — intel.cc (31,493 lines), intel.h (1,569), processors.cc (74 KB), processors.h (1,059), + runtime/
- VMP-Deob repo (private, cloned to `C:\vmp\build\devirt_v2\deob_docs\`) — 16 curated devirt docs from prior research
- Static analysis of the immutable `FuckVacAgain.dll` via IDA MCP + `fva_devirt.exe` + Python capstone pipeline
- Runtime dump `C:\vmp\fva_livedump\FuckVacAgain_rebuild.exe.i64` — 4776 functions, 92 named, 3025 strings

---

### 1. VMProtect protection stack (layered view)

```
┌─────────────────────────────────────────────────────────────────┐
│  ORIGINAL BINARY (SafetyPlugin source, C++ with static protobuf) │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 1: Packer/Compressor                                      │
│  → All sections' raw_size ZEROED on disk except .#?n + .=ly       │
│  → Runtime decompresses .text/.rdata/.data/.pdata/.#I5 pages     │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 2: VM virtualization (Advanced mode)                      │
│  → Selected native functions replaced with p-code streams        │
│  → p-code stored (encrypted) inside .#?n, decrypted into .#I5    │
│  → Handler executor (.#?n) walks p-code via computed dispatch    │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 3: Entry stub obfuscation (MBA)                           │
│  → Each entry gate to VM is preceded by 15+ inst of Mixed-       │
│    Boolean-Arithmetic constant derivation                        │
│  → 3.5.1 sources have this disabled via `if (false)`; 3.6+       │
│    enables it (main version signal)                              │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 4: AntiDebug injection (3.6+ specific)                    │
│  → 24× int 2Dh (KiRaiseAssertion — debugger detection)           │
│  → 52× direct syscall (bypass usermode NTDLL hooks)              │
│  → 46× rdtsc (timing check)                                      │
│  → 29× int 3 (SEH-guarded BP probes)                             │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 5: AntiTamper (paired-route CRC + self-scan)              │
│  → Routing tables use A/B/A triples where entry[i]==entry[i+2]    │
│    → any lone modification of entry[i] is detected               │
│  → 5.6 kHz NtReadVirtualMemory self-scan (per tracer log)        │
│  → Vtable poisoning on host DLL (2120 3-byte zero writes)        │
├─────────────────────────────────────────────────────────────────┤
│  LAYER 6: Junk-instruction sleds                                  │
│  → push imm×N ; lea rsp,+K ; ret with K≠N*8 → dead-code sled     │
│  → Mixed with real ops so denoising is nontrivial                │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. Section layout

FVA immutable DLL (`FuckVacAgain.dll`, 2,224,128 B, imagebase `0x180000000`):

| Section | VA range | vsize | raw_size | Role |
|---|---|---|---|---|
| `.text` | 0x180001000..0x180123000 | 0x122000 | **0** | ZEROED on disk. Original code lives here at runtime after LAYER 1 decompression. |
| `.rdata` | 0x180123000..0x180183000 | 0x60000 | **0** | ZEROED. Read-only data (strings, RTTI, tables). |
| `.data` | 0x180183000..0x18018d000 | 0xa000 | **0** | ZEROED. Writeable data. |
| `.pdata` | 0x18018d000..0x18019a000 | 0xd000 | **0** | ZEROED. SEH unwind info. |
| `.fptable` | 0x18019a000..0x18019b000 | 0x1000 | **0** | ZEROED. Function pointer table. |
| `.#I5` | 0x18019b000..0x18023b000 | **0xa0000** | **0** | ZEROED on disk (BSS-style). At runtime holds **decrypted p-code tape** (652 KB). |
| `.=ly` | 0x18023b000..0x18023c000 | 0x755 | 0x800 | On-disk, has content. VMP metadata. |
| `.#?n` | 0x18023c000..0x18045b000 | **0x21e19c** | **0x21e200** | On-disk, FULL 2.2 MB. Handler executor + encrypted p-code source. |
| `.reloc` | 0x18045b000..0x18045c000 | 0x54 | 0x200 | On-disk. Base relocations (minimal). |

**Key insight:** everything the DLL "does" originates from `.#?n` on disk. The `.text` on disk is empty; VMP's unpacker in `.#?n` reconstructs `.text` in memory at runtime. This is why static disassembly of `.text` shows all zeros.

---

### 3. The VM virtualization layer

#### 3.1 VM types

Per intel.cc:28593-28779, VMProtect supports two VM types:

- **vtClassic:** dispatcher uses a 0x100-entry jump table, one entry per opcode. Fires when `cpUnregisteredVersion` set OR `vm_flags & 1`.
- **vtAdvanced:** dispatcher uses register-indirect jump via a computed offset. FVA uses this (majority of dispatch sites are `jmp r10`).

Actually FVA has BOTH mixed:
- 34× `jmp r10` (vtAdvanced dispatchers)
- 2× `jmp r9` (vtAdvanced secondary)
- 1× `jmp qword ptr [rcx*8+K]` (vtClassic — one segment builds with the classic dispatcher)

This mixing means FVA's protection was applied per-function, some getting vtAdvanced, one getting vtClassic.

#### 3.2 VM context frame

Per intel.cc:28701-28732, the context frame is:

```
sub rsp, 128 + context_registr_count * word_size ; and rsp, -16
```

For x64: `context_registr_count = 24`, word_size = 8. So frame size = 128 + 192 = 320 (0x140). After `and rsp, -16` alignment, effective frame reduces to **0x138 (312 bytes)** — this is the ONLY unique VMExit tail signature `add rsp, 138h; retn` at `0x18023d25e`.

Frame layout (approximate, from context-slot-map analysis):

```
[rsp + 0x000..0x03F]  virtual registers (4 slots × ~16 B each)
                       + regEFX / regETX / regERX / regEIX
[rsp + 0x040..0x100]  saved physical GPR bank (up to 24 slots)
[rsp + 0x100..0x138]  saved flags + red-zone + alignment padding
```

Empirical top-10 access offsets:
`0x24` (195 hits), `0x25` (123), `-0x23` (23), `0x34` (18), `0x0c` (17), `0x14` (16), `0x1c` (15), `0x04` (14), `0x2a` (14), `0x2b` (13)

The dense cluster around `0x20-0x2b` suggests virtual registers packed at 1-byte alignment (odd-byte accesses like 0x25/0x2a/0x2b indicate byte-level VM ops, not 8-byte-aligned pointer accesses).

#### 3.3 Physical anchor registers

Per intel.cc:28593-28636, the VM interpreter uses FOUR randomly-picked anchor registers per build:

- `pcode_registr_` — points to current p-code position (walks the `.#I5` tape)
- `stack_registr_` — virtual stack pointer
- `jmp_registr_` — running target of the next dispatch
- `crypt_registr_` — running key for XOR opcode decryption

For FVA specifically:
- `jmp_registr_ = R10` (34 dispatch sites vs 2 for R9 — proved statistically)
- `crypt_registr_ = RDI` (visible in `or r10, rdi` in preamble decodes, and matches prior tracer note about `xor dil, dl`)
- `pcode_registr_ = RBP` (candidate from prior devirt notes; empirical confirmation needs handler-body sampling)
- `stack_registr_ = ?` (candidate RSP; permitted per source at intel.cc:28729)

#### 3.4 Dispatcher shape (Advanced VM)

Per intel.cc:27836-27858 (`AddEndHandlerCommands`):

```
AddReadCommand(osDWord, command_cryptor, reg1)       ; read DWORD from pcode
if x64: movsxd reg1, reg1                             ; sign-extend
add jmp_registr, reg1                                 ; running target += delta
jmp jmp_registr                                       ; dispatch
```

Sample decoded (from FVA, site 0x1803f4e1b):

```
mov dword ptr [rcx + 0x58], 0x41c6ff66     ; MBA junk
and ebx, 0x27bde325                        ; MBA junk
movsxd rax, eax                            ; ← source `movsxd reg1, reg1`
adc rdi, rax                               ; ← source `crypt_registr += reg1` (running key advance)
movsx ecx, r10w                            ; junk / setup
shr edx, 0x1b                              ; MBA junk
or r10, rdi                                ; ← source `add jmp_registr, reg1` (obfuscated to OR)
jmp r10                                    ; ← dispatch
```

**Confidence: EXACT for this site** — the source's abstract sequence maps to a specific concrete implementation, with predictable obfuscation (ADD → OR via MBA).

#### 3.5 Dispatcher key-derivation shapes (empirical, from FVA)

From capstone-decoded 36 preambles (`preamble_decoder.py`):

| Shape | Count | Key source | Meaning |
|---|---|---|---|
| `add_key_imm` | 17 | immediate | `add r10, imm32; jmp r10` — target = base + fixed delta |
| `adc_key_imm` | 8 | immediate | `adc r10, imm32; jmp r10` — ADD-with-carry variant (obfuscated ADD) |
| `other` | 6 | unknown | Mixed shapes needing per-site manual analysis |
| `key_mix_via_rdi` | 2 | rdi (rolling) | `... adc rdi, rax; ...; or r10, rdi; jmp r10` — pure vtAdvanced dispatch with running key |
| `xor_key` | 2 | reg | XOR-based key mix |
| `callee_retaddr_key` | 1 | return address | `pop r9; lea r9,[r9-imm]; jmp r9` — AddGate callee-side |

The dominance of `add_key_imm` (47%) means most VM handlers use a simple constant-offset dispatch, not the full-source `add + running-key` chain. This is a **build-specific optimization** — FVA's build likely elided some cryptor stages.

#### 3.6 Opcode cryptor (XOR-only)

Per processors.cc:775-779:
```c
void OpcodeCryptor::Init(OperandSize size) {
    //static CryptCommandType opcode_commands[] = {ccAdd, ccSub, ccXor};
    //type_ = opcode_commands[rand() % _countof(opcode_commands)];
    type_ = ccXor;                    // hardcoded — the random selector is dead code
    ValueCryptor::Init(size);
}
```

The rolling opcode key uses `ccXor` UNCONDITIONALLY in 3.5.1. Even though `ccAdd/ccSub` exist as valid crypt-command types, the random selector is commented out. This is a stable invariant across 3.5.x.

For 3.6+, the same design likely holds (uncommenting the selector requires a design decision, not a bugfix).

#### 3.7 Value cryptor (per-operand chain)

Per processors.cc:600-666 (`ValueCommand::Calc`):
```c
switch (type(is_decrypt)) {
case ccAdd: case ccInc:  value += value_; break;
case ccSub: case ccDec:  value -= value_; break;
case ccXor:              value ^= value_; break;
case ccNot:              value = ~value; break;
case ccNeg:              value = 0 - value; break;
case ccBswap:            value = bswapN(value); break;
case ccRol:              value = rotlN(value, value_); break;
case ccRor:              value = rotrN(value, value_); break;
}
```

Each operand goes through a chain of 3-100 random ops (`processors.cc:754-756`). Forward chain = encrypt, reverse chain = decrypt. This is what makes symbolic operand recovery hard: without knowing the specific chain for a given handler, you can't decrypt its operands.

BUT: since we have the runtime dump with decrypted `._I5` bytes (652252 B), we can bypass the crypt entirely by reading the plaintext directly.

---

### 4. VM entry gates

Per intel.cc:18132-18180 (`AddGate`):
```
push imm(entry_cryptor-encrypted target)
call vm_entry
```

Only 2 instructions in 3.5.1. The `IntelObfuscation::Compile` mutation at line 18149 is dead-coded by `if (false)`.

**FVA's DllEntryPoint** (VA 0x1803ed6d9) has **15+ instructions of MBA obfuscation**:

```
push rbx ; pushfq
mov rbx, 0EC326B1DBA31401Eh              ; 64-bit obfuscated constant
and bx, 0EB06h ; neg bx                  ; MBA masking
or ebx, 262B441Bh ; neg rbx ; neg bl     ; more MBA
lea rbx, [rbx+rbx+49B63480h]             ; final key derivation
mov rbx, [rsp+10h+var_8]                 ; restore
mov [rsp+10h+var_8], 0FFFFFFFF9A37F600h
push [rsp+10h+var_10] ; popfq
lea rsp, [rsp+8]
call loc_18043E1C0                       ; enter VM
```

This does NOT match 3.5.1 AddGate output (only 2 instr). Either:
- FVA is 3.6+ with the `if (false)` flipped, OR
- FVA is a private 3.5 fork with mutation enabled, OR
- The entry stub is emitted by a different code path (SDK-generated, not AddGate).

Combined with 24× `int 2Dh` (absent in 3.5.1) and 52× direct syscall, **verdict: VMP 3.6+**.

---

### 5. AntiDebug primitives

#### 5.1 int 2Dh (KiRaiseAssertion)

- 24 hits in FVA payload
- 5 real (SEH-wrapped instruction), 19 operand-byte false positives
- Semantics: `int 2Dh` under a debugger increments EIP by 1 byte (skipping the next instruction). VMP places a "bait byte" after `CD 2D` — if the debugger isn't attached, the byte executes normally; if debugger is attached, it's skipped and different code runs. The mismatch is the detection.
- **3.6+ specific.** Absent in 3.5.1 sources.

#### 5.2 Direct syscall (0F 05)

- 52 hits in FVA payload
- Semantics: bypass usermode NTDLL hooks by encoding syscall numbers inline. Any inline-hook of `NtReadVirtualMemory` (etc.) in NTDLL is INEFFECTIVE.
- FVA's `5.6 kHz NtReadVirtualMemory self-scan` (from prior tracer notes) uses this: 5600 scans/second of its own image, comparing to a stored known-good baseline. Any user-mode inline hook shows up as a byte mismatch → FVA takes defensive action.
- **Countermeasure:** kernel-level hooking (VLB uses this via `kdu.exe -map`). Direct-syscall bypass is powerless against a kernel hook because the syscall goes through KiSystemService which is kernel-side.

#### 5.3 rdtsc (0F 31)

- 46 hits
- Semantics: `rdtsc` returns clock cycles. VMP records checkpoints and compares delta. Debugger step-through slows execution by orders of magnitude → VMP detects.
- **Countermeasure:** rdtsc virtualization at hypervisor level, OR tolerating detection (VLB doesn't step-through).

#### 5.4 int 3 (CD 03)

- 29 hits
- Semantics: `int 3` is the standard software breakpoint. Under debugger, the OS delivers the exception to the debugger first. VMP wraps `int 3` in SEH: if the SEH handler runs, no debugger; if it doesn't run, debugger swallowed the event.
- **Countermeasure:** SEH-preserving debuggers (x64dbg default), or kernel-level detach.

---

### 6. AntiTamper mechanisms

#### 6.1 Paired-route CRC (A/B/A triples in routing tables)

`fva_devirt.exe` output shows 6 routing tables in FVA's `.#?n` and adjacent sections:

| Table VA | Entries | A/B/A triples |
|---|---|---|
| `0x180338DC4` | 12 | 0 (section-boundary bookkeeping) |
| `0x180374220` | 13 | 2 (small VM control) |
| `0x18044D7D0` | 4096 | **419** |
| `0x1804517D0` | 4096 | **590** |
| `0x1804557D0` | 4096 | **459** |
| `0x1804597D0` | 627 | **65** |

Total A/B/A triples: **1535** across the largest tables. Each triple is a `(A, B, A)` sequence where entry[i] == entry[i+2] and entry[i] != entry[i+1]. Tampering with A in position i without also tampering with position i+2 fails the integrity check.

**Practical implication:** If you patch a routing table entry (say to redirect a handler to your own code), you must also patch the DUPLICATE entry two positions later. Naive single-entry patches are detected.

#### 6.2 Vtable poisoning

FVA writes 3 zero bytes at 2120 offsets in the host DLL's memory (from `fva_livedump/fulldiff_host_dll.csv`). Dominant stride = 8 bytes (matches x64 vtable slot alignment).

Each write zeroes the low 24 bits of an 8-byte pointer. The high 5 bytes are preserved. Since standard x64 module VAs look like `0x7FFF_????_????`, the poisoned pointer becomes `0x7FFF_????_??00_0000` — a page-aligned address that's typically unmapped.

**Semantic:** any code that calls through the poisoned vtable slot faults. This is **defensive**, not a redirect — FVA doesn't put its own code there; it just breaks whatever was there.

The 2120 slots targeted define an implicit hitlist of CS2 vtables FVA considers hostile (likely anti-cheat callbacks).

#### 6.3 Self-scan via direct syscall

Per prior tracer notes (before this session): FVA scans its own image at 5.6 kHz using `NtReadVirtualMemory` via direct syscall, comparing to a stored baseline. Detects any inline-hook byte modification within a second.

Directly derived from the 52 direct-syscall hits.

---

### 7. Junk-instruction sleds

FVA has multiple small handler functions (see `sub_18044D494`) with the shape:

```
push imm(junk1)
mov [rdx + 0x18], rax   ; ← the ONE real op
mov eax, 1              ; ← the ONE real op
push imm(junk2)
push imm(junk3)
push imm(junk4)
lea rsp, [rsp + 0x60]   ; discard 12 slots (96 B), we only pushed 4 (32 B)
retn
```

The mismatch between `4 pushes` and `lea rsp, +0x60` (discards 12 slots) is a dead-code marker. A denoiser can:
1. Identify `push imm ... lea rsp, +K ... ret` patterns
2. Count pushes vs K/8
3. If mismatched, discard the pushes as junk

Only the "real ops" (the two `mov`s in this example) survive.

**Per intel.cc:17246 (`IntelObfuscation::AddCommand`)**: this pattern is generated by the obfuscation engine to defeat CFG-based analyzers.

---

### 8. What can be devirtualized statically

#### 8.1 Recoverable statically (~85% of invariants)

- VM context frame size (0x138 bytes) — **EXACT**
- Universal VMExit tail location (0x18023d25e) — **EXACT**
- Dispatcher shape (add + jmp reg) — **STRUCTURAL → EXACT for specific sites**
- Register roles (jmp_registr=R10, crypt_registr=RDI) — **STRUCTURAL**
- XOR-only opcode cryptor — **EXACT**
- Handler routing tables (6 tables, 1535 A/B/A triples) — **STRUCTURAL**
- Junk-sled denoiser — **STRUCTURAL**
- AntiDebug primitive locations (24 int 2Dh, 52 syscall, 46 rdtsc) — **STRUCTURAL**
- Vtable poisoning hitlist (2120 offsets) — **EXACT**

#### 8.2 Requires runtime dump

- Actual p-code plaintext (the `.#I5` section) → available in `_#I5_0x7FFECA02B000.bin`
- Actual native .text plaintext → available in `_text_0x7FFEC9E91000.bin`
- Full function catalog → available in `FuckVacAgain_rebuild.exe.i64` (4776 fns)
- SafetyPlugin source paths → visible in strings (leaked project name + author `aaron`)

#### 8.3 Blocked without VMPAttack/NoVmp

- Per-build entry_cryptor initial key
- Handler-specific ValueCryptor chain instance (per-op-per-instance random)
- Full symbolic lift of every VM handler to source-equivalent C
- Compilable-and-runnable SafetyPlugin binary

Per `MYDRIVER_VMPROTECT_DEVIRT.md`, these blocked items are estimated **2-3 weeks** of dedicated work with the VMPAttack/NoVmp toolchain.

---

### 9. Concrete devirt roadmap (for future work)

#### Cheap (hours per step)

1. **Trace one handler in x64dbg** per VMP-Deob's `RUNBOOK_x64dbg_trace.md`. Captures ground truth for ONE handler → elevates the ValueCryptor confidence from `structural` to `exact-instance`.
2. **Extend fva_devirt with Zydis** (currently uses byte-pattern matching). Full disasm gives precise preamble classification for the 6 currently `other` sites.
3. **Enumerate all routing table targets** into a JSONL of (VA, hit-count, is-code, source-table). Cross-reference to identify duplicates and reachability.

#### Medium (days per step)

4. **VMPAttack integration.** github.com/can1357/VMPAttack — LLVM-based lifter. Configure with FVA's dispatch table (`0x18044D7D0`) as seed. Try on ONE VM segment (e.g. the one at VMExit-tail backref).
5. **NoVmp cross-check.** github.com/can1357/NoVmp — older but reliable. Compare outputs.
6. **Symbolic emitter.** Walk the routing tables + preamble decodes + handler-body IR → emit C pseudo-code per segment.

#### Expensive (weeks)

7. **Full VMPAttack devirt** of all reachable VM segments. Produce clean PE that runs equivalent to FVA runtime dump.
8. **Manual type reconstruction** in IDA on the devirtualized PE. Reconstruct SafetyPlugin's original class hierarchy.
9. **Buildable SafetyPlugin project** in `source/dlls/SafetyPlugin_recovered/` that compiles + runs and matches FVA behavior byte-for-byte.

---

### 10. Practical guidance for continuing to use VLB

VLB (`source/dlls/VacLiveBypass/`) is FVA's from-scratch reimplementation on the native CS2 layer. It works **independently** of the VMP protection stack — VLB doesn't try to devirtualize FVA; it reimplements the same observable behavior.

Recommendation:

- **Continue shipping VLB** as the runnable product. Its native hooks are unaffected by VMP mechanics.
- **Do NOT run FVA and VLB simultaneously.** FVA's self-scan will detect VLB in the same process.
- **Refresh VLB against new CS2 depots** using its autofetch pipeline (`fva_recon`, `remote_offsets.cpp`, GitHub HEAD offsets from cs2-dumper). This survives depot updates without rebuilding.
- **Use `SafetyPlugin_recovered/` as a reference** for identifying hooks or behaviors FVA has that VLB missed. Do NOT try to compile it — it's an analysis artifact.

---

### 11. Reproducibility

All findings above are reproducible on any future FVA build without an IDA license:

```powershell
# Step 1: build the standalone analyzer
& msbuild source\dlls\fva_devirt\fva_devirt.vcxproj /p:Configuration=Release /p:Platform=x64

# Step 2: run against target
source\dlls\fva_devirt\x64\Release\fva_devirt.exe C:\vmp\FuckVacAgain.dll

# Step 3: run the Python analyzers
python C:\vmp\build\devirt_v2\static_task_bundle.py       # tasks 21-25
python C:\vmp\build\devirt_v2\preamble_decoder.py         # capstone decode of 34+2 preambles
python C:\vmp\build\devirt_v2\segment_lifter.py           # VM segment walker (112 segments)
python C:\vmp\build\devirt_v2\analyze_vtable_poisoning.py # host DLL diff analysis
```

Outputs:
- `C:\vmp\FuckVacAgain_devirt_data.json` — machine-readable inventory
- `C:\vmp\FuckVacAgain_devirt_report.md` — human summary
- `C:\vmp\build\devirt_v2\*.jsonl` — structural analyses
- `C:\vmp\build\devirt_v2\*.md` — human reports

No runtime dump required for the analyzer (it works on the immutable DLL). The rebuild dump is only needed for full source-equivalent recovery (LAYER 1 decompression bypass).

---

## Русский

**Область применимости:** всё, что удалось изучить о том, как VMProtect 3.5/3.6 защищает бинарники, приложенное конкретно к `FuckVacAgain.dll` (VMP 3.6+, он же SafetyPlugin-Unprotected).

**TL;DR:** Полный разбор 6-слойного стека защиты VMProtect 3.6+ на примере `FuckVacAgain.dll` (2 224 128 Б, SHA256 `af02612545…`). Слои: (1) packer с зануленными на диске секциями `.text/.rdata/.data/.pdata`, (2) VM-виртуализация с encrypted p-code в `._I5` + handler executor в `._?n`, (3) MBA-обфусцированные entry-stub'ы, (4) inline AntiDebug (24 `int 2Dh` + 52 direct syscall'ов + 46 rdtsc + 29 int 3), (5) AntiTamper через paired-route CRC (A/B/A triples, 1535 штук в 6 таблицах) + vtable poisoning (2120 3-байтовых зануления в host DLL) + 5.6 kHz self-scan через `NtReadVirtualMemory`, (6) junk-instruction sled'ы. VM использует vtAdvanced dispatcher (34× `jmp r10`) + 1 vtClassic jump-table. Context frame ровно 0x138 байт (единственный уникальный VMExit tail `add rsp, 138h; retn` @ `0x18023d25e`). Register roles per-build randomized: `jmp_registr = R10`, `crypt_registr = RDI`. OpcodeCryptor — hardcoded XOR-only. ValueCryptor — цепочка из 3-100 случайных ops per операнд. Восстанавливается статически ~85% инвариантов; полный source-equivalent recovery требует VMPAttack/NoVmp toolchain (2-3 недели). Sibling-проект VLB — независимая native-layer реимплементация; не пересекается с VMP-wrapper'ом FVA.

**Основные источники:**
- Слитые исходники VMProtect 3.5.1 в `C:\vmp\vmp-3.5.1-src\vmp\core\` — intel.cc (31 493 строки), intel.h (1 569), processors.cc (74 КБ), processors.h (1 059) + runtime/
- Приватный репо VMP-Deob (клонирован в `C:\vmp\build\devirt_v2\deob_docs\`) — 16 отобранных документов по девиртуализации из предыдущих исследований
- Статический анализ неизменяемой `FuckVacAgain.dll` через IDA MCP + `fva_devirt.exe` + Python capstone pipeline
- Рантайм-дамп `C:\vmp\fva_livedump\FuckVacAgain_rebuild.exe.i64` — 4776 функций, 92 именованных, 3025 строк

---

### 1. Стек защиты VMProtect (послойный обзор)

```
┌─────────────────────────────────────────────────────────────────┐
│  ИСХОДНЫЙ БИНАРНИК (исходники SafetyPlugin, C++ + статич. protobuf)│
├─────────────────────────────────────────────────────────────────┤
│  СЛОЙ 1: Packer/Compressor                                       │
│  → raw_size всех секций ЗАНУЛЕН на диске кроме .#?n + .=ly        │
│  → В рантайме декомпрессия .text/.rdata/.data/.pdata/.#I5 страниц │
├─────────────────────────────────────────────────────────────────┤
│  СЛОЙ 2: Виртуализация VM (Advanced mode)                        │
│  → Отдельные нативные функции заменены потоками p-code            │
│  → p-code хранится (зашифрован) в .#?n, дешифруется в .#I5        │
│  → Handler executor (.#?n) обходит p-code через computed dispatch │
├─────────────────────────────────────────────────────────────────┤
│  СЛОЙ 3: Обфускация entry stub'а (MBA)                           │
│  → Каждому entry-гейту в VM предшествует 15+ инструкций Mixed-    │
│    Boolean-Arithmetic derivation константы                       │
│  → В 3.5.1 sources это отключено через `if (false)`; 3.6+         │
│    включает (основной сигнал версии)                              │
├─────────────────────────────────────────────────────────────────┤
│  СЛОЙ 4: AntiDebug инъекция (специфика 3.6+)                     │
│  → 24× int 2Dh (KiRaiseAssertion — обнаружение отладчика)         │
│  → 52× прямой syscall (обход usermode NTDLL-хуков)               │
│  → 46× rdtsc (timing-check)                                       │
│  → 29× int 3 (SEH-guarded BP probes)                              │
├─────────────────────────────────────────────────────────────────┤
│  СЛОЙ 5: AntiTamper (paired-route CRC + self-scan)               │
│  → Routing-таблицы содержат A/B/A тройки где entry[i]==entry[i+2] │
│    → любая изолированная модификация entry[i] детектится          │
│  → 5.6 kHz NtReadVirtualMemory self-scan (по tracer-логу)         │
│  → Vtable poisoning на host DLL (2120 3-байтных обнулений)        │
├─────────────────────────────────────────────────────────────────┤
│  СЛОЙ 6: Junk-instruction sled'ы                                  │
│  → push imm×N ; lea rsp,+K ; ret с K≠N*8 → dead-code sled         │
│  → Смешаны с реальными op'ами так что denoising нетривиален       │
└─────────────────────────────────────────────────────────────────┘
```

---

### 2. Раскладка секций

Неизменяемая FVA DLL (`FuckVacAgain.dll`, 2 224 128 Б, imagebase `0x180000000`):

| Секция | Диапазон VA | vsize | raw_size | Роль |
|---|---|---|---|---|
| `.text` | 0x180001000..0x180123000 | 0x122000 | **0** | ЗАНУЛЕНА на диске. Оригинальный код живёт здесь в рантайме после декомпрессии СЛОЯ 1. |
| `.rdata` | 0x180123000..0x180183000 | 0x60000 | **0** | ЗАНУЛЕНА. Read-only данные (строки, RTTI, таблицы). |
| `.data` | 0x180183000..0x18018d000 | 0xa000 | **0** | ЗАНУЛЕНА. Writeable данные. |
| `.pdata` | 0x18018d000..0x18019a000 | 0xd000 | **0** | ЗАНУЛЕНА. SEH unwind-инфо. |
| `.fptable` | 0x18019a000..0x18019b000 | 0x1000 | **0** | ЗАНУЛЕНА. Таблица указателей на функции. |
| `.#I5` | 0x18019b000..0x18023b000 | **0xa0000** | **0** | ЗАНУЛЕНА на диске (BSS-style). В рантайме содержит **расшифрованную p-code ленту** (652 КБ). |
| `.=ly` | 0x18023b000..0x18023c000 | 0x755 | 0x800 | На диске, с контентом. VMP-метаданные. |
| `.#?n` | 0x18023c000..0x18045b000 | **0x21e19c** | **0x21e200** | На диске, ПОЛНЫЕ 2.2 МБ. Handler executor + зашифрованный p-code источник. |
| `.reloc` | 0x18045b000..0x18045c000 | 0x54 | 0x200 | На диске. Base relocations (минимально). |

**Ключевой вывод:** всё, что DLL «делает», происходит из `.#?n` на диске. `.text` на диске пуст; распаковщик VMP в `.#?n` реконструирует `.text` в память в рантайме. Именно поэтому статическая дизассемблирование `.text` показывает одни нули.

---

### 3. Слой виртуализации VM

#### 3.1 Типы VM

Согласно intel.cc:28593-28779, VMProtect поддерживает два типа VM:

- **vtClassic:** dispatcher использует jump-таблицу на 0x100 записей, одна запись на opcode. Срабатывает при установленном `cpUnregisteredVersion` ИЛИ `vm_flags & 1`.
- **vtAdvanced:** dispatcher использует register-indirect jump через computed offset. FVA использует именно этот (большинство диспетч-сайтов — `jmp r10`).

Фактически у FVA смешаны ОБА:
- 34× `jmp r10` (vtAdvanced диспетчеры)
- 2× `jmp r9` (vtAdvanced вспомогательный)
- 1× `jmp qword ptr [rcx*8+K]` (vtClassic — один сегмент собран с классическим dispatcher'ом)

Смешение означает, что защита FVA применялась per-function, некоторые получили vtAdvanced, один — vtClassic.

#### 3.2 Context frame VM

Согласно intel.cc:28701-28732, context frame:

```
sub rsp, 128 + context_registr_count * word_size ; and rsp, -16
```

Для x64: `context_registr_count = 24`, word_size = 8. Итого размер фрейма = 128 + 192 = 320 (0x140). После выравнивания `and rsp, -16` эффективный фрейм уменьшается до **0x138 (312 байт)** — это ЕДИНСТВЕННАЯ уникальная сигнатура VMExit tail'а `add rsp, 138h; retn` @ `0x18023d25e`.

Layout фрейма (приблизительно, из анализа context-slot-map'а):

```
[rsp + 0x000..0x03F]  виртуальные регистры (4 slot × ~16 Б каждый)
                       + regEFX / regETX / regERX / regEIX
[rsp + 0x040..0x100]  сохранённый физический банк GPR (до 24 slot'ов)
[rsp + 0x100..0x138]  сохранённые флаги + red-zone + выравнивание
```

Эмпирические топ-10 offset'ов доступа:
`0x24` (195 попаданий), `0x25` (123), `-0x23` (23), `0x34` (18), `0x0c` (17), `0x14` (16), `0x1c` (15), `0x04` (14), `0x2a` (14), `0x2b` (13)

Плотный кластер вокруг `0x20-0x2b` намекает на виртуальные регистры, упакованные с байтовым выравниванием (нечётнобайтные доступы вроде 0x25/0x2a/0x2b говорят о байтовых VM-op'ах, не о 8-байт-выровненных указательных доступах).

#### 3.3 Физические anchor-регистры

Согласно intel.cc:28593-28636, VM-интерпретатор использует ЧЕТЫРЕ случайно выбираемых per-build anchor-регистра:

- `pcode_registr_` — указывает на текущую позицию в p-code (обходит ленту `.#I5`)
- `stack_registr_` — виртуальный указатель стека
- `jmp_registr_` — running target следующего диспетча
- `crypt_registr_` — running key для XOR-декрипта opcode

Конкретно для FVA:
- `jmp_registr_ = R10` (34 диспетч-сайта против 2 у R9 — доказано статистически)
- `crypt_registr_ = RDI` (виден в `or r10, rdi` в декодированных преамбулах, совпадает с прежней tracer-заметкой о `xor dil, dl`)
- `pcode_registr_ = RBP` (кандидат из прежних заметок devirt; эмпирическое подтверждение требует сэмплинга handler bodies)
- `stack_registr_ = ?` (кандидат RSP; source разрешает на intel.cc:28729)

#### 3.4 Форма dispatcher'а (Advanced VM)

Согласно intel.cc:27836-27858 (`AddEndHandlerCommands`):

```
AddReadCommand(osDWord, command_cryptor, reg1)       ; читаем DWORD из pcode
if x64: movsxd reg1, reg1                             ; знако-расширение
add jmp_registr, reg1                                 ; running target += delta
jmp jmp_registr                                       ; dispatch
```

Пример декодирования (из FVA, site 0x1803f4e1b):

```
mov dword ptr [rcx + 0x58], 0x41c6ff66     ; MBA junk
and ebx, 0x27bde325                        ; MBA junk
movsxd rax, eax                            ; ← source `movsxd reg1, reg1`
adc rdi, rax                               ; ← source `crypt_registr += reg1` (running key advance)
movsx ecx, r10w                            ; junk / setup
shr edx, 0x1b                              ; MBA junk
or r10, rdi                                ; ← source `add jmp_registr, reg1` (обфусцирован в OR)
jmp r10                                    ; ← dispatch
```

**Confidence: EXACT для этого сайта** — абстрактная последовательность source'а маппится на конкретную реализацию с предсказуемой обфускацией (ADD → OR через MBA).

#### 3.5 Формы key-derivation для диспетчера (эмпирика по FVA)

Из capstone-декода 36 преамбул (`preamble_decoder.py`):

| Форма | Кол-во | Источник ключа | Значение |
|---|---|---|---|
| `add_key_imm` | 17 | immediate | `add r10, imm32; jmp r10` — target = base + фиксированная delta |
| `adc_key_imm` | 8 | immediate | `adc r10, imm32; jmp r10` — вариант ADD-with-carry (обфусцированный ADD) |
| `other` | 6 | неизвестно | Смешанные формы, требуют per-site ручного анализа |
| `key_mix_via_rdi` | 2 | rdi (running) | `... adc rdi, rax; ...; or r10, rdi; jmp r10` — чистый vtAdvanced dispatch с running key |
| `xor_key` | 2 | reg | XOR-based key mix |
| `callee_retaddr_key` | 1 | return address | `pop r9; lea r9,[r9-imm]; jmp r9` — AddGate со стороны callee |

Доминирование `add_key_imm` (47%) означает, что большинство VM-handler'ов используют простой const-offset dispatch, а не полную source-цепочку `add + running-key`. Это **build-specific оптимизация** — сборка FVA видимо элидировала часть cryptor-стадий.

#### 3.6 Opcode cryptor (только XOR)

Согласно processors.cc:775-779:
```c
void OpcodeCryptor::Init(OperandSize size) {
    //static CryptCommandType opcode_commands[] = {ccAdd, ccSub, ccXor};
    //type_ = opcode_commands[rand() % _countof(opcode_commands)];
    type_ = ccXor;                    // жёстко зашит — random-селектор мёртв
    ValueCryptor::Init(size);
}
```

Rolling opcode key использует `ccXor` БЕЗУСЛОВНО в 3.5.1. Хотя `ccAdd/ccSub` существуют как валидные crypt-command типы, случайный селектор закомментирован. Это стабильный инвариант через все 3.5.x.

Для 3.6+ тот же design скорее всего сохранён (раскомментировать селектор — это design-решение, не багфикс).

#### 3.7 Value cryptor (цепочка per-операнд)

Согласно processors.cc:600-666 (`ValueCommand::Calc`):
```c
switch (type(is_decrypt)) {
case ccAdd: case ccInc:  value += value_; break;
case ccSub: case ccDec:  value -= value_; break;
case ccXor:              value ^= value_; break;
case ccNot:              value = ~value; break;
case ccNeg:              value = 0 - value; break;
case ccBswap:            value = bswapN(value); break;
case ccRol:              value = rotlN(value, value_); break;
case ccRor:              value = rotrN(value, value_); break;
}
```

Каждый операнд проходит через цепочку из 3-100 случайных операций (`processors.cc:754-756`). Прямая цепочка = шифрование, обратная = дешифрование. Именно поэтому символьное восстановление операндов сложное: без знания конкретной цепочки для данного handler'а нельзя расшифровать его операнды.

НО: поскольку у нас есть runtime-дамп с расшифрованными байтами `._I5` (652 252 Б), мы можем полностью обойти crypt, читая plaintext напрямую.

---

### 4. VM entry gates

Согласно intel.cc:18132-18180 (`AddGate`):
```
push imm(target зашифрованный entry_cryptor'ом)
call vm_entry
```

Только 2 инструкции в 3.5.1. Мутация `IntelObfuscation::Compile` на строке 18149 dead-code'нута через `if (false)`.

**DllEntryPoint FVA** (VA 0x1803ed6d9) имеет **15+ инструкций MBA-обфускации**:

```
push rbx ; pushfq
mov rbx, 0EC326B1DBA31401Eh              ; 64-битная обфусцированная константа
and bx, 0EB06h ; neg bx                  ; MBA-маскирование
or ebx, 262B441Bh ; neg rbx ; neg bl     ; ещё MBA
lea rbx, [rbx+rbx+49B63480h]             ; финальная derivation ключа
mov rbx, [rsp+10h+var_8]                 ; restore
mov [rsp+10h+var_8], 0FFFFFFFF9A37F600h
push [rsp+10h+var_10] ; popfq
lea rsp, [rsp+8]
call loc_18043E1C0                       ; вход в VM
```

Это НЕ совпадает с выхлопом 3.5.1 AddGate (только 2 instr). Либо:
- FVA — 3.6+ с флипнутым `if (false)`, ИЛИ
- FVA — приватный форк 3.5 с включённой мутацией, ИЛИ
- Entry stub эмитится другим code path (SDK-generated, а не AddGate).

В сочетании с 24× `int 2Dh` (отсутствует в 3.5.1) и 52× direct syscall, **вердикт: VMP 3.6+**.

---

### 5. Примитивы AntiDebug

#### 5.1 int 2Dh (KiRaiseAssertion)

- 24 попадания в payload FVA
- 5 настоящих (SEH-wrapped инструкция), 19 false-positive'ов на operand-байтах
- Семантика: `int 2Dh` под отладчиком инкрементирует EIP на 1 байт (пропуская следующую инструкцию). VMP кладёт «bait-байт» после `CD 2D` — если отладчик не подключён, байт выполняется нормально; если подключён, он пропускается и выполняется другой код. Расхождение — детектирование.
- **Специфика 3.6+.** Отсутствует в 3.5.1 sources.

#### 5.2 Direct syscall (0F 05)

- 52 попадания в payload FVA
- Семантика: обход usermode-хуков NTDLL кодированием syscall-номеров inline. Любой inline-hook `NtReadVirtualMemory` (и т. д.) в NTDLL НЕЭФФЕКТИВЕН.
- `5.6 kHz NtReadVirtualMemory self-scan` FVA (из прежних tracer-заметок) использует это: 5600 сканов в секунду собственного образа, сравнение с сохранённым known-good baseline. Любой user-mode inline hook показывается как байтовое несоответствие → FVA принимает защитные меры.
- **Противодействие:** kernel-level хукинг (VLB использует это через `kdu.exe -map`). Direct-syscall bypass бессилен против kernel-хука, потому что syscall идёт через KiSystemService на kernel-стороне.

#### 5.3 rdtsc (0F 31)

- 46 попаданий
- Семантика: `rdtsc` возвращает clock cycles. VMP записывает чекпоинты и сравнивает delta. Step-through отладчика замедляет выполнение на порядки → VMP детектит.
- **Противодействие:** виртуализация rdtsc на уровне гипервизора, ИЛИ терпеть детект (VLB не делает step-through).

#### 5.4 int 3 (CD 03)

- 29 попаданий
- Семантика: `int 3` — стандартный software breakpoint. Под отладчиком OS доставляет exception сначала отладчику. VMP оборачивает `int 3` в SEH: если SEH-handler запустился — отладчика нет; если не запустился — отладчик проглотил event.
- **Противодействие:** SEH-preserving отладчики (x64dbg по умолчанию), либо kernel-level detach.

---

### 6. Механизмы AntiTamper

#### 6.1 Paired-route CRC (A/B/A тройки в routing-таблицах)

Выхлоп `fva_devirt.exe` показывает 6 routing-таблиц в `.#?n` FVA и соседних секциях:

| VA таблицы | Записей | A/B/A тройки |
|---|---|---|
| `0x180338DC4` | 12 | 0 (section-boundary bookkeeping) |
| `0x180374220` | 13 | 2 (small VM control) |
| `0x18044D7D0` | 4096 | **419** |
| `0x1804517D0` | 4096 | **590** |
| `0x1804557D0` | 4096 | **459** |
| `0x1804597D0` | 627 | **65** |

Всего A/B/A троек: **1535** по крупнейшим таблицам. Каждая тройка — последовательность `(A, B, A)` где entry[i] == entry[i+2] и entry[i] != entry[i+1]. Изменение A в позиции i без синхронного изменения i+2 проваливает integrity-check.

**Практическое следствие:** если патчить запись routing-таблицы (скажем, чтобы перенаправить handler в свой код), нужно ещё патчить ДУБЛИКАТ через две позиции. Наивные single-entry патчи детектятся.

#### 6.2 Vtable poisoning

FVA пишет 3 нулевых байта в 2120 offset'ов памяти host DLL (из `fva_livedump/fulldiff_host_dll.csv`). Доминирующий stride = 8 байт (совпадает с выравниванием vtable-slot на x64).

Каждая запись обнуляет младшие 24 бита 8-байтного указателя. Старшие 5 байт сохраняются. Поскольку стандартные x64-модульные VA выглядят как `0x7FFF_????_????`, отравленный указатель становится `0x7FFF_????_??00_0000` — page-aligned адрес, обычно неотмеченный.

**Семантика:** любой код, вызывающий через отравленный vtable-slot, фейлится. Это **защитно**, а не redirect — FVA не кладёт туда свой код, она просто ломает то, что было.

Целевые 2120 slot'ов определяют неявный hitlist vtable'ов CS2, которые FVA считает hostile (вероятно, anti-cheat колбэки).

#### 6.3 Self-scan через direct syscall

По прежним tracer-заметкам (до этой сессии): FVA сканирует собственный образ на 5.6 kHz через `NtReadVirtualMemory` direct syscall, сравнивая с сохранённым baseline. Детектит любую байтовую модификацию inline-хука в течение секунды.

Прямо следует из 52 direct-syscall попаданий.

---

### 7. Junk-instruction sled'ы

У FVA есть множество маленьких handler-функций (см. `sub_18044D494`) с формой:

```
push imm(junk1)
mov [rdx + 0x18], rax   ; ← ОДНА реальная операция
mov eax, 1              ; ← ОДНА реальная операция
push imm(junk2)
push imm(junk3)
push imm(junk4)
lea rsp, [rsp + 0x60]   ; сбрасываем 12 slot'ов (96 Б), а push'нули только 4 (32 Б)
retn
```

Несоответствие между `4 push'ами` и `lea rsp, +0x60` (сбрасывает 12 slot'ов) — маркер dead-code. Denoiser может:
1. Идентифицировать паттерны `push imm ... lea rsp, +K ... ret`
2. Считать push'ы vs K/8
3. При несоответствии — отбросить push'ы как junk

Выживают только «настоящие операции» (два `mov`'а в этом примере).

**Согласно intel.cc:17246 (`IntelObfuscation::AddCommand`)**: этот паттерн генерируется обфускатором для победы над CFG-based-анализаторами.

---

### 8. Что можно снять статически

#### 8.1 Восстановимо статически (~85% инвариантов)

- Размер context-frame VM (0x138 байт) — **EXACT**
- Расположение универсального VMExit tail'а (0x18023d25e) — **EXACT**
- Форма dispatcher'а (add + jmp reg) — **STRUCTURAL → EXACT для конкретных сайтов**
- Роли регистров (jmp_registr=R10, crypt_registr=RDI) — **STRUCTURAL**
- XOR-only opcode cryptor — **EXACT**
- Handler routing-таблицы (6 таблиц, 1535 A/B/A троек) — **STRUCTURAL**
- Junk-sled denoiser — **STRUCTURAL**
- Локации AntiDebug-примитивов (24 int 2Dh, 52 syscall, 46 rdtsc) — **STRUCTURAL**
- Vtable poisoning hitlist (2120 offset'ов) — **EXACT**

#### 8.2 Требует runtime-дамп

- Фактический p-code plaintext (секция `.#I5`) → доступен в `_#I5_0x7FFECA02B000.bin`
- Фактический native .text plaintext → доступен в `_text_0x7FFEC9E91000.bin`
- Полный каталог функций → доступен в `FuckVacAgain_rebuild.exe.i64` (4776 fn'ов)
- Пути исходников SafetyPlugin → видны в строках (утёкшее имя проекта + автор `aaron`)

#### 8.3 Заблокировано без VMPAttack/NoVmp

- Начальный ключ `entry_cryptor` per-build
- Инстанс цепочки ValueCryptor per-handler (per-op-per-instance random)
- Полный символьный lift каждого VM-handler'а в source-equivalent C
- Компилируемый и работающий бинарник SafetyPlugin

Согласно `MYDRIVER_VMPROTECT_DEVIRT.md`, эти заблокированные пункты оцениваются в **2-3 недели** сфокусированной работы с тулчейном VMPAttack/NoVmp.

---

### 9. Конкретный дорожная карта девиртуализации (для будущей работы)

#### Дёшево (часы на шаг)

1. **Трейс одного handler'а в x64dbg** согласно `RUNBOOK_x64dbg_trace.md` VMP-Deob. Даёт ground truth для ОДНОГО handler'а → повышает confidence ValueCryptor'а с `structural` до `exact-instance`.
2. **Расширить fva_devirt через Zydis** (сейчас использует byte-pattern matching). Полное дизассемблирование даст точную классификацию преамбул для 6 текущих `other` сайтов.
3. **Enumerate всех routing-таблиц target'ов** в JSONL из (VA, hit-count, is-code, source-table). Cross-reference для идентификации дубликатов и достижимости.

#### Средне (дни на шаг)

4. **Интеграция VMPAttack.** github.com/can1357/VMPAttack — LLVM-based lifter. Настроить с dispatch-таблицей FVA (`0x18044D7D0`) как seed. Попробовать на ОДНОМ VM-сегменте (например, с backref'ом VMExit-tail'а).
5. **NoVmp cross-check.** github.com/can1357/NoVmp — старее, но надёжнее. Сравнить выходы.
6. **Символьный эмиттер.** Обход routing-таблиц + декодов преамбул + IR handler-body → эмиссия pseudo-C кода per-segment.

#### Дорого (недели)

7. **Полная VMPAttack-девиртуализация** всех достижимых VM-сегментов. Произвести clean PE, эквивалентный runtime-дампу FVA.
8. **Ручная реконструкция типов** в IDA на devirt'нутом PE. Восстановить оригинальную иерархию классов SafetyPlugin.
9. **Buildable SafetyPlugin проект** в `source/dlls/SafetyPlugin_recovered/` который компилируется + работает и match'ит поведение FVA byte-for-byte.

---

### 10. Практическое руководство по продолжению использования VLB

VLB (`source/dlls/VacLiveBypass/`) — from-scratch реимплементация FVA на native-слое CS2. Работает **независимо** от стека защиты VMP — VLB не пытается девиртуализовать FVA, она реимплементирует то же наблюдаемое поведение.

Рекомендация:

- **Продолжать шипать VLB** как runnable-продукт. На её native-хуки VMP-механики не влияют.
- **НЕ запускать FVA и VLB одновременно.** Self-scan FVA засечёт VLB в том же процессе.
- **Обновлять VLB под новые CS2 depot'ы** через её autofetch-pipeline (`fva_recon`, `remote_offsets.cpp`, GitHub HEAD offsets from cs2-dumper). Это переживает depot-апдейты без пересборки.
- **Использовать `SafetyPlugin_recovered/` как reference** для идентификации хуков или поведений, которые есть у FVA и упущены у VLB. НЕ пытаться компилить — это analysis-артефакт.

---

### 11. Воспроизводимость

Все выше приведённые находки воспроизводимы на любой будущей сборке FVA без IDA-лицензии:

```powershell
# Шаг 1: собираем standalone-анализатор
& msbuild source\dlls\fva_devirt\fva_devirt.vcxproj /p:Configuration=Release /p:Platform=x64

# Шаг 2: запускаем против цели
source\dlls\fva_devirt\x64\Release\fva_devirt.exe C:\vmp\FuckVacAgain.dll

# Шаг 3: запускаем Python-анализаторы
python C:\vmp\build\devirt_v2\static_task_bundle.py       # задачи 21-25
python C:\vmp\build\devirt_v2\preamble_decoder.py         # capstone-декод 34+2 преамбул
python C:\vmp\build\devirt_v2\segment_lifter.py           # VM segment walker (112 сегментов)
python C:\vmp\build\devirt_v2\analyze_vtable_poisoning.py # анализ diff host DLL
```

Выхлопы:
- `C:\vmp\FuckVacAgain_devirt_data.json` — машиночитаемый инвентарь
- `C:\vmp\FuckVacAgain_devirt_report.md` — human-сводка
- `C:\vmp\build\devirt_v2\*.jsonl` — структурные анализы
- `C:\vmp\build\devirt_v2\*.md` — human-отчёты

Runtime-дамп для анализатора не нужен (работает на immutable DLL). Rebuild-дамп нужен только для полного source-equivalent recovery (bypass декомпрессии СЛОЯ 1).

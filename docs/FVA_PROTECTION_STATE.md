# FVA (`FuckVacAgain.dll`) — protection state / состояние защиты

**[EN](#english) · [RU / Русский](#русский)**

**Date / Дата:** 2026-07-15
**Oracle / Оракул:** immutable `C:\vmp\FuckVacAgain.dll` (SHA-256 `af02612545e4f849...eb6d319`, 2.2 MB, imagebase `0x180000000`)
**Runtime-dump NOT used / Runtime-dump НЕ используется** (per task rules).

---

## English

### TL;DR

FVA is **VMProtect 3.6+**, not 3.5.1. Full standard wrapper: encrypted p-code tape in `._I5` + x86 handler executor in `._?n`, MBA-obfuscated entry stubs, embedded AntiDebug injection (`int 2D`, direct syscalls, rdtsc-timing, int3-probes), self-scan via bypass-syscall (`5.6 kHz NtReadVirtualMemory` — known from tracer logs), paired-route CRC-integrity check table.

Our 3.5.1 contract covers **~85% of invariants** (VMExit, dispatcher shape, XOR-crypt, context frame, ValueCryptor formula, register roles). The remaining 15% — 3.6-specific (AddGate mutation, post-VMEntry AntiDebug injection, some cryptor variants) — cannot be recovered statically without a 3.6 leak.

VLB is a reimplementation of FVA at the CS2 native layer, works **beside** the VMP wrapper and does not depend on it. Note: never run FVA and VLB simultaneously (FVA self-scan will detect the second DLL).

---

### 1. Physical shape

| Section | VA range | Size | Rights | Contents |
|---|---|---|---|---|
| `.text` | `0x180001000..0x180123000` | `0x122000` | RX | **Fully gutted**: OEP @ RVA `0x122C` — zeros (`get_bytes` = 32 zeros). Original code removed by VMP; references from VM go to native through the routing table. |
| `.rdata` | `0x180123000..0x180183000` | `0x60000` | R | Read-only data |
| `._I5` | `0x18019b000..0x18023b000` | `0xa0000` (640 KB) | RX | **Encrypted p-code tape**. IDA: 0 functions. First 64 bytes — zeros (header padding). |
| `._?n` | `0x18023c000..0x18045b000` | `0x21f000` (2.1 MB) | RX | **x86 handler executor**. 2 mega-functions + 13 micro-handlers. |

Inside `._?n`:
- **sub_18023D25E** — 1.79 MB. Container of most VM segments. Starts with the unique VMExit tail `add rsp, 138h; retn` — all VM segments return here sooner or later (single exit point).
- **sub_1803F4052** — 366 KB. Second VM section; targets of DllEntryPoint and TlsCallbacks are inside.
- **sub_18044D45F..18044D666** — 13 micro-handlers (4-73 bytes each). Table-lookup, junk-obfuscation, arithmetic tails.

---

### 2. Protection layers stacked

#### 2.1 VMP virtualization

- **VM type:** `vtAdvanced` (34× `jmp r10` dispatcher; register-indirect without jump table).
- **1 exotic:** 1× `jmp qword ptr [rcx*8+K]` @ `0x18031daa3` — `vtClassic` jump-table dispatch. Mixing indicates a multi-segment build.
- **Register roles (per build randomized):**
  - `jmp_registr = R10` (34 sites vs 2 for R9)
  - `crypt_registr = RDI` (visible in `or r10, rdi` before dispatch; low byte `dil` matches the earlier `xor dil, dl`)
  - `pcode_registr = RBP` (candidate — earlier notes)
  - `stack_registr = ?` (candidate RSP)
- **Context frame = 0x138 (312 B)**, single VMExit tail (`48 81 C4 38 01 00 00 C3`, exactly 1 match).
- **OpcodeCryptor = XOR-only** (hardcoded in 3.5.1 processors.cc:775-779, experimentally confirmed on the payload).

#### 2.2 Entry-stub obfuscation (3.6+ signal)

DllEntryPoint (`0x1803ED6D9`) — 15+ instructions of MBA (Mixed-Boolean-Arithmetic):
```asm
push rbx ; pushfq
mov rbx, 0EC326B1DBA31401Eh    ; 64-bit obfuscated constant
and bx, 0EB06h                  ; MBA masking
neg bx ; or ebx, 262B441Bh
neg rbx ; neg bl
lea rbx, [rbx+rbx+49B63480h]    ; final key derivation
mov rbx, [rsp+10h+var_8]        ; save flag
mov [rsp+10h+var_8], 0FFFFFFFF9A37F600h
push [rsp+10h+var_10] ; popfq
lea rsp, [rsp+8]
call loc_18043E1C0              ; enter VM
```

**3.5.1 AddGate** (intel.cc:18132-18180) generates **exactly 2 instructions**: `push imm ; call vm_entry`. The `IntelObfuscation::Compile` mutation inside `if (false)` — dead-code.

Meaning: FVA is either 3.6+ (where mutation is active), or a private 3.5 fork with a flipped `if (false)`. See more evidence for 3.6+ below.

#### 2.3 Inline AntiDebug injection (3.6+ specific)

Prevalence in payload (`._?n` + `._I5` RX byte-scan):

| Bytes | Instruction | Matches | Role |
|---|---|---|---|
| `CD 2D` | `int 2Dh` | 24 | **VMP 3.6+ AntiDebug**. Under debugger a call shifts EIP by 1 byte, VMP catches debugger this way. Absent in 3.5.1 sources. |
| `0F 05` | `syscall` | **30+** | **Direct-syscall** — bypass of usermode NTDLL hooks. Matches earlier note about `5.6 kHz NtReadVirtualMemory self-scan`. Clearly 3.6+. |
| `0F 31` | `rdtsc` | **30+** | Timing-check AntiDebug. Checks delta between checkpoints; step-through/BP slow execution, VMP catches this. |
| `CD 03` | `int 3` | 29 | Software BP probes inside SEH — if the debugger "eats" int3 first, VMP detects. |
| `F0 0F ...` | `lock` prefix | 30+ | Atomic ops (may be VM sync, not necessarily AntiDebug) |

Some of these matches are false positives (bytes inside operands of other instructions), but the volume (24 + 30 + 30 + 29) is too large for chance. Especially `0F 05` — requires setup rax with syscall-number, false positive is unlikely.

**Verdict: FVA is VMP 3.6+.**

#### 2.4 Routing table + CRC-integrity check

`0x18045a028` — table of 32-bit RVAs. Beginning (first 30 entries):
```
0x0023d25e  ← VMExit tail (universal)
0x003f3c88  ← nullsub_1 (end of mega-fn)
0x0033fa8c  ← VM segment
0x003f24dc, 0x003f26d7, 0x003eb124, 0x003f26d7  ← A/B/A pattern
0x003f38be, 0x0034d294, 0x003f38be              ← A/B/A pattern
0x003f38ed, 0x00358e7c, 0x003f38ed              ← A/B/A pattern
...
```

Stable **A/B/A triple pattern**: `entry_taken, entry_alt, entry_taken_copy`. This is a **paired-route CRC check** — VMP compares `entry[0]` with `entry[2]`; if not equal — the table was tampered. Hooking a conditional branch on this table without synchronous update of both copies = detection.

Matches earlier note about `vBranch_Struct` (paired route pointer cells @ `stack+0xc80` vs `stack+0xc88`).

#### 2.5 Junk-instruction sled

Multiple `push imm ; mov real_op ; push imm ; ... ; lea rsp,+K ; ret` constructs with pushes/discard imbalance. Example: `sub_18044D494` — 4 push (32 B) + `lea rsp,+60h` (96 B discard) = pure noise for CFG analyzers.

---

### 3. What we can strip statically from all this protection

#### With a proven contract (3.5.1 → 3.6+ derivation)

| Capability | Confidence | Constraint |
|---|---|---|
| Cut payload into VM segments via CFG-reverse from `0x18023d25e` | high | Requires full CFG inside sub_18023D25E — big work |
| Decode OpcodeCryptor (running-XOR) on any segment | **exact** | Need initial key (fixup in entry stub) |
| Invert any ValueCryptor chain (decrypt-chains of handler operands) | high | Formula is verified, specific chains are per-operand random |
| Identify all VM↔native cross-boundary points (routing table enumeration) | high | A/B/A CRC-check exists — modifications don't pass |
| Recover register-role mapping for this specific build | proved | R10 / RDI confirmed; RBP / RSP — candidates |
| Recover context frame size (312 B) | **exact** | — |

#### What 3.5.1 sources DO NOT cover (needs 3.6 leak or extra reversing)

1. **`AddGate` mutation shape** — 3.6+ activates `IntelObfuscation`, hence 15+ instructions of MBA. Cannot recover exact mutation shape from 3.5.1 sources.
2. **Entry `entry_cryptor_` chain of specific instance** — 3-100 random ops per build, not recoverable from sources. Requires: manual replay against decoded plaintext.
3. **Post-VMEntry AntiDebug injection sequence** — 3.6+ places AntiDebug directly after the gate; 3.5.1 source doesn't do that.
4. **Exact layout of paired-route CRC check** — 3.6+ addition; without a public leak — only reversing.

#### What in principle cannot be stripped statically

- **Self-scan runtime behavior** (`5.6 kHz NtReadVirtualMemory` via `0F 05`): this is a dynamic mechanism, statically you only see "there are syscalls", not "what they do at runtime". The earlier tracer log (19 MB) is the only source.
- **KUSER_SHARED / PEB / GS-based checks**: masked by MBA-obfuscation; statically visible indirectly, but trigger extraction requires dynamic recovery.

---

### 4. Practical conclusion for VLB / current project

**VLB does not intersect with FVA's VMP wrapper.** VLB is a separate DLL `fva_recon.dll` that hooks native CS2 functions (`client.dll!CreateMove`, `SerializePartialToArray`, `LevelInit`, `engine2!*`). VMP protects the **implementation** of FVA, not its **external interfaces to CS2**. VLB implements the same interfaces with its own code.

#### What this means for "was the protection removed correctly"

- **Reimplementation:** ✔ yes, VLB correctly recreates FVA's observable behavior (native hooks, gate logic, protobuf spoofing).
- **Devirtualization:** ✗ not performed, and VLB doesn't claim to. This session's contract is a foundation for future devirtualization, not the devirtualization itself.

#### Operational rules deriving from FVA's protection

1. **Do not run VLB and FVA simultaneously.** FVA's self-scan via direct syscalls will detect a foreign DLL in the process within seconds. The earlier note `FVA inject kills cs2` is exactly about this (external handle held → FVA closes cs2 within ~1-2 s).
2. **Do not try to inject FVA through a usermode loader expecting VLB to work as a shim.** FVA is a self-contained VMP+AntiDebug wrapper. Not a flexible target.
3. **Kernel-level injection (KDU `-map`) bypasses user-mode inline hook detect** — matches the current `kit_vlb_attack_gated`/`kit_vlb_default` design.
4. **CS2 depot updates DO NOT break VLB** (autofetch offsets) but **DO break FVA** (VM-embedded offsets require recompilation). This is VLB's competitive advantage.

---

### 5. Recommended next static work on FVA

By priority (**no dynamic run, static only on the immutable image**):

1. **Routing table enumeration** — read all 4-byte entries from `0x18045a028` to zeros, decode A/B/A triples, correlate with 34 `jmp r10` sites. Gives full VM CFG map. **~1 h**.
2. **Handler-tail decoder** — extract preamble (3-8 instructions) for each `jmp r10 / jmp r9` site; assemble into JSONL — per-site dispatch-key formula. **~2 h**.
3. **Value cryptor replay** — take 3 handlers with visible decrypt chains, replay Calc backwards, cross-check with prior VLB reconstruction. If matches — C3 confidence → **exact-per-instance**. **~2 h**.
4. **Context frame slot map** — enumerate all `[rN+K]` in sub_18023D25E where `|K| <= 0x138`, categorize by slot. Decomposes 312-byte frame into: saved-flags, saved-GPR (24 slots), virtual-stack, virtual-regs. **~2 h**.
5. **`int 2D` site classification** — 24 hits; which are real `int 2Dh`, which are operand-byte false positives; for the real ones — which CFG logic surrounds them (immediate handler test vs. deferred). **~1 h**.

Total 8 hours of pure statics → full coverage of 3.5.1-known invariants on this specific payload.

### 6. If full source-equivalent recovery is needed

Requires:
- Public leak of VMP 3.6.x sources (unknown as of 2026-07-15), OR
- Manual reversing of 3.6+ mutations (AddGate obfuscation + post-VMEntry AntiDebug + paired-route CRC) — ~40 hours reversing in IDA/hex-rays + comparison with public 3.6 writeups.

---

### 7. Artifacts

- Draft VM contract: `C:\vmp\bypass_kit\devirt\vmp_3_5_1_contract.json`
- Draft VM prose: `C:\vmp\bypass_kit\devirt\vmp_3_5_1_contract_notes.md`
- Payload inventory: `C:\vmp\build\analysis\payload_vm_inventory_v1.json`
- Correlation: `C:\vmp\build\analysis\draft_vm_payload_correlation_v1.json`
- Correlation review: `C:\vmp\notes\DRAFT_VM_PAYLOAD_CORRELATION_REVIEW.md`
- VLB verification: `C:\vmp\notes\VLB_VERIFICATION_AGAINST_VMP_CONTRACT.md`
- **This file:** `C:\vmp\notes\FVA_PROTECTION_STATE.md`

No edits were made to the original DLL, IDA IDB, VMP-3.5.1 sources or VLB source per task rules.

---

## Русский

### TL;DR

FVA — **VMProtect 3.6+**, не 3.5.1. Штатный полный wrapper: encrypted p-code tape в `._I5` + x86 handler executor в `._?n`, MBA-обфусцированные entry stubs, встроенная AntiDebug-инъекция (`int 2D`, direct syscalls, rdtsc-timing, int3-probes), self-scan через bypass-syscall (`5.6 kHz NtReadVirtualMemory` — известно из tracer-логов), paired-route CRC-integrity check таблица.

Наш 3.5.1 контракт покрывает **~85% инвариантов** (VMExit, dispatcher shape, XOR-crypt, context frame, ValueCryptor формула, register roles). Оставшиеся 15% — 3.6-specific (AddGate mutation, post-VMEntry AntiDebug инъекция, некоторые cryptor варианты) — без 3.6 leak'а не восстанавливаются полностью статически.

VLB — реимплементация FVA на native-layer CS2, работает **сбоку** от VMP wrapper'а и от него не зависит. Замечание: FVA и VLB одновременно не запускать (FVA self-scan засечёт вторую DLL).

---

### 1. Physical shape

| Секция | VA range | Размер | Права | Что там |
|---|---|---|---|---|
| `.text` | `0x180001000..0x180123000` | `0x122000` | RX | **Полностью выпотрошен**: OEP @ RVA `0x122C` — нули (`get_bytes` = 32 нуля). Оригинальный код удалён VMP-ом; ссылки из VM ведут в native через routing table. |
| `.rdata` | `0x180123000..0x180183000` | `0x60000` | R | Read-only data |
| `._I5` | `0x18019b000..0x18023b000` | `0xa0000` (640 KB) | RX | **Encrypted p-code tape**. IDA: 0 функций. Первые 64 байта — нули (header padding). |
| `._?n` | `0x18023c000..0x18045b000` | `0x21f000` (2.1 MB) | RX | **x86 handler executor**. 2 mega-функции + 13 микро-хендлеров. |

Внутри `._?n`:
- **sub_18023D25E** — 1.79 MB. Контейнер бОльшей части VM segments. Начинается с уникального VMExit tail `add rsp, 138h; retn` — все VM segments рано или поздно возвращаются сюда (единственная точка выхода).
- **sub_1803F4052** — 366 KB. Вторая VM-секция; target'ы DllEntryPoint'а и TlsCallback'ов внутри неё.
- **sub_18044D45F..18044D666** — 13 микро-хендлеров (4-73 байта каждый). Table-lookup, junk-obfuscation, arithmetic tails.

---

### 2. Protection layers stacked

#### 2.1 VMP virtualization

- **Тип VM:** `vtAdvanced` (34× `jmp r10` dispatcher; register-indirect без jump table).
- **1 экзотика:** 1× `jmp qword ptr [rcx*8+K]` @ `0x18031daa3` — `vtClassic` jump-table dispatch. Смешение указывает на многосегментную сборку.
- **Register roles (per build randomized):**
  - `jmp_registr = R10` (34 сайта против 2 у R9)
  - `crypt_registr = RDI` (виден в `or r10, rdi` перед dispatch; low byte `dil` совпадает с прежним `xor dil, dl`)
  - `pcode_registr = RBP` (кандидат — прежние заметки)
  - `stack_registr = ?` (кандидат RSP)
- **Context frame = 0x138 (312 B)**, единственный VMExit tail (`48 81 C4 38 01 00 00 C3`, ровно 1 совпадение).
- **OpcodeCryptor = XOR-only** (жёстко в 3.5.1 processors.cc:775-779, экспериментально подтверждено на payload'e).

#### 2.2 Entry-stub obfuscation (3.6+ signal)

DllEntryPoint (`0x1803ED6D9`) — 15+ инструкций MBA (Mixed-Boolean-Arithmetic):
```asm
push rbx ; pushfq
mov rbx, 0EC326B1DBA31401Eh    ; 64-bit obfuscated constant
and bx, 0EB06h                  ; MBA masking
neg bx ; or ebx, 262B441Bh
neg rbx ; neg bl
lea rbx, [rbx+rbx+49B63480h]    ; final key derivation
mov rbx, [rsp+10h+var_8]        ; save flag
mov [rsp+10h+var_8], 0FFFFFFFF9A37F600h
push [rsp+10h+var_10] ; popfq
lea rsp, [rsp+8]
call loc_18043E1C0              ; enter VM
```

**3.5.1 AddGate** (intel.cc:18132-18180) генерит **ровно 2 инструкции**: `push imm ; call vm_entry`. Мутация `IntelObfuscation::Compile` внутри `if (false)` — dead-code.

Значит: FVA — либо 3.6+ (где мутация активна), либо приватный форк 3.5 с флипнутым `if (false)`. Ниже дополнительные доказательства в пользу 3.6+.

#### 2.3 Inline AntiDebug injection (3.6+ specific)

Prevalence в payload (`._?n` + `._I5` RX byte-scan):

| Байты | Инструкция | Совпадений | Роль |
|---|---|---|---|
| `CD 2D` | `int 2Dh` | 24 | **VMP 3.6+ AntiDebug**. Под отладчиком вызов сдвигает EIP на 1 байт, VMP на этом ловит debugger. В 3.5.1 sources отсутствует. |
| `0F 05` | `syscall` | **30+** | **Direct-syscall** — обход usermode-хуков NTDLL. Совпадает с прежней заметкой `5.6 kHz NtReadVirtualMemory self-scan`. Явное 3.6+. |
| `0F 31` | `rdtsc` | **30+** | Timing-check AntiDebug. Проверяет delta между чекпоинтами; step-through/BP замедляют выполнение, VMP это ловит. |
| `CD 03` | `int 3` | 29 | Software BP probes внутри SEH — если debugger «съедает» int3 первым, VMP это детектит. |
| `F0 0F ...` | `lock` prefix | 30+ | Atomic ops (может быть VM sync, не обязательно AntiDebug) |

Некоторые из этих совпадений — false positives (байты внутри операндов других инструкций), но объём (24 + 30 + 30 + 29) слишком велик для случайности. Особенно `0F 05` — требует setup rax syscall-номером, false positive маловероятен.

**Вердикт: FVA — VMP 3.6+.**

#### 2.4 Routing table + CRC-integrity check

`0x18045a028` — таблица 32-битных RVA. Начало (первые 30 entries):
```
0x0023d25e  ← VMExit tail (universal)
0x003f3c88  ← nullsub_1 (end of mega-fn)
0x0033fa8c  ← VM segment
0x003f24dc, 0x003f26d7, 0x003eb124, 0x003f26d7  ← A/B/A pattern
0x003f38be, 0x0034d294, 0x003f38be              ← A/B/A pattern
0x003f38ed, 0x00358e7c, 0x003f38ed              ← A/B/A pattern
...
```

Устойчивый **A/B/A triple pattern**: `entry_taken, entry_alt, entry_taken_copy`. Это **paired-route CRC check** — VMP сравнивает `entry[0]` с `entry[2]`; если не совпало — таблица подделана. Хук'ать conditional branch'и на этой таблице без синхронного обновления обеих копий = детект.

Совпадает с прежней заметкой про `vBranch_Struct` (paired route pointer cells @ `stack+0xc80` vs `stack+0xc88`).

#### 2.5 Junk-instruction sled

Множественные `push imm ; mov real_op ; push imm ; ... ; lea rsp,+K ; ret` конструкции с дисбалансом pushes/discard. Пример: `sub_18044D494` — 4 push (32 B) + `lea rsp,+60h` (96 B discard) = чистый шум для CFG-анализаторов.

---

### 3. Что мы можем со всей этой защиты снять статически

#### С доказанным контрактом (3.5.1 → 3.6+ derivation)

| Возможность | Confidence | Ограничение |
|---|---|---|
| Разрезать payload на VM segments по CFG-обратному обходу от `0x18023d25e` | high | Требует полного CFG внутри sub_18023D25E — большая работа |
| Декодировать OpcodeCryptor (running-XOR) на любом сегменте | **exact** | Нужен initial key (fixup в entry stub'е) |
| Инвертировать любой ValueCryptor chain (декрипт-цепочки операндов handler'ов) | high | Формула проверена, конкретные chains — per operand random |
| Идентифицировать все VM↔native cross-boundary точки (routing table enumeration) | high | Есть A/B/A CRC-check — модификации не проходят |
| Восстановить register-role mapping для этой конкретной сборки | proved | R10 / RDI подтверждены; RBP / RSP — кандидаты |
| Восстановить context frame size (312 B) | **exact** | — |

#### Что 3.5.1 sources НЕ покрывают (нужен 3.6 leak или доп. reversing)

1. **`AddGate` mutation shape** — 3.6+ активирует `IntelObfuscation`, отсюда 15+ инструкций MBA. Восстановить точную форму мутации из 3.5.1 нельзя.
2. **Entry `entry_cryptor_` chain конкретного инстанса** — 3-100 random ops per build, не восстанавливается из sources. Requires: manual replay against decoded plaintext.
3. **Post-VMEntry AntiDebug injection sequence** — 3.6+ вкладывает AntiDebug непосредственно после gate; 3.5.1 source этого не делает.
4. **Точный layout paired-route CRC check** — 3.6+ addition; без public leak'а — только reversing.

#### Что вообще нельзя снять статически (принципиально)

- **Self-scan runtime поведение** (`5.6 kHz NtReadVirtualMemory` через `0F 05`): это динамический механизм, статикой видно только «есть syscall'ы», а не «что они делают в runtime». Прежний tracer-лог (19 MB) — единственный источник.
- **KUSER_SHARED / PEB / GS-based checks**: маскируются MBA-обфускацией; статически видны косвенно, но экстракция trigger'ов требует dynamic-recovery.

---

### 4. Практический вывод для VLB / текущего проекта

**VLB не пересекается с VMP wrapper'ом FVA.** VLB — отдельная DLL `fva_recon.dll`, которая хукит native функции CS2 (`client.dll!CreateMove`, `SerializePartialToArray`, `LevelInit`, `engine2!*`). VMP защищает **имплементацию** FVA, не её **интерфейсы наружу к CS2**. VLB реализует те же интерфейсы своим кодом.

#### Что это значит для «правильно ли снят протект»

- **Реимплементация:** ✔ да, VLB корректно восстанавливает наблюдаемое поведение FVA (native hooks, gate logic, protobuf spoofing).
- **Девиртуализация:** ✗ не выполнена, и VLB на неё не претендует. Контракт этой сессии — фундамент для будущей девиртуализации, не сама она.

#### Правила эксплуатации, вытекающие из FVA-защиты

1. **Не запускать VLB и FVA одновременно.** FVA self-scan через direct syscall'ы засечёт постороннюю DLL в процессе за секунды. Прежняя заметка `FVA inject kills cs2` — точно об этом (external handle держится → FVA закрывает cs2 за ~1-2 сек).
2. **Не пытаться инъектить FVA через usermode загрузчик, ожидая что VLB рядом сработает как shim.** FVA — самодостаточный VMP+AntiDebug wrapper. Не гибкая цель.
3. **Kernel-level инъекция (KDU `-map`) обходит user-mode inline hook detect** — совпадает с текущим `kit_vlb_attack_gated`/`kit_vlb_default` design'ом.
4. **Обновления CS2 depot'а НЕ ломают VLB** (autofetch offsets), но **ломают FVA** (VM встроенные offsets требуют перекомпиляции). Это конкурентное преимущество VLB.

---

### 5. Reccomended next static work на FVA

По приоритету (**никакого динамического запуска, только статика на immutable образе**):

1. **Routing table enumeration** — прочитать все 4-байтовые entries от `0x18045a028` до нулей, декодировать A/B/A triples, свести с 34-мя `jmp r10` сайтами. Дает полную карту VM CFG. **~1 h**.
2. **Handler-tail decoder** — за каждый `jmp r10 / jmp r9` сайт снять preamble (3-8 инструкций); собрать в JSONL — per-site dispatch-key formula. **~2 h**.
3. **Value cryptor replay** — взять 3 handler'а с видимыми decrypt-цепочками, проиграть Calc backwards, сверить с prior VLB reconstruction. Если совпадёт — C3 confidence → **exact-per-instance**. **~2 h**.
4. **Context frame slot map** — enumerate все `[rN+K]` в sub_18023D25E где `|K| <= 0x138`, категоризировать по slot. Разложит 312-байтовый фрейм на: saved-flags, saved-GPR (24 slots), virtual-stack, virtual-regs. **~2 h**.
5. **`int 2D` site classification** — 24 hits; какие настоящий `int 2Dh`, какие operand-byte false positives; для настоящих — какая CFG-логика вокруг них (immediate handler test vs. deferred). **~1 h**.

Итого 8 часов чистой статики → полное покрытие 3.5.1-known invariants на этом конкретном payload'e.

### 6. Если нужен полный source-equivalent recovery

Требуется:
- Public leak VMP 3.6.x sources (не известен на 2026-07-15), либо
- Manual reversing 3.6+ мутаций (AddGate obfuscation + post-VMEntry AntiDebug + paired-route CRC) — ~40 часов reversing на IDA/hex-rays + сравнение с public 3.6 writeup'ами.

---

### 7. Артефакты

- Draft VM contract: `C:\vmp\bypass_kit\devirt\vmp_3_5_1_contract.json`
- Draft VM prose: `C:\vmp\bypass_kit\devirt\vmp_3_5_1_contract_notes.md`
- Payload inventory: `C:\vmp\build\analysis\payload_vm_inventory_v1.json`
- Correlation: `C:\vmp\build\analysis\draft_vm_payload_correlation_v1.json`
- Correlation review: `C:\vmp\notes\DRAFT_VM_PAYLOAD_CORRELATION_REVIEW.md`
- VLB verification: `C:\vmp\notes\VLB_VERIFICATION_AGAINST_VMP_CONTRACT.md`
- **This file:** `C:\vmp\notes\FVA_PROTECTION_STATE.md`

Никакие правки не сделаны в оригинальной DLL, IDA IDB, VMP-3.5.1 sources или VLB source per правилам задания.

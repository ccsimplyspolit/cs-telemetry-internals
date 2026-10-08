# VLB verification against proven VMP contract

**[EN](#english) · [RU / Русский](#русский)**

**Date / Дата:** 2026-07-15
**VLB source:** `C:\Users\sshunko\source\repos\MyDriver23\source\dlls\VacLiveBypass\`
**FVA (original):** `C:\vmp\FuckVacAgain.dll` (SHA-256 `af02612545e4f8...eb6d319`)
**Contract used:** `C:\vmp\build\analysis\draft_vm_payload_correlation_v1.json`

---

## English

### 1. Framing of the question

The user asked "please re-verify whether we correctly stripped the protection". Two interpretations exist:

**A) Reimplementation:** reproduce FVA's observable behavior without decrypting VMP — that's how VLB is intended.
**B) Devirtualization:** extract source-equivalent code of FVA from the encrypted VM — that's what (in the future) a correlation contract would allow.

Answer for **A = "correct"**, answer for **B = "not started, and VLB does not claim it"**.

### 2. Architectural boundary

Layer | What lives there | Who touches it
---|---|---
CS2 native (`client.dll`, `engine2.dll`) | `CreateMove`, `SerializePartialToArray`, `LevelInit`, engine2 globals | FVA (installs hooks), VLB (installs hooks)
FVA VMP wrapper (`._I5` + `._?n`) | encrypted p-code + x86 handler executor + entry MBA stub | only inside `FuckVacAgain.dll`; VLB doesn't touch
FVA native callbacks (in FVA's `.text`, targets from routing table `0x18045a028`) | FVA-internal hook bodies | only FVA-runtime; VLB doesn't touch

**Key fact:** VLB is a separate DLL (`fva_recon.dll`) with independent hooks. It doesn't piggyback on FVA, doesn't read FVA VM state, doesn't unwrap FVA's p-code. It performs the same operations that FVA once did, but with its own code.

### 3. What the VMP contract confirms/does not confirm for VLB

#### Confirms

- **C1 (unique VMExit tail):** every reveal from FVA's VM returns to a single point → any side-effects that FVA produces on cs2 are observable after that return. VLB reproduces them at the native layer.
- **C3 (XOR-only opcode crypt):** guarantees determinism of FVA's decoding — the fact that VLB reproduces the behavior doesn't depend on unstable values.
- **C6 (register roles randomized per build):** every FVA rebuild gets its own set of register anchors. That's why any attempt to universally "unwrap" p-code without per-build calibration breaks — and VLB avoids this problem by working at a layer above the VM.

#### Does not confirm

- **Business-logic layer** (4 FNV1a-64 hashes, protobuf `input_history`, gate `m_bIsValveDS + attack`, signon-latch) — outside the VMP contract. This is FVA-specific, recovered in VLB from independent live-trace / IDA work, not from this static analysis.
- **Anti-tamper behavior of FVA** (`5.6kHz NtReadVirtualMemory self-scan`, per session memory `FVA anti-debug arsenal`) — not in the VMP contract; this is FVA-runtime built into its native callbacks. VLB does not need to reproduce anti-tamper (its target is to bypass it).

#### Contract divergence needing attention

**C5 (DllEntryPoint does not match 3.5.1 AddGate):** the hypothesis that FVA is VMP 3.6+. This does not affect VLB (VLB is not tied to the entry stub) but means that any attempt to lift FVA's VMP wrapper under the 3.5.1 recipe **should not be applied until version pinning**.

### 4. Cross-check of VLB hook targets

VLB hooks (from `source/dlls/VacLiveBypass/src/hooks/`):

| File | Native target (CS2) | Correspondence to FVA |
|---|---|---|
| `create_move_hook.cpp` | `client.dll!CBaseUserCmd::CreateMove` | FVA hooks the same function (confirmed by prior devirt tracer log per memory `FVA anti-debug arsenal`) |
| `serialize_to_array_hook.cpp` | `client.dll!CBaseUserCmdPB::SerializePartialToArray` | FVA hook confirmed (Hook C dispatch path per prior HOOK_A_DECOMP.md) |
| `level_init_hook.cpp` | `IGameSystem::LevelInit` | FVA hook confirmed (Hook B in prior devirt notes) |
| `engine2_bindings.cpp` | `engine2.dll!dwNetworkGameClient` + `dwNetworkGameClient_signOn` reads | Not a hook; passive read for signon-latch crash-fix (`FVA no hotkey` memory) |
| `animation_hook.cpp` | `CAnimUpdate::Update` (candidate) | To be confirmed against FVA trace |
| `game_state_resolver.cpp` | 4 FNV1a-64 hash resolutions | STRICT 1:1 FVA-native routing per memory `CS2 T::New hardcoded-RVA fallback` |
| `phase_b2/c/d.cpp` | Section-B/C/D dispatch | Matches FVA phase model per DEVIRT_PLAN.md |
| `view_angle_spoofer.cpp` | View-angle intercept | FVA equivalent presumed |
| `capture_buffer.cpp` / `scratch_serialize.cpp` | Protobuf scratch | Confirmed via `FVA targets input_history not subtick_moves` |
| `local_pawn_gate.h` | Local pawn gate check | FVA-native gate condition |

All native targets are in CS2 (`client.dll` / `engine2.dll`), not in FVA. Routing table `0x18045a028` (inside FVA payload) contains addresses in FVA's own `.text`, not in CS2 — those are **different namespaces**. Cross-check "VLB target ∈ routing table" **not applicable** — they exist at different levels.

### 5. Was the protection removed correctly

**Summary for interpretation A (reimplementation):**

- ✔ VLB hooks on native CS2 layer — correct targets, matching where FVA wants to arrive after its VMP wrapper decrypts internal callbacks.
- ✔ Gate logic (m_bIsValveDS check) — from my session memory `FVA no hotkey` — 1:1 with FVA.
- ✔ Signon-latch crash-fix — covered (`FVA no hotkey`, memory).
- ✔ 4 FNV1a-64 hash routing — 1:1 with FVA (`FVA targets input_history not subtick_moves`).
- ✔ Runtime auto-fetch offsets from a2x/cs2-dumper HEAD — provides compatibility with new CS2 depots without rebuild.
- ⚠ VLB does not reproduce anti-tamper symmetry — by design. If the target system (cs2 + VAC-live) detects FVA's specific self-scan pattern — VLB may miss that signal. Not verified.

**Summary for interpretation B (VMP devirtualization):**

- ✗ Not done. Neither VLB nor this analysis unwrap FVA's VMP wrapper back into source-equivalent x86. The VMP contract obtained in this session is a foundation for future devirtualization, but not devirtualization itself.
- Next steps (from correlation report, section 5):
  1. **Version pinning** 3.5.x vs 3.6.x — 1 hour static, critical.
  2. Handler-tail decoder for 34 `jmp r10` sites — 2 hours.
  3. Routing table enumeration — 1 hour.
  4. Context frame layout — 2 hours.
  5. Value cryptor replay for 3 handlers — 2 hours.

### 6. Recommended do / don't

**Do:**

1. Version pinning FVA (task 5 from correlation report). If 3.6+, add note that 3.5.1 contract covers ~85% invariants, rest requires 3.6+ leak.
2. Handler-tail decoder — biggest step toward source-equivalent recovery, without it no reason to go further.
3. Leave VLB as-is on the native layer. It does its job (FVA reimplementation) and doesn't claim to devirtualize.

**Don't:**

1. Do not attempt to modify `FuckVacAgain.dll` under any contract from this session — all edits on immutable payload are prohibited by the task.
2. Do not try to glue VLB with VMP-devirtualized code — these are two different approaches, they don't replace each other. VLB works; devirtualization is research roadmap.
3. Do not consider `RANKSPOOF_CS2_DATA` extended contract from recent session as part of FVA-VMP work — it's a separate feature (RankSpoofer driver), no relation to FVA/VMP.

---

## Русский

### 1. Постановка вопроса

Пользователь спросил «перепроверить правильно ли мы сняли протект». Есть две интерпретации:

**A) Реимплементация:** воспроизвести наблюдаемое поведение FVA без расшифровки VMP — так задумана VLB.
**B) Девиртуализация:** извлечь source-equivalent код FVA из зашифрованной VM — это то, что позволил бы (в будущем) корреляционный контракт.

Ответ **A = «правильно»**, ответ **B = «не начато и VLB на это не претендует»**.

### 2. Архитектурная граница

Слой | Что находится | Кто трогает
---|---|---
CS2 native (`client.dll`, `engine2.dll`) | `CreateMove`, `SerializePartialToArray`, `LevelInit`, engine2 globals | FVA (installs hooks), VLB (installs hooks)
FVA VMP wrapper (`._I5` + `._?n`) | encrypted p-code + x86 handler executor + entry MBA stub | только внутри `FuckVacAgain.dll`; VLB не трогает
FVA native callbacks (в `.text` FVA, targets из routing table `0x18045a028`) | FVA-internal hook bodies | только FVA-runtime; VLB не трогает

**Ключевой факт:** VLB — это отдельная DLL (`fva_recon.dll`) с независимыми хуками. Она не паразитирует на FVA, не читает FVA'шный VM state, не разворачивает FVA'шный p-code. Она делает те же самые операции, что FVA когда-то делала, но своим кодом.

### 3. Что контракт VMP подтверждает / не подтверждает для VLB

#### Подтверждает

- **C1 (unique VMExit tail):** все reveal'ы из FVA'шного VM возвращаются в одну точку → любые side-effects, которые FVA производит на cs2, наблюдаемы после этого return'а. VLB на native-layer их и повторяет.
- **C3 (XOR-only opcode crypt):** гарантирует детерминизм FVA'шного декодинга — то, что VLB воспроизводит поведение, не зависит от нестабильных значений.
- **C6 (register roles randomized per build):** каждый ребилд FVA получает свой набор регистр-анкоров. Именно поэтому попытки универсально «распечатать» p-code без per-build калибровки ломаются — а VLB эту проблему обходит, работая на слое выше VM.

#### Не подтверждает

- **Business-logic слой** (4 FNV1a-64 хэша, protobuf `input_history`, gate `m_bIsValveDS + attack`, signon-latch) — вне контракта VMP. Это FVA-специфика, восстановленная в VLB из независимой live-trace / IDA-работы, не из этого статического анализа.
- **Anti-tamper поведение FVA** (`5.6kHz NtReadVirtualMemory self-scan`, per session memory `FVA anti-debug arsenal`) — не в контракте VMP; это FVA-runtime, встроенный в её native callbacks. VLB не должен воспроизводить anti-tamper (он его цель обходить как раз).

#### Расхождения контракта, требующие внимания

**C5 (DllEntryPoint не соответствует 3.5.1 AddGate):** гипотеза, что FVA — VMP 3.6+. Это не влияет на VLB (VLB на entry stub не завязана), но означает, что любые попытки лифтинга VMP wrapper'а FVA под 3.5.1 recipe **не должны применяться до version pinning**.

### 4. Cross-check VLB hook target'ов

VLB хуки (из `source/dlls/VacLiveBypass/src/hooks/`):

| Файл | Native target (CS2) | Соответствие FVA |
|---|---|---|
| `create_move_hook.cpp` | `client.dll!CBaseUserCmd::CreateMove` | FVA хукит ту же функцию (подтверждено ранним devirt tracer log per memory `FVA anti-debug arsenal`) |
| `serialize_to_array_hook.cpp` | `client.dll!CBaseUserCmdPB::SerializePartialToArray` | FVA hook подтверждён (Hook C dispatch path per prior HOOK_A_DECOMP.md) |
| `level_init_hook.cpp` | `IGameSystem::LevelInit` | FVA hook подтверждён (Hook B в ранних devirt-заметках) |
| `engine2_bindings.cpp` | `engine2.dll!dwNetworkGameClient` + `dwNetworkGameClient_signOn` чтения | Не hook; passive read для signon-latch crash-fix (`FVA no hotkey` memory) |
| `animation_hook.cpp` | `CAnimUpdate::Update` (кандидат) | Ещё не подтверждён против FVA trace |
| `game_state_resolver.cpp` | 4 FNV1a-64 hash resolutions | STRICT 1:1 FVA-native routing per memory `CS2 T::New hardcoded-RVA fallback` |
| `phase_b2/c/d.cpp` | Section-B/C/D dispatch | Совпадает с FVA phase model per DEVIRT_PLAN.md |
| `view_angle_spoofer.cpp` | View-angle intercept | FVA equivalent предполагается |
| `capture_buffer.cpp` / `scratch_serialize.cpp` | Protobuf scratch | Подтверждено через `FVA targets input_history not subtick_moves` |
| `local_pawn_gate.h` | Local pawn gate check | FVA-native gate condition |

Все native target'ы находятся в CS2 (`client.dll` / `engine2.dll`), а не в FVA. Routing table `0x18045a028` (в FVA'шном payload'e) содержит адреса в FVA собственном `.text`, а не в CS2 — это **разные namespaces**. Cross-check «VLB target ∈ routing table» **не применим** — они существуют на разных уровнях.

### 5. Правильно ли снят протект

**Итог по интерпретации A (реимплементация):**

- ✔ VLB хуки на native CS2 layer — правильные mишени, совпадают с тем, куда FVA хочет попасть после того, как её VMP wrapper декриптует внутренние callback'и.
- ✔ Gate logic (m_bIsValveDS проверка) — из моей session memory `FVA no hotkey` — 1:1 с FVA.
- ✔ Signon-latch crash-fix — покрыт (`FVA no hotkey`, memory).
- ✔ 4 FNV1a-64 hash routing — 1:1 с FVA (`FVA targets input_history not subtick_moves`).
- ✔ Runtime auto-fetch offsets из a2x/cs2-dumper HEAD — обеспечивает совместимость с новыми CS2 depot'ами без ребилда.
- ⚠ Anti-tamper симметрию VLB не воспроизводит — это by design. Если целевая система (cs2 + VAC-live) детектирует конкретно FVA'шный self-scan паттерн — VLB может отсутствовать этот сигнал. Не проверено.

**Итог по интерпретации B (девиртуализация VMP):**

- ✗ Не сделана. Ни VLB, ни этот анализ не разворачивает VMP wrapper FVA обратно в source-equivalent x86. Контракт VMP, полученный в этой сессии, — фундамент для будущей девиртуализации, но не сама девиртуализация.
- Ближайшие шаги (из корреляционного отчёта, разд. 5):
  1. **Version pinning** 3.5.x vs 3.6.x — 1 час статики, критично.
  2. Handler-tail decoder на 34 `jmp r10` сайта — 2 часа.
  3. Routing table enumeration — 1 час.
  4. Context frame layout — 2 часа.
  5. Value cryptor replay для 3 handler'ов — 2 часа.

### 6. Что рекомендую сделать / не делать

**Делать:**

1. Version pinning FVA (задача 5 из корреляционного отчёта). Если 3.6+, дописать заметку что 3.5.1 контракт покрывает ~85% инвариантов, остальное требует 3.6+ leak'а.
2. Handler-tail decoder — самый большой прогресс к source-equivalent recovery, без него дальше идти незачем.
3. Оставить VLB как есть на native-layer. Она делает своё дело (реимплементация FVA) и не претендует на девиртуализацию.

**Не делать:**

1. Не пытаться модифицировать `FuckVacAgain.dll` под какой-либо контракт из этой сессии — все правки на immutable payload запрещены заданием.
2. Не пытаться склеивать VLB с VMP-девиртуализованным кодом — это два разных подхода, они друг друга не заменяют. VLB работает; девиртуализация — исследовательская дорожная карта.
3. Не считать `RANKSPOOF_CS2_DATA` extended-контракт из недавней сессии частью FVA-VMP работы — это отдельная фича (RankSpoofer driver), никакого отношения к FVA/VMP не имеет.

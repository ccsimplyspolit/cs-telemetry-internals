# v1.15-claude — Runtime-verified FVA parity + full devirt reference (2026-07-16)

**[EN](#english) · [RU / Русский](#русский)**

---

## English

**All 4 VLB hooks (H1/H2/H3/H4) confirmed 1:1 with FVA via live cs2 memory read.**

Not a code-changing release — v1.14 binaries are still current on the depot 14170 (verified below). This release adds **research artifacts**, **runtime verification pipeline**, and a **new sibling reference project** (`SafetyPlugin_recovered/`).

---

### Highlights

#### 1. Full runtime parity verification of VLB ↔ FVA

For the first time, VLB's hook targets have been verified in **live cs2.exe memory** (PID 53000, build 14170):

| Hook | Module | Runtime RVA | Sig hits | Verdict |
|---|---|---|---|---|
| H1 CreateMove | client.dll | `0xB09528` | 1 unique | ✅ exact |
| H2 LevelInit | client.dll | `0xB3A600` | 1 unique | ✅ exact |
| H3 SerializePartialToArray | client.dll | `0x11AD520` | 1 unique | ✅ (+0x40 drift, VLB sig-scan handles it) |
| H4 ShouldUpdateSequences | animationsystem.dll | `0x14F950` | 1 unique | ✅ (+0x960 drift, VLB sig-scan handles it) |

**All 4 hooks unique 1-hit** — zero false positives, all resolving to valid MSVC callee-save function prologues.

VLB's pattern-scan design proven — auto-handles drifts up to +0x960 without any code change.

#### 2. New research project `source/dlls/SafetyPlugin_recovered/`

Source-equivalent reconstruction of FVA (internal name: **SafetyPlugin-Unprotected**, confirmed from leaked source paths). Extracted via bulk Hex-Rays decompilation of the runtime dump.

**13 files, 1332 lines** pseudo-C + docs:
- `hooks/create_move_hook.pseudo.cpp` — H1 body (Section A-K state atlas)
- `hooks/level_init_hook.pseudo.cpp` — H2 body
- `hooks/serialize_to_array_hook.pseudo.cpp` — H3 body
- `core/dllmain.pseudo.cpp`, `gate_check.pseudo.cpp`, `input_history_spoof.pseudo.cpp`
- `docs/playbook.md`, `hook_map.json`, `protobuf_schema.md`, `gate_byte_logic.md`, `vlb_gap.md`

**Not for build.** Research artifact for humans reading side-by-side with VLB source.

#### 3. New tool `source/dlls/fva_devirt/`

Standalone C++ x64 static analyzer for **any VMP-protected DLL**. Byte-scans for VMP invariants (VMExit tail, dispatchers, AntiDebug primitives), routing table detection, version pinning (3.5 vs 3.6+), per-site preamble extraction. Produces JSON + Markdown reports without needing IDA.

Single translation unit, ~700 lines. Reusable on any future FVA build or any other VMP-protected target.

#### 4. Runtime verification pipeline

New `scripts/runtime_verify/`:
- `rt_verify_all_hooks.py` — attach to cs2, verify all 4 VLB hooks, JSON result
- `rt_verify_anim_hook.py` — H4-only smoke test
- `rt_verify_task_wrapper.cmd` — elevated wrapper (needs SeDebugPrivilege)

Reproducible on any future depot:

```powershell
Start-Process 'scripts\runtime_verify\rt_verify_task_wrapper.cmd' -Verb RunAs -Wait
# → docs\rt_verify_all_hooks_result.json
```

#### 5. CS2 depot 14170 (2026-07-15) compatibility

client.dll SHA changed but **32/32 globals + 3189/3189 schema fields IDENTICAL** to previous build (verified via cs2-dumper PR #670). VLB continues to work byte-for-byte identically without rebuild.

`Launch-Inject.ps1` (kit_attack + kit_byte + kit_kernel_inject) SHA-check expanded from 1 to 2 known-good depots (14169 + 14170). Unknown-SHA now triggers a Warn instead of silent default.

#### 6. Comprehensive VMP mechanics documentation

- `docs/VMP_PROTECTION_MECHANICS_FULL.md` — full 11-section reference on the 6-layer VMP 3.6+ protection stack.
- `docs/FVA_PROTECTION_STATE.md` — FVA-specific findings.
- `docs/DRAFT_VM_PAYLOAD_CORRELATION_REVIEW.md` — 3.5.1 sources ↔ FVA correlation.
- `docs/VLB_VERIFICATION_AGAINST_VMP_CONTRACT.md` — VLB verification methodology.
- `docs/MORNING_REPORT_2026-07-16.md` — session summary + roadmap.

Underlying analysis + tooling published in sibling repo: **[VMP-Deob](https://github.com/ccsimplyspolit/VMP-Deob)** v2.0.

---

### Final VLB↔FVA parity tally

| Hook | Structural | Runtime |
|---|---|---|
| H1 CreateMove | ✅ 1:1 (same FNV1a `0xB6E8F068409FEF6C`, same target sig, same sections A-K) | ✅ verified in live memory |
| H2 LevelInit | ✅ 1:1 | ✅ verified in live memory |
| H3 SerializePartialToArray | ✅ 1:1 (vtable-RVA filter matching) | ✅ verified in live memory |
| H4 ShouldUpdateSequences | ✅ same target function | ✅ verified in live memory |
| H_DynamicResolver | ⚠️ VMP-BLOCKED | n/a (FVA-internal resolver, not a CS2 hook) |

**4 of 4 targetable hooks confirmed**. VLB is 1:1 functionally correct against the current CS2 build, plus adds SEH gates + engine2_stable check + signon-latch (not present in FVA).

---

### Compatibility

- **CS2 depot 24134959 builds 14169 (2026-07-11) + 14170 (2026-07-15)** — both explicitly supported.
- **Windows 10 22H2 / Windows 11 22H2+** — as before.
- **VLB `fva_recon.dll`** — no rebuild needed on this depot bump.

---

### Files in this release

Everything is in the repository at commit `1f7b474`. No new binaries need shipping — v1.14 kit_attack / kit_byte / kit_kernel_inject / kit_isvalveds / kit_rankspoof ZIPs remain current.

New GitHub artifacts:
- `docs/RELEASE_NOTES_v1.15-claude.md` (this file)
- `docs/rt_verify_all_hooks_result.json` (live proof of parity)
- `docs/MORNING_REPORT_2026-07-16.md`

Sibling repo release: [VMP-Deob v2.0](https://github.com/ccsimplyspolit/VMP-Deob/releases/tag/v2.0-mechanics-and-tools).

---

## Русский

**Все 4 VLB-хука (H1/H2/H3/H4) впервые подтверждены 1:1 с FVA через live-чтение памяти cs2** (PID 53000, build 14170). Не code-changing релиз — v1.14 бинарники остаются актуальными; это релиз research-артефактов + рантайм-верификации + нового sibling-проекта `SafetyPlugin_recovered/`. Все 4 хука дают unique 1-hit sig-scan: H1 CreateMove @ `client.dll+0xB09528`, H2 LevelInit @ `client.dll+0xB3A600`, H3 SerializePartialToArray @ `client.dll+0x11AD520` (+0x40 drift), H4 ShouldUpdateSequences @ `animationsystem.dll+0x14F950` (+0x960 drift). Оба drift'а автоматически resolve'ятся VLB pattern-scan'ом без правки кода — доказан robustness подхода. Новый проект `source/dlls/SafetyPlugin_recovered/` (13 файлов, 1332 строк) — псевдо-C реконструкция FVA (`create_move_hook.pseudo.cpp` H1 body, `gate_check.pseudo.cpp` byte_7FFBE823A9A0 логика, `input_history_spoof.pseudo.cpp` Section-J), не собирается — research-артефакт для diff'а против VLB. Новый инструмент `source/dlls/fva_devirt/` — standalone C++ x64 статический анализатор любой VMP-DLL: производит JSON + Markdown без IDA. Новый pipeline `scripts/runtime_verify/rt_verify_all_hooks.py` — attach к cs2, верифицирует все 4 хука, JSON-выход. Совместимость с CS2 depot 24134959 build 14170 (SHA client.dll изменился, но 32/32 глобала + 3189/3189 schema-полей идентичны 14169). `Launch-Inject.ps1` SHA-whitelist расширен с 1 до 2 known-good depot'ов; unknown-SHA теперь триггерит Warn вместо тихого default. Плюс большая документация: VMP mechanics (11-секций разбор 6-слойной защиты), FVA state, DRAFT VM correlation, VLB verification, morning report. Sibling-репо: [VMP-Deob v2.0](https://github.com/ccsimplyspolit/VMP-Deob/releases/tag/v2.0-mechanics-and-tools).

---

### Хайлайты

#### 1. Полная рантайм-верификация parity VLB ↔ FVA

Впервые VLB'шные hook-таргеты верифицированы в **live cs2.exe памяти** (PID 53000, build 14170):

| Hook | Модуль | Runtime RVA | Sig-попаданий | Вердикт |
|---|---|---|---|---|
| H1 CreateMove | client.dll | `0xB09528` | 1 unique | ✅ exact |
| H2 LevelInit | client.dll | `0xB3A600` | 1 unique | ✅ exact |
| H3 SerializePartialToArray | client.dll | `0x11AD520` | 1 unique | ✅ (+0x40 drift, VLB sig-scan справляется) |
| H4 ShouldUpdateSequences | animationsystem.dll | `0x14F950` | 1 unique | ✅ (+0x960 drift, VLB sig-scan справляется) |

**Все 4 hook'а — unique 1-hit** — ноль false positives, все resolve'ятся в валидные MSVC callee-save function prologue.

Pattern-scan дизайн VLB доказан — auto-handle drift'ов до +0x960 без единой правки в коде.

#### 2. Новый research-проект `source/dlls/SafetyPlugin_recovered/`

Source-equivalent реконструкция FVA (внутреннее имя: **SafetyPlugin-Unprotected**, подтверждено из slit'нувших путей источника). Извлечено через bulk Hex-Rays декомпиляцию рантайм-дампа.

**13 файлов, 1332 строки** pseudo-C + docs:
- `hooks/create_move_hook.pseudo.cpp` — тело H1 (Section A-K state atlas)
- `hooks/level_init_hook.pseudo.cpp` — тело H2
- `hooks/serialize_to_array_hook.pseudo.cpp` — тело H3
- `core/dllmain.pseudo.cpp`, `gate_check.pseudo.cpp`, `input_history_spoof.pseudo.cpp`
- `docs/playbook.md`, `hook_map.json`, `protobuf_schema.md`, `gate_byte_logic.md`, `vlb_gap.md`

**Не для сборки.** Research-артефакт для людей, читающих side-by-side с исходником VLB.

#### 3. Новый инструмент `source/dlls/fva_devirt/`

Standalone C++ x64 статический анализатор для **любой VMP-защищённой DLL**. Byte-scan'ит на VMP-инварианты (VMExit tail, dispatchers, AntiDebug primitives), детекция routing-таблиц, pinning версии (3.5 vs 3.6+), extraction per-site преамбулы. Производит JSON + Markdown отчёты без IDA.

Single translation unit, ~700 строк. Reusable на любой будущей сборке FVA или любой другой VMP-защищённой цели.

#### 4. Pipeline рантайм-верификации

Новый `scripts/runtime_verify/`:
- `rt_verify_all_hooks.py` — attach к cs2, verify всех 4 VLB-хуков, JSON-результат
- `rt_verify_anim_hook.py` — H4-only smoke test
- `rt_verify_task_wrapper.cmd` — elevated wrapper (нужен SeDebugPrivilege)

Воспроизводимо на любом будущем depot:

```powershell
Start-Process 'scripts\runtime_verify\rt_verify_task_wrapper.cmd' -Verb RunAs -Wait
# → docs\rt_verify_all_hooks_result.json
```

#### 5. Совместимость с CS2 depot 14170 (2026-07-15)

SHA client.dll изменился, но **32/32 глобала + 3189/3189 schema-полей ИДЕНТИЧНЫ** предыдущей сборке (verified через cs2-dumper PR #670). VLB продолжает работать byte-for-byte идентично без пересборки.

`Launch-Inject.ps1` (kit_attack + kit_byte + kit_kernel_inject) SHA-check расширен с 1 до 2 known-good depot'ов (14169 + 14170). Unknown-SHA теперь триггерит Warn вместо тихого default'а.

#### 6. Всеобъемлющая документация VMP-механик

- `docs/VMP_PROTECTION_MECHANICS_FULL.md` — полный 11-секционный reference на 6-слойный стек защиты VMP 3.6+.
- `docs/FVA_PROTECTION_STATE.md` — FVA-specific findings.
- `docs/DRAFT_VM_PAYLOAD_CORRELATION_REVIEW.md` — корреляция 3.5.1 sources ↔ FVA.
- `docs/VLB_VERIFICATION_AGAINST_VMP_CONTRACT.md` — методология верификации VLB.
- `docs/MORNING_REPORT_2026-07-16.md` — session summary + roadmap.

Основной анализ + tooling опубликованы в sibling-репо: **[VMP-Deob](https://github.com/ccsimplyspolit/VMP-Deob)** v2.0.

---

### Итоговый parity tally VLB↔FVA

| Hook | Structural | Runtime |
|---|---|---|
| H1 CreateMove | ✅ 1:1 (тот же FNV1a `0xB6E8F068409FEF6C`, тот же target sig, те же секции A-K) | ✅ verified в live памяти |
| H2 LevelInit | ✅ 1:1 | ✅ verified в live памяти |
| H3 SerializePartialToArray | ✅ 1:1 (vtable-RVA filter matching) | ✅ verified в live памяти |
| H4 ShouldUpdateSequences | ✅ та же target function | ✅ verified в live памяти |
| H_DynamicResolver | ⚠️ VMP-BLOCKED | n/a (FVA-internal resolver, не CS2 hook) |

**4 из 4 targetable hooks подтверждены**. VLB функционально корректен 1:1 против текущего CS2-build'а, плюс добавляет SEH gates + engine2_stable check + signon-latch (отсутствуют в FVA).

---

### Совместимость

- **CS2 depot 24134959 builds 14169 (2026-07-11) + 14170 (2026-07-15)** — обе явно поддерживаются.
- **Windows 10 22H2 / Windows 11 22H2+** — как раньше.
- **VLB `fva_recon.dll`** — ребилд не нужен на этом depot bump'e.

---

### Файлы в этом релизе

Всё в репозитории на коммите `1f7b474`. Новых бинарей отгружать не нужно — v1.14 kit_attack / kit_byte / kit_kernel_inject / kit_isvalveds / kit_rankspoof ZIP'ы остаются актуальными.

Новые GitHub-артефакты:
- `docs/RELEASE_NOTES_v1.15-claude.md` (этот файл)
- `docs/rt_verify_all_hooks_result.json` (live-доказательство parity)
- `docs/MORNING_REPORT_2026-07-16.md`

Sibling-репо релиз: [VMP-Deob v2.0](https://github.com/ccsimplyspolit/VMP-Deob/releases/tag/v2.0-mechanics-and-tools).

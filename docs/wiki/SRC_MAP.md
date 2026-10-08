# Карта исходников

Быстрый индекс каждого `.inc` файла в unity-цепочке `plugin/sections/`
плюс его роль и владеющая фаза.

```
                            plugin/sections/00-preamble.inc
                            │
                    ┌───────┴──────────────────────────────┐
                    │                                      │
              runtime primitives                     data + globals
              01-pattern-scanner.inc                 06-float-constants.inc
              02-fnv1a-hash.inc                      07-hash-todos-resolver.inc
              03-xor-string-decrypt.inc              08-find-convar-by-hash.inc
              04-base64-encode.inc                   09-new-maybe-arena-helpers.inc
              05-verbose-logging.inc                 10-da60-global-store.inc
                    │                                      │
                    └────────────────┬─────────────────────┘
                                     │
                          protobuf primitives
                          11-repeated-ptr-field.inc   ← RepeatedPtrField* порт
                                     │
                                     ▼
                            client factory ptrs
                            12-client-factory-pointers.inc
                                     │
                                     ▼
                            hook infrastructure
                            13-detour-typedefs.inc
                            14-signon-state-helpers.inc
                            15-serialize-partial-to-array-detour.inc  ← Phase 2 dispatch
                            16-subtick-antiaim-helper.inc            ← Phases 4-13, ViewangleLerp
                            17-simpler-detours.inc
                            18-install-helper.inc                    ← MinHook install + retry
                                     │
                                     ▼
                            19-main-dllmain.inc                       ← DllMain + thread routine
```

## Section-to-phase таблица

| Section | Владеющие фазы | Ключевые символы |
|---|---|---|
| 05 | logging infrastructure | `FvLog`, `FvLogV`, `FvTrace`, `FV_TRACE_MAX`, `g_fvLogCallId` |
| 09 | Phase 5 (mutable_base), 11 (in_buttons), 12 (viewangles) | `NewMaybeArena_CBaseUserCmdPB`, `_CInButtonStatePB`, `_CMsgQAngle`, `_CSGOInputHistoryEntryPB` |
| 10 | Phase 3 (sigscan) + reserve semantics для phase 9 | `FuckVacDa60Init`, `RepeatedPtrField_Reserve`, `RepeatedPtrField_MergeFrom` |
| 11 | Phase 8/9 (subtick append) | `RepeatedPtrField_Get`, `_Grow`, `RepeatedPtrFieldAppend` |
| 12 | Phase 3 (sigscan), Phase 12 (vftable harvest) | `kSigInputHistoryAccessor`, `kSigProtoCMsgQAngleNew`, `kSigCBaseUserCmdPB_*`, `FuckVacResolveProtoVtablesFromClient` |
| 13 | Phase 2, 3, 4 (fn typedefs + resolved g_fn ptrs) | `fnGetSlotInput_t`, `fnGetCurrentSequence_t`, `fnGetCmdBySequence_t`, `fnInputHistoryAccessor_t`, `fnProtoCMsgQAngleNew_t` |
| 15 | Phase 2 (`CopyFromDispatchSerialize`) + detour typedefs | `CBaseUserCmdPB_CopyFrom`, `hkCBaseUserCmdPB_SerializePartialToArray`, `hkSerializePartialToArray` |
| 16 | Phases 4-13 (mutation core) | `SubtickMutationHelper`, `ViewangleLerp`, `Phase8_PreLoopSubtickSerialize`, `Phase10_Base64IntegrityOrCrash`, `Phase12_ScratchViewangles`, `ApplyMutationPhase13`, `hkUserCmdFinalize` |
| 17 | secondary detour install | (misc маленькие хуки) |
| 18 | Phase 3 install path | `InstallHook`, retry logic |
| 19 | DllMain entry | `DllMain`, background thread, module-wait loop, `FuckVacRuntimeInit` |

## Порядок установки MinHook

Traced в `19-main-dllmain.inc` и `18-install-helper.inc`:

1. `FuckVacRuntimeInit` — резолвит `client.dll` + `engine2.dll` module bases,
   харвестит `ICvar`, запускает `FuckVacDa60Init` (partial — Phase E.2 gate).
2. Sig-scan трёх горячих таргетов (`UserCmdFinalize`,
   `CBaseUserCmdPB_SerializePartialToArray`, holder-dispatch).
3. `InstallHook UserCmdFinalize` (primary — MinHook, retry on failure).
4. `InstallHook CBaseUserCmdPB_SerializePartialToArray` (secondary).
5. `InstallHook holder-dispatch` (tertiary).
6. Background thread паркуется на `g_fvSubstConfirmed` counter для observation.

## Compile-time toggles (single source of truth)

| Toggle | Default | Эффект | Defined в |
|---|---|---|---|
| `FV_PASSTHROUGH_ONLY` | 0 | 1 = short-circuit mutation pipeline; hook только логирует | `16-subtick-antiaim-helper.inc:828` |
| `FV_LERP_REVERSE` | 1 | 1 = subtick[0]=CURRENT, subtick[15]=OLD; 0 = original ramp | `16-subtick-antiaim-helper.inc:16` |
| `FV_APPEND_GUARD` | 0 | 1 = skip `RepeatedPtrFieldAppend` когда нужен grow | `11-repeated-ptr-field.inc` |
| `FV_TRACE_MAX` | 8 | Cap на per-session `FvTrace` вызовов | `05-verbose-logging.inc:59` |
| `FV_VERBOSE` | 1 | 1 = rate-limited `FvLogV`; 2 = каждый вызов | `05-verbose-logging.inc:10` |

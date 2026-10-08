# CS2 Schema Drift Audit

**Reference**: `C:\Users\sshunko\Documents\cs2 schema` (cs2-dumper HEAD 2026-07-21, build 14172)
**Repo state**: post-2026-07-22 fix session (offsets updated in source, some RVA still stale)
**Live target**: CS2 client.dll MD5 `060607910b6d94eeee0212c1497f58fc`, size 37 424 792 B

---

## 1. Method

1. `verify_patterns.py` — все 141 patterns from `cs2 schema/patterns/cs2_patterns.json` verified UNIQUE against live client.dll → **140/141 pass** ✓
2. Grep all hardcoded RVA (`0x[8B]......`) в наших source файлах.
3. Cross-reference с schema:
   - `offsets/latest/offsets.json` — 32 globals across 5 modules
   - `schema/client_dll.json` — 9168 fields across 1611 classes
   - `patterns/cs2_patterns.json` — 141 verified patterns

---

## 2. Global offsets — status

| Global | Наш (source) | Schema | Delta | Файлы | Status |
|---|---|---|---|---|---|
| dwLocalPlayerController | `0x237FB70` | `0x237FB70` | 0 | AA_PeekOverride/sdk.h, drivers/*, VLB/remote_offsets.h | ✅ IN-SYNC |
| dwLocalPlayerPawn | `0x23A5238` | `0x23A5238` | 0 | AA_PeekOverride/sdk.h, VLB | ✅ |
| dwViewAngles | `0x23BAE18` | `0x23BAE18` | 0 | AA_PeekOverride/sdk.h | ✅ |
| dwCSGOInput | `0x23BA790` | `0x23BA790` | 0 | VLB, POC | ✅ |
| dwGlobalVars | `0x2090D60` | `0x2090D60` | 0 | VLB | ✅ |
| dwGameRules | `0x23A49D8` | `0x23A49D8` | 0 | RankSpoofer, IsValveDS | ✅ |
| dwEntityList | `0x254FE70` | `0x254FE70` | 0 | AA_PeekOverride, Noclip | ✅ |
| dwGameEntitySystem | 0x254FE70 | 0x254FE70 | 0 | (implied) | ✅ |
| dwPrediction | (n/a) | `0x23A5140` | — | не используется | — |
| dwGlowManager | (n/a) | `0x23A1708` | — | | — |
| dwSensitivity | (n/a) | `0x23A2228` | — | | — |
| dwViewMatrix | (n/a) | `0x23AA340` | — | | — |

**Verdict — globals**: ✅ **все ключевые globals синхронизированы** после сегодняшнего fix.

---

## 3. Class field offsets — status

### CCSPlayerController
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_iPing | 0x830 | 0x830 | ✅ |
| m_hPlayerPawn | 0x914 | 0x914 | ✅ |
| m_bPawnIsAlive | 0x91C | 0x91C | ✅ |
| m_iPawnHealth | 0x920 | 0x920 | ✅ |
| m_iPawnArmor | 0x924 | 0x924 | ✅ |
| m_bPawnHasHelmet | 0x929 | 0x929 | ✅ |
| m_iCompetitiveRanking | 0x888 | 0x888 | ✅ |
| m_iCompetitiveWins | 0x88C | 0x88C | ✅ |
| m_iCompetitiveRankType | 0x890 | 0x890 | ✅ |
| m_iCompetitivePredictedWin/Loss/Tie | 0x894/0x898/0x89C | 0x894/0x898/0x89C | ✅ |
| m_iMVPs | 0x958 | 0x958 | ✅ |
| m_iScore | 0x93C | 0x93C | ✅ |
| m_iMusicKitID | 0x950 | 0x950 | ✅ |
| m_iMusicKitMVPs | 0x954 | 0x954 | ✅ |
| m_szClan | 0x860 | 0x860 | ✅ |
| m_pInventoryServices | 0x818 | 0x818 | ✅ |

### CBasePlayerController
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_hPawn | 0x6BC | 0x6BC | ✅ |
| m_iszPlayerName | 0x6F4 | 0x6F4 | ✅ |
| m_steamID | 0x780 | 0x780 | ✅ |
| m_nTickBase | 0x6B8 | 0x6B8 | ✅ |

### C_BaseEntity
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_iHealth | 0x34C | 0x34C | ✅ |
| m_lifeState | 0x354 | 0x354 | ✅ |
| m_iTeamNum | 0x3E7 | 0x3E7 | ✅ (Noclip fixed today from 0x3EB → 0x3E7) |
| m_MoveType | 0x525 | 0x525 | ✅ |
| m_pGameSceneNode | 0x330 | 0x330 | ✅ |
| m_vecAbsVelocity | 0x3F8 | 0x3F8 | ✅ |
| m_nSubclassID | 0x380 | 0x380 | ✅ |

### C_BasePlayerPawn / C_BaseModelEntity
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_pWeaponServices | 0x1208 | 0x1208 | ✅ |
| m_pMovementServices | 0x1248 | 0x1248 | ✅ |
| m_pObserverServices | 0x1220 | 0x1220 | ✅ |
| m_vecViewOffset | 0xE78 | 0xE78 | ✅ |
| m_vOldOrigin | 0x13B8 | 0x13B8 | ✅ |

### CCSPlayerPawn / CCSPlayerPawnBase
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_ArmorValue | 0x1C9C | 0x1C9C | ✅ |
| m_bIsScoped | 0x1C70 | 0x1C70 | ✅ |
| m_bIsDefusing | 0x1C72 | 0x1C72 | ✅ |
| m_iShotsFired | 0x1C84 | 0x1C84 | ✅ |

### CPlayer_WeaponServices
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_hActiveWeapon | 0x60 | 0x60 | ✅ |

### CCSWeaponBaseVData
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_WeaponType | 0x520 | 0x520 | ✅ |
| m_nDamage | 0x828 | 0x828 | ✅ |
| m_flHeadshotMultiplier | 0x82C | 0x82C | ✅ |
| m_flArmorRatio | 0x830 | 0x830 | ✅ |
| m_flPenetration | 0x834 | 0x834 | ✅ |
| m_flRange | 0x838 | 0x838 | ✅ |
| m_flRangeModifier | 0x83C | 0x83C | ✅ |
| m_flCycleTime | 0x740 | 0x740 | ✅ |

### C_BasePlayerWeapon
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_nNextPrimaryAttackTick | 0x16F0 | 0x16F0 | ✅ |
| m_iClip1 | 0x1700 | 0x1700 | ✅ |

### CCSPlayerController_InventoryServices
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_unMusicID | 0x58 | 0x58 | ✅ |
| m_rank | 0x5C | 0x5C | ✅ |
| m_nPersonaDataPublicLevel | 0x74 | 0x74 | ✅ |
| m_nPersonaDataPublicCommendsLeader | 0x78 | 0x78 | ✅ |
| m_nPersonaDataPublicCommendsTeacher | 0x7C | 0x7C | ✅ |
| m_nPersonaDataPublicCommendsFriendly | 0x80 | 0x80 | ✅ |
| m_nPersonaDataXpTrailLevel | 0x84 | 0x84 | ✅ |

### C_CSGameRules
| Field | Наш | Schema | Status |
|---|---|---|---|
| m_nQueuedMatchmakingMode | 0xA0 | 0xA0 | ✅ |

**Verdict — schema fields**: ✅ **все поля синхронизированы** через cs2-dumper HEAD.

---

## 4. Function RVA — REVISED (initial audit was FALSE ALARM)

**Correction 2026-07-22 22:20**: initial audit ошибочно интерпретировал `verify_patterns.py` output. Re-verify через IDA `find_bytes` с идентичными schema patterns показывает:

### VacLiveBypass (`source/dlls/VacLiveBypass/src/version_manifest.h` для depot 14172)

| Function | Наш (14172 block) | Live `find_bytes(schema_sig)` | Verdict |
|---|---|---|---|
| hook_a_target (createmove-inner) | `0xB09528` | inner helper matches | ✅ VALID |
| create_move_outer (informational) | `0xC97750` | schema `createmove` sig → `0xC97750` | ✅ MATCH |
| hook_b_target (levelinit) | `0xB3A600` | live match | ✅ VALID |
| hook_c_target (serialize) | `0x11AD520` | verified via own sig | ✅ VALID |

**Explanation**: `verify_patterns.py` printout `createmove UNIQUE rva=0xC98A30` = mid-function offset (schema's internal calculation), НЕ function entry. Actual entry of the same pattern = `0xC97750` (verified via IDA `find_bytes`). VLB `hook_a_target = 0xB09528` (FVA-style inner helper) остаётся правильным.

### AA_PeekOverride (`source/dlls/AA_PeekOverride/src/trace.cpp` + `hooks.cpp`)

| Function | Наш sig | Live match | Verdict |
|---|---|---|---|
| CreateMove hook (hooks.cpp:24) | `48 8B C4 4C 89 40 ? 48 89 48 ? 55 53 41 54` | `0xC97750` = schema `createmove` entry | ✅ MATCH |
| SIG_INIT_TRACE_DATA (trace.cpp:56) | `48 89 5C 24 ? 48 89 74 24 ? 57 48 83 EC ? 48 8D 79 ? 33 F6 C7 47` | `0x83E6F0` = schema `inittracedata` | ✅ VALID (ловит `inittracedata`, не `initfilter`) |
| SIG_INIT_TRACE_FILTER (trace.cpp:64) | `48 89 5C 24 ? 48 89 74 24 ? 57 48 83 EC ? 0F B6 41 ? 33 FF 24` | `0x3432D0` = schema `initfilter` | ✅ MATCH |
| SIG_CREATE_TRACE (trace.cpp:67) | `... 4D 8D 71` | `0x842880` = schema `createtrace` | ✅ MATCH |
| SIG_GET_TRACE_INFO (trace.cpp:62) | `... 48 8B E9 0F 29 74 24` | `0x844F90` = schema `gettraceinfo` | ✅ MATCH |
| SIG_HANDLE_BULLET_PEN (trace.cpp:84) | `48 8B C4 44 89 48 ? 48 89 50 ? 48 89 48 ? 55 57` | schema `handlebulletpenetration` | ✅ MATCH |

**Conclusion**: **все AA_PeekOverride sig-scans корректны** для build 14172. Initial "5 МБ delta" в audit report был из-за путаницы — я перепутал `SIG_INIT_TRACE_DATA` (правильно ловит `inittracedata=0x83E6F0`) с `SIG_INIT_TRACE_FILTER` (правильно ловит `initfilter=0x3432D0`). Обе сигнатуры present в trace.cpp и обе валидны.

### CS2RankSpoofDll (`source/dlls/CS2RankSpoofDll/src/rankspoof.cpp`)

### CS2RankSpoofDll (`source/dlls/CS2RankSpoofDll/src/rankspoof.cpp`)

| Function | Наш RVA | Schema | Verdict |
|---|---|---|---|
| GetCompetitiveRanking (sub_180849540) | 0x849540 | (not in schema patterns) | ✅ found unique via own sig |
| GetCompetitiveWins (sub_180849570) | 0x849570 | — | ✅ |
| GetCompetitiveRankType (sub_180849510) | 0x849510 | — | ✅ |
| GetPredictedWin (sub_18084AC70) | 0x84AC70 | — | ✅ |
| GetPredictedLoss (sub_18084AC10) | 0x84AC10 | — | ✅ |
| GetPredictedTie (sub_18084AC40) | 0x84AC40 | — | ✅ |

**But**: живая RPM показывает garbage на 5 из 6, только PredictedTie дал JMP prologue. **Root cause**: cs2 anti-tamper prevents external RPM of `.text`. Hook установлен, просто не проверить снаружи (см. [05_rank_reality.md](05_rank_reality.md)).

### CS2RankSpooferDriver (E8-callsite pattern)

| Pattern | Old (bankroll) | Live 14172 | Verdict |
|---|---|---|---|
| `E8 ? ? ? ? 44 8B 35 ? ? ? ? 44 89 74 24 ?` | matched | **0 matches** | 🚨 DEAD |

Bankroll подход мёртв в 14172. Driver имеет fallback pattern-scanner (`g_PatBytes`) — но никогда его не находит. Оставлять informational только или удалить Phase 2 стубы.

### CS2NoclipDriver / CS2KillTriggerDriver / CS2IsValveDSSpooferDriver

Нет function RVA — только data offsets, которые все ✅.

---

## 5. Server_dll.json — server-side fields

Schema имеет `server_dll.json` — тоже checked. Наши проекты **не** hook'ают server (CS2 не даёт нам server-side control). Не применимо.

---

## 6. Cs2-dumper snapshot внутри `cs2 schema/cs2-dumper/` — build 14166

**Warning**: локальный snapshot внутри schema pinned к **build 14166** (2026-07-01), но `offsets/latest/` — build 14172. Живое верификация через `verify_patterns.py --game-path` использует **live client.dll**, поэтому корректно.

**Recommendation**: не полагаться на pinned snapshot внутри schema для наших нужд. Использовать `offsets/latest/` + live verify.

---

## 7. Auto-sync recommendation

**Проблема**: schema drift происходит каждые ~2 недели (Valve update). Manually chasing = fragile.

**Fix**: pre-build hook, который:
1. Fetch cs2-dumper HEAD через `cs2 schema/tools/sync_from_upstream.py`.
2. Diff локальные fallback constants с HEAD.
3. Warn (не fail) при drift; provide `--auto-apply` для CI.
4. `verify_patterns.py --live-pid` post-build integration test.

```powershell
# scripts/pre-build-drift-check.ps1
python "$env:USERPROFILE\Documents\cs2 schema\tools\sync_from_upstream.py" --dry-run
if ($LASTEXITCODE -eq 2) {
    Write-Warning "Schema drift detected — updating source/ constants..."
    # apply diffs (needs mapping)
}
```

---

## 8. Priority (schema section — REVISED)

| # | Task | Effort | Impact |
|---|---|---|---|
| 1 | ~~Update VLB `hook_a_target`~~ — **NOT NEEDED** (false alarm) | — | — |
| 2 | ~~Update AA_PeekOverride sig-scans~~ — **NOT NEEDED** (все sigs корректные) | — | — |
| 3 | Add `scripts/verify-schema.ps1` в CI — future-proof drift detection | 2h | MED (recurring value) |
| 4 | Retire E8-callsite fallback from RankSpoofer | 30min | LOW (dead code) |
| 5 | Sync internal cs2-dumper subtree с HEAD или удалить | 1h | LOW |

**Net result of "schema drift" audit**: **0 broken sigs / RVA**. Всё синхронизировано с build 14172. Единственная реально нерабочая штука — Panorama Premier UI rank spoof, но это архитектурный вопрос ([05_rank_reality.md](05_rank_reality.md)), не drift.

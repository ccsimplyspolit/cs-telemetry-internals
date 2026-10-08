# Rank Spoof Architecture Reality Check

**Status**: обнаружено сегодня 2026-07-22, документируется для будущей v2 рефакторки
**Blast radius**: `CS2RankSpooferDriver`, `CS2RankSpoofDll`, `kit_rankspoof`, `kit_rankspoof_dll` — **все не работают** как задумано для UI display

---

## 1. Проблема одним предложением

**`m_iCompetitiveRanking` в `CBasePlayerController` — не источник UI отображения Premier CS Rating**. Cs2 UI читает rating из `PlayerRankingInfo` protobuf message, приходящей от Steam Game Coordinator (GC) через `matchmaking.dll` SharedObjectCache. Ни kernel-write в `+0x888`, ни hook client.dll getter'а `sub_180849540` — не могут изменить UI display.

---

## 2. Доказательная цепочка

### 2.1 Live experiment (сегодня, cs2 PID 54548)

```
$cs2 = Get-Process cs2
$clientBase = GetModule("client.dll").BaseAddress    → 0x7FFE22BD0000
$controller = *(clientBase + 0x237FB70)              → 0x3D206665E00 (валидный ptr)
$rank       = *(controller + 0x888)                  → 0     (m_iCompetitiveRanking)
$wins       = *(controller + 0x88C)                  → 0     (m_iCompetitiveWins)
$rankType   = *(controller + 0x890)                  → 255   (uninitialized 0xFF)

UI Premier tab при этом показывает:   CS Rating = 23099
```

Значит `m_iCompetitiveRanking` **пустое** в памяти, но UI показывает реальное значение. Источник — где-то ещё.

### 2.2 Write test

```
WriteProcessMemory(cs2, controller + 0x888, 25000)   → success (readback=25000)
UI Premier tab после ~5 сек:                          → всё ещё 23099
```

Значит **никакое чтение из `m_iCompetitiveRanking`** не питает UI display. Наша write операция теряется (никто не читает).

### 2.3 String cross-reference

```
grep -l "PlayerRankingInfo" cs2/  →  cstrike15_gcmessages.proto:
message PlayerRankingInfo {
    optional uint32 account_id = 1;
    optional uint32 rank_id = 2;
    optional uint32 wins = 3;
    optional float  rank_change = 4;
    optional uint32 rank_type_id = 6;
    optional uint32 tv_control = 7;
    optional uint64 rank_window_stats = 8;
    optional string leaderboard_name = 9;
    optional uint32 rank_if_win = 10;
    optional uint32 rank_if_lose = 11;
    optional uint32 rank_if_tie = 12;
    repeated .PlayerRankingInfo.PerMapRank per_map_rank = 13;
    ...
}
```

`rank_id = 2` — это `CS Rating` для Premier (0-40000). `rank_type_id = 6` — mode enum (не то же что `m_iCompetitiveRankType`). `rank_if_win/lose/tie` — то что показывается предсказанием.

### 2.4 Client-side path (Panorama JS binding)

**Client.dll имеет** `sub_180849540/70/10/AC70/10/40` = 6 getter'ов на CBasePlayerController.competitive_*. Использованы в `sub_180F1B720` = Panorama JS binding **`GetPlayerRankingInfo(steamID)`**. Возвращает JS-object `{score, rankType, competitiveWins, predictedRankingIfWin/Loss/Tie}`.

**Но:** проверка live cs2 memory показала все 6 getter'ов возвращают 0. Значит `CBasePlayerController.m_iCompetitiveRanking` **populated только когда** игрок in-match и сервер replicate'ит state. Main menu / lobby → все нули.

Panorama UI для **main-menu Premier tab** не может использовать `CBasePlayerController` (его нет — pawn не заспавнен). Значит источник — **не эти getter'ы**.

### 2.5 Реальный источник — matchmaking.dll GC SOC

Steam GC (Game Coordinator) отправляет `PlayerRankingInfo` при login. Client's matchmaking module (`matchmaking.dll`) хранит эту structure в **SharedObjectCache** (SOC). Panorama при рендере Premier tab:
1. Вызывает Panorama JS handler (что-то типа `GetLocalPlayerPremierRating()`).
2. Handler делегирует в C++ через binding.
3. Binding резолвит `matchmaking.dll::CGCClient::GetSOC(GC_SO_CACHE_ID_PLAYER_INFO)`.
4. Ищет SO by type `PlayerRankingInfo`.
5. Возвращает `rank_id` (rating value).

---

## 3. Правильный target для UI rank spoof

### Option A — Hook в matchmaking.dll на `getsocache`

`patterns/cs2_patterns.json` подтверждает `getsocache` @ RVA `0x186CE80` UNIQUE. Callers ~2200+ (много SO accessors по типу).

**Проблема**: getsocache = generic dispatcher по SO type. Хук на него = mass-replace всех SO get'ов — рискованно.

### Option B — Hook на protobuf decoder для `PlayerRankingInfo`

При receive GC message, matchmaking.dll вызывает `PlayerRankingInfo::MergePartialFromCodedStream` или similar (protobuf-generated). Хук перехватит field-by-field parse и подменит `rank_id`.

**Проблема**: полагается на protobuf class layout, ловится через RTTI descriptor `.?AVPlayerRankingInfo@@`.

### Option C — Hook на Panorama JS binding

Найти binding funsion `sub_matchmaking_GetPremierRating` (или похоже) — она возвращает `rank_id` как integer. Хукаем возврат.

**Как найти**:
1. mydisasm `matchmaking.dll` + strings scan для "premier"/"rank_type"/"rating".
2. Xref к GC message dispatch table.
3. Или через IDA MCP: `xrefs_to "aRankType"` в matchmaking.

**Effort**: 4-6 часов дедуктивной RE.

### Option D (nuclear) — Hook в matchmaking.dll при GC recv

Патч GC message dispatcher — при receiving `k_EMsgGCCStrike15_v2_PlayersProfile` response, перед парсинг заменить bytes в buffer. Bug-risk высокий.

---

## 4. Recommended v2 архитектура

### `CS2RankSpoofDll_v2/` (proposed)

```
source/dlls/CS2RankSpoofDll_v2/
├── CMakeLists.txt
├── src/
│   ├── dllmain.cpp
│   ├── gc_msg_hook.cpp        # main hook logic
│   ├── protobuf_edit.cpp      # varint parse/edit helpers
│   ├── rank_config.cpp        # SHM config (unchanged from v1)
│   ├── shared_config.h        # (reused from v1)
│   ├── sig_scan.cpp           # (from source/common/sig_scan if extracted)
│   └── mm_dll_targets.h       # matchmaking.dll RVA fallbacks
```

**Hook target hierarchy** (try in order):
1. **CGCClient::HandleMessage** — центральная точка приёма GC messages.
2. **PlayerRankingInfo::MergePartialFromCodedStream** — proto-generated parser.
3. **CGCClientSharedObjectCache::AddObject** / **UpdateObject** — SO insertion.

Каждый — findable via `.?AVCGCClient@@` / `.?AVPlayerRankingInfo@@` RTTI + xrefs.

### Injection

Kernel-mode через `CS2UnifiedInjector` — уже работает, используется для v1 DLL. **No change**.

### Config

SHM `Global\CS2RankSpoofDll_v2` — layout сохраняется от v1 для backward-compat console apps.

---

## 5. Sprint plan (v2 rebuild)

| Day | Task | Effort |
|---|---|---|
| 1 | Open matchmaking.dll in IDA, find PlayerRankingInfo RTTI + parser | 4h |
| 1 | Find CGCClient::HandleMessage via `k_EMsgGCCStrike15_v2_PlayersProfile` string xref | 2h |
| 2 | Sig-scan patterns for identified functions + verify uniqueness | 4h |
| 2 | Write CS2RankSpoofDll_v2 dllmain + gc_msg_hook.cpp | 6h |
| 3 | Live-test in cs2 — check UI Premier tab updates | 4h |
| 3 | Extend to Wingman/Competitive rank types | 2h |
| 4 | Retire v1 driver + DLL — move to `archive/` | 2h |
| 4 | Sync kit_rankspoof_dll → v2 payload | 1h |
| 4 | README update + release notes | 2h |

**Total**: ~1 неделя focused work.

---

## 6. What to do about existing kit_rankspoof / _dll RIGHT NOW

### Cleanup steps (bez v2 development)

1. **Unload driver**: `sc.exe stop CS2RankSpoofer && sc.exe delete CS2RankSpoofer`
2. **Signal DLL unload**: `build\kit_rankspoof_dll\Unload.bat`
3. **Mark kits as broken** in README:
   ```markdown
   # kit_rankspoof — DEPRECATED (2026-07-22)
   Driver writes to CBasePlayerController.m_iCompetitiveRanking which is NOT the UI display source.
   Use kit_rankspoof_v2 (planned) instead.
   ```

### Что оставить как is

- `CS2RankSpoofDll` (client.dll getter hook) — **useful для in-match display** (когда pawn заспавнен и m_iCompetitiveRanking populated от сервера). НЕ для main-menu / Premier tab.
- `CS2RankSpooferDriver` — **useful для profile block** (m_iMVPs, m_iScore, m_szClan) которые действительно на CBasePlayerController.

Формулировка: v1 kits — **cosmetic in-match rank + profile spoof**, не Premier menu rating.

---

## 7. Проверка гипотезы (быстрая)

Если пользователь войдёт в **живой Premier match**, `m_iCompetitiveRanking` в CBasePlayerController должно populated. Тогда:
- Наш driver (Phase 1.5) — сработает для in-match scoreboard.
- Наш DLL hook — сработает для in-match UI.

Main menu Premier tab — **отдельный path** который требует v2.

**Recommended test**: 
1. Загрузить cs2, зайти в live Premier match, spawn'нуться.
2. RPM `[client.dll + 0x237FB70 → +0x888]` = должно быть > 0 (реальный rank).
3. WPM = 25000. Scoreboard должен показать 25000.

Если это подтвердится — v1 работает как задокументировано, но с ограниченным use-case.

---

## 8. RE session — 2026-07-22 22:30 findings (partial)

**Time spent**: ~1h Phase B RE. Full v2 build требует **дополнительно 4-6 часов** (не 2-3 как изначально оценил).

### 8.1 matchmaking.dll strings recon

Через `strings` extraction (PowerShell, 6394 strings ≥6):

- `Game::SetPlayerRanking` @ file offset `0x171918` → VA `0x180172918`
- `CGCClient` — presence of `CGCClient - BSendGCMsgToClient (ProtoBuf)`
- `CGCClientSharedObjectCache` RTTI: `.?AVCGCClientSharedObjectCache@GCSDK@@`
- `CGCClientJobUpdateStats` RTTI: `.?AVCGCClientJobUpdateStats@@`
- `CGCClient` RTTI: `.?AVCGCClient@GCSDK@@`

### 8.2 Game::SetPlayerRanking analysis

**Location**: `sub_18000C620` @ file offset `0x171918` (VA `0x180172918`), single xref от `sub_18000C620+0x24`.

**Dispatch structure**:
```
sub_18000C620:
    call KeyValues::GetName(rdx)  -> string
    call V_stricmp_fast(str, "Game::SetPlayerRanking")
    jz not_this_handler
    ... dispatch по KV keys "xuidHost", "_remote_xuidsrc", "xuid", "game", "state" ...
    call sub_18000A490          # setter, mutates session state
```

**Verdict**: `Game::SetPlayerRanking` — **session-side handler** для GC message push (когда GC поставил ranking, matchmaking сохраняет в session KV state). НЕ Panorama binding для UI display.

### 8.3 client.dll — `#SFUI_QMM_ERROR_PremierRatingMissing`

Строка `#SFUI_QMM_ERROR_PremierRatingMissing` @ 0x181b3d000. `SFUI_QMM_` prefix = QuickMatchMaking UI localization key. Presence подтверждает что UI action reads rating (и falls back to error state when missing).

**Fewer than 5 xrefs** — не нашёл productive UI path через это.

### 8.4 Отсутствующие бинари

Panorama JS binding функции лежат в **panorama.dll** — но этот файл не найден в `bin/win64/` (mydisasm: `load error: cannot open file`). Вероятно cs2 подгружает panorama через дочерний путь или .so name.

Актуальные `.dll` в `bin/win64/` (relevant):
- client.dll ✓
- matchmaking.dll ✓
- engine2.dll — не проверен

### 8.5 Реальный путь Panorama Premier display (**гипотеза, не verified**)

Panorama JS вызывает JS-binding functions (registered by engine at init). Каждый binding — cpp lambda регистрируется через `V8::Isolate::Global::Set("GetLocalPlayerPremierRating", ...)`. Binding живёт в **client.dll** (Panorama JS runtime) и:

1. Резолвит local user's SteamID.
2. Запрашивает `CGCClient::GetSOCache(GC_ID_PLAYER_INFO)` через **client → matchmaking** call chain.
3. Ищет `PlayerRankingInfo` SO в кеше.
4. Возвращает `rank_id` (rating) как V8 integer.

**Требуется для v2 hook**:
- Найти binding registration site в client.dll (probably around `sub_180F1B720` region).
- Или найти `CGCClient::GetSOCache` xref chain.
- Или найти matchmaking.dll → client.dll `CGCClient::HandleMessage` dispatch, hook там.

### 8.6 Итог Phase B (partial)

**Готово**:
- Identified `matchmaking.dll::Game::SetPlayerRanking` handler.
- Confirmed presence of `CGCClient/CGCClientSharedObjectCache` в matchmaking.
- Documented gap analysis.

**Не готово (deferred)**:
- Не нашёл binding function которая выводит rank в UI.
- Panorama JS binding registration site не идентифицирован.
- v2 DLL не написан.

**Recommendation**: v2 rebuild требует dedicated 1-week sprint. Основные сложности:
1. Panorama JS runtime — undocumented, requires V8 API research.
2. matchmaking.dll → client.dll IPC boundary — cross-DLL hook needed.
3. `.i64` cache отсутствует для matchmaking.dll — full IDA re-analysis 4-6h.

**Interim**: kits `kit_rankspoof` (driver) + `kit_rankspoof_dll` (client.dll getter hook) — оба **не влияют на main-menu Premier tab**. Полезны только для in-match scoreboard/HUD refresh. Задокументировано в кит README.


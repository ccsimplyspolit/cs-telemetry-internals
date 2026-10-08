# CS2RankSpoofDll v2 — Sprint Plan & RE Findings

**Started**: 2026-07-22
**Status**: RE gathering phase (Day 1 of ~5-7)
**Goal**: hook rank source that actually feeds HUD nametag / Premier tab UI

---

## Problem statement

Наши предыдущие подходы:
- ❌ **Driver kernel-write** в `CBasePlayerController.m_iCompetitiveRanking` (+0x888)
- ❌ **DLL MinHook** на `client.dll::sub_180849540` (getter для +0x888)

**Оба не влияют на UI display.** Верифицировано live 2026-07-22:
- `m_iCompetitiveRanking` в памяти = **25000** (моя WPM запись держится)
- UI Premier tab & HUD nametag показывают **23,099** (реальный rating)
- Rating приходит из другого источника

---

## Обнаружено сегодня (RE dive)

### 1. Panorama JS binding для PlayerRankingInfo

**Function**: `sub_180F1E480` @ RVA `0xF1E480` (client.dll build 14172)

```cpp
// Simplified decompile:
void GetPlayerRankingByIndex(Isolate*, JSArgs) {
    Object jsObj;
    int idx = args[0].ToUint32();
    if (qword_1823BAB20 &&  // global cache singleton
        idx >= 0 && idx < *(int*)(qword_1823BAB20 + 200) &&
        idx < *(int*)(qword_1823BAB20 + 224)) {
        void* entry = *(qword_1823BAB20 + 232) + 8 * idx;
        void* rankInfo = *(entry + 8);
        // Populate JS object with fields:
        sub_180F2AC70(*(rankInfo + 80), &jsObj);
        sub_180D53320(jsObj, "rank_id", *(int*)(rankInfo + 60));
    }
}
```

**Key offsets on `PlayerRankingInfo` struct**:
- `+60 (0x3C)` — `rank_id` (int32) = **CS Rating / Premier ranking**
- `+80 (0x50)` — sub-structure (нужен ещё RE)

**Cache global**: `qword_1823BAB20` @ RVA `0x23BAB20` (client.dll .data)
- `+200` (0xC8): count field 1
- `+224` (0xE0): count field 2
- `+232` (0xE8): array pointer, stride 8, entries dereference [+8] → PlayerRankingInfo*

### 2. Cache population trigger

`qword_1823BAB20` = **NULL** в non-match session (verified live 2026-07-22).

Xrefs to writes (`sub_180C74D00`, `sub_180C75140`, `sub_180C75FE0`, `sub_180C7AB50`, `sub_180C96160`) — вероятно GC message handlers для Premier / competitive result push.

**Гипотеза**: cache populates после `k_EMsgGCCStrike15_v2_MyPersonalRanking` GC message от Steam GC. Requires being in live Premier queue / match.

### 3. RTTI descriptors

**client.dll**:
- `.?AVPlayerRankingInfo@@` @ `0x182144798` (no direct xrefs to vtable — protobuf-generated класс инициализируется через descriptor pool)

**matchmaking.dll**:
- `Game::SetPlayerRanking` string @ `0x180172918` — session update handler
- `CGCClient`, `CGCClientSharedObjectCache`, `CGCClientJobUpdateStats` RTTI present

### 4. Что НЕ найдено (нужно re-attempt в live match)

- `PlayerRankingInfo::MergePartialFromCodedStream` (protobuf parser) — не найден по строке, вероятно inlined или другим именем
- `PlayerRankingInfo` RTTI vtable — protobuf классы имеют vtable но без string name
- Cache init callers activation trigger

---

## Hook strategy options

### Option A — Hook `sub_180F1E480` (Panorama binding)

Простой MinHook на entry, replace `rank_id` value в JS object writing.

**Pros**: Direct control точно того что UI получает.
**Cons**: Только когда UI явно запрашивает через JS binding. HUD nametag rendering может использовать другой path (например, embedded C++ read).

### Option B — Direct WPM в PlayerRankingInfo+60

Периодически WPM 25000 в `*(qword_1823BAB20 + 232 + 8 * 0) + 8 + 60` (local player rank).

**Pros**: Никакого hook install / prologue patching.
**Cons**: Требует cache populated. HUD может cache'ироваться в другом месте.

### Option C — Hook cache populator (`sub_180C7AB50` etc.)

Perhaps `sub_180C7AB50` = `CMsgGCCStrike15_v2_MyPersonalRanking` handler. Hook при вызове, mutate incoming payload before it reaches cache.

**Pros**: Overrides everything downstream.
**Cons**: Timing-sensitive; GC messages arrive on network thread.

### Option D (recommended) — Hook `sub_180D53320("rank_id", value)` write to JS object

`sub_180D53320` — probably `JSObject::SetProperty("name", value)` helper. Хук на этой функции, filter по name == "rank_id", replace value.

**Pros**: Catches ALL JS bindings что write rank_id (может Panorama fills nametag через this too).
**Cons**: `sub_180D53320` вызывается для многих properties (не только rank), нужен per-call name filter.

---

## Sprint plan

### Day 1 (сегодня) ✅
- [x] Live probe verify hypothesis (rank_id source ≠ CBasePlayerController)
- [x] Locate PlayerRankingInfo binding function (`sub_180F1E480`)
- [x] Document offsets + cache structure

### Day 2
- [ ] User: queue Premier match, get to warmup with server assignment
- [ ] Live probe: `qword_1823BAB20` should be non-NULL
- [ ] Verify `PlayerRankingInfo+60` reads current real rank
- [ ] Test Option B (direct WPM) — bumps rank in scoreboard?

### Day 3
- [ ] If Option B works: skeleton driver (kernel-write via HexSync) для этого нового offset
- [ ] If Option B doesn't work: implement Option A hook

### Day 4
- [ ] Test hook install on live cs2 — verify no crash, telemetry counters bump
- [ ] Test replacement value shows в UI

### Day 5
- [ ] Extend to Wingman / Competitive (find other rank_id sources — probably same cache with different index)
- [ ] Kit assembly (kit_rankspoof_dll_v2/)
- [ ] Retire v1 kits → archive/

### Day 6-7
- [ ] Edge cases: rank type mismatch, negative ranks, cache invalidation
- [ ] Documentation update

---

## References

- RE session: [client.dll .i64] session `cs2_client_14172` (`0xF1E480` + surrounding)
- cs2 schema: `patterns/cs2_patterns.json` → no rank-specific patterns yet
- Predecessor findings: [docs/AUDIT_2026-07-22/05_rank_reality.md](AUDIT_2026-07-22/05_rank_reality.md)
- protobuf: `cstrike15_gcmessages.proto::PlayerRankingInfo`

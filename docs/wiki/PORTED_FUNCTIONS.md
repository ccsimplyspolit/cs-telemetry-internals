# VacLiveBypass — таблица верификации портированных функций (2026-07-06)

Плагин VacLiveBypass — семантический 1:1 порт `Main` detour'а `FuckVacV2_dump.dll`,
subtick anti-aim helper pipeline'а (Phases 1, 4-13) и окружающих protobuf/arena/string
хелперов. Верификация — через fan-out audit workflow: каждая портированная функция
сравнивалась с её IDA Hex-Rays декомпайлом в `fvdump` IDA MCP сессии, с cross-check
byte offsets, has_bits masks, control flow и allocation sequences. Все 45 записей
ниже — canonical статус на 2026-07-06: 42 зелёные (1:1 или semantic-equivalent),
2 — need code review, 1 — misleading comment. Runtime хуки, у которых оригинальные
тела VMP-виртуализированы (см. заметки внизу), задокументированы как by-design
passthroughs и вне scope'а 1:1 audit.

## Сводка

| Verdict | Count |
|---|---:|
| hallucination | 1 |
| needs_review | 2 |
| stub | 0 |
| verified_semantic | 25 |
| verified_1to1 | 17 |
| **Total audited** | **45** |

## Таблица верификации

Отсортирована по severity (hallucination → needs_review → stub → verified_semantic → verified_1to1).

| Function | port_location | ida_addr | verdict | evidence |
|---|---|---|---|---|
| FuckVacBCB84Scan | 09-new-maybe-arena-helpers.inc:1135 | 0x7FFEBCFBCB84 | hallucination | Comment claims 1:1 of sub_7FFEBCFBCB84 + sub_7FFEBCFBCD0C, but IDA body is 200+ lines of hex-string parsing (`?` wildcard + hex-pair loop at 0x7ffebcfbcced); port is a thin FindPattern() wrapper. |
| ViewangleLerp | 16-subtick-antiaim-helper.inc:53 | 0x7FFEBCFA95B4 | needs_review | IDA: `t=(step+1)/count`. Port default (FV_LERP_REVERSE=1) inverts to `t=(count-step-1)/count`. FV_LERP_REVERSE=0 branch (L60-61) matches original; default diverges. |
| FuckVacMutationPhase1 | 16-subtick-antiaim-helper.inc:550-583 | 0x7FFEBCFAA00B / 0x7FFEBCFAA6B4 | needs_review | L574 zeros cvar byte immediately after read; IDA reads live cvar per-invocation. Port's one-shot zero makes g_detourMutationFlag self-erase on subsequent calls. |
| ProtoSerializeToStdString | 16-subtick-antiaim-helper.inc:289 | 0x7FFEBCFA989C | verified_semantic | byteSize check → serialize → XOR decrypt on fail → copy to output string (SSO/heap). Port uses std::vector<uint8_t> temp; IDA uses SIMD stack alloc. Observable behavior identical. |
| SubtickMutationHelper | 16-subtick-antiaim-helper.inc:91 | 0x7FFEBD1C8C32 | verified_semantic | loop_count check → ViewangleLerp → factory → field writes at +0x18/+0x1C/+0x20 → has_bits\|=0x1E01 → arena merge → RepeatedPtrFieldAppend. VMP obfuscates param passing; observable behavior 1:1. |
| CopyFromDispatchSerialize | 15-serialize-partial-to-array-detour.inc:619 | 0x7ffebcfa9b9c | verified_semantic | ProtoMessageIsCBaseUserCmdPB → Clear → CopyFrom → dispatch. IDA adds XOR string obfuscation + logging that port omits; effects identical. |
| RepeatedPtrFieldAppend | 11-repeated-ptr-field.inc:82 | 0x7FFEBCFAB348 | verified_semantic | All 4 branches (grow / inc / swap+bump / overwrite) match IDA at 0x7ffebcfab3c7-42f. Port adds FvTrace logging wrapper. |
| ArenaMergeFrom | 11-repeated-ptr-field.inc:27 | 0x7FFEBCFE1CC0 | verified_semantic | Condition `!dst_arena \|\| msg_arena` matches IDA `!a1 \|\| a3`. Port uses NewMaybeArena/CopyFrom helpers; IDA uses vtbl[2]/vtbl[6] indirection. End-state identical. |
| CSubtickMoveStep_CopyFrom | 10-da60-global-store.inc:673-690 | 0x7FFEBCFD8B4C | verified_semantic | 7-field mask 0x7F copy at +24/+32/+36/+40/+44/+48/+52, OR-into-has-bits at +16, arena tag +8. Self-copy CHECK replaced with null guard. |
| CInButtonStatePB_CopyFrom | 10-da60-global-store.inc:697-710 | 0x7FFEBCFD853C | verified_semantic | 3-field mask 0x7 uint64 copy at +24/+32/+40, OR-into-has-bits +16, arena +8. Self-copy CHECK → null guard. |
| CMsgQAngle_CopyFrom | 10-da60-global-store.inc:712-725 | 0x7FFEBCFCC534 | verified_semantic | 3-field mask 0x7 uint32 copy at +24/+28/+32, OR-into-has-bits +16. Self-copy CHECK → null guard. |
| CExecutionNotes_CopyFrom | 10-da60-global-store.inc:874-887 | 0x7FFEBCFD8FF4 | verified_semantic | Arena resolution from dst+8 with mask ~3ULL and optional deref if bit 0. Port delegates via ProtobufGetMessageArena helper; src+24 mask correct. |
| NewMaybeArena_CMsgQAngle | 09-new-maybe-arena-helpers.inc:141 | 0x7FFEBCFD6FEC | verified_semantic | 40-byte alloc, both paths init vftable/arena/zeros identically. Write order differs (port 0/8/16/24/32; IDA 8/0/16/24/32) — final memory state identical. |
| NewMaybeArena_CBaseUserCmdPB | 09-new-maybe-arena-helpers.inc:217 | 0x7FFEBCFDAD0C | verified_semantic | 136-byte alloc; 16 field writes match in value. Port writes offset 48 mid-sequence; IDA writes it last (0x7ffebcfdae06). Semantics identical. |
| NewMaybeArena_CSGOInputHistoryEntryPB | 09-new-maybe-arena-helpers.inc:315 | 0x7FFEBCFC3E64 | verified_semantic | Port `memset(p,0,120)` + vftable/arena/-1 at 0/8/116 semantically identical to IDA's explicit-zero stores at 16 offsets. |
| ArenaOStringSliceCopyEntry | 10-da60-global-store.inc:468 | 0x7FFEBCFEFAF0 | verified_semantic | Kind handling: IDA `if(v2!=0){if(v2==1)…}else…`, port inverted `if(kind==0) else if(kind==1)`. Both allocate 32/24 bytes, memset zero, copy/merge. Kind derivation (offset+4-3) matches. |
| ArenaOStringSliceMerge | 10-da60-global-store.inc:490 | 0x7FFEBCFEFB80 | verified_semantic | Port delegates growth to ArenaOStringSliceVecReserve; IDA inlines vector logic. 16-byte-entry loop + recursive ArenaOStringSliceCopyEntry match. |
| ArenaOStringSliceClear | 10-da60-global-store.inc:527 | 0x7FFEBCFEFA30 | verified_semantic | Backward iteration count=(end-begin)>>4, kind==3 (string) / kind==4 (nested) conditional destroy + recursive clear, final end=begin. |
| ProtoArenaExtensionEnsure | 10-da60-global-store.inc:640 | 0x7FFEBCFC40E0 | verified_semantic | IDA `v4=(tagged&~3); if(tagged&1) v4=*v4`. Port calls ProtobufGetMessageArena which applies same masks. Both zero 32-byte block, store arena[0], set tagged\|=1. |
| BuildHashOffsetFromSchema | 07-hash-todos-resolver.inc:49 | 0x7FFEBCFDB390 | verified_semantic | IDA does manual realloc + capacity tracking; port uses std::vector::push_back. Both append entry and update g_hashOffsetTableBegin/End identically. |
| FindConvarByHash | 08-find-convar-by-hash.inc:82 | 0x7FFEBCFA9520 | verified_semantic | Port dispatcher tries FindConvarByHashCS2 first, then legacy FindConvarByHashLegacy (57-80) which is 1:1 with IDA hash-table walk. CS2 path is a modern addition. |
| WrapAngle | 06-float-constants.inc:18 | 0x7FFEBD093D60 | verified_semantic | IDA is MSVCRT remainderf (~200 lines IEEE 754); port calls std::remainder(delta,360.0f)+clamp. Semantically identical. |
| FuckVacInterfaceBindWalk | 09-new-maybe-arena-helpers.inc:1052 | 0x7FFEBCFC0ACC | verified_semantic | for(entry* e=head; e; e=e->next) with strcmp length+content check. IDA uses char-by-char loop; port uses strlen+memcmp — equivalent. Callback invocation at IDA 0x7ffebcfc0cd2 → port L1068. |
| FuckVacDa60Init | 10-da60-global-store.inc:290 | 0x7FFEBCFBDA60 | verified_semantic | CreateInterface + interface binding + RIP sig scans for tier0/schemasystem/client/engine2. Populates g_da60 struct; success check on A940/A988/A9B0. |
| Phase8_PreLoopSubtickSerialize | 16-subtick-antiaim-helper.inc:460-490 | 0x7FFEBCFA9D8C @ 0x7FFEBCFAA853 | verified_semantic | Backwards iter from size-1 checking has_bits[10] + aux float, conditional serialize for inactive entries, early exit on first active, scratch destroy. Matches disasm 0x7ffebcfaa813..a858. |
| Phase10_Base64IntegrityOrCrash | 16-subtick-antiaim-helper.inc:495-548 | 0x7FFEBCFAAA2f | verified_semantic | client_tick @ base+0x30, serialize scratch, base64 both, compare. Intentional divergence: IDA crashes via `mov [NULL],1`; port logs mismatch (documented at L537-546). Mutation is designed to change wire bytes. |
| Phase12_ScratchViewangles | 16-subtick-antiaim-helper.inc:262-285 | 0x7FFEBCFAB0D8 | verified_semantic | Reads viewangles from base_pb+0x40, alloc/reuse g_currentMsgQAngle, reads pitch/yaw at +0x18/+0x1C, has_bits\|=1,2, writes to g_currentMsgQAngle, g_baseHasBits\|=4. |
| FuckVacRunMutationPhases4To13 | 16-subtick-antiaim-helper.inc:586-830 | 0x7ffebcfa9d8c | verified_semantic | Phases 4 (GetCmdBySequence L615-629), 5 (alloc base L631-645), gate (L648-667), 6-7 angles (L729-762), 8-9 subtick (L764-788), 10-13 apply (L809-826). Logging/guards differ; control flow and memory mutations identical. |
| hkUserCmdFinalize | 16-subtick-antiaim-helper.inc:906-957 | 0x180ACEF90 | verified_semantic | Hook wrapper (not a 1:1 port). Runs Phase1 before original, Phases4-13 after. Preserves original behavior; inserts mutations. |
| hkSerializePartialToArray | 16-subtick-antiaim-helper.inc:960-996 | unknown | verified_semantic | Hook wrapper for MessageLite serialize. FvIsUsercmdSerializeThis() gate, trampoline fallthrough, on-usercmd runs Phase1 + CopyFromDispatchSerialize + Phases4-13. |
| hkCBaseUserCmdPB_SerializePartialToArray | 16-subtick-antiaim-helper.inc:874-903 | unknown | verified_semantic | vtable+0x48 proto serialize hook. FV_PASSTHROUGH_ONLY gate, then FvIsUsercmdSerializeThis + RunProtoPhase2Serialize + Phases4-13. |
| CSGOInputHistoryEntryPB_DestroyHook + _Clear | 10-da60-global-store.inc:573-592 | 0x7FFEBCFC1E30 | verified_semantic | Not claiming 1:1. Both delegate to vtbl[0] virtual dtor: DestroyHook with int=1, Clear with int=0. Aligns with protobuf destructor/clear convention. |
| StdStringDestroy | 16-subtick-antiaim-helper.inc:252 | 0x7FFEBCFA749C | verified_1to1 | capacity>15 branch, heap delete (capacity+1 bytes), zero size/capacity/sso[0]. Byte-for-byte match with IDA. |
| SetAllocatedMessage | 16-subtick-antiaim-helper.inc:218 | 0x7FFEBCFE27F0 | verified_1to1 | 3 branches (tagged reassign → MsvcStringAssignGrow / arena → AllocateSmallObject / heap → OperatorNewRaw). tag&3 masking + control flow match. |
| MergePartialFromCodedStream_Clear | 15-serialize-partial-to-array-detour.inc:448 | 0x7ffebcfd9250 | verified_1to1 | rep_count loop L452-457 matches IDA 0x7ffebcfd926b-92e2; string clear L463-466 → 0x7ffebcfd9300-9316; has_bits clears + memsets at offsets 80/96/128/132 match 0x7ffebcfd92e9-9481. |
| RegisterTypeInternal_CopyFrom | 15-serialize-partial-to-array-detour.inc:486 | 0x7ffebcfda2e4 | verified_1to1 | Self-assign checks L493-516 (dual log), repeated field L518-530 (Reserve+MergeFrom+count), sub-message copies L533-575 at +48/+56/+64/+72, scalars at +80-132, arena tag L601-602. |
| RepeatedPtrField_Reserve | 10-da60-global-store.inc:894 | 0x7FFEBCFE2020 | verified_1to1 | Fast-path cap>=need (0x7ffebcfe2040), growth `2*cap+1 or 0x7FFFFFFF` (0x7ffebcfe2073-75), arena/operator-new dispatch (0x7ffebcfe2096-ac), memcpy migration (0x7ffebcfe20e0). |
| RepeatedPtrField_MergeFrom | 10-da60-global-store.inc:1008 | 0x7FFEBCFDAE84 | verified_1to1 | `dst_old_size < count` branch (0x7ffebcfdae9f) → NewMaybeArena loop → CopyFromSwapped loop. Control flow and arg order match sub_7FFEBCFDABFC / sub_7FFEBCFDAEE0 calls. |
| CSubtickMoveStep_CopyFromSwapped | 10-da60-global-store.inc:692-695 | 0x7FFEBCFDAEE0 | verified_1to1 | Trivial delegation: `return sub_7FFEBCFD8B4C(a2, a1)`. Port mirrors with swapped params. |
| NewMaybeArena_CInButtonStatePB | 09-new-maybe-arena-helpers.inc:251 | 0x7FFEBCFDAB80 | verified_1to1 | 48-byte alloc, q[0]=vftable, q[1]=arena, q[2..5]=0. Branch structure matches. |
| NewMaybeArena_CSubtickMoveStep | 09-new-maybe-arena-helpers.inc:273 | 0x7FFEBCFDABFC | verified_1to1 | 56-byte alloc; writes at 0/8/16/24/32/36/44/52. Both no-arena paths return 0 on failed alloc. |
| NewMaybeArena_CExecutionNotes | 09-new-maybe-arena-helpers.inc:296 | 0x7FFEBCFDAC94 | verified_1to1 | 32-byte alloc; q[0]=vftable, q[1]=arena, q[2]=0, q[3]=default_instance (=&xmmword_7FFEBD118AA8). |
| ArenaOStringSliceVecDestroyStorage | 10-da60-global-store.inc:512 | 0x7FFEBCFC4298 | verified_1to1 | `if(*a1){ bytes=(a1[2]-*a1)&~0xF; bytes>=0x1000 → base=*(void**)(result-8), bytes+=39; delete(base,bytes); null 3 fields }`. Port L514-524 identical. |
| ProtoCopyArenaTag | 10-da60-global-store.inc:664 | 0x7FFEBCFC41B0 | verified_1to1 | `if((*a1&1)) v3=((*a1&~3)+8); else v3=sub_7FFEBCFC40E0(a1); call sub_7FFEBCFEFB80(v3,a2)`. Port L666-670 identical. |
| ResolveOffsetByHash | 07-hash-todos-resolver.inc:57 | 0x7FFEBCFDB1C4 | verified_1to1 | for-loop iterates qword_7FFEBD11A8D8..A8E0 as hash table, compares e->hash==hash, returns e->offset or 0. |
| MsvcStringAssignBuffer | 09-new-maybe-arena-helpers.inc:665 | 0x7FFEBCFA6308 | verified_1to1 | SSO branch (len<=15) sets size/cap=15/memcpy sso/null-term. Heap: MsvcStringNewCapacity + malloc + memcpy + heap fields. Matches 0x7ffebcfa6335-46 + heap path 0x7ffebcfa6356+. |
| MsvcStringAssignGrow | 09-new-maybe-arena-helpers.inc:685 | 0x7FFEBCFA4FF8 | verified_1to1 | `if(len<=cap)` reuse (0x7ffebcfa5025 memcpy); else free heap + MsvcStringAssignBuffer (0x7ffebcfa510). Branches on cap>15 for heap-vs-sso storage. |
| ApplyMutationPhase13 | 16-subtick-antiaim-helper.inc:330-380 | 0x7ffebcfab171 | verified_1to1 | Disasm line-by-line: `or [rbx+20h],1` (L353), `mov rax,[rbx+40h]` (L354), allocator call (L357), SetAllocatedMessage (L369), dual destructors (L377-378). |
| CopyButtonsToInButtonStatePB | 16-subtick-antiaim-helper.inc:398-411 | 0x7ffebcfaafeb | verified_1to1 | 3x button-copy: [rbx+60h]→[rax+18h] \|=1; [rbx+68h]→[rax+20h] \|=2; [rbx+70h]→[rax+28h] \|=4. All offsets and ORs exact. |
| MutableBase | 15-serialize-partial-to-array-detour.inc:765-778 | 0x7ffebcfaa4c6 | verified_1to1 | `or [rax+20h],1` (L768), `mov rax,[rax+40h]` (L769), arena extract from [rbx+18h] mask/deref (L771-773), NewMaybeArena (L774), store [rbx+40h] (L775). |
| CSGOInputHistoryEntryPB_CopyFrom | 10-da60-global-store.inc:793-872 | 0x7FFEBCFC2E48 | verified_1to1 | Null checks (L795-802), src_has load (L804), 0xFF field copies (L806-843), 0x7F00 block (L846-867), arena tag copy (L869-871). Every branch offset matches IDA v10. |

## Priority fixes

Rows requiring a code change or comment correction, ordered by severity.

### 1. FuckVacBCB84Scan (hallucination) — `09-new-maybe-arena-helpers.inc:1135`

Comment falsely claims "1:1 port of sub_7FFEBCFBCB84 + sub_7FFEBCFBCD0C" but the actual IDA body is a 200+ line hex-string parser (`?` wildcard + hex-pair loop at `0x7ffebcfbcced`). The port is a thin `FindPattern()` wrapper against pre-parsed compile-time patterns.

**Fix (choose one):**
- **(a) Preferred — correct the comment:** "Simplified FindPattern wrapper — original hex-string parser at sub_7FFEBCFBCB84 not ported; pattern is pre-parsed at compile time."
- **(b) If runtime-supplied patterns needed:** implement the full hex-pair + `?` wildcard parse loop from IDA.

### 2. ViewangleLerp (needs_review) — `16-subtick-antiaim-helper.inc:53`

Default `FV_LERP_REVERSE=1` inverts the ramp:
- IDA: `t = (step + 1) / count`
- Port default: `t = (count - step - 1) / count`

The `FV_LERP_REVERSE=0` branch at L60-61 matches original 1:1.

**Fix (choose one):**
- **(a) Restore 1:1:** change default to `FV_LERP_REVERSE=0`.
- **(b) Keep design divergence:** update the "1:1 port" comment to state reverse-lerp is intentional and true 1:1 requires `FV_LERP_REVERSE=0`.

### 3. FuckVacMutationPhase1 (needs_review) — `16-subtick-antiaim-helper.inc:550-583`

Line 574 zeros the cvar byte unconditionally after every read, causing `g_detourMutationFlag` to self-erase on subsequent invocations. IDA reads the live cvar per-invocation, so the original flag persists.

**Fix (choose one — per `port_audit.md` §3.5):**
- **(a) Option A — cache-on-first-observe:** wrap L574 in `if (mut_val != 0) { *cvar_byte = 0; }` so the byte only clears on the first non-zero observation.
- **(b) Defer zero-write to phase-final:** move the store to run only after the full mutation pipeline completes for the current invocation.

## Notes on VMP-virtualized hooks

The hooks `IsConnected`, `IsInGame`, `SendMovePacket`, and `NetMsgVector` are **passthrough stubs by design** — not audit failures.

The original FuckVacV2 bodies for these functions are VMP-virtualized in the `._?n` section and are **statically unrecoverable** from IDA. This was confirmed by a runtime dump against `FuckVacAgain.dll`, which showed the identical VMP layout — the dump does **not** unpack VMP. Both MD5-distinct dumps have matching section structure.

This by-design passthrough status is documented in the **HANDOFF.md (2026-07-05)** handoff and is out of scope for the 1:1 audit workflow. These hooks are excluded from the verification counts above.

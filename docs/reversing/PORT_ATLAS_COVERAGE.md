# Port Atlas — Coverage Index (auto-generated)

**Total covered:** 222 functions with self-contained port notes.

| Function | RVA | Role | Port status |
|---|---|---|---|
| `sub_7FFEBCF912E0` | `0x12E0` | (role not in header) | (unset) |
| `sub_7FFEBCF9C27C` | `0xC27C` | obfuscated magic-static `std::string` initializer (64-byte extended-YMM variant) | (unset) |
| `sub_7FFEBCFA10C0` | `0x110C0` | HDE64 length-disassembly engine (`hde64_disasm`) | matches |
| `sub_7FFEBCFA1848` | `0x11848` | MinHook `Freeze` (thread freezer + IP relocation) | not_ported |
| `sub_7FFEBCFA1B6C` | `0x11B6C` | MinHook `EnableHookLL` | (unset) |
| `sub_7FFEBCFA1DC4` | `0x11DC4` | MinHook `MH_CreateHook` (installs hook record + builds trampoline) | matches |
| `sub_7FFEBCFA20F0` | `0x120F0` | MinHook `CreateTrampolineFunction` | (unset) |
| `sub_7FFEBCFA3A7C` | `0x13A7C` | (role not in header) | (unset) |
| `sub_7FFEBCFA3D78` | `0x13D78` | (role not in header) | (unset) |
| `sub_7FFEBCFA5150` | `0x15150` | StdStringDestroy thunk (ICF-folded) | (unset) |
| `sub_7FFEBCFA6308` | `0x16308` | MSVC `std::string::assign(const char*, size_t)` (SSO-aware) | minor_diff |
| `sub_7FFEBCFA6738` | `0x16738` | keyed-registry `emplace_back` (grows begin/end container of 0x50-byte records) | not_ported |
| `sub_7FFEBCFA6FEC` | `0x16FEC` | (role not in header) | (unset) |
| `sub_7FFEBCFA749C` | `0x1749C` | StdStringDestroy (MSVC std::basic_string::_Tidy_deallocate) | (unset) |
| `sub_7FFEBCFA8E68` | `0x18E68` | lazy hook-resolver "triplet A" (three AOB scans + tail-call to original) | not_ported |
| `sub_7FFEBCFA98BC` | `0x198BC` | ProtoSerializeToStdString (allocation body) | (unset) |
| `sub_7FFEBCFAB708` | `0x1B708` | fmtlib Grisu-style double-to-scientific-decimal formatter | n/a_out_of_scope |
| `sub_7FFEBCFABF10` | `0x1BF10` | grisu2_digit_gen (shortest-round-trip d2a digit generator) | (unset) |
| `sub_7FFEBCFAC010` | `0x1C010` | (role not in header) | (unset) |
| `sub_7FFEBCFAC280` | `0x1C280` | mid-block, NOT a function | (unset) |
| `sub_7FFEBCFAC510` | `0x1C510` | mid-body of Grisu wide-multiply microkernel (sub_7FFEBCFAC4B4) | not_a_function |
| `sub_7FFEBCFAC558` | `0x1C558` | double-to-decimal Grisu/Ryu digit-generation core | n/a_out_of_scope |
| `sub_7FFEBCFACAB0` | `0x1CAB0` | (role not in header) | (unset) |
| `sub_7FFEBCFAD344` | `0x1D344` | SerializePartialToArray detour-slot installer (init-once) | (unset) |
| `sub_7FFEBCFADAC8` | `0x1DAC8` | SafetyPlugin `RegisterHookAndTrampoline` | (unset) |
| `sub_7FFEBCFB0148` | `0x20148` | (role not in header) | n/a_out_of_scope |
| `sub_7FFEBCFB2FD4` | `0x22FD4` | fmtlib general-notation (`%g`) double formatter dispatcher | n/a_out_of_scope |
| `sub_7FFEBCFB3608` | `0x23608` | fmtlib Grisu fixed-precision double-to-decimal formatter | n/a_out_of_scope |
| `sub_7FFEBCFB4AB4` | `0x24AB4` | Ryu-style float-to-string formatter core | (unset) |
| `sub_7FFEBCFB4F80` | `0x24F80` | std::to_chars floating-point formatter (fixed / scientific writer) | n/a_out_of_scope |
| `sub_7FFEBCFB5EF4` | `0x25EF4` | `num_put::_Iput` (formatted numeric output writer) | (unset) |
| `sub_7FFEBCFB6A28` | `0x26A28` | (role not in header) | (unset) |
| `sub_7FFEBCFB7380` | `0x27380` | (role not in header) | n/a_out_of_scope |
| `sub_7FFEBCFB7608` | `0x27608` | (role not in header) | n/a_out_of_scope |
| `sub_7FFEBCFB7970` | `0x27970` | fmtlib float32 writer (fmt::detail::write<float>) | n/a_out_of_scope |
| `sub_7FFEBCFB8080` | `0x28080` | (role not in header) | n/a_out_of_scope |
| `sub_7FFEBCFB8304` | `0x28304` | MSVC STL num_put / _Fput double-to-string formatter | n/a_out_of_scope |
| `sub_7FFEBCFB8B20` | `0x28B20` | (role not in header) | n/a_out_of_scope |
| `sub_7FFEBCFB9108` | `0x29108` | (role not in header) | n/a_out_of_scope |
| `sub_7FFEBCFBA374` | `0x2A374` | (role not in header) | n/a_out_of_scope |
| `sub_7FFEBCFBBC50` | `0x2BC50` | Runtime API pointer resolver (7-slot initializer) | (unset) |
| `sub_7FFEBCFBCD0C` | `0x2CD0C` | PE byte-and-mask scan engine (worker of SigscanFind) | (unset) |
| `sub_7FFEBCFBD1D4` | `0x2D1D4` | Obfuscated tier0.dll RNG import resolver | (unset) |
| `sub_7FFEBCFC0ACC` | `0x30ACC` | CreateInterface linked-list walker (interface bind lookup) | (unset) |
| `sub_7FFEBCFC1E30` | `0x31E30` | CSGOInputHistoryEntryPB SharedDtor (Clear + free-fields) | (unset) |
| `sub_7FFEBCFC2014` | `0x32014` | CSGOInputHistoryEntryPB::Clear (per-field has-bit walker) | (unset) |
| `sub_7FFEBCFC23E0` | `0x323E0` | Protobuf MergePartialFromCodedStream (rich CS2 message, ~15 fields) | (unset) |
| `sub_7FFEBCFC286C` | `0x3286C` | protobuf `_InternalSerialize` (unknown CS2 net message, 15 optional fields, submessage-heavy) | (unset) |
| `sub_7FFEBCFC2E48` | `0x32E48` | CSGOInputHistoryEntryPB::CopyFrom | (unset) |
| `sub_7FFEBCFC3458` | `0x33458` | Protobuf MergePartialFromCodedStream (CSGOUserCmdPB-shaped wrapper) | (unset) |
| `sub_7FFEBCFC3E64` | `0x33E64` | CSGOInputHistoryEntryPB::NewMaybeArena | (unset) |
| `sub_7FFEBCFC41B0` | `0x341B0` | ProtoCopyArenaTag | (unset) |
| `sub_7FFEBCFC50D0` | `0x350D0` | ProtoMsg::_InternalParse (has_bits-gated 13-field wire parser) | (unset) |
| `sub_7FFEBCFC5444` | `0x35444` | ProtoMsgSerializeToArray (has_bits-gated 13-field emitter) | (unset) |
| `sub_7FFEBCFC8028` | `0x38028` | `CMsgSource1LegacyGameEvent::key_t::_InternalParse` | (unset) |
| `sub_7FFEBCFC82D0` | `0x382D0` | `CMsgSource1LegacyGameEvent::key_t::_InternalSerialize` | (unset) |
| `sub_7FFEBCFC8C3C` | `0x38C3C` | `CMsgSource1LegacyGameEvent::_InternalSerialize` | (unset) |
| `sub_7FFEBCFCC534` | `0x3C534` | CMsgQAngle::CopyFrom | (unset) |
| `sub_7FFEBCFCEA00` | `0x3EA00` | mid-body of `sub_7FFEBCFCE9AC` (protobuf `MergeImpl` from `networkbasetypes.pb.cpp`) | (unset) |
| `sub_7FFEBCFCEBE0` | `0x3EBE0` | CNETMsg_Tick::_InternalParse | (unset) |
| `sub_7FFEBCFCEEE0` | `0x3EEE0` | CNETMsg_Tick::SerializeWithCachedSizesToArray | (unset) |
| `sub_7FFEBCFCF000` | `0x3F000` | not a function head | (unset) |
| `sub_7FFEBCFD0148` | `0x40148` | `CNETMsg_SignonState::MergePartialFromCodedStream` | (unset) |
| `sub_7FFEBCFD04BC` | `0x404BC` | `CNETMsg_SignonState::_InternalSerialize` | (unset) |
| `sub_7FFEBCFD0AE8` | `0x40AE8` | `CSVCMsg_GameEvent::key_t::MergePartialFromCodedStream` | (unset) |
| `sub_7FFEBCFD0D90` | `0x40D90` | `CSVCMsg_GameEvent::key_t::_InternalSerialize` | (unset) |
| `sub_7FFEBCFD28D0` | `0x428D0` | `CNETMsg_SpawnGroup_Load::MergePartialFromCodedStream` | (unset) |
| `sub_7FFEBCFD2F78` | `0x42F78` | (role not in header) | (unset) |
| `sub_7FFEBCFD3000` | `0x43000` | (role not in header) | (unset) |
| `sub_7FFEBCFD3514` | `0x43514` | `CNETMsg_SpawnGroup_Load::ByteSizeLong` | (unset) |
| `sub_7FFEBCFD3824` | `0x43824` | `CNETMsg_SpawnGroup_Load::MergeImpl` | (unset) |
| `sub_7FFEBCFD4DE0` | `0x44DE0` | CSVCMsg_GameSessionConfiguration::MergePartialFromCodedStream | (unset) |
| `sub_7FFEBCFD5424` | `0x45424` | (role not in header) | (unset) |
| `sub_7FFEBCFD58BC` | `0x458BC` | (role not in header) | (unset) |
| `sub_7FFEBCFD5900` | `0x45900` | (role not in header) | (unset) |
| `sub_7FFEBCFD5B38` | `0x45B38` | `networkbasetypes.pb.cpp` message `MergeImpl` (protoc-generated) | (unset) |
| `sub_7FFEBCFD6154` | `0x46154` | (role not in header) | (unset) |
| `sub_7FFEBCFD65A8` | `0x465A8` | CNETMsg_DebugOverlay::SerializeWithCachedSizesToArray | (unset) |
| `sub_7FFEBCFD7A00` | `0x47A00` | mid-block store inside `sub_7FFEBCFD7934` | (unset) |
| `sub_7FFEBCFD853C` | `0x4853C` | CInButtonStatePB::CopyFrom | (unset) |
| `sub_7FFEBCFD8FF4` | `0x48FF4` | CBaseUserCmdExecutionNotes::MergeFromInternal (aka CExecutionNotes_CopyFrom) | (unset) |
| `sub_7FFEBCFD9250` | `0x49250` | CBaseUserCmdPB::Clear (scratch usercmd protobuf reset) | (unset) |
| `sub_7FFEBCFD94AC` | `0x494AC` | `CBaseUserCmdPB::MergePartialFromCodedStream` (wire parser) | (unset) |
| `sub_7FFEBCFD99B0` | `0x499B0` | (role not in header) | (unset) |
| `sub_7FFEBCFD9FF8` | `0x49FF8` | (role not in header) | (unset) |
| `sub_7FFEBCFDABFC` | `0x4ABFC` | `CSubtickMoveStep::NewMaybeArena` factory | (unset) |
| `sub_7FFEBCFDAD70` | `0x4AD70` | (role not in header) | (unset) |
| `sub_7FFEBCFDAEF0` | `0x4AEF0` | BuildHashOffsetFromSchema | (unset) |
| `sub_7FFEBCFDBAA0` | `0x4BAA0` | Phase-E sig-scan shard pair (BCB84 calls #1 & #2) inside FDB520 orchestrator | (unset) |
| `sub_7FFEBCFDCA00` | `0x4CA00` | (role not in header) | (unset) |
| `sub_7FFEBCFDD400` | `0x4D400` | # sub_7FFEBCFDD400 (NOT A FUNCTION — mid-block address) | (unset) |
| `sub_7FFEBCFDF6E0` | `0x4F6E0` | Phase-E signature-scan shard inside FDB520 orchestrator | (unset) |
| `sub_7FFEBCFDF7B0` | `0x4F7B0` | mid-function XOR-decrypt + BCB84 sig-scan block inside RipGlobals-style orchestrator (FDB520) | (unset) |
| `sub_7FFEBCFDF880` | `0x4F880` | (role not in header) | (unset) |
| `sub_7FFEBCFE01E0` | `0x501E0` | Batch signature resolver #1 (import/export VA cache init) | (unset) |
| `sub_7FFEBCFE0680` | `0x50680` | mid-function chunk of bulk sigscan-init routine | (unset) |
| `sub_7FFEBCFE1160` | `0x51160` | `google::protobuf::internal::LogMessage::LogMessage` | (unset) |
| `sub_7FFEBCFE1240` | `0x51240` | google::protobuf::internal::LogMessage::~LogMessage() | (unset) |
| `sub_7FFEBCFE1250` | `0x51250` | `ProtobufLogMessageEmit` | (unset) |
| `sub_7FFEBCFE1470` | `0x51470` | ProtobufLogMessageAppend | (unset) |
| `sub_7FFEBCFE2020` | `0x52020` | (role not in header) | (unset) |
| `sub_7FFEBCFE29A0` | `0x529A0` | Arena aligned-allocation fast path | (unset) |
| `sub_7FFEBCFE2B40` | `0x52B40` | ArenaOwnOnSerial (ThreadSafeArena::AddCleanupFromExisting) | (unset) |
| `sub_7FFEBCFE3070` | `0x53070` | Arena allocate thunk (protobuf `Arena::AllocateAlignedNoHooks`) | (unset) |
| `sub_7FFEBCFE38C0` | `0x538C0` | ProtoSerializeAppendToStdString (impl body) | (unset) |
| `sub_7FFEBCFE3A70` | `0x53A70` | MessageLite::AppendToString (thunk → sub_7FFEBCFE38C0) | (unset) |
| `sub_7FFEBCFE41B0` | `0x541B0` | MessageLite::ParsePartialFromString(std::string_view) | (unset) |
| `sub_7FFEBCFE49E0` | `0x549E0` | mid-block, not a function head | (unset) |
| `sub_7FFEBCFE5C60` | `0x55C60` | NOT A FUNCTION (mid-block anchor inside sub_7FFEBCFE5C00) | (unset) |
| `sub_7FFEBCFE6EF0` | `0x56EF0` | mid-function of std::sort median/ninther pivot helper | (unset) |
| `sub_7FFEBCFE7060` | `0x57060` | MSVC std::sort introsort driver (partition + heapsort fallback + insertion sort) | (unset) |
| `sub_7FFEBCFE7B90` | `0x57B90` | Reflection::AddEnum (typed wrapper) | (unset) |
| `sub_7FFEBCFE86E0` | `0x586E0` | protobuf `AssignDescriptors`-style reflection builder | (unset) |
| `sub_7FFEBCFE8F60` | `0x58F60` | protobuf `Reflection::ClearField` | (unset) |
| `sub_7FFEBCFE9420` | `0x59420` | (role not in header) | (unset) |
| `sub_7FFEBCFED300` | `0x5D300` | `google::protobuf::Reflection::SetString(Message*, const FieldDescriptor*, std::string)` | (unset) |
| `sub_7FFEBCFED840` | `0x5D840` | protobuf Reflection ByteSize walker | (unset) |
| `sub_7FFEBCFEE420` | `0x5E420` | `google::protobuf::Reflection::SwapFieldsImpl(Message* lhs, Message* rhs, std::vector<const FieldDes | (unset) |
| `sub_7FFEBCFEE770` | `0x5E770` | `google::protobuf::Reflection::SwapField(Message*, Message*, const FieldDescriptor*)` | (unset) |
| `sub_7FFEBCFF2E90` | `0x62E90` | protobuf std::__inplace_merge driver over sorted MapKey* range | (unset) |
| `sub_7FFEBCFF3830` | `0x63830` | (role not in header) | (unset) |
| `sub_7FFEBCFF3C40` | `0x63C40` | protobuf MapKeySorter insertion-sort inner loop | (unset) |
| `sub_7FFEBCFF4090` | `0x64090` | protobuf MapKeySorter `std::__make_heap` (heapsort fallback build-phase) | (unset) |
| `sub_7FFEBCFF4430` | `0x64430` | protobuf MapKeySorter::Sort (introsort recursion body) | (unset) |
| `sub_7FFEBCFF5980` | `0x65980` | (role not in header) | (unset) |
| `sub_7FFEBCFF5DA0` | `0x65DA0` | protobuf std::__upper_bound over sorted map-key range | (unset) |
| `sub_7FFEBCFF63A0` | `0x663A0` | protobuf DynamicMessage MapKey `operator<` (standalone) | (unset) |
| `sub_7FFEBCFF6840` | `0x66840` | (role not in header) | (unset) |
| `sub_7FFEBCFF70C0` | `0x670C0` | (role not in header) | (unset) |
| `sub_7FFEBCFFAEF0` | `0x6AEF0` | (role not in header) | (unset) |
| `sub_7FFEBCFFB560` | `0x6B560` | (role not in header) | (unset) |
| `sub_7FFEBCFFB9A0` | `0x6B9A0` | protobuf MapKey serializer (key half of Map<K,V> entry) | (unset) |
| `sub_7FFEBCFFBDE0` | `0x6BDE0` | protobuf MapValue serializer (value half of Map<K,V> entry) | (unset) |
| `sub_7FFEBCFFC850` | `0x6C850` | RepeatedFieldRef read-into-`std::vector<int64>` + std::sort | (unset) |
| `sub_7FFEBCFFCE50` | `0x6CE50` | protobuf ExtensionSet / MessageSet raw-byte serialization loop | (unset) |
| `sub_7FFEBCFFD5C0` | `0x6D5C0` | WireFormat::SerializeFieldWithCachedSizesToArray | (unset) |
| `sub_7FFEBCFFE240` | `0x6E240` | `WireFormat::SerializeMessageWithCachedSizesToArray` (fields + ExtensionSet, MessageSet-aware) | (unset) |
| `sub_7FFEBCFFE910` | `0x6E910` | (role not in header) | (unset) |
| `sub_7FFEBCFFF760` | `0x6F760` | `MessageFactory::PrototypeMap` FNV-1a `insert`/emplace (message.cc RegisterMessage path) | (unset) |
| `sub_7FFEBD000870` | `0x70870` | `google::protobuf::MessageFactory` generated-pool `GetPrototype` (message.cc:293/311) | (unset) |
| `sub_7FFEBD0019E0` | `0x719E0` | `google::protobuf::Reflection::UnsafeShallowSwapRepeatedField` / `SwapFieldsOneRepeatedString` (repe | (unset) |
| `sub_7FFEBD0048B0` | `0x748B0` | ExtensionSet registry map `emplace(key)` (hash-map find-or-insert) | (unset) |
| `sub_7FFEBD005780` | `0x75780` | (role not in header) | (unset) |
| `sub_7FFEBD007730` | `0x77730` | ExtensionSet flat-map grow / flat-to-tree promotion | (unset) |
| `sub_7FFEBD00A5D0` | `0x7A5D0` | (role not in header) | (unset) |
| `sub_7FFEBD00ABA0` | `0x7ABA0` | protobuf `ExtensionSet::Register` (lazy singleton + emplace + duplicate diag) | (unset) |
| `sub_7FFEBD00D1C0` | `0x7D1C0` | MethodDescriptorProto::MergePartialFromCodedStream | (unset) |
| `sub_7FFEBD00D6A0` | `0x7D6A0` | (role not in header) | (unset) |
| `sub_7FFEBD00E7C0` | `0x7E7C0` | (role not in header) | (unset) |
| `sub_7FFEBD00FC50` | `0x7FC50` | FieldDescriptorProto::MergePartialFromCodedStream | (unset) |
| `sub_7FFEBD0147E0` | `0x847E0` | (role not in header) | (unset) |
| `sub_7FFEBD014D70` | `0x84D70` | (role not in header) | (unset) |
| `sub_7FFEBD015170` | `0x85170` | (role not in header) | (unset) |
| `sub_7FFEBD017D60` | `0x87D60` | protoc `MergePartialFromCodedStream` (10-field CS2 message; 9 RepeatedPtr submsg fields + packed var | (unset) |
| `sub_7FFEBD018300` | `0x88300` | protoc `MergePartialFromCodedStream` (5-field CS2 message; packed varint f1 + 3 RepPtrField submsg + | (unset) |
| `sub_7FFEBD018610` | `0x88610` | protoc `MergePartialFromCodedStream` (2-bool CS2 message with extension range + field-999 group mark | (unset) |
| `sub_7FFEBD018D00` | `0x88D00` | protobuf `_InternalParse` for a small CS2/anti-cheat message class | (unset) |
| `sub_7FFEBD01A540` | `0x8A540` | (role not in header) | (unset) |
| `sub_7FFEBD01ABC0` | `0x8ABC0` | (role not in header) | (unset) |
| `sub_7FFEBD01B9C0` | `0x8B9C0` | (role not in header) | (unset) |
| `sub_7FFEBD01CB40` | `0x8CB40` | protoc-generated `_InternalSerialize` for a CS2 message with proto2 extension range (>=1000) and one | (unset) |
| `sub_7FFEBD01D6F0` | `0x8D6F0` | (role not in header) | (unset) |
| `sub_7FFEBD01DC30` | `0x8DC30` | `SplitStringViewIntoVector` (delimiter-set tokenizer → std::vector&lt;std::string&gt;) | (unset) |
| `sub_7FFEBD01DF70` | `0x8DF70` | (role not in header) | (unset) |
| `sub_7FFEBD01FC80` | `0x8FC80` | google::protobuf::CUnescapeInternal (C-escape decoder) | (unset) |
| `sub_7FFEBD022BC0` | `0x92BC0` | port-atlas R8 (session f6d38f56) | (unset) |
| `sub_7FFEBD028580` | `0x98580` | `std::vector<T104>::_Emplace_reallocate(pos, &&value)` | (unset) |
| `sub_7FFEBD0292A0` | `0x992A0` | std::unordered_map<string,int32> bulk range-insert (FNV-1a keyed) | (unset) |
| `sub_7FFEBD029BF0` | `0x99BF0` | STL sort Hoare partition over {ptr,len} pairs | (unset) |
| `sub_7FFEBD02AD10` | `0x9AD10` | std::unordered_map<uint64_t, RangeConflictEntry>::try_emplace | (unset) |
| `sub_7FFEBD02B180` | `0x9B180` | `unordered_map<{hash,char*,size_t}, FieldDescriptor*>::try_emplace` (48-B node, hybrid pre-hash + Be | (unset) |
| `sub_7FFEBD02B420` | `0x9B420` | `unordered_map<std::string,uint64_t>` **`try_emplace(key)`** (find-or-insert, string-keyed) | (unset) |
| `sub_7FFEBD02F300` | `0x9F300` | `basic_istream<char>::sentry::sentry(bool noskipws)` | (unset) |
| `sub_7FFEBD033F50` | `0xA3F50` | protoc descriptor-pool trampoline that registers `google.protobuf.FileOptions` (plus a `<scope>.dumm | (unset) |
| `sub_7FFEBD03C4C0` | `0xAC4C0` | `google::protobuf::DescriptorBuilder::BuildService` | (unset) |
| `sub_7FFEBD03DC80` | `0xADC80` | `<Msg>::MergeFrom(const <Msg>& from)` (protobuf generated code) | (unset) |
| `sub_7FFEBD044AD0` | `0xB4AD0` | `google::protobuf::FieldDescriptor::DefaultValueAsString` | (unset) |
| `sub_7FFEBD045D30` | `0xB5D30` | `google::protobuf::DescriptorBuilder::EnumValueToPascalCase` (enum-name case-folding normalizer) | (unset) |
| `sub_7FFEBD046030` | `0xB6030` | `google::protobuf::DescriptorBuilder::OptionInterpreter::ExamineIfOptionIsSet` | (unset) |
| `sub_7FFEBD047CB0` | `0xB7CB0` | protobuf `DescriptorPool::FindFileByName` (recursive, self-underlay + fallback-DB) | (unset) |
| `sub_7FFEBD0489C0` | `0xB89C0` | FormatCommentAsString (protobuf-plugin comment printer) | (unset) |
| `sub_7FFEBD048D40` | `0xB8D40` | FormatLineOptions (protobuf descriptor.cc `option $1;` printer) | (unset) |
| `sub_7FFEBD049730` | `0xB9730` | FieldDescriptor::GetSourceLocation (path build + lookup) | (unset) |
| `sub_7FFEBD04CAF0` | `0xBCAF0` | `google::protobuf::DescriptorPool::IsSubSymbolOfBuiltType` | (unset) |
| `sub_7FFEBD04CE40` | `0xBCE40` | `google::protobuf::DescriptorBuilder::LogUnusedDependency` | (unset) |
| `sub_7FFEBD04EAF0` | `0xBEAF0` | protobuf `Descriptor` nested-types size-counter (recursive) | (unset) |
| `sub_7FFEBD04EE30` | `0xBEE30` | protobuf `EnumDescriptor` table-sizer (nested-enum walker) | (unset) |
| `sub_7FFEBD04F830` | `0xBF830` | protobuf `Descriptor` top-level size-counter (TableSizer::Visit(Descriptor)) | (unset) |
| `sub_7FFEBD050280` | `0xC0280` | `google::protobuf::(anonymous)::RetrieveOptionsAssumingRightPool` (fast path) | (unset) |
| `sub_7FFEBD055330` | `0xC5330` | protobuf `FieldDescriptor::ToJsonName` (snake_case to camelCase converter) | (unset) |
| `sub_7FFEBD055670` | `0xC5670` | protobuf `FieldDescriptor` proto3 JSON-camelcase collision key (`ToLowercaseWithoutUnderscores`) | (unset) |
| `sub_7FFEBD055CF0` | `0xC5CF0` | protobuf `DescriptorBuilder::AddSymbol` / `TryFindSymbolInParent` (unknown-name inserter) | (unset) |
| `sub_7FFEBD057B30` | `0xC7B30` | DescriptorBuilder::IsMapEntryStyleMessage(field) | (unset) |
| `sub_7FFEBD0596E0` | `0xC96E0` | `google::protobuf::DescriptorBuilder::ValidateSymbolName` | (unset) |
| `sub_7FFEBD05A030` | `0xCA030` | (role not in header) | (unset) |
| `sub_7FFEBD05A1A0` | `0xCA1A0` | MSVC STL `_Hash::_Rehash` inner (string-key, FNV-1a-64, 56-B node) | (unset) |
| `sub_7FFEBD05A430` | `0xCA430` | STL unordered_map/set _Rehash helper (FNV-1a keyed) | (unset) |
| `sub_7FFEBD05A920` | `0xCA920` | protobuf DescriptorPool `unordered_map::_Rehash` (5*h byte-mix, no prehash cache) | (unset) |
| `sub_7FFEBD05F2D0` | `0xCF2D0` | (role not in header) | (unset) |
| `sub_7FFEBD05F8A0` | `0xCF8A0` | protobuf DynamicMapField::AllocateMapValue (default-construct new map value by CppType) | (unset) |
| `sub_7FFEBD062950` | `0xD2950` | protobuf MapField::SyncRepeatedFieldWithMapNoLock | (unset) |
| `sub_7FFEBD062F20` | `0xD2F20` | (role not in header) | (unset) |
| `sub_7FFEBD0631D0` | `0xD31D0` | (role not in header) | (unset) |
| `sub_7FFEBD064270` | `0xD4270` | ReflectionOps::FindInitializationErrors (recursive) | (unset) |
| `sub_7FFEBD065AE0` | `0xD5AE0` | protobuf std::__inplace_merge driver (text_format.cc twin) | (unset) |
| `sub_7FFEBD067EC0` | `0xD7EC0` | protobuf DynamicMessage MapKey `operator<` (second standalone instantiation) | (unset) |
| `sub_7FFEBD06C480` | `0xDC480` | TextFormat::ParserImpl::ConsumeFullIdentifier (dotted-name accumulator) | (unset) |
| `sub_7FFEBD06EC70` | `0xDEC70` | TextFormat::Parser::ParserImpl::Parse tail (required-field validation + error report) | (unset) |
| `sub_7FFEBD072AF0` | `0xE2AF0` | TextFormat::Parser::ParserImpl::ConsumeMessage (`{`-delimited body, recursion-guarded) | (unset) |
| `sub_7FFEBD0776B0` | `0xE76B0` | DescriptorPool "prefix+suffix" full-name lex comparator | (unset) |
| `sub_7FFEBD07C180` | `0xEC180` | collect names from an ordered map + a paired vector into an output MsvcString vector | (unset) |
| `sub_7FFEBD07CDE0` | `0xECDE0` | `unordered_map<const Descriptor*, PrototypeState*>` **`try_emplace(key)`** (find-or-insert, pointer- | (unset) |
| `sub_7FFEBD07E230` | `0xEE230` | DynamicMessage::SharedCtor (default-field initializer) | (unset) |
| `sub_7FFEBD07F8C0` | `0xEF8C0` | (role not in header) | (unset) |
| `sub_7FFEBD081710` | `0xF1710` | `_LCMapStringA_stat` (MSVC CRT internal, ANSI LCMapString via wide-char round-trip) | (unset) |
| `sub_7FFEBD08F370` | `0xFF370` | CRT wide `scanf` format-string state machine | (unset) |
| `sub_7FFEBD093D60` | `0x103D60` | (role not in header) | (unset) |
| `sub_7FFEBD0A1550` | `0x111550` | CRT IEEE-754 FP exception record builder + raiser | (unset) |
| `sub_7FFEBD0A1B10` | `0x111B10` | CRT `fopen` mode-string parser (`_openfile` inner) | (unset) |
| `sub_7FFEBD0A40E8` | `0x1140E8` | (role not in header) | (unset) |
| `sub_7FFEBD0A5850` | `0x115850` | (role not in header) | (unset) |
| `sub_7FFEBD0AC070` | `0x11C070` | (role not in header) | (unset) |

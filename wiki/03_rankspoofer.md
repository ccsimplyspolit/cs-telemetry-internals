# 03 — RankSpoofer

Client-side visual spoofer for rank / profile / matchmaking fields in CS2. Two components:

- **CS2RankSpooferDriver.sys** — kernel driver (~27 KB, KDU-mapped).
- **CS2RankSpooferConsole.exe** — interactive VT100 TUI (~195 KB).

Source:
- Driver: [`source/drivers/CS2RankSpooferDriver/`](../../source/drivers/CS2RankSpooferDriver/)
- Console: [`source/apps/CS2RankSpooferConsole/`](../../source/apps/CS2RankSpooferConsole/)
- Kit: [`build/kit_rankspoof/`](../../build/kit_rankspoof/)

Version: **v1.14-claude** (2026-07-15). This release upgraded the driver from Phase 1 (pattern-scan only, no writes) to **Phase 1.5** (direct-write via `KeStackAttachProcess` + `MmCopyVirtualMemory`).

---

## What it can spoof (client-side visual only)

Ranks:
- Competitive rank id (0–18) — Silver 1 through Global Elite.
- Wingman rank id (0–18) — same range.
- Competitive rank type (6=classic, 7=wingman, 11=premier).
- Premier CS rating (0–40000 Elo).
- Wins / losses / draws.
- Predicted win / loss / tie (rank-up UI arrow).

Profile:
- Private rank / level (1–40) — Steam CS level in menu.
- Private rank XP progress.
- Commends (leader / teacher / friendly).
- Music kit id + MVPs count.
- Controller MVPs star + Score (scoreboard).
- Clan tag (raw 16-byte write; may show garbage without a `CUtlSymbolLarge` intern-table poke).

Matchmaking:
- Queued matchmaking mode (menu label).

## What it **cannot** spoof (server-authoritative)

- **Prime status** — Steam entitlement, replicated from Game Coordinator, not in client.dll.
- **Trust factor** — server-side score, not read from client.dll.
- **Actual rank displayed to other players** — they read from GC directly. You see fake rank; opponents see your real rank.

---

## Architecture

```
User console ─────► SHM Global\CS2RankSpoofState (magic 'RASX') ◄───── Driver worker (100 ms)
       │                                                                    │
       │                                                                    ▼
       │                                                          KeStackAttachProcess(cs2)
       │                                                                    │
       │                                                                    ▼
       │                                                     Resolve chain:
       │                                                       client.dll + dwLocalPlayerController
       │                                                     → CCSPlayerController*
       │                                                     → InventoryServices
       │                                                                    │
       │                                                                    ▼
       │                                                     WriteEnabledFields:
       │                                                       Premier / Wingman / Competitive
       │                                                       / Profile / Matchmaking blocks
       │                                                                    │
       └── freeze_mask bit set ────────────────────────────────► re-write every tick
```

Named objects (Win32 → NT):

| Type | Win32 name | NT path |
|---|---|---|
| SECTION | `Global\CS2RankSpoofState` | `\BaseNamedObjects\CS2RankSpoofState` |
| EVENT | `Global\CS2RankSpoofStop` | `\BaseNamedObjects\CS2RankSpoofStop` |
| EVENT | `Global\CS2RankSpoofStopped` | `\BaseNamedObjects\CS2RankSpoofStopped` |

Magic: `RANKSPOOF_MAGIC = 0x52415358` (ASCII `RASX`).

Definitions in [`shared.h`](../../source/drivers/CS2RankSpooferDriver/shared.h) (identical copy in the console).

---

## Driver capabilities (Phase 1.5)

From `docs/RELEASE_NOTES_v1.14-claude.md`:

- `LoadSchemaOffsetsFromRegistry` — reads 22 offsets from `HKLM\SYSTEM\CurrentControlSet\Services\CS2RankSpoofer` at DriverEntry.
- `PublishSchemaAndVersion` — one-shot SHM push of the resolved schema.
- `WriteProcMem` — SEH-wrapped `MmCopyVirtualMemory` write direction.
- `ResolveLocalPlayerController` — chained deref: `client.dll` → LPC → InventoryServices; `C_CSGameRules` also resolved.
- `WriteEnabledFields` — iterates Premier / Wingman / Competitive / Profile / Matchmaking with `freeze_mask` gating.

Old Phase-1 pattern-scan path retained for future Phase 2 trampoline shellcode injection.

Auto-update: `Load-Spoofer.ps1` fetches offsets from `a2x/cs2-dumper` HEAD before every load. Falls back to hardcoded defaults if offline.

---

## Console TUI

Full-screen VT100 layout:

- Colored hook badge (INSTALLED / IDLE / ERROR).
- Live tick counter + write counter.
- LPC / Inv / GR pointer display.
- 5 field editors (Premier / Wingman / Competitive / Profile / Matchmaking) with `+/-` and `PgUp/PgDn`.
- 12 presets: Silver 1 fresh → Global Elite 25W → Premier 25000/35000 Elo → Wingman LE → Prestige 40 → Everything Maxed.
- Freeze mask editor with per-block toggles.
- Config save/load to `%LOCALAPPDATA%\CS2RankSpoofer\config.json` (hand-rolled JSON, no deps).

Hotkeys:

| Key | Action |
|---|---|
| P / W / C / O / M | Switch to Premier / Wingman / Competitive / Profile / MM |
| Space | Toggle spoof on/off |
| +/- , PgUp/PgDn | Increment / decrement current field |
| S | Preset picker |
| F | Freeze mask editor |
| B | Bump `write_generation` (force re-apply) |
| J / L | Save / load config JSON |
| U | Unload driver, exit |
| Q | Quit (leave driver running) |

CLI flags: `--unload`, `--set-preset N`, `--print-state`.

---

## Freeze mode

Per-block bit mask. When a bit is set, the driver re-writes the enabled fields every 100 ms unconditionally, even if the game overwrites them. Useful for Score / MVPs which the server refreshes each round.

Wire contract:
- `freeze_mask` (uint32) — bit per block, console writes.
- `write_generation` ↔ `driver_write_generation` handshake for observable sync.

---

## Mode IDs (observed in `get_rank_data` calls)

| ID | Mode |
|---|---|
| 1 | Competitive |
| 7 | Wingman |
| 11 | Premier |

Ranges:
- Premier: CS rating 0–35000.
- Competitive / Wingman: rank 0–18.

---

## Usage

```
1. Launch CS2, wait for main menu (not required but faster to see effect).
2. Right-click Load-Spoofer.bat -> Run as administrator (or double-click, UAC prompt appears).
3. Console opens with live status. Use hotkeys above.
4. Values apply to YOUR client only. Rejoin main menu / match to see them on the rank card / scoreboard.
```

Config file: `%LOCALAPPDATA%\CS2RankSpoofer\config.json`.

Registry key populated by `Load-Spoofer.ps1`:
`HKLM\SYSTEM\CurrentControlSet\Services\CS2RankSpoofer` — 22 schema offsets refreshed from cs2-dumper HEAD.

---

## Known limitations (v1.14-claude)

- **Clan tag** — direct 16-byte write is emitted, but CS2 uses `CUtlSymbolLarge` intern handle; display may show garbage until the intern-table poke lands. `LOG_WARN` fired on first write.
- **Service medal** — `m_rank[6]` slot struct layout not fully mapped; TODO marker left in driver.
- **Phase 2 trampoline** — still not implemented. The `RANKSPOOF_CS2_DATA` contract is fully specified in [`shared.h`](../../source/drivers/CS2RankSpooferDriver/shared.h) v2 for future work; `callsite_va` / `original_fn_va` still published for informational Phase-2 debugging.

---

## Requirements

- Windows 10 / 11 x64 (tested on Win11 22H2+).
- Administrator.
- MSI Afterburner / RTSS / HWinfo will be auto-closed by `Load-Spoofer.ps1` (they hold `RTCore64` exclusive, which KDU needs for DSE-off).

---

## Cross-refs

- [`source/drivers/CS2RankSpooferDriver/README.md`](../../source/drivers/CS2RankSpooferDriver/README.md)
- [`source/apps/CS2RankSpooferConsole/README.md`](../../source/apps/CS2RankSpooferConsole/README.md)
- [`build/kit_rankspoof/README.txt`](../../build/kit_rankspoof/README.txt)
- Release notes: [`docs/RELEASE_NOTES_v1.14-claude.md`](../../docs/RELEASE_NOTES_v1.14-claude.md)
- Driver hardening improvements roadmap: [`docs/DRIVER_HARDENING.md`](../../docs/DRIVER_HARDENING.md)

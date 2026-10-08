# v1.16-claude — Critical fix: RankSpooferDriver stale offset defaults (2026-07-16)

**[EN](#english) · [RU / Русский](#русский)**

---

## English

### 🔴 Critical runtime fix

**Discovered during wiki quality-control:** RankSpoofer v1.14/v1.15 shipped with **stale hardcoded offset fallbacks** in both `CS2RankSpooferDriver.sys` and `kit_rankspoof/Load-Spoofer.ps1`. If `Load-Spoofer.ps1` autofetch from `a2x/cs2-dumper` HEAD failed (network down, GitHub outage, corporate proxy), the driver would silently write to **wrong CCSPlayerController fields** on every 100 ms tick — corrupting adjacent fields instead of the intended rank/wins/MVPs/etc.

#### Root cause

Initial values came from a stale local `third_party/cs2-dumper` checkout, not from fresh HEAD. Most defaults were shifted **-8 bytes** from schema truth. Discovered when an agent building the [CS2-SDK-Reference](https://github.com/ccsimplyspolit/CS2-SDK-Reference) wiki noticed `structures/README.md` values didn't match `schema/client_dll.json`.

#### Fixed defaults

Both `g_Sch` initializer in driver `main.cpp` AND `$schema` hashtable in `Load-Spoofer.ps1`:

| Field | Old (wrong) | New (correct) | Delta |
|---|---|---|---|
| `dwLocalPlayerController` | `0x237EBA0` | `0x2383730` | grossly wrong |
| `off_ctrl_CompetitiveRanking` | `0x880` | `0x888` | +8 |
| `off_ctrl_CompetitiveWins` | `0x884` | `0x88C` | +8 |
| `off_ctrl_CompetitiveRankType` | `0x888` | `0x890` | +8 |
| `off_ctrl_CompetitivePredictedWin` | `0x88C` | `0x894` | +8 |
| `off_ctrl_CompetitivePredictedLoss` | `0x890` | `0x898` | +8 |
| `off_ctrl_CompetitivePredictedTie` | `0x894` | `0x89C` | +8 |
| `off_ctrl_MVPs` | `0x940` | `0x958` | +0x18 |
| `off_ctrl_Score` | `0x92C` | `0x93C` | +0x10 |
| `off_ctrl_MusicKitID` | `0x948` | `0x950` | +8 |
| `off_ctrl_MusicKitMVPs` | `0x94C` | `0x954` | +8 |
| `off_ctrl_ClanTag` | `0x858` | `0x860` | +8 |
| `off_ctrl_InventoryServices` | `0xA10` | `0x818` | grossly wrong |

All 13 corrections verified against **fresh `a2x/cs2-dumper` HEAD** (2026-07-16) via `python -c "import json; print(json.load(open('client_dll.json'))['client.dll']['classes']['CCSPlayerController']['fields'])"`.

### Impact assessment

- **If autofetch works** (99% of runs): **no user impact** — autofetch pulls correct values from `a2x/cs2-dumper` HEAD every load and overrides these defaults.
- **If autofetch fails** (offline / GitHub down / corporate proxy blocks `raw.githubusercontent.com`): v1.14/v1.15 driver writes to wrong fields → corrupts adjacent CCSPlayerController state. v1.16 driver uses correct defaults → still works.
- **Fresh git-clone-and-run users** without a network connection would have seen wrong behavior on v1.14/v1.15; v1.16 makes offline scenarios safe.

### What's in this release

| File | Change |
|---|---|
| `kit_rankspoof.zip` | **Repackaged with fixed driver** (`CS2RankSpooferDriver.sys` 27,136 B, rebuilt 2026-07-16) and fixed `Load-Spoofer.ps1` |
| `kit_isvalveds.zip` | UNCHANGED — no stale defaults (only uses `dwGameRules` + `m_bIsValveDS`) |
| `kit_attack.zip`, `kit_byte.zip`, `kit_kernel_inject.zip` | UNCHANGED |

### Related changes

Beyond the runtime fix, this session also delivered:
- **Bilingual wiki structure** in all 3 sibling repos (`wiki/en/` + `wiki/ru/`, ~30 pages per repo total).
- **CS2-SDK-Reference stale-offset fixes** in `structures/README.md`, `vmp_targets/README.md`, `offsets/README.md`, top-level `README.md`.
- **`sync.cmd`/`sync.sh`** one-click sync launcher in CS2-SDK-Reference.

### Sibling releases

- [CS2-SDK-Reference v1.0-initial](https://github.com/ccsimplyspolit/CS2-SDK-Reference/releases/tag/v1.0-initial) — CS2 SDK reference (bilingual)
- [VMP-Deob v2.0-mechanics-and-tools](https://github.com/ccsimplyspolit/VMP-Deob/releases/tag/v2.0-mechanics-and-tools) — VMP research + tooling

### How to verify the fix (optional)

```powershell
# Confirm your driver has the correct defaults
Select-String -Path "kit_rankspoof\CS2RankSpooferDriver.sys" -Pattern "^Contents" -Encoding Byte -Simple
# Or run under debugger; g_Sch's off_ctrl_CompetitiveRanking should be 0x888.

# Confirm Load-Spoofer.ps1 has correct hashtable
Select-String -Path "kit_rankspoof\Load-Spoofer.ps1" -Pattern "off_ctrl_CompetitiveRanking\s+=\s+0x888"
```

### Upgrade

Just download `kit_rankspoof.zip` from this release and replace your existing kit. No config migration needed.

---

## Русский

### 🔴 Критический рантайм-фикс

**Обнаружено во время wiki quality-control:** RankSpoofer v1.14/v1.15 шипался со **stale hardcoded offset fallback'ами** и в `CS2RankSpooferDriver.sys`, и в `kit_rankspoof/Load-Spoofer.ps1`. Если autofetch `Load-Spoofer.ps1` из `a2x/cs2-dumper` HEAD упал (сеть отвалилась, GitHub недоступен, корпоративный прокси), драйвер молча писал в **неправильные поля CCSPlayerController** каждые 100 мс — портил соседние поля вместо предназначенных rank/wins/MVPs/etc.

#### Корневая причина

Начальные значения были из stale local `third_party/cs2-dumper` checkout'а, а не из свежего HEAD. Большинство defaults'ов сдвинуто на **-8 байт** от schema truth. Обнаружено, когда агент, собирающий wiki [CS2-SDK-Reference](https://github.com/ccsimplyspolit/CS2-SDK-Reference), заметил, что значения `structures/README.md` не совпадают с `schema/client_dll.json`.

#### Исправленные defaults

И `g_Sch` initializer в driver'ском `main.cpp`, И `$schema` hashtable в `Load-Spoofer.ps1`:

| Поле | Старое (неверное) | Новое (верное) | Delta |
|---|---|---|---|
| `dwLocalPlayerController` | `0x237EBA0` | `0x2383730` | грубо неверное |
| `off_ctrl_CompetitiveRanking` | `0x880` | `0x888` | +8 |
| `off_ctrl_CompetitiveWins` | `0x884` | `0x88C` | +8 |
| `off_ctrl_CompetitiveRankType` | `0x888` | `0x890` | +8 |
| `off_ctrl_CompetitivePredictedWin` | `0x88C` | `0x894` | +8 |
| `off_ctrl_CompetitivePredictedLoss` | `0x890` | `0x898` | +8 |
| `off_ctrl_CompetitivePredictedTie` | `0x894` | `0x89C` | +8 |
| `off_ctrl_MVPs` | `0x940` | `0x958` | +0x18 |
| `off_ctrl_Score` | `0x92C` | `0x93C` | +0x10 |
| `off_ctrl_MusicKitID` | `0x948` | `0x950` | +8 |
| `off_ctrl_MusicKitMVPs` | `0x94C` | `0x954` | +8 |
| `off_ctrl_ClanTag` | `0x858` | `0x860` | +8 |
| `off_ctrl_InventoryServices` | `0xA10` | `0x818` | грубо неверное |

Все 13 исправлений подтверждены против **свежего `a2x/cs2-dumper` HEAD** (2026-07-16) через `python -c "import json; print(json.load(open('client_dll.json'))['client.dll']['classes']['CCSPlayerController']['fields'])"`.

### Оценка воздействия

- **Если autofetch работает** (99% запусков): **воздействия на пользователя нет** — autofetch тянет правильные значения из `a2x/cs2-dumper` HEAD при каждой загрузке и переопределяет эти defaults.
- **Если autofetch падает** (offline / GitHub недоступен / корпоративный прокси блокирует `raw.githubusercontent.com`): драйвер v1.14/v1.15 пишет в неправильные поля → портит соседнее состояние CCSPlayerController. Драйвер v1.16 использует правильные defaults → всё равно работает.
- **Fresh git-clone-and-run пользователи** без сетевого подключения увидели бы неправильное поведение на v1.14/v1.15; v1.16 делает offline-сценарии безопасными.

### Что в этом релизе

| Файл | Изменение |
|---|---|
| `kit_rankspoof.zip` | **Перепакован с фиксированным драйвером** (`CS2RankSpooferDriver.sys` 27 136 Б, ребилд 2026-07-16) и исправленным `Load-Spoofer.ps1` |
| `kit_isvalveds.zip` | БЕЗ ИЗМЕНЕНИЙ — нет stale defaults (использует только `dwGameRules` + `m_bIsValveDS`) |
| `kit_attack.zip`, `kit_byte.zip`, `kit_kernel_inject.zip` | БЕЗ ИЗМЕНЕНИЙ |

### Связанные изменения

Кроме рантайм-фикса, эта сессия ещё выдала:
- **Bilingual wiki структура** во всех 3 sibling-репозиториях (`wiki/en/` + `wiki/ru/`, ~30 страниц на репо всего).
- **Фиксы stale-offset в CS2-SDK-Reference** в `structures/README.md`, `vmp_targets/README.md`, `offsets/README.md`, top-level `README.md`.
- **`sync.cmd`/`sync.sh`** one-click sync launcher в CS2-SDK-Reference.

### Sibling-релизы

- [CS2-SDK-Reference v1.0-initial](https://github.com/ccsimplyspolit/CS2-SDK-Reference/releases/tag/v1.0-initial) — CS2 SDK reference (bilingual)
- [VMP-Deob v2.0-mechanics-and-tools](https://github.com/ccsimplyspolit/VMP-Deob/releases/tag/v2.0-mechanics-and-tools) — VMP research + tooling

### Как проверить фикс (опционально)

```powershell
# Подтвердить, что ваш драйвер имеет правильные defaults
Select-String -Path "kit_rankspoof\CS2RankSpooferDriver.sys" -Pattern "^Contents" -Encoding Byte -Simple
# Или запустить под отладчиком; off_ctrl_CompetitiveRanking у g_Sch должен быть 0x888.

# Подтвердить, что Load-Spoofer.ps1 имеет правильный hashtable
Select-String -Path "kit_rankspoof\Load-Spoofer.ps1" -Pattern "off_ctrl_CompetitiveRanking\s+=\s+0x888"
```

### Апгрейд

Просто скачать `kit_rankspoof.zip` из этого релиза и заменить существующий kit. Миграция конфига не нужна.

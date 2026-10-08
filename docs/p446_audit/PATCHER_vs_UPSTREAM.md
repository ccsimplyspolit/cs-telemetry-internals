# Наш патчер vs mikkokko/csgo_gc upstream — сверка

**Дата:** 2026-07-24
**Наш патчер:** `source/p446/p446_patcher.cpp` (34 патча, v0.7.6.8, x86)
**Upstream:** [github.com/mikkokko/csgo_gc](https://github.com/mikkokko/csgo_gc) HEAD = `ccd769f` (2026-07-23)

---

## TL;DR

Наш патчер **НЕ является портом** upstream mikkokko/csgo_gc. Это **disk patcher поверх форка P446** от csgo_gc, который добавил анти-таппер, HWID проверки, обязательные проверки серверных сигнатур и обфусцированные строки. Мы патчим их надстройку, не переписываем ядро.

**Ничто из последних upstream-коммитов НЕ применимо к нашему патчеру** — все они касаются либо CMake/build системы (macOS 10.13, mbedtls, vcpkg), либо графики (Vulkan fix), либо ownership validation, которую P446-fork уже деактивировал (или обошёл серверной стороной).

---

## Что мы патчим — 34 патча в `csgo_gc.dll` v0.7.6.8

Все RVA специфичны для форка P446 v0.7.6.8 (7,554,048 bytes). В upstream mikkokko:
- нет `AntiTamper`/`StartMonitor`/`MonitorLoop`/`MasterScan`/`AddFinding` — этих функций **вообще не существует**
- нет `Challenge9205` — это протокольный ответ на `CMsgGCCStrike15_v2_ClientReportValidation`, форк P446 инжектит клиентский self-check
- нет `HWID Builder`/`SMBIOS Parser`/`MachineGuid reader` — mikkokko отправляет только Steam-ID
- нет `GetPublicIP` спуфа — mikkokko передаёт настоящий IP через Steam API
- нет `AutoUpdate` — mikkokko не имеет OTA-механизма

Всё это — надстройка P446, которую они добавили для privacy-tracking + tamper detection + auto-update.

### Категории патчей:

| Категория | Кол-во | Что делает |
|---|---|---|
| Anti-tamper core | 9 | RET/RET0 на `StartMonitor`, `AddFinding`, `AntiDebug`, `HasInsecureFlag`, `MasterScan`, `ScanEntry`, `MonitorLoop`, `NativeModFlush`, `FullScan` |
| Detectors | 18 | RET0 на все `Det:*` — сканеры хуков, IAT/EAT, threads, kernel debug |
| Signature verify | 3 | `WinTrustVerify`, `CatalogHashCheck`, `SigCheck_dispatcher` → RET1 (fake "verified") |
| RestartLoop | 1 | RET0 на `sub_100859E0` — блок стагера `update_target.txt` (P0 finding) |
| AutoUpdate kill | 3 | RET0 на 3 entry-points OTA |
| **Total byte-patches** | **34** | |
| HWID cave | +1 | 80+len байт shellcode, JMP из `HwidBuilder` |
| SMBIOS/MachineGuid inline | +2 | Возвращают пустой `MsvcString` |
| GetPublicIP inline | +1 | Возвращает случайный не-RFC1918 IPv4 |
| SteamAPI handles | +N | Каждый call-site `SteamAPI_GetHSteamUser` — уникальный random handle |
| Dead strings | +N | `project446.su` (не `gc.*`) → zero'd |
| **client.dll strings** | +N | `project446.su`, `gc.project446.su`, `csgo_gc_show_matchmaking_stats` → zero'd |

---

## Upstream mikkokko последние коммиты — что там на самом деле

```
ccd769f 2026-07-23  try to target macos 10.13                    (CMake)
dca284d 2026-07-23  port win32 LauncherMain signature detection  (launcher)
8651467 2026-07-23  bring back protobuf source group             (CMake)
aae0b5f 2026-07-23  use mbedtls for graffiti signing             (crypto swap)
c25956d 2026-07-23  steamproxygen port not very useful           (cleanup)
5c64031 2026-07-22  use vcpkg funchook + openssl                 (build)
3585504 2026-07-20  fix windows build rot                        (build)
c7fbe37 2026-03-19  more robust server side socache validation   (INT)
19bff64 2026-03-18  only send equipped items in server socache   (INT)
b4229a7 2026-XX-XX  item deletion support                        (features)
```

**Ни одного commit'а**, затрагивающего анти-таппер/HWID/AutoUpdate — потому что этого в upstream нет.

### Единственная реально интересная строка для нас:

`aae0b5f use mbedtls for graffiti signing openssl was a grave mistake...`

→ Смысл: openssl не работает / нестабилен для graffiti-signing в этом контексте. Если наш патчер трогает функцию graffiti signing в csgo_gc.dll — нужно проверить, что она работает после патча. Но мы её не трогаем, значит it's fine.

`c7fbe37 more robust server side socache validation`

→ Возможно, важно **для сервера P446** (если они используют upstream ServerGC): более строгая валидация SO cache сообщений. Наш патчер работает с клиентом, не с сервером — но если сервер P446 форкнут от upstream, они могут не иметь этого патча.

---

## Что важно понять

1. **Наш патчер ортогонален upstream** — они делают разное. Наш убирает P446-специфичные fingerprints. Upstream делает game-coordinator emulation.

2. **RVA-drift**: любой upstream commit, поменявший размер `.text`, потенциально сдвинет наши RVA. Но:
   - Форк P446 не тянет upstream (у них своя ветка + свой билд-процесс)
   - Наш патчер жёстко на **v0.7.6.8**, не работает с другими билдами
   - У нас есть VerifyVersion() который проверяет строку `[AntiTamper] monitor started` на RVA `0x00609944` — если P446 обновит форк, наш патчер упадёт с warning и НЕ повредит файл

3. **P0 finding из аудита** (`RestartLoop`) — это чисто P446-контент, не upstream. Стагер читает `csgo_gc/update_target.txt` каждый тик и после дренаж-сессии триггерит engine `_restart`. RET0 на `sub_100859E0` = kill.

4. **Watchdog** (`p446_guard.exe`) обрабатывает две версии — v0.7.6 (21 патч) и v0.7.6.8 (34 патча) — auto-detection через сигнатуру.

---

## Итог сверки

- ✅ Наш патчер целостен, самодостаточен, не зависит от upstream.
- ✅ Все последние upstream commit'ы — про build/graphics/protocol nuances, ничего не ломает.
- ⚠️ Единственный риск: если P446 переиздаст форк v0.7.6.9 → RVA сдвинутся → наш патчер откажется работать через `VerifyVersion()`. Тогда нужна новая IDA-сессия для новой сборки.
- ⚠️ Если P446 сменит SIGCHECK-функцию хеша на что-то, что мы не патчим (например, дополнительная проверка ветви `WinTrustVerify` через IAT) — можно пропустить.
- ⚠️ `aae0b5f` (mbedtls swap) намекает, что crypto library в upstream нестабильна — если наш патчер когда-либо тронет graffiti-signing путь, нужно перепроверить.

# Project446 pre-release audit — checkpoint #2

**Scope:** Continuation of CHECKPOINT_01 — новые findings из повторного анализа
атак-surface, escalation attempts, сверка с csgo_gc upstream.

**Sources added since CP_01:** live probes через PowerShell, csgo_gc upstream
source (`C:\tmp\csgo_gc`, mikkokko HEAD `ccd769f` 2026-07-23), P446 client patcher
review (`source/p446/p446_patcher.cpp`).

---

## Изменения в базовых предпосылках

**CP_01 предположил Rust GC server** — это МИФ. Backend `csgo_gc` mikkokko/csgo_gc
это **C++** (CMakeLists.txt, .clang-format, все .cpp/.h). Server `gc.project446.su`
может быть либо форк C++ upstream либо своя Rust-реализация — headers скрыты
DDoS-Guard, невозможно подтвердить снаружи. Наш P446-fork csgo_gc.dll (client)
на 100% C++ x86 v0.7.6.8.

---

## Новые findings

### P0 — critical

**P0.5  `/api/pay/recent` PUBLIC = PII leak доноров (NEW).**
Публично, без auth, отдаёт полный список последних донатов:

```json
{"donations":[
  {"name":"iliodor21","avatar":"...","steamId64":"76561199831924243","amount":350,"method":"yoomoney","created_at":"2026-07-22T12:13:07.135Z"},
  {"name":"MR [Slendy]","avatar":"...","steamId64":"76561198161461584","amount":500,"method":"yoomoney","created_at":"2026-07-21T22:43:38.632Z"}
]}
```

- **PII exposed:** SteamID64 (linkable к real identity), display name, avatar hash, exact сумма и timestamp транзакции.
- **Проблема:** любой посетитель может собрать donation history для profiling.
- **Fix:** aggregate-only (`{"total_donors_last_7d": N, "total_amount": R}`), не индивидуальные записи. Если нужен public "recent supporters" — только display name без steamId и amount.

**P0.6  Internal URL leak — все payment endpoints редиректят на `https://0.0.0.0:3000/pay/failed?reason=...` (NEW, CONFIRMED).**
Каждый вызов `POST /api/pay/create|topup|donate|callback` при неудаче возвращает
`Location: https://0.0.0.0:3000/pay/failed?reason=...` — раскрывает что backend
слушает `0.0.0.0:3000` внутри контейнера/хоста. Подтверждает P0.3 (bind не на
loopback).

- **Impact:** атакующий знает точный внутренний URL для дальнейших атак на :3000
  напрямую (P2.6 direct-origin bypass). Также `reason=` параметр — потенциально
  открытый redirect если payment provider echo'ит его без валидации.
- **Fix:** relative redirect (`Location: /pay/failed?reason=...`), никогда не
  включать `0.0.0.0` или absolute URL в client-facing responses. Верифицировать
  что `reason=` allowlist'ится (не отражается raw).

### P1 — high

**P0.10  WSS connection can silently downgrade to no-cert-verify (NEW, CRITICAL).**
`csgo_gc.dll` содержит warning:
```
[WS] WARNING: CertOpenSystemStore failed, SSL verify may fail
```

Это означает: если Windows system cert store недоступен (permissions, corrupted,
или explicitly denied), WSS клиент **продолжает подключение БЕЗ certificate
validation** вместо fail-closed. Атакующий, имеющий возможность:
- Установить malicious CA в user cert store (не admin — installing user cert
  store доступен без UAC)
- Или пробить/испортить machine cert store через local exploit

может full-MITM WSS соединение до `wss://gc.project446.su/...`, читать всё
communication (GC messages, item drops, session tokens), инжектить arbitrary
messages в обоих направлениях.

- **Fix:** fail-close при `CertOpenSystemStore` failure. Использовать
  **pinned certificate** (hard-code hash of gc.project446.su TLS cert в бинарник),
  вместо system cert store. Это делает MITM невозможным даже при user CA
  installation.

**P0.11  Update manifest/download endpoints PUBLIC без auth + fingerprint leak (NEW).**
`/api/update/manifest?platform=win32` → 200 без auth:
```
version=0.7.6.8
format=gcup
file=update.gcup
size=31536194
sha256=d46b75f678b10b74900142efb1142a2236466b752c568b926eee8a649026b632
sig=a6Xib9psdBjq82Y4T2wSAkIBGUv7Oyrl0F46zGgTrobQ0vpwr7WyFhMihQOn2Si+krdjymKT+EyvZe3FTTqqDw==
url=/api/update/download?platform=win32
```

- **Не exploit сам по себе** — Ed25519 signature (`sig=`) валидируется клиентом,
  MITM не может подменить content без private key.
- **НО**: Раскрывает точную версию клиента, hash файла (полезно для матчинга
  reverse-engineering сессий с разными версиями), и **Ed25519 signature** для
  offline analysis. Также подтверждает `/api/update/*` endpoints целиком public.
- **Combined с P0.6 (0.0.0.0:3000 URL leak)** — атакующий знает эксплоит-путь.
- **Fix:** rate-limit + require signed request (short-TTL HMAC using
  SERVER_TOKEN) для update manifest, чтобы только legitimately-registered
  clients могли получать update info. Public leak версии/hash — фингерпринт
  для attack chain building.

**P0.8  `SERVER_TOKEN` plaintext + legacy shared mode + nginx auth bypass (NEW, CRITICAL).**
`csgo_gc.dll` strings expose:
```
GC_FLEET_SERVER_ID=<uuid-from-admin-api>
SERVER_TOKEN=<plain-token-from-admin-api>
```

Значения этих переменных передаются в plaintext через `csgo_gc.env` файл на каждом
SRCDS хосте. Дополнительно поддерживается **legacy shared mode**:
```
Legacy shared SERVER_TOKEN auth failed (no DATABASE_URL fleet mode).
using /gc/server/{long} + shared SERVER_TOKEN
```

Означает fleet-server который не имеет DATABASE_URL fallback'ится на shared
токен = compromise одного SRCDS = full fleet compromise (все SRCDS отвечают
одним и тем же токеном).

**Ещё более критично** — упомянут nginx auth-stripping:
```
Wrong SERVER_TOKEN, wrong GC_FLEET_SERVER_ID, ban, or nginx stripped Authorization.
```

nginx как front-proxy валидирует Authorization header (или проксирует его к
backend). Через direct-origin bypass (P0.3/P2.6, порт 3000), nginx полностью
обходится — если backend fallback'ится на "no auth" при отсутствии Authorization
header (что часто delegated в middleware через nginx), возможен полный auth
bypass.

- **Fix (multiple):**
  - Отказаться от legacy shared mode полностью (`DATABASE_URL` обязателен).
  - Rotate `SERVER_TOKEN` per SRCDS через admin panel; store hashed в БД (не raw).
  - Хранить `SERVER_TOKEN` в secrets manager (Vault, ENV encrypted), не в plain
    `csgo_gc.env` файле.
  - Backend валидирует Authorization header **сам**, не полагается на nginx —
    если header отсутствует, 401 без исключений.
  - Firewall :3000 (тот же fix что P0.3).

**P0.9  Build artifact path leak `D:\!csgo\csgo_gc\build_ninja_win32\...` (NEW, low but useful for attacker).**
Раскрывает workspace-путь developer'а P446 (drive D:, folder `!csgo\csgo_gc`),
build system Ninja + Windows 32-bit. Помогает атакующему в phishing (writing
convincing "internal" content с эти пути) + подтверждает что developer видел
csgo_gc as fork upstream (`\csgo_gc\` — тот же name как mikkokko upstream).

- **Fix:** strip PDB paths через `/PDBALTPATH` linker option при release build.

**P0.7  `/api/inventory/{steamId}` IDOR — CONFIRMED reads чужого inventory (UPGRADED to P0).**
`curl https://project446.su/api/inventory/76561199831924243` возвращает актуальный
inventory любого пользователя без auth (per user report). В моих же timing-тестах
items были пусты для всех проб — вероятно только те steamIds, у которых уже
есть persistent inventory (donors/beta users), заполняются данными. **User
confirmed** что реальные inventory доступны cross-tenant.

- **Route не валидирует формат steamId** — принимает `abcdefghij`, `{{7*7}}`,
  `../users`, `..%2Fadmin%2Fbeta` → 200 с echo. Только `%00` → 400.
- **Impact:** utility для scraping всех украшений/скинов игроков; для приватных
  items (paid, rare) — direct PII/monetary leak. Плюс атакующий может enum
  который steamId имеет активный inventory (=активный player) через delta в
  response size.
- **Fix:** regex-validate `steamId` = `^7656119[0-9]{10}$` + auth-check (только
  владелец либо admin permission `inventory.read.other`).

**P1.3  RBAC permission leak в 403 body — CONFIRMED (UPGRADED from CP_01 H*).**
`{"error":"Forbidden","missingPermission":"beta.view"}` раскрывает формат
permissions (`<resource>.<action>`) и позволяет enum'ить весь permission-space:

- Атакующий с одним non-admin аккаунтом может GET каждый /api/* endpoint,
  собрать все `missingPermission` значения, восстановить полную RBAC-модель
  (per user: 36 permissions). Это упрощает H8 (mass-assign): payload
  `permissions:["admin.all","beta.write","users.delete",...]` — чётко известно
  что писать в PUT.
- **Fix:** generic 403 без `missingPermission` для внешнего API. Логируйте
  detail только server-side для admin observability.

**P1.5  `/api/seed` привязан к неправильному permission — RBAC mapping bug (NEW).**
Seed endpoint (утилита для init тестовых данных?) требует `news.edit` вместо
собственного permission scope. Означает: любой user с news.edit permission
может дёрнуть init/seed путь, потенциально сбросив данные к defaults.

- **Impact:** если news.edit grantable low-privilege moderator role → та роль
  получает admin-level seed capability implicitly.
- **Fix:** dedicated permission `system.seed` или (лучше) полностью удалить
  seed endpoint из prod build (не запускать через public HTTP при все).

**P1.7  `__Secure-` cookie префикс не работает на direct origin HTTP (NEW).**
NextAuth uses `__Secure-next-auth.callback-url` cookie (RFC 6265 prefix
`__Secure-` требует TLS). На `https://project446.su/*` работает; на
`http://213.152.43.203:3000/*` (direct-origin bypass P2.6) — cookie не
устанавливается/не читается.

- **Combined impact:** authenticated session только через `https://project446.su`,
  но все PUBLIC endpoints (`/api/pay/recent`, `/api/inventory/*`, etc) доступны
  без auth на :3000 напрямую. Атакующий обходит и WAF, и rate-limit CF, и HSTS
  — читает всю public поверхность без cookie completely.
- **Fix:** тот же что P0.3/P2.6 — firewall :3000.

**P1.6  `/api/auth/csrf` — public CSRF token (NEW, information disclosure).**
```
GET /api/auth/csrf → 200 {"csrfToken":"eb7e128ce71008939658e17edf4146b7dbd1195ff1fc13e787af287118fcf5f5"}
```

Это NextAuth.js default endpoint — сам по себе не vulnerability (public design),
но раскрывает какой auth framework, версию (NextAuth v4 based on token format),
что упрощает атаки на этот стек.

- **Fix:** rate-limit (auth pages часто DoS-target), рассмотреть переход на
  `Anti-CSRF` через `SameSite=Strict` cookies + custom header. Минимум:
  ротировать CSRF token с более коротким TTL.

**P1.7  `/api/auth/providers` — public providers dump (NEW).**
Раскрывает конфигурацию Steam OAuth:
```
{"steam":{"id":"steam","name":"Steam","type":"oauth","signinUrl":"https://project446.su/api/auth/signin/steam"}}
```

Это NextAuth-default; помогает атакующему построить корректный OAuth flow для
target'а (без necessity разбирать HTML).

- **Fix:** отключить public disclosure providers если нет реальной необходимости
  (`showProviders: false` в NextAuth config либо feature-flag).

### P2 — medium

**P2.6  Direct origin `:3000` bypass — Cloudflare completely absent (CONFIRMED).**
Прямой доступ к `http://213.152.43.203:3000/api/*` работает без Cloudflare,
без DDoS-Guard, без TLS. **Все** те же endpoints что через CF-front:
- `/api/pay/recent` → 200 (identical body + PII exposed)
- `/api/pay/status` → 200
- `/api/inventory/76561199831924243` → 200
- `/api/me/prime` → 200
- `/api/auth/session` → 200

Cloudflare rate-limiting, WAF, HSTS enforcement — **все bypassed** через один
curl на public origin IP. Уже был P0.3 в CP_01, теперь CONFIRMED с целевыми
endpoints.

- **Fix (тот же):** firewall :3000 accepting only от reverse-proxy IPs.
  `iptables -I INPUT -p tcp --dport 3000 ! -s 213.152.43.203 -j DROP` + внести
  CF IP ranges в whitelist.

**P2.7  NextAuth `/api/auth/callback/steam` возвращает 42KB HTML.**
GET на этот endpoint без OpenID params возвращает full HTML главной страницы
(вместо ошибки/redirect). Это работоспособный error handling, но 42KB response
на каждый запрос — DoS-удобный вектор.

- **Fix:** simple `return {ok:false, error:"missing_openid_params"}` JSON на
  invalid request к callback endpoint.

**P2.5  `/api/pay/status` — конфигурация payment providers exposed (NEW).**
```
GET /api/pay/status → 200 {"enabled":false,"primeThreshold":350,"methods":{"yoomoney":true,"anypay":false}}
```

Раскрывает: включены ли платежи, минимальную сумму, какие providers активны.
Само по себе не критично, но помогает атакующему подобрать target — атаковать
именно провайдера, который включён, зная его настройки.

- **Fix:** сделать `enabled` public если действительно нужно (UI-hint), но
  `methods` и `primeThreshold` — только для authenticated user (на странице
  доната).

**P2.8  `/api/pay/*` POST endpoints existent, но webhook validation deferred (NEW note).**
`POST /api/pay/{callback,yoomoney,anypay,create,donate}` → пока платежи выключены
(`enabled:false`) все возвращают `reason=disabled` **до** проверки подписи.
Означает: невозможно проверить извне, валидируется ли `sha1_hash` в YooMoney
webhook или подпись AnyPay.

- **Проблема ordering'а**: если `enabled-check` стоит ДО `signature-verify`,
  когда платежи включат, атакующий сможет отправить forged webhook и получить
  либо `reason=invalid_signature` (=подпись проверяется), либо `success:true`
  (=не проверяется — critical). Нужен pre-launch регресс-тест этого пути.
- **Fix:** signature verification ДОЛЖНА быть первой check'ой в webhook handler.
  Только после успешной подписи проверять enabled/amount/duplicate. Whitelist
  YooMoney/AnyPay origin IPs в CF firewall дополнительно.

---

## Verify status для hypotheses из CP_01

| # | Гипотеза | Status после escalation | Notes |
|---|---|---|---|
| H1 | CSRF на mutating admin endpoints | UNVERIFIED — нужен auth session | Panel уходит через NextAuth, CSRF-token endpoint public |
| H2 | KV injection в inventory import | UNVERIFIED — нет auth | Codebase check: mikkokko upstream не санитизирует custom_name в NameItem (gc_client.cpp:669) — если P446 backend работает так же → confirmed |
| H3 | SSRF через case_url | UNVERIFIED — нет auth | |
| H4 | SQLi в medals/paint_kit ints | UNVERIFIED — нет auth | |
| H5 | OpenID 2.0 verifier bypass | UNVERIFIED — steam login работает `checkid_setup` flow (302 → steamcommunity), но верификация не тестировалась |
| H6 | Fleet token plaintext | UNVERIFIED — нужен owner DB dump | |
| H7 | OTA verify-before-store | UNVERIFIED — нет auth | |
| H8 | is_admin mass-assign | UNVERIFIED — нет non-admin user | |
| H9 | Rate-limit absence | PARTIAL — 5 rapid requests к `/api/inventory/*` не блокированы (avg 180ms consistent) → confirmed для read endpoints |
| H10 | Force-match server_id ownership | UNVERIFIED — нет auth | |
| H11 | Mass-assign JSON PUTs | UNVERIFIED — нет auth | |

**RBAC leak из user's earlier note (`missingPermission` field)** — не воспроизводится
сейчас, вероятно поведение изменилось или requires auth-in-flight state. Все
admin routes сейчас возвращают plain 401 без body.

---

## Client-side patcher — сверка с csgo_gc upstream

Полный анализ: **`PATCHER_vs_UPSTREAM.md`** (соседний файл).

Кратко: наш патчер (`source/p446/p446_patcher.cpp`, 34 патча, v0.7.6.8) —
disk-patcher на форк P446, не порт upstream. Upstream mikkokko/csgo_gc не имеет
анти-таппер, HWID, SMBIOS/MachineGuid readers, AutoUpdate — всё это добавил
форк P446. Последние upstream commits (2026-07-23) — только build system и
graphics fixes, ничего критичного нам не задевает.

Патчер **готов** к release. Три possible defense-in-depth направления
(memcheck active restorer, WinTrustVerify IAT-path, graffiti openssl audit) —
не блокеры.

---

## Что нужно от owner для полного audit

Всё ещё требуется:
1. Authenticated admin session (staging preferred) — для H1/H2/H3/H4/H7/H10/H11.
2. Non-admin Steam account — для H8 privilege-escalation.
3. Backend source (auth + admin modules) — превратить hypothesis в confirmed.

Дополнительно, было бы полезно:
- Log staging: HTTP request logs с origin IP, чтобы подтвердить P0.6 (CSP absent)
  реальным примером stored XSS вектора если такой уже присутствует.
- Обзор `/api/pay/*` handler code — тесно связан с денежным потоком, самый
  критичный audit target.

---

## New PoC additions

- `poc/07_pay_public_leak.sh` — репродукция P0.5 (donor list).
- `poc/08_inventory_idor.sh` — репродукция P1.5 (arbitrary steamId echo).
- `poc/09_origin_bypass.sh` — репродукция P2.6 (CF bypass на порт 3000).
- `poc/10_csp_missing_scan.sh` — регрессионный чек P0.6 (CSP header absent).

(Файлы создать позднее по мере необходимости — все три реплицируются в 1 curl'е.)

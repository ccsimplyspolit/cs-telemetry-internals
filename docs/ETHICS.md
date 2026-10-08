# Ethics and legal boundaries / Этика и правовые рамки

**[EN](#english) · [RU / Русский](#русский)**

An extended companion to the notice in the root [`README.md`](../README.md). / Развёрнутое дополнение к notice'у в корневом [`README.md`](../README.md).

Read this once before building or running anything from this repository. / Прочти это один раз до сборки или запуска чего-либо из репозитория.

---

## English

### Short version

- This is defensive-research material. Publication does not grant permission to run this against Valve's live services.
- Such use violates the Steam Subscriber Agreement, CS2 EULA, and in a number of jurisdictions, computer-misuse statutes. Risk: account, and in extreme cases — freedom.
- No "it's only a research build" changes the fact that injecting into `cs2.exe` while connected to matchmaking is an unauthorised modification of a running service.

### In detail

#### Why study VacLiveBypass at all

Anti-cheat teams need to understand adversary techniques to build defensive measures. VMProtect-obfuscated protobuf-mutation DLLs targeting client-side sub-tick state — a real class of adversary tools. Source-first port is the shortest path to understanding one. This is the mandate of this repository.

Output — documented 13-phase mutation pipeline with byte-level disasm anchors and chronological crash log — directly consumable for:

- server-side detection engineers writing heuristics for the *shape* of mutation (`has_bits |= 0x1E01` markers, `input_history` growth patterns, `aux` float distribution),
- reverse engineers studying VMProtect unpacking and post-unpack RVA mapping,
- protobuf implementors studying `RepeatedPtrField` invariants under adversarial mutation,
- Windows in-process hook developers looking for MinHook install pattern with retry and PDB fallback.

None of them need a working cheat. They need a readable reference for the class of techniques. That's what this repo publishes.

### What we do NOT publish

- No packaged, one-click injector.
- No compiled binaries in Releases ready to inject against a live server (the DLL we ship is the one that BAILS during Phase 9, doesn't spoof anything).
- No documentation on obtaining the reference DLL from the original distribution channel.
- No workarounds for VAC runtime memory scanning.

### Statutes

If interested in the specific legal frameworks referenced by `README.md`:

#### USA — 18 U.S.C. § 1030 (Computer Fraud and Abuse Act)

`§ 1030(a)(2)` criminalizes knowingly accessing a computer without authorisation or exceeding authorised access, and thereby obtaining information from any protected computer. Matchmaking servers are "protected computers" under § 1030(e)(2)(B). Ninth Circuit's *hiQ Labs v. LinkedIn* narrowed CFAA reach on "gates-down" scenarios, but game servers are exactly it: TOS defines gates at the moment of connect.

`§ 1030(a)(5)(A)` — knowingly causing the transmission of a program that intentionally causes damage without authorisation. Protobuf-mutation DLL against live matchmaking arguably qualifies as soon as it degrades match integrity.

#### UK — Computer Misuse Act 1990

`§ 1` — "Unauthorised access to computer material" — up to 2 years imprisonment.
`§ 3` — "Unauthorised acts with intent to impair" — up to 10 years. Applies to acts committed in UK or with "significant link" to UK, which includes running a modified client from a UK internet connection against a service terminating in UK.

#### Germany — Strafgesetzbuch (StGB)

`§ 202a` — "Ausspähen von Daten" — 3 years imprisonment or fine for access to protected data without authorisation. `§ 303a` — "Datenveränderung" — 2 years or fine for unauthorised alteration of data. `§ 303b` — "Computersabotage" — 3 years or fine, when alteration disrupts business-critical data-processing operation.

#### Steam Subscriber Agreement (SSA) & CS2 EULA

`SSA § 2.C` prohibits use of Steam client "in any manner that is not in accordance with … documented functionality". `SSA § 3.A.iv` prohibits "circumvent[ing] or modif[ying] any technological measure taken to protect the Steam Content and Services". CS2 EULA § 4 repeats these prohibitions specific to CS2 gameplay integrity.

VAC bans — contractual. They do not require a court order. Once a VAC ban happens, Steam's dispute-resolution clause routes appeals to an arbitrator, not to court. In practice VAC bans are permanent.

### Practical guide

- **DO NOT inject** anything from this repository into `cs2.exe` while Steam thinks you are in matchmaking, warm-up queue or competitive lobby. VAC is watching.
- **CAN inject** into local `cs2.exe` launched on offline `map de_dust2` with bots — for reverse-engineering, if trace-log evidence is needed for research.
- **DO NOT publish** videos, screenshots or trace logs from live matchmaking showing you were running an experimental build. You will be the first Steam bans when the heuristic catches the shape.
- **CAN contribute** — the port is intentionally incomplete so it CANNOT be run against production. Keeping it this way is a virtue, not a bug.

### Reporting misuse

If you find someone distributing a compiled build derived from this repository as a working cheat — send a report to `cc.simply.spolit@gmail.com` with URL and any archived evidence. We'll go to Valve Steam Security team and, if necessary, to `github/dmca` or equivalent takedown surface for the host.

---

## Русский

### Кратко

- Это defensive-research материал. Публикация не даёт разрешения запускать
  это против live-сервисов Valve.
- Такое использование нарушает Steam Subscriber Agreement, CS2 EULA, а в
  ряде юрисдикций — computer-misuse statutes. Риск: аккаунт, а в экстремальном
  случае — свобода.
- Никакое "это только research build" не меняет факта, что инжект в `cs2.exe`
  при подключении к matchmaking — unauthorised modification of a running service.

### Подробно

#### Зачем VacLiveBypass вообще изучать

Anti-cheat командам нужно понимать техники adversary, чтобы строить defensive-меры.
VMProtect-обфусцированные protobuf-mutation DLL'ы, таргетирующие client-side sub-tick
state — реальный класс adversary-инструментов. Source-first порт — кратчайший путь
к пониманию одного из них. Это — мандат этого репозитория.

Выход — задокументированный 13-фазовый mutation pipeline с byte-level disasm anchors
и хронологическим crash log'ом — напрямую consumable для:

- server-side detection инженеров, пишущих эвристики для *формы* мутации
  (`has_bits |= 0x1E01` маркеры, `input_history` growth patterns, `aux` float distribution),
- reverse engineers, изучающих VMProtect unpacking и post-unpack RVA mapping,
- protobuf implementors, изучающих `RepeatedPtrField` инварианты под adversarial mutation,
- Windows in-process hook developers, ищущих MinHook install паттерн с retry и PDB fallback.

Никому из них не нужен working cheat. Им нужен readable reference для класса техник.
Это репо публикует именно это.

#### Что мы НЕ публикуем

- Нет packaged, one-click инжектора.
- Нет compiled бинарей в Releases, готовых к инжекту против live-сервера (DLL,
  который мы шипаем, — тот, который BAIL'ит во время Phase 9, ничего не spoof'ит).
- Нет документации по получению reference DLL из оригинального distribution channel.
- Нет обходов VAC runtime memory scanning.

#### Статьи

Если интересуют конкретные legal frameworks, на которые ссылается `README.md`:

##### США — 18 U.S.C. § 1030 (Computer Fraud and Abuse Act)

`§ 1030(a)(2)` криминализирует knowingly accessing a computer without authorisation
or exceeding authorised access, and thereby obtaining information from any protected
computer. Matchmaking серверы — "protected computers" под § 1030(e)(2)(B). Ninth
Circuit'ская *hiQ Labs v. LinkedIn* narrowed CFAA reach на "gates-down" сценарии,
но game servers — именно оно: TOS определяет gates в момент connect'а.

`§ 1030(a)(5)(A)` — knowingly causing the transmission of a program that intentionally
causes damage without authorisation. Protobuf-mutation DLL против live matchmaking
arguably qualifies, как только он degrade'ит match integrity.

##### Великобритания — Computer Misuse Act 1990

`§ 1` — "Unauthorised access to computer material" — до 2 лет заключения.
`§ 3` — "Unauthorised acts with intent to impair" — до 10 лет. Применяется к
актам, совершённым в UK или с "significant link" к UK, что включает запуск
модифицированного клиента с UK internet connection против service, оканчивающегося в UK.

##### Германия — Strafgesetzbuch (StGB)

`§ 202a` — "Ausspähen von Daten" — 3 года заключения или штраф за доступ
к protected данным без authorisation'а. `§ 303a` — "Datenveränderung" — 2 года
или штраф за unauthorised alteration данных. `§ 303b` — "Computersabotage" —
3 года или штраф, когда alteration disrupt'ит business-critical data-processing operation.

##### Steam Subscriber Agreement (SSA) & CS2 EULA

`SSA § 2.C` запрещает use of Steam client "in any manner that is not in accordance
with … documented functionality". `SSA § 3.A.iv` запрещает "circumvent[ing] or
modif[ying] any technological measure taken to protect the Steam Content and Services".
CS2 EULA § 4 повторяет эти prohibitions специфично для CS2 gameplay integrity.

VAC bans — contractual. Они не требуют court order. Как только VAC ban случился,
Steam's dispute-resolution пункт направляет appeals к arbitrator'у, не в суд.
На практике VAC bans permanent.

#### Практический гайд

- **НЕ инжекти** ничего из этого репозитория в `cs2.exe`, пока Steam думает, что
  ты в matchmaking, warm-up queue или competitive lobby. VAC watching.
- **МОЖНО инжектить** в локальный `cs2.exe`, запущенный на offline `map de_dust2`
  с ботами — для reverse-engineering, если trace-log evidence нужен для research.
- **НЕ публикуй** видео, скриншоты или trace-логи из live matchmaking, показывающие,
  что ты гонял experimental build. Ты будешь тем, кого Steam забанит первым, когда
  эвристика поймает форму.
- **МОЖНО контрибьютить** — порт намеренно неполный, чтобы его НЕЛЬЗЯ было запускать
  против production. Держать так — добродетель, а не баг.

#### Reporting misuse

Если нашёл кого-то, распространяющего compiled build, derived from этого репозитория,
как working cheat — пришли отчёт на `cc.simply.spolit@gmail.com` с URL и любыми
archived evidences. Мы пойдём в Valve Steam Security team и, при необходимости,
в `github/dmca` или equivalent takedown surface для host'а.

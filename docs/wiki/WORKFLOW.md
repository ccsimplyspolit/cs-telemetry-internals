# Development Workflow

Всё в одном месте: сборка, инжект, наблюдение, воспроизведение.

Инструменты:

- Visual Studio 2022 Community с *Desktop C++* workload (MSBuild 17.14+).
- Git (любой свежий).
- Cheat Engine 7.6+ с `cheatengine-mcp` bridge (автоматический инжект);
  ручной инжект через `CE → Process → Open → Cheat Engine → Auto Assemble` тоже работает.
- IDA Pro 8.4+ с Hex-Rays для реверса.
- Копия `cs2.exe` (Steam retail подходит).

---

## 1. Сборка DLL

```powershell
& "C:/Program Files/Microsoft Visual Studio/2022/Community/MSBuild/Current/Bin/MSBuild.exe" `
  "source/dlls/VacLiveBypass.sln" `
  -p:Configuration=Release `
  -p:Platform=x64 `
  -verbosity:minimal
```

Выход в `source/dlls/x64/Release/VacLiveBypass.dll` (~256 KB).
Warning `D9025` про `/GS-` override — ожидаемый и безобидный: MinHook prologue
patching плохо дружит с `/GS` cookies.

Копируем в `builds/` с датой, чтобы можно было бисектить регрессии:

```bash
cp source/dlls/x64/Release/VacLiveBypass.dll \
   builds/VacLiveBypass_$(date +%F)_x64.dll
```

Файлы `builds/*.dll` force-added в git (см. `.gitattributes`) — timestamped
артефакты попадают в историю вместе со своим коммитом.

---

## 2. Запуск cs2 с открытой консолью

Хук `hkUserCmdFinalize` срабатывает только когда локальный игрок в карте
или на локальном разогреве — тестировать subtick мутацию имеет смысл только
в live-сессии. Запуск через Steam с `-console`, чтобы developer-консоль была
доступна для `map de_dust2`:

```powershell
Start-Process "steam://run/730//-console"
```

Ждём процесс:

```powershell
$deadline = (Get-Date).AddSeconds(90)
$pid = $null
while ((Get-Date) -lt $deadline -and -not $pid) {
  try { $p = Get-Process cs2 -ErrorAction Stop; $pid = $p.Id }
  catch { Start-Sleep -Milliseconds 500 }
}
```

---

## 3. Инжект

Cheat Engine `injectDLL` API — путь наименьшего сопротивления:

```lua
-- внутри CE Lua Engine
injectDLL([[C:\Users\sshunko\source\repos\MyDriver23\builds\VacLiveBypass_2026-07-06_x64.dll]])
```

Anti-injection кикает в какой-то момент во время старта CS2 — инжектим **рано**,
идеально в первые 30 секунд после того, как процесс поднят. Если `injectDLL`
возвращает `false` — перезапускаем cs2 и повторяем.

Если `mcp__cheatengine__inject_dll` подключён:

```
open_process(pid=<cs2 pid>)
inject_dll(filepath=…, skip_symbol_reload=true)
```

Note: инжект **после** того, как cs2 полностью присоединился к паблик-серверу,
провалится — VAC-adjacent memory-protection хуки блокируют `VirtualAllocEx` от
external процессов. Перезапускаем cs2 чтобы разлочить.

---

## 4. Наблюдение

`logs/fv_trace.log` открывается для exclusive write (`_SH_DENYWR`) лениво на
первом log-вызове. Смотрим:

```bash
tail -F logs/fv_trace.log
```

Или фильтруем только grow-path traces:

```bash
tail -F logs/fv_trace.log | grep -E "RPFA|RPFR|subtick"
```

Ключевые вехи, которые должны быть видны:

1. **Startup**: `=== VacLiveBypass runtime log (fresh) ===`, потом pattern-scan
   строки со списком резолвнутых адресов.
2. **Первый `hkUserCmdFinalize`**: `serialize #1 enter this=… via=UserCmdFinalize`.
3. **Mutation phases 1-9**: `#N phase1 …` через `#N phase9 subtick_loops=…`.
4. **Subtick trace**: `#N subtick[0] before …` через `#N subtick[15] append DONE`.
5. **BAIL** (пока Phase E.2 не готова): `#N subtick BAIL: accessor_src=NULL`.
6. **Serialize return**: `#N after_mutation_body — returning ret=1 to game serialize`.

Если последняя строка — на полпути через subtick trace, cs2 крашнулся на этом
байте. Grep выше по последнему успешному `RPFA EXIT` — там stable state перед крахом.

---

## 5. Детерминистическое воспроизведение крешей

Subtick loop управляется реальным input'ом игрока. Чтобы повторить:

1. Запускаем cs2 с `-console -insecure` (обход VAC handshake wait).
2. In-game consle: `map de_dust2` (стартует бот-игру).
3. В карте — двигаем мышью ~5 секунд, чтобы `input_history` наполнился до ~16
   pre-existing entries, и переходы Case B2 → Case C реально фаяли. Статичные
   viewangles попадают только в Case B2 и никогда не показывают Case C баги.

Сравнивать crash-repro между `.gitignore`'d локальными настройками удобно через
`bin/repro.cfg` в cs2's `csgo/cfg/`, который биндит `wheelup` → `+jump`, `wheeldown`
→ 720° yaw-flip, `mouse1` → `+attack`. Кадры с `+attack` — где `has_bits |= 0x400`
(bit 10) переключается.

---

## 6. Бисект

Каждый коммит в `main` соответствует discrete crash-chain milestone. Используем
как границы бисекта:

- `7b163f235f3d` — subtick BAIL guard (сейчас HEAD).
- `58fbe8a6276e` — Case C shim.
- `14f8a2e6ebd8` — Case A `++*inner` fix + Reserve trace.

Чтобы воспроизвести старый билд:

```bash
git checkout <sha>
MSBuild.exe source/dlls/VacLiveBypass.sln -p:Configuration=Release ...
```

Потом инжект — и смотрим, какой crash возвращается.

---

## 7. Re-generation IDA analysis артефактов

Под `analysis/`:

```
functions.json           — полный список функций FuckVacV2_dump.dll
globals.json             — data section globals
rdata_blobs.json         — .rdata литерал блобы (Base64 signatures здесь)
wf1_decomp.json          — batched Hex-Rays декомпиляции
wf1_map.json             — cross-ref matrix
```

Регенерируем:

```bash
python scripts/generate_offsets.py
python scripts/verify_rvas.py
```

Оба скрипта разговаривают с IDA MCP bridge (`mcp__plugin_ida-pro_idalib__*`)
и сбрасывают JSON в `analysis/`. Перед запуском убедиться, что в IDA загружен
target `.i64` и MCP-сервер прибинжен.

---

## 8. Частые проблемы

- **`injectDLL` возвращает false молча**: наиболее частая причина —
  cs2's anti-inject уже активен. Перезапустить cs2 и инжектнуть раньше.
  Вторая по частоте: DLL уже загружен предыдущей сессией — loader молча отказывает
  double-load'ить тот же module. Переименуй DLL и попробуй снова.

- **`fv_trace.log` не растёт после инжекта**: DllMain DLL'а спавнит background-тред,
  который ждёт присутствия `client.dll` и `engine2.dll`. Если cs2 умер на старте,
  тред никогда не пройдёт module-wait loop. Смотрим `logs/inject-*.log` на
  countdown module-availability.

- **Trace log обрывается mid-frame без fault dialog'а**: cs2 крашнулся молча.
  Task Manager покажет его отсутствие. Последняя строка в trace — последний
  успешный шаг перед fault'ом.

- **Rebuild производит идентичный DLL**: MSVC делает инкрементальную компиляцию.
  Если правил `05-verbose-logging.inc`, но компилятор говорит "0 of 493 functions
  compiled" — touch'ни `dllmain.cpp` или удали `source/dlls/x64/Release/*.obj`
  и пересобери.

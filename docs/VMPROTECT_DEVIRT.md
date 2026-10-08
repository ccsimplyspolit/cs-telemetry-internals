# VMProtect devirtualization roadmap for FuckVacV2.dll (future work)

**[EN](#english) · [RU / Русский](#русский)**

---

## English

This is a **future-work** track — not part of v3.0. It documents what
a full self-devirt of `FuckVacV2.dll` would require so that a later
research session can pick it up without re-discovery.

### Why it's out of scope for v3.0

- The real `FuckVacV2.dll` is packed with VMProtect 3.6.x. The MCP
  session refused to open the packed file (`access violation reading
  0x0000000000000000` in IDB init) — VMProtect defeats static analysis
  by design.
- The `FuckVacV2_dump.dll` we already own is a **memory dump** taken
  after VMProtect's TLS callback executed. Non-VM code (protobuf,
  MinHook, string tables) is readable; VM-encrypted routines
  (log-message construction, hook installer bodies, `MH_CreateHook`
  argument setup) still live in `._I5` + `._?n` sections as opcode
  streams for the VMProtect virtual machine.
- Extracting the 5-hook installer semantics from these streams
  requires either symbolic execution or a VMProtect-specific unpacker.
  We do not need this to ship v3.0 — the runtime log (`[Debug] Hooked
  X!`) is enough to know **which** functions FuckVacV2 targets, and our
  independent resolvers (RTTI vtable slot, engine2 RVAs) let us reach
  the same targets without needing FuckVacV2's own resolver logic.

### Toolchain

If a future session decides to pursue this, the recommended stack:

1. **VMPAttack** (github.com/can1357/VMPAttack) — LLVM-based VMProtect
   3.x virtual-machine lifter. Handles VMP 3.6.x when configured with
   the right handler-key table.
2. **NoVmp** (github.com/can1357/NoVmp) — older but still effective
   VMProtect 2.x/3.x devirtualizer. Good for cross-checking VMPAttack
   output.
3. **x64dbg + VMTracer plugin** — dynamic trace of a single VMProtect
   handler execution while cs2.exe runs. Gives ground-truth semantics
   per handler, feeds back into VMPAttack.
4. **IDA Pro 9.x** with Hex-Rays — for post-devirt cleanup and manual
   type reconstruction. MCP session (`fv2pack` name reserved) will be
   able to load the devirtualized DLL after the tools above produce a
   clean PE.

### Estimated effort

Rough sizing based on published devirt writeups of similar VMProtect 3.x
targets (~2 MB `.text` + `._?n` sections):

- Handler table extraction + lifter config: 3-5 days
- Trace-refined lifter output + validation: 5-7 days
- Post-devirt IDA cleanup + hook signature capture: 2-3 days
- **Total: ~2-3 weeks of focused work**

### Deliverable if pursued

If devirt succeeds, checkpoint the artifacts into:

```
ida_work/FuckVacV2_devirtualized_by_us/
  FuckVacV2_devirt_v1.dll        # clean PE produced by VMPAttack
  FuckVacV2_devirt_v1.dll.i64    # IDA IDB with reconstructed types
  hook_installer_bodies.md       # cleaned-up hkSetupMove-equivalent code
  vmprotect_handler_map.json     # opcode → semantic mapping
  DEVIRT_LOG.md                  # session notes + trace commands
```

At that point, `docs/FUCKVACV2_PARITY_CHECKLIST.md` gets a section 11
with byte-exact cross-reference between our v3.x hooks and the
devirt'd hooks — closing the last "we don't have byte-exact
verification" gap in the checklist.

### Not-doing signals

Devirt of FuckVacV2 is optional research infrastructure. It does not:

- Improve gameplay mutation.
- Fix any of the runtime issues in the current v2.x/v3.x DLL.
- Reduce false-positive risk against VAC (both packed and unpacked
  match the same runtime silhouette from cs2's perspective).

Pursue only if a specific comparison target requires byte-exact
FuckVacV2 semantics.

---

## Русский

Это **future-work** трек — не часть v3.0. Документирует, что потребует
полный self-devirt `FuckVacV2.dll`, чтобы более поздняя research-сессия
могла подхватить эту работу без re-discovery.

### Почему это вне scope'а v3.0

- Настоящая `FuckVacV2.dll` упакована VMProtect 3.6.x. MCP-сессия
  отказалась открыть packed-файл (`access violation reading
  0x0000000000000000` в IDB init) — VMProtect побеждает статический
  анализ by design.
- `FuckVacV2_dump.dll`, который у нас уже есть, — это **memory dump**,
  снятый после отработки TLS-колбэка VMProtect'а. Non-VM код (protobuf,
  MinHook, таблицы строк) — читабелен; VM-зашифрованные рутины
  (конструкция log-сообщений, тела инсталляторов хуков, setup аргументов
  `MH_CreateHook`) до сих пор живут в секциях `._I5` + `._?n` как
  opcode-потоки виртуальной машины VMProtect'а.
- Извлечение семантики 5-хук-инсталлятора из этих потоков требует либо
  символьного исполнения, либо VMProtect-specific unpacker. Это не нужно
  чтобы шипнуть v3.0 — runtime-лог (`[Debug] Hooked X!`) достаточно,
  чтобы знать **какие** функции целит FuckVacV2, а наши независимые
  resolver'ы (RTTI vtable slot, engine2 RVAs) позволяют попасть в те же
  target'ы без своего resolver-логика FuckVacV2.

### Тулчейн

Если будущая сессия решит идти дальше, рекомендуемый стек:

1. **VMPAttack** (github.com/can1357/VMPAttack) — LLVM-based lifter VM
   VMProtect 3.x. Справляется с VMP 3.6.x при правильной настройке
   handler-key таблицы.
2. **NoVmp** (github.com/can1357/NoVmp) — старее, но всё ещё эффективный
   девиртуализатор VMProtect 2.x/3.x. Хорош для cross-check выходов
   VMPAttack.
3. **x64dbg + VMTracer plugin** — динамический трейс исполнения одного
   VMProtect-handler'а пока запущен cs2.exe. Даёт ground-truth семантику
   per-handler, feed'ится обратно в VMPAttack.
4. **IDA Pro 9.x** с Hex-Rays — для post-devirt cleanup'а и ручной
   реконструкции типов. MCP-сессия (имя `fv2pack` зарезервировано) сможет
   загрузить devirt'нутый DLL после того, как инструменты выше произведут
   clean PE.

### Оценка усилий

Грубая оценка на основе опубликованных devirt-writeup'ов похожих VMProtect
3.x целей (~2 МБ `.text` + `._?n` секций):

- Handler table extraction + lifter config: 3-5 дней
- Trace-refined lifter output + validation: 5-7 дней
- Post-devirt IDA cleanup + hook signature capture: 2-3 дня
- **Всего: ~2-3 недели сфокусированной работы**

### Deliverable в случае реализации

Если devirt удался, checkpoint артефактов в:

```
ida_work/FuckVacV2_devirtualized_by_us/
  FuckVacV2_devirt_v1.dll        # clean PE, произведённый VMPAttack
  FuckVacV2_devirt_v1.dll.i64    # IDA IDB с реконструированными типами
  hook_installer_bodies.md       # cleaned-up hkSetupMove-эквивалентный код
  vmprotect_handler_map.json     # opcode → semantic mapping
  DEVIRT_LOG.md                  # session notes + trace-команды
```

В этот момент `docs/FUCKVACV2_PARITY_CHECKLIST.md` получает секцию 11
с byte-exact cross-reference между нашими v3.x хуками и devirt'нутыми —
закрывает последнюю «нет byte-exact верификации» дыру в checklist'е.

### Not-doing сигналы

Devirt FuckVacV2 — optional research-инфраструктура. Она НЕ:

- Улучшает gameplay-мутацию.
- Фиксит runtime-проблемы в текущем v2.x/v3.x DLL.
- Снижает риск false-positive против VAC (и packed, и unpacked с точки
  зрения cs2 имеют тот же runtime-силуэт).

Пробовать только если конкретная compare-target'а требует byte-exact
FuckVacV2 семантики.

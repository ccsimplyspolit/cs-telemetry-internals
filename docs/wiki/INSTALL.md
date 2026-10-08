# INSTALL — полная инструкция · full installation guide

**[Русский](#русская-версия) · [English](#english-version)**

---

## Русская версия

### Предусловия

| Компонент | Версия | Как получить |
|-----------|--------|--------------|
| Windows | 10/11 x64 build 22621+ | — |
| Steam CS2 | depot 24134959 | Steam auto-update |
| Visual Studio | 2022 (v145 toolset) | https://visualstudio.microsoft.com/downloads/ |
| Windows SDK | 10.0.26100+ | Через VS installer |
| Windows WDK | 10.0.26100 | https://learn.microsoft.com/windows-hardware/drivers/download-the-wdk |
| CMake | 3.20+ | https://cmake.org/download/ |
| Chocolatey (опц.) | latest | https://chocolatey.org/install |

**Проверить установку:**
```powershell
cmake --version
msbuild -version
"C:\Program Files\Microsoft Visual Studio\2022\*\VC\Tools\MSVC\*\bin\Hostx64\x64\cl.exe" | Select-String -Pattern "версии"
```

### Шаг 1 — клон и первый билд

```powershell
git clone https://github.com/ccsimplyspolit/CS2-P2C-TEMPLATES.git
cd CS2-P2C-TEMPLATES
```

**Сборка VLB DLL (обе версии attack + byte):**
```powershell
# Attack version (schema-way, default)
cd source\dlls\VacLiveBypass
cmake -S . -B build -A x64 -DFVA_GATE_MODE=attack
cmake --build build --config Release --target fva_recon

# Byte version (FVA original 1:1)
cmake -S . -B build_byte -A x64 -DFVA_GATE_MODE=byte
cmake --build build_byte --config Release --target fva_recon
```

**Артефакты:** `build/Release/fva_recon.dll` и `build_byte/Release/fva_recon.dll`.

**Сборка injector'а:**
```powershell
cd ..\..\..\tools\CS2UnifiedInjector
msbuild CS2UnifiedInjector.vcxproj /p:Configuration=Release /p:Platform=x64
```

**Сборка kernel driver'а (нужен WDK):**
```powershell
cd ..\..\drivers\CS2HexSyncCompatDriver
msbuild CS2HexSyncCompatDriver.vcxproj /p:Configuration=Release /p:Platform=x64
```

### Шаг 2 — использование готовых kits

Готовые kits уже в `build/`:

```
build/
├── kit_vlb_attack_gated/         ← schema-way gate (по клику ЛКМ/ПКМ)
├── kit_vlb_byte_gated/           ← FVA-original 1:1 (byte @CCSGOInput+0xA4)
└── kit_vlb_default/  ← alias kit_vlb_attack_gated (для kernel inject)
```

**Каждый kit содержит:**
```
CS2HexSyncCompatCert.cer         Code-signing certificate
CS2HexSyncCompatDriver.sys       Kernel driver (16 KB, signed)
CS2UnifiedInjector.exe           Injector (273 KB, 8 methods)
fva_recon_14167.dll              VLB для baseline depot 14167
fva_recon_24134959.dll           VLB для current depot 24134959
GATE_MODE.txt                    Описание gate режима
kdu.exe                          KDU utility (~2.4 MB)
Launch-Inject.bat                Bootstrap → elevate
Launch-Inject.ps1                Main launcher script
README.txt                       Info
```

### Шаг 3 — запуск

**Порядок:**

1. **Запустить cs2 обычно через Steam** (НЕ через launcher, launcher ждёт запущенный процесс)
2. Дождаться главного меню CS2
3. Запустить `Launch-Inject.bat` из выбранного kit'а
4. Подтвердить UAC prompt
5. Наблюдать в консоли launcher'а:
   ```
   [+] Stopped MSIAfterburner (holds RTCore64 exclusive)
   [+] MSFT driver blocklist disabled
   [+] cs2.exe PID 47056
   [+] DLL: fva_recon_24134959.dll
   [+] Cert installed
   [+] DSE off (provider 1)
   [+] Driver started
   [*] Inject fva_recon_24134959.dll -> cs2.exe
   [+] DSE restored
   [+] Service unloaded
   [+] Injector done.
   ```

**Проверить успех:**
- Открыть `C:\vmp\fva_recon.log`
- Найти строки:
  ```
  [fva_recon][engine2] init: sig-scan resolved:
    engine2!IsInGame              RVA 0x76470  ptr=...
    engine2!IsConnected           RVA 0x764A0  ptr=...
    client!LevelShutdown          RVA 0xB3A700  ptr=...
  [fva_recon] hooks installed
  [fva_recon] LevelShutdown hook installed
  ```

**Зайти в матч (Deathmatch / Casual / Practice) для активации:**
- Дождаться spawn
- Открыть `fva_recon.log` — должны появляться `[fva_recon][H1] tick=N` строки

**Выгрузить DLL:**
- В CS2 окне нажать клавишу `END` — worker thread выгрузит hooks и вернёт `FreeLibrary`

### Шаг 4 — troubleshooting

**Проблема: `KDU DSE off failed (provider 1)`**
- MSI Afterburner не полностью закрылся — kill вручную через Task Manager
- Или попробовать fallback: `Launch-Inject.ps1 -KduProvider 0 -WithFallback` (Intel NAL)

**Проблема: `cs2.exe not running (60s wait)`**
- Steam запусти CS2 ДО запуска launcher
- Проверить что CS2 не работает под "Compatibility mode"

**Проблема: `[fva_recon] FATAL: install_all failed`**
- Проверить MD5 client.dll: `powershell "(Get-FileHash 'D:\...\client.dll' -Algorithm MD5).Hash"`
- Ожидается `16917FCE6C15715434F6604E8086D38A` для depot 24134959
- Если depot 14167 — используй `fva_recon_14167.dll` (SHA-check в launcher переключит автоматически)

**Проблема: Cs2 crashит на смене карты**
- Собери с `-DFVA_STRICT_FINGERPRINT=ON` чтобы отказать инжект при mismatch fingerprint
- Проверить `fva_recon.log` последние строки — где именно упал
- См. `docs/wiki/WORKFLOW.md` раздел crash-diagnostic

**Проблема: BSOD 0x50 при загрузке driver'а**
- Обычно проблема с DSE bypass или signed cert timing
- Kill Afterburner + перезагрузка → повтор

### Шаг 5 — debug сборка

**Включить logging (default off в retail):**
```powershell
# Через ENV variable
$env:FVA_DEBUG = "1"
# ИЛИ создать файл-toggle
New-Item -ItemType File -Path C:\vmp\.fva_debug -Force
```

**Собрать с console attached:**
```powershell
cd source\dlls\VacLiveBypass
cmake -S . -B build -A x64 -DFVA_CONSOLE=ON -DFVA_TRACE_HOOKA=ON
cmake --build build --config Release
```

`FVA_TRACE_HOOKA` = per-tick детальный state trace (~128 log lines/sec — только для reverse-разработки).

---

## English version

### Prerequisites

| Component | Version | How to get |
|-----------|---------|------------|
| Windows | 10/11 x64 build 22621+ | — |
| Steam CS2 | depot 24134959 | Steam auto-update |
| Visual Studio | 2022 (v145 toolset) | https://visualstudio.microsoft.com/downloads/ |
| Windows SDK | 10.0.26100+ | Via VS installer |
| Windows WDK | 10.0.26100 | https://learn.microsoft.com/windows-hardware/drivers/download-the-wdk |
| CMake | 3.20+ | https://cmake.org/download/ |
| Chocolatey (opt.) | latest | https://chocolatey.org/install |

**Verify install:**
```powershell
cmake --version
msbuild -version
"C:\Program Files\Microsoft Visual Studio\2022\*\VC\Tools\MSVC\*\bin\Hostx64\x64\cl.exe" | Select-String -Pattern "version"
```

### Step 1 — clone and first build

```powershell
git clone https://github.com/ccsimplyspolit/CS2-P2C-TEMPLATES.git
cd CS2-P2C-TEMPLATES
```

**Build VLB DLL (both attack + byte variants):**
```powershell
# Attack version (schema-way, default)
cd source\dlls\VacLiveBypass
cmake -S . -B build -A x64 -DFVA_GATE_MODE=attack
cmake --build build --config Release --target fva_recon

# Byte version (FVA original 1:1)
cmake -S . -B build_byte -A x64 -DFVA_GATE_MODE=byte
cmake --build build_byte --config Release --target fva_recon
```

**Artifacts:** `build/Release/fva_recon.dll` and `build_byte/Release/fva_recon.dll`.

**Build injector:**
```powershell
cd ..\..\..\tools\CS2UnifiedInjector
msbuild CS2UnifiedInjector.vcxproj /p:Configuration=Release /p:Platform=x64
```

**Build kernel driver (requires WDK):**
```powershell
cd ..\..\drivers\CS2HexSyncCompatDriver
msbuild CS2HexSyncCompatDriver.vcxproj /p:Configuration=Release /p:Platform=x64
```

### Step 2 — use pre-built kits

Pre-built kits are in `build/`:

```
build/
├── kit_vlb_attack_gated/         ← schema-way gate (on LMB/RMB click)
├── kit_vlb_byte_gated/           ← FVA-original 1:1 (byte @CCSGOInput+0xA4)
└── kit_vlb_default/  ← alias for kit_vlb_attack_gated (kernel inject)
```

**Each kit contains:**
```
CS2HexSyncCompatCert.cer         Code-signing certificate
CS2HexSyncCompatDriver.sys       Kernel driver (16 KB, signed)
CS2UnifiedInjector.exe           Injector (273 KB, 8 methods)
fva_recon_14167.dll              VLB for baseline depot 14167
fva_recon_24134959.dll           VLB for current depot 24134959
GATE_MODE.txt                    Gate mode description
kdu.exe                          KDU utility (~2.4 MB)
Launch-Inject.bat                Bootstrap → elevate
Launch-Inject.ps1                Main launcher script
README.txt                       Info
```

### Step 3 — run

**Order:**

1. **Launch cs2 normally via Steam** (NOT via launcher, launcher waits for running process)
2. Wait for CS2 main menu
3. Run `Launch-Inject.bat` from chosen kit
4. Accept UAC prompt
5. Watch launcher console:
   ```
   [+] Stopped MSIAfterburner (holds RTCore64 exclusive)
   [+] MSFT driver blocklist disabled
   [+] cs2.exe PID 47056
   [+] DLL: fva_recon_24134959.dll
   [+] Cert installed
   [+] DSE off (provider 1)
   [+] Driver started
   [*] Inject fva_recon_24134959.dll -> cs2.exe
   [+] DSE restored
   [+] Service unloaded
   [+] Injector done.
   ```

**Verify success:**
- Open `C:\vmp\fva_recon.log`
- Find lines:
  ```
  [fva_recon][engine2] init: sig-scan resolved:
    engine2!IsInGame              RVA 0x76470  ptr=...
    engine2!IsConnected           RVA 0x764A0  ptr=...
    client!LevelShutdown          RVA 0xB3A700  ptr=...
  [fva_recon] hooks installed
  [fva_recon] LevelShutdown hook installed
  ```

**Enter a match (Deathmatch / Casual / Practice) to activate:**
- Wait for spawn
- Open `fva_recon.log` — `[fva_recon][H1] tick=N` lines should appear

**Unload DLL:**
- In CS2 window press `END` key — worker thread will unload hooks and `FreeLibrary`

### Step 4 — troubleshooting

**Issue: `KDU DSE off failed (provider 1)`**
- MSI Afterburner didn't close fully — kill manually via Task Manager
- Or try fallback: `Launch-Inject.ps1 -KduProvider 0 -WithFallback` (Intel NAL)

**Issue: `cs2.exe not running (60s wait)`**
- Launch CS2 via Steam BEFORE running launcher
- Check that CS2 isn't running under "Compatibility mode"

**Issue: `[fva_recon] FATAL: install_all failed`**
- Check client.dll MD5: `powershell "(Get-FileHash 'D:\...\client.dll' -Algorithm MD5).Hash"`
- Expected `16917FCE6C15715434F6604E8086D38A` for depot 24134959
- If depot 14167 — use `fva_recon_14167.dll` (SHA-check in launcher switches automatically)

**Issue: Cs2 crashes on map change**
- Build with `-DFVA_STRICT_FINGERPRINT=ON` to refuse inject on fingerprint mismatch
- Check `fva_recon.log` last lines — where exactly it crashed
- See `docs/wiki/WORKFLOW.md` crash-diagnostic section

**Issue: BSOD 0x50 on driver load**
- Usually DSE bypass or signed cert timing issue
- Kill Afterburner + reboot → retry

### Step 5 — debug build

**Enable logging (default off in retail):**
```powershell
# Via ENV variable
$env:FVA_DEBUG = "1"
# OR create toggle file
New-Item -ItemType File -Path C:\vmp\.fva_debug -Force
```

**Build with console attached:**
```powershell
cd source\dlls\VacLiveBypass
cmake -S . -B build -A x64 -DFVA_CONSOLE=ON -DFVA_TRACE_HOOKA=ON
cmake --build build --config Release
```

`FVA_TRACE_HOOKA` = per-tick detailed state trace (~128 log lines/sec — for reverse-development only).

---

## Support · Donations

See [main README](../../README.md#поддержка-проекта--donations) for all payment methods.
См. [main README](../../README.md#поддержка-проекта--donations) для всех способов оплаты.

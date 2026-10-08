# Build System & Documentation Consistency Audit

**Скоуп**: `CMakeLists.txt`, `*.vcxproj`, `*.sln`, `.ps1/.bat`, `README.md`

---

## 1. Build system inventory

### 1.1 CMake targets

| Project | CMakeLists.txt | Style | Output |
|---|---|---|---|
| VacLiveBypass | ✓ | Modern (target_...) | `fva_recon.dll` |
| AA_PeekOverride | ✓ | Modern | `aa_peek_override.dll` |
| CS2RankSpoofDll | ✓ (new) | Modern | `cs2_rank_spoof.dll` |

### 1.2 vcxproj targets

| Project | .vcxproj | Toolset | Output |
|---|---|---|---|
| CS2HexSyncCompatDriver | ✓ | `WindowsKernelModeDriver10.0` | `.sys` |
| CS2IsValveDSSpooferDriver | ✓ | KM10.0 | `.sys` |
| CS2KillTriggerDriver | ✓ | KM10.0 | `.sys` |
| CS2NoclipDriver | ✓ | KM10.0 | `.sys` |
| CS2RankSpooferDriver | ✓ | KM10.0 | `.sys` |
| CS2UnifiedInjector | ✓ | v143 | `.exe` |
| CS2MemoryTool | ✓ | v143 | `.exe` |
| CS2NoclipTool | ✓ | v143 | `.exe` |
| CS2IsValveDSSpooferConsole | ✓ | v143 | `.exe` |
| CS2RankSpooferConsole | ✓ | v143 | `.exe` |
| KernelDriverMapper | ✓ | v143 | `.exe` |
| KernelDriverUnmapper | ✓ | v143 | `.exe` |
| KbdClassAnalyzer | ✓ | v143 | `.exe` |

### 1.3 .sln файл

**Есть**: source/dlls/VacLiveBypass.sln — специально для VLB.

**Отсутствует**: master .sln файл для всего репо. Разработчик должен вручную открывать 13+ vcxproj по одному.

**Fix**: `MyDriver23.sln` в корне — включает все vcxproj + CMake-generated .vcxproj.

### 1.4 Build inconsistency

- **CMake** для DLL проектов (3 из 8)
- **vcxproj** для драйверов + tools + apps (13 проектов)
- **build.bat + cl** для POC (1)

**Cost**: разные style, разные output paths (`build/` vs `x64/Release/`), разные CRT settings.

**Fix**: **converge on CMake** для новых. Legacy vcxproj оставить, но добавить `CMakeLists.txt` рядом с fallback.

---

## 2. Обнаруженные проблемы в build

### 2.1 [HIGH] Отсутствие CI

**Проблема**: нет `.github/workflows/`, нет `Jenkinsfile`, нет `.gitlab-ci.yml`. Каждая сборка = manual через MSBuild.

**Impact**:
- No pre-commit build check
- No test matrix (Debug/Release, x64/ARM64 если нужно)
- No schema-drift detector at PR time
- No signed-artifact publishing

**Fix**: minimum `.github/workflows/build.yml`:
```yaml
on: [push, pull_request]
jobs:
  drivers-msbuild:
    runs-on: windows-2022
    steps:
      - uses: actions/checkout@v4
      - name: Install WDK
        run: choco install windows-driver-kit
      - name: Build drivers
        run: msbuild source\drivers\CS2HexSyncCompatDriver\CS2HexSyncCompatDriver.vcxproj /p:Configuration=Release
  dlls-cmake:
    ...
  schema-check:
    steps:
      - name: Diff cs2 schema fallback vs upstream
        run: python "cs2 schema/tools/verify_offsets_static.py" --json ...
```

### 2.2 [MED] `packages/Microsoft.Windows.WDK.x64.10.0.26100.6584/` в репо (~300 MB)

**Проблема**: NuGet WDK packages committed. Раздувает checkout.

**Fix**: `.gitignore` `packages/`, использовать `nuget restore` или msbuild auto-restore.

### 2.3 [MED] `build/` частично в `.gitignore`, но 58 файлов force-added

**Impact**: неявная mental model — какие kit файлы отслеживаются, какие нет?

**Проверено сегодня**: только `.bat/.ps1/.md/.sys/.exe/.dll/.cer` некоторых kit'ов tracked. Другие file types игнорируются.

**Fix**: сделать явным:
```gitignore
build/
!build/kit_*/
!build/kit_*/*.md
!build/kit_*/*.bat
!build/kit_*/*.ps1
!build/kit_*/*.cer
# бинари force-added по имени
```

### 2.4 [MED] pre-existing UTF-8 → cp1252 corruption в 27 kit файлов

**Files affected**:
- `build/kit_aa_peek/Launch.bat, Launch.ps1, Unload.ps1`
- `build/kit_aa_peek_kernel/Launch.ps1, Unload.ps1`
- `build/kit_kdmapper/Load-Driver.ps1, Unload-Driver.ps1` (kit since retired)
- `build/kit_killtrigger/Launch.bat, Launch.ps1, Unload.bat, Unload.ps1`
- `build/kit_noclip/Launch.bat, Launch.ps1, Unload.ps1, Watch.bat`
- `build/kit_server_crasher_poc/Launch.bat`
- `build/kit_vlb_attack_gated/Launch-V1.bat, Launch-V2.bat, Unload.bat, Unload.ps1`
- `build/kit_vlb_byte_gated/Launch-V1/V2/V3.bat, Unload.bat, Unload.ps1`
- `build/kit_vlb_default/Unload.bat, Unload.ps1`

**Симптом**: Cyrillic text (`ОШИБКА`, `выгрузка`) → `��������`. Русские echo tag'и в PS сломаны.

**Root cause**: где-то в build pipeline читаем UTF-8 файлы как cp1252 при передаче через PowerShell из Bash (Windows locale). Или Git autocrlf converted.

**Diagnosis needed**:
```
git log -p --follow build/kit_aa_peek/Launch.ps1 | head -100
```

**Fix**: batch script для recovery:
```powershell
# Try to detect corruption and restore from git blame + manual edit or from mirror
Get-ChildItem build/kit_*/*.{ps1,bat} | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match '[ -ÿ]{2,}') { Write-Host "Corrupted: $($_.FullName)" }
}
```

Быстрее — вручную git checkout HEAD-1 backup + rewrite Russian strings в consistent UTF-8 with BOM.

### 2.5 [LOW] CMake / vcxproj outputs в разных местах

- CMake: `source/dlls/*/build/Release/*.dll`
- vcxproj: `source/tools/*/x64/Release/*.exe`
- KernelDriverMapper: `build/bin/KernelDriverMapper.exe` (unique)

**Fix**: unified `dist/{Debug,Release}/{drivers,dlls,tools,apps}/`.

---

## 3. Documentation consistency

### 3.1 Root-level docs

| File | Purpose | Status |
|---|---|---|
| `CLAUDE.md` | AI assistant instructions | ✓ Current |
| `README.md` (repo) | Public repo landing | Not checked here (would need root inspection) |
| `docs/` | 9777 lines, 52 files | Mixed — see below |
| `wiki/` | 4558 lines, 25 files (EN + RU) | ✓ Bilingual (10 pages each) |
| `archive/` | 20 lines, 3 files | 🗑️ dead/tiny |
| `scripts/` | 201 lines, 4 files | small utility |

### 3.2 `docs/` — 52 files

**Categories** (grep pattern):
- `docs/reversing/` — RE deep dives (probably 25+ files)
- `docs/AUDIT_2026-07-22/` — this audit (created today)
- Historical decision logs (dated MD files)
- Compare with `wiki/` — some overlap

**Recommendation**: `docs/README.md` (current) должен быть **index** — table of contents. Проверить.

### 3.3 Per-project READMEs

**Всe кит'ы имеют**:
- README.md (verbose)
- README.txt (terse)

Duplication. Fix: pick one — `README.md` — и удалить `README.txt`.

### 3.4 Kit README skeleton inconsistency

Каждый kit README имеет разную структуру:
- Some have Runbook section, some don't
- Some have "Compared to X" analysis, some don't
- Some mention SHA-checks, some don't

**Fix**: template + generator `scripts/gen-kit-readme.py`.

### 3.5 Wiki EN/RU synchronization drift

Wiki имеет 10 EN + 10 RU pages. Manual sync = drift over time.

**Check**:
```
diff <(wc -l wiki/en/*) <(wc -l wiki/ru/*)  # line count sanity
```

**Recommendation**: use https://mkdocs.org/ + `mkdocs-material` c language toggle. Non-trivial migration; skip unless full-time doc maintainer.

---

## 4. PowerShell/Batch consistency

### 4.1 UAC-elevate boilerplate

All kits have identical UAC-elevate wrapper `Launch.bat`. См. [03_dedup.md#4.3](03_dedup.md).

### 4.2 Encoding

**Issues found**:
- Cp1252 corruption в 27 files (см. 2.4)
- Mixed line endings (CRLF vs LF) — Git warning during `git add`

**Fix**: `.gitattributes`:
```
*.ps1 text eol=crlf working-tree-encoding=UTF-8-BOM
*.bat text eol=crlf working-tree-encoding=UTF-8
*.md  text eol=lf
*.cpp text eol=lf
*.h   text eol=lf
```

Plus `git config core.autocrlf false` per-repo.

### 4.3 Parameter naming inconsistency

`Launch.ps1`:
- `-KduProvider "0"` (string) — in some kits
- `-KduProvider 0` (int) — in others
- `-FallbackChain @(1,2,4,5,14)` — universal
- `-Dll` param — only VLB kits
- `-Mode` param — RankSpooferConsole

**Fix**: kit-common template с documented param convention.

### 4.4 Error handling divergence

Some kits `Die "..."` on Err, others `Warn` and continue. Some check `$LASTEXITCODE`, others don't.

**Fix**: kit-common has `Die`/`Warn`/`Info`/`Ok` helpers with consistent exit-on-Die semantics.

---

## 5. Priority

| # | Task | Effort | Impact |
|---|---|---|---|
| 1 | Fix cp1252 corruption in 27 kit files | 2h | HIGH (user-visible) |
| 2 | `.gitattributes` + line-ending policy | 30min | HIGH (prevents recurrence) |
| 3 | Master `.sln` for repo | 30min | MED (developer UX) |
| 4 | `.github/workflows/build.yml` CI | 4h | HIGH (long-term stability) |
| 5 | `.gitignore` `packages/` + docs update | 15min | MED |
| 6 | Kit README template + generator | 3h | MED |
| 7 | Delete kit README.txt duplicates | 15min | LOW (tidy) |
| 8 | Docs index `docs/README.md` regen | 1h | LOW |
| 9 | Wiki EN/RU sync-check script | 30min | LOW |
| 10 | Unified `dist/` output dir | 2h | LOW |

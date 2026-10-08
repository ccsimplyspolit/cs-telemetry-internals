# Vulnerable Driver Providers / Уязвимые драйвер-провайдеры

**[EN](#english) · [RU / Русский](#русский)**

---

## English

List of known public vulnerable drivers suitable for kernel r/w exploitation.
Base — [hfiref0x/KDU providers.md](https://github.com/hfiref0x/KDU/blob/master/Help/providers.md) (v1.4.9, June 2026).

### CVE list not yet in Microsoft Vulnerable Driver Blocklist

These drivers can be legally downloaded (Signed) and are still exploitable on **default Win11 22H2+** (blocklist doesn't mark them):

| KDU ID | Driver | CVE | Comment |
|---|---|---|---|
| 30 | AMDRyzenMasterDriver | CVE-2020-12928 (AODDriver) | No blocklist entry; MinBuild 7601 |
| 44 | PdFwKrnl | CVE-2023-20598 | AMD Radeon USB-C PD Utility, no upper limit |
| 54 | NeacSafe64 | CVE-2025-45737 | mini-filter, MinBuild 10240 |
| 55 | ThrottleStop | CVE-2025-7771 | TechPowerUp, MinBuild 7601 |
| 57 | LnvMSRIO | CVE-2025-8061 | Lenovo MSR I/O Driver, MinBuild 7601 |

These drivers can be used for DSE-bypass or direct manual-map without prior disabling of `VulnerableDriverBlocklistEnable`.

### Full list of KDU providers (65 drivers)

All drivers supported by current KDU v1.4.9. For each — known CVE or developer.

| ID | Driver | Source / CVE |
|---|---|---|
| 0 | IQVM64/Nal | Intel NAL, CVE-2015-2291 |
| 1 | RTCore64 | MSI Afterburner, CVE-2019-16098 |
| 2 | Gdrv | Gigabyte GDRV, CVE-2018-19320 |
| 3 | ATSZIO | ASUSTeK WinFlash utility |
| 4 | MsIo64 | Patriot Viper RGB, CVE-2019-18845 |
| 5 | GLCKIO2 | ASRock Polychrome RGB |
| 6 | EneIo64 | G.SKILL Trident Z Lighting |
| 7 | WinRing0x64 | EVGA Precision X1 |
| 8 | EneTechIo64 | Thermaltake TOUGHRAM |
| 9 | PhyMemx64 | Huawei MateBook Manager |
| 10 | RtkIo64 | Realtek Dash Client |
| 11 | EneTechIo64 | MSI Dragon Center |
| 12 | lha | LG Device Manager, CVE-2019-8372 |
| 13 | AsIO2 | ASUS GPU Tweak |
| 14 | DirectIo64 | PassMark Performance Test |
| 15 | gmerdrv | GMER Antirootkit |
| 16 | DBUtil23 | Dell BIOS Utility, CVE-2021-21551 |
| 17 | mimidrv | Mimikatz driver |
| 18 | KProcessHacker | Process Hacker |
| 19 | PROCEXP152 | Process Explorer v16 |
| 20 | DBUtilDrv2 | Dell DBUtil 2.5, CVE-2021-36276 |
| 21 | CEDRIVER73 | Cheat Engine Dbk64 |
| 22 | AsIO3 | ASUS GPU Tweak II |
| 23 | hw64 | Marvin Hardware Access Driver |
| 24 | SysDrv3S | CODESYS SysDrv3S, CVE-2022-22516 |
| 25 | ZemanaAntimalware | Zemana AntiMalware, CVE-2021-31728, CVE-2022-42045 |
| 26 | inpoutx64 | inpoutx64 v1.2 |
| 27 | DirectIo64 | PassMark OSForensics |
| 28 | AsrDrv106 | ASRock IO Driver |
| 29 | ALSysIO64 | Core Temp |
| **30** | **AMDRyzenMasterDriver** | **AMD Ryzen Master Service, CVE-2020-12928** ⭐ |
| 31 | physmem | Physical Memory Access Driver |
| 32 | LenovoDiagnosticsDriver | Lenovo Diagnostics, CVE-2022-3699 |
| 33 | pcdsrvc_x64 | PC-Doctor, CVE-2019-12280 |
| 34 | WinIo | MSI Foundation Service |
| 35 | EtdSupport | ETDi Support Driver v18.0 |
| 36 | KExplore | Kernel Explorer Driver |
| 37 | KObjExp | Kernel Object Explorer |
| 38 | KRegExp | Kernel Registry Explorer |
| 39 | EchoDrv | Echo AntiCheat driver |
| 40 | nvoclock | NVIDIA System Utility Driver |
| 41 | IREC | Binalyze DFIR, CVE-2023-41444 |
| 42 | PhyDMACC | SLIC ToolKit |
| 43 | rzpnk | Razer Synapse, CVE-2017-9769 |
| **44** | **PdFwKrnl** | **AMD Radeon USB-C PD, CVE-2023-20598** ⭐ |
| 45 | AODDriver | AMD OverDrive, CVE-2020-12928 |
| 46 | wnBios64 | Wincor Nixdorf BIOS |
| 47 | EleetX1 | EVGA ELEET X1 |
| 48 | AxtuDrv | ASRock Extreme Tuner |
| 49 | AppShopDrv103 | ASRock APP Shop |
| 50 | AsrDrv107n | ASRock Motherboard Utility |
| 51 | AsrDrv107 | ASRock Motherboard Utility |
| 52 | PMxDrv | Intel Management Engine Tools |
| 53 | HwRwDrv.x64 | Hardware R/W driver |
| **54** | **NeacSafe64** | **mini-filter, CVE-2025-45737** ⭐ |
| **55** | **ThrottleStop** | **TechPowerUp, CVE-2025-7771** ⭐ |
| 56 | TPwSav | Toshiba power saving |
| **57** | **LnvMSRIO** | **Lenovo MSR I/O, CVE-2025-8061** ⭐ |
| 58 | CORMEM | Sapera Memory Manager |
| 59 | IPCType | IPCType Device Driver |
| 60 | WinHwDriver | Guangzhou Shangke giveio |
| 61 | affdriver | AMD BIOS Flash Utility |
| 62 | mtxC9CB | Matrox Graphics |
| 63 | PGRHostControl | FLIR PGRHostControl SDK |
| 64 | LECOMAx | LECO LECOMA Device Driver |

⭐ = not in Microsoft Vulnerable Driver Blocklist on Win11 22H2+ (working on default install).

### How to use in the project

**Kernel driver mapping** — three options by increasing complexity:

#### 1. Our KernelDriverMapper (single provider: iqvw64e.sys)
```powershell
KernelDriverMapper.exe --key <name> --indPages <driver.sys>
```
- **Works**: Win7 → Win10 21H2
- **DOES NOT work** on Win11 22H2+ if VulnerableDriverBlocklist is active (will fail on loading `iqvw64e.sys`)

#### 2. External KDU (65 fallback providers)
```
kdu.exe -map <driver.sys>
```
- Works on any Win11 with any build
- Automatic fallback: if one provider blocked, next is tried
- Download: https://github.com/hfiref0x/KDU/releases

#### 3. sc create + testsigning (simplest)
```powershell
bcdedit /set testsigning on   # + reboot
sc create <name> type= kernel binPath= "<path>"
sc start <name>
```
- Only for research (testsigning banner visible in screen corner)
- DOES NOT work if Secure Boot is active

### Roadmap: integration of KDU-style into KernelDriverMapper

TODO for future releases: extended provider table in `KernelDriverMapper.exe` with fallback logic. Significant work — 65 providers, each with own exploitation payload. See [`docs/DRIVER_HARDENING.md`](DRIVER_HARDENING.md) roadmap P2.

### Legal

- **Downloading** vulnerable drivers from manufacturer — legal (it's Signed producer's driver).
- **Using** vulnerable driver for kernel r/w in **your own system** — legal (personal research).
- **Using** against a machine you don't have access to — CFAA / CMA / StGB § 202a violation.

See [`ETHICS.md`](ETHICS.md).

---

## Русский

Список известных публичных vulnerable driver'ов, пригодных для kernel r/w exploitation.
Основа — [hfiref0x/KDU providers.md](https://github.com/hfiref0x/KDU/blob/master/Help/providers.md) (v1.4.9, июнь 2026).

### CVE список, ещё не в Microsoft Vulnerable Driver Blocklist

Эти driver'ы можно легально скачать (Signed) и они всё ещё эксплуатируются на **default Win11 22H2+** (blocklist не помечает их):

| KDU ID | Driver | CVE | Комментарий |
|---|---|---|---|
| 30 | AMDRyzenMasterDriver | CVE-2020-12928 (AODDriver) | No blocklist entry; MinBuild 7601 |
| 44 | PdFwKrnl | CVE-2023-20598 | AMD Radeon USB-C PD Utility, no upper limit |
| 54 | NeacSafe64 | CVE-2025-45737 | mini-filter, MinBuild 10240 |
| 55 | ThrottleStop | CVE-2025-7771 | TechPowerUp, MinBuild 7601 |
| 57 | LnvMSRIO | CVE-2025-8061 | Lenovo MSR I/O Driver, MinBuild 7601 |

Эти driver'ы можно использовать для DSE-bypass или прямого manual-map без предварительного отключения `VulnerableDriverBlocklistEnable`.

### Полный список KDU providers (65 драйверов)

Все driver'ы поддерживаются актуальной KDU v1.4.9. Для каждого — известная CVE или разработчик.

| ID | Driver | Source / CVE |
|---|---|---|
| 0 | IQVM64/Nal | Intel NAL, CVE-2015-2291 |
| 1 | RTCore64 | MSI Afterburner, CVE-2019-16098 |
| 2 | Gdrv | Gigabyte GDRV, CVE-2018-19320 |
| 3 | ATSZIO | ASUSTeK WinFlash utility |
| 4 | MsIo64 | Patriot Viper RGB, CVE-2019-18845 |
| 5 | GLCKIO2 | ASRock Polychrome RGB |
| 6 | EneIo64 | G.SKILL Trident Z Lighting |
| 7 | WinRing0x64 | EVGA Precision X1 |
| 8 | EneTechIo64 | Thermaltake TOUGHRAM |
| 9 | PhyMemx64 | Huawei MateBook Manager |
| 10 | RtkIo64 | Realtek Dash Client |
| 11 | EneTechIo64 | MSI Dragon Center |
| 12 | lha | LG Device Manager, CVE-2019-8372 |
| 13 | AsIO2 | ASUS GPU Tweak |
| 14 | DirectIo64 | PassMark Performance Test |
| 15 | gmerdrv | GMER Antirootkit |
| 16 | DBUtil23 | Dell BIOS Utility, CVE-2021-21551 |
| 17 | mimidrv | Mimikatz driver |
| 18 | KProcessHacker | Process Hacker |
| 19 | PROCEXP152 | Process Explorer v16 |
| 20 | DBUtilDrv2 | Dell DBUtil 2.5, CVE-2021-36276 |
| 21 | CEDRIVER73 | Cheat Engine Dbk64 |
| 22 | AsIO3 | ASUS GPU Tweak II |
| 23 | hw64 | Marvin Hardware Access Driver |
| 24 | SysDrv3S | CODESYS SysDrv3S, CVE-2022-22516 |
| 25 | ZemanaAntimalware | Zemana AntiMalware, CVE-2021-31728, CVE-2022-42045 |
| 26 | inpoutx64 | inpoutx64 v1.2 |
| 27 | DirectIo64 | PassMark OSForensics |
| 28 | AsrDrv106 | ASRock IO Driver |
| 29 | ALSysIO64 | Core Temp |
| **30** | **AMDRyzenMasterDriver** | **AMD Ryzen Master Service, CVE-2020-12928** ⭐ |
| 31 | physmem | Physical Memory Access Driver |
| 32 | LenovoDiagnosticsDriver | Lenovo Diagnostics, CVE-2022-3699 |
| 33 | pcdsrvc_x64 | PC-Doctor, CVE-2019-12280 |
| 34 | WinIo | MSI Foundation Service |
| 35 | EtdSupport | ETDi Support Driver v18.0 |
| 36 | KExplore | Kernel Explorer Driver |
| 37 | KObjExp | Kernel Object Explorer |
| 38 | KRegExp | Kernel Registry Explorer |
| 39 | EchoDrv | Echo AntiCheat driver |
| 40 | nvoclock | NVIDIA System Utility Driver |
| 41 | IREC | Binalyze DFIR, CVE-2023-41444 |
| 42 | PhyDMACC | SLIC ToolKit |
| 43 | rzpnk | Razer Synapse, CVE-2017-9769 |
| **44** | **PdFwKrnl** | **AMD Radeon USB-C PD, CVE-2023-20598** ⭐ |
| 45 | AODDriver | AMD OverDrive, CVE-2020-12928 |
| 46 | wnBios64 | Wincor Nixdorf BIOS |
| 47 | EleetX1 | EVGA ELEET X1 |
| 48 | AxtuDrv | ASRock Extreme Tuner |
| 49 | AppShopDrv103 | ASRock APP Shop |
| 50 | AsrDrv107n | ASRock Motherboard Utility |
| 51 | AsrDrv107 | ASRock Motherboard Utility |
| 52 | PMxDrv | Intel Management Engine Tools |
| 53 | HwRwDrv.x64 | Hardware R/W driver |
| **54** | **NeacSafe64** | **mini-filter, CVE-2025-45737** ⭐ |
| **55** | **ThrottleStop** | **TechPowerUp, CVE-2025-7771** ⭐ |
| 56 | TPwSav | Toshiba power saving |
| **57** | **LnvMSRIO** | **Lenovo MSR I/O, CVE-2025-8061** ⭐ |
| 58 | CORMEM | Sapera Memory Manager |
| 59 | IPCType | IPCType Device Driver |
| 60 | WinHwDriver | Guangzhou Shangke giveio |
| 61 | affdriver | AMD BIOS Flash Utility |
| 62 | mtxC9CB | Matrox Graphics |
| 63 | PGRHostControl | FLIR PGRHostControl SDK |
| 64 | LECOMAx | LECO LECOMA Device Driver |

⭐ = не в Microsoft Vulnerable Driver Blocklist на Win11 22H2+ (working on default install).

### Как использовать в проекте

**Kernel driver mapping** — три опции по возрастанию сложности:

#### 1. Наш KernelDriverMapper (single provider: iqvw64e.sys)
```powershell
KernelDriverMapper.exe --key <name> --indPages <driver.sys>
```
- **Работает**: Win7 → Win10 21H2
- **НЕ работает** на Win11 22H2+ если VulnerableDriverBlocklist активен (провалится при загрузке `iqvw64e.sys`)

#### 2. Внешний KDU (65 fallback providers)
```
kdu.exe -map <driver.sys>
```
- Работает на любом Win11 с любым build'ом
- Автоматический fallback: если один provider blocked, пробуется следующий
- Download: https://github.com/hfiref0x/KDU/releases

#### 3. sc create + testsigning (простейший)
```powershell
bcdedit /set testsigning on   # + reboot
sc create <name> type= kernel binPath= "<path>"
sc start <name>
```
- Только для research (testsigning banner видно в углу экрана)
- НЕ работает если Secure Boot активен

### Roadmap: интеграция KDU-стиля в KernelDriverMapper

TODO для будущих релизов: extended provider table в `KernelDriverMapper.exe` с fallback logic. Значительная работа — 65 providers, каждый со своим exploitation payload'ом. См. [`docs/DRIVER_HARDENING.md`](DRIVER_HARDENING.md) roadmap P2.

### Legal

- **Скачивание** vulnerable driver'ов из manufacturer'а — legal (это Signed producer's driver).
- **Использование** vulnerable driver для kernel r/w в **твоей own system** — legal (personal research).
- **Использование** против machine, к которой у тебя нет доступа — CFAA / CMA / StGB § 202a violation.

См. [`ETHICS.md`](ETHICS.md).

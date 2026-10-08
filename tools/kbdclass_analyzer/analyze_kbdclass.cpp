//
// analyze_kbdclass.exe - native analyzer for kbdclass.sys.
//
// Parses kbdclass.sys, finds KeyboardClassServiceCallback via Microsoft PDB
// symbols first, then falls back to legacy prologue signatures. Writes the
// RVA + fingerprint to HKLM\SOFTWARE\F20Driver for the F20 kernel driver.
//
// Zero Python dependency. Uses DbgHelp for symbol lookup, URLMon for direct
// PDB download when symsrv.dll is unavailable, and BCrypt for SHA256.
//

#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <bcrypt.h>
#include <DbgHelp.h>
#include <urlmon.h>

#include <cstdio>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#pragma comment(lib, "bcrypt.lib")
#pragma comment(lib, "dbghelp.lib")
#pragma comment(lib, "urlmon.lib")

// ============================================================================
// Signature table - MUST stay in sync with:
//   - F20Driver/main.cpp  kSigs[] (used by ValidateCallbackPrologue)
//   - Legacy F20Kit/analyze_kbdclass.py SIGS
// ============================================================================
struct Sig {
    const char*                  name;
    std::vector<unsigned char>   bytes;
    std::string                  mask;
};

static std::vector<Sig> BuildSigs() {
    return {
        // Win11 24H2 (build 26100): 4-arg save + push r12..r15
        { "win11_24h2_4arg",
          { 0x48,0x89,0x5C,0x24,0,  0x48,0x89,0x6C,0x24,0,
            0x48,0x89,0x74,0x24,0,  0x48,0x89,0x4C,0x24,0,
            0x57,  0x41,0x54, 0x41,0x55, 0x41,0x56, 0x41,0x57,
            0x48,0x83,0xEC,0,  0x4D,0x8B,0xE9 },
          "xxxx?xxxx?xxxx?xxxx?xxxxxxxxxxxx?xxx" },

        // Win11 22H2/23H2: 3-arg + push rdi/r14/r15 + mov r14,r9
        { "win11_22h2_3arg",
          { 0x48,0x89,0x5C,0x24,0,  0x48,0x89,0x6C,0x24,0,
            0x48,0x89,0x74,0x24,0,  0x57, 0x41,0x56, 0x41,0x57,
            0x48,0x83,0xEC,0,  0x4D,0x8B,0xF1 },
          "xxxx?xxxx?xxxx?xxxxxxxx?xxx" },

        // Win10 22H2 / Server 2022: 3-arg + xor ebx,ebx + mov r14,r8
        { "win10_22h2_3arg_xor",
          { 0x48,0x89,0x5C,0x24,0,  0x48,0x89,0x6C,0x24,0,
            0x48,0x89,0x74,0x24,0,  0x57, 0x41,0x56, 0x41,0x57,
            0x48,0x83,0xEC,0,  0x33,0xDB,  0x4D,0x8B,0xF0 },
          "xxxx?xxxx?xxxx?xxxxxxxx?xxxxx" },

        // [REMOVED] win10_22h2_19045_4push - matched the WRONG function and
        // caused DRIVER_IRQL_NOT_LESS_OR_EQUAL BSOD on Win10 22H2 19045.x.
        // PDB lookup now handles this build family. Keep this unsafe byte
        // pattern removed so signature fallback cannot reintroduce the BSOD.

        // Win10 1903-21H2: standard 3-arg prologue + xor ebp,ebp + mov rsi,r8
        { "win10_1903_3arg",
          { 0x48,0x89,0x5C,0x24,0,  0x48,0x89,0x6C,0x24,0,
            0x48,0x89,0x74,0x24,0,  0x57,  0x48,0x83,0xEC,0,
            0x33,0xED,  0x49,0x8B,0xF0 },
          "xxxx?xxxx?xxxx?xxxxx?xxxxx" },

        // Win10 1809-: 2-arg + mov r10,r9 + xor ebx,r8
        { "win10_1809_2arg",
          { 0x48,0x89,0x5C,0x24,0,  0x48,0x89,0x74,0x24,0,
            0x57,  0x48,0x83,0xEC,0,  0x4D,0x8B,0xD1, 0x41,0x33,0xD8 },
          "xxxx?xxxx?xxxx?xxxxxx" },

        // Win8/8.1: short 1-arg + push rdi + sub rsp + mov rdi,rdx
        { "win8_2arg_short",
          { 0x48,0x89,0x5C,0x24,0,  0x57, 0x48,0x83,0xEC,0,
            0x48,0x8B,0xFA,  0x48,0x8B,0xD9,  0x48,0x81,0xC1 },
          "xxxx?xxxx?xxxxxxxxx" },

        // Win7
        { "win7_legacy",
          { 0x48,0x89,0x5C,0x24,0,  0x48,0x89,0x74,0x24,0,  0x57,
            0x48,0x83,0xEC,0,  0x33,0xED,  0x48,0x8B,0xFA,  0x49,0x8B,0xD9 },
          "xxxx?xxxx?xxxxx?xxxxxxxxx" },

        // Generic lenient catch-all - last resort
        { "generic_3arg_lenient",
          { 0x48,0x89,0x5C,0x24,0,  0x48,0x89,0x6C,0x24,0,
            0x48,0x89,0x74,0x24,0,  0x57 },
          "xxxx?xxxx?xxxx?x" },
    };
}

// ============================================================================
// PE parsing
// ============================================================================
struct SectionInfo {
    char name[9];
    DWORD rva;
    DWORD virtual_size;
    DWORD raw_off;
    DWORD raw_size;
};

struct PdbInfo {
    bool present = false;
    GUID guid = {};
    DWORD age = 0;
    std::string original_path;
    std::string pdb_name;
    std::string guid_age;
};

struct TextInfo {
    DWORD text_rva;
    DWORD text_size;
    DWORD text_file_off;
    DWORD timestamp;
    DWORD image_size;
    DWORD debug_rva;
    DWORD debug_size;
    std::vector<SectionInfo> sections;
};

static bool parse_pe(const std::vector<unsigned char>& data, TextInfo* out) {
    *out = {};
    if (data.size() < 0x40) return false;
    DWORD e_lfanew = *(const DWORD*)&data[0x3C];
    if (e_lfanew + sizeof(IMAGE_NT_HEADERS64) > data.size()) return false;
    if (data[e_lfanew] != 'P' || data[e_lfanew + 1] != 'E' ||
        data[e_lfanew + 2] != 0 || data[e_lfanew + 3] != 0) return false;

    const IMAGE_NT_HEADERS64* nt =
        (const IMAGE_NT_HEADERS64*)&data[e_lfanew];

    if (nt->OptionalHeader.Magic != IMAGE_NT_OPTIONAL_HDR64_MAGIC) return false;

    out->timestamp = nt->FileHeader.TimeDateStamp;
    out->image_size = nt->OptionalHeader.SizeOfImage;
    out->debug_rva =
        nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_DEBUG].VirtualAddress;
    out->debug_size =
        nt->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_DEBUG].Size;

    const IMAGE_SECTION_HEADER* sec = IMAGE_FIRST_SECTION(nt);
    bool found_text = false;
    for (int i = 0; i < nt->FileHeader.NumberOfSections; i++) {
        SectionInfo si = {};
        memcpy(si.name, sec[i].Name, sizeof(sec[i].Name));
        si.name[8] = 0;
        si.rva = sec[i].VirtualAddress;
        si.virtual_size = sec[i].Misc.VirtualSize;
        si.raw_off = sec[i].PointerToRawData;
        si.raw_size = sec[i].SizeOfRawData;
        out->sections.push_back(si);

        if (memcmp(sec[i].Name, ".text", 5) == 0) {
            out->text_rva = sec[i].VirtualAddress;
            out->text_size = sec[i].Misc.VirtualSize;
            out->text_file_off = sec[i].PointerToRawData;
            found_text = true;
        }
    }
    return found_text;
}

static bool rva_to_file_off(const TextInfo& pe, DWORD rva, DWORD size,
                            DWORD* out_off)
{
    if (!out_off) return false;
    for (const auto& s : pe.sections) {
        DWORD span = s.virtual_size > s.raw_size ? s.virtual_size : s.raw_size;
        if (span == 0) continue;
        if (rva < s.rva) continue;
        DWORD rel = rva - s.rva;
        if (rel > span || size > span - rel) continue;
        *out_off = s.raw_off + rel;
        return true;
    }
    return false;
}

static std::string basename_from_path(const std::string& path) {
    size_t p = path.find_last_of("\\/");
    if (p == std::string::npos) return path;
    return path.substr(p + 1);
}

static std::wstring widen_acp(const std::string& s) {
    if (s.empty()) return std::wstring();
    int n = MultiByteToWideChar(CP_ACP, 0, s.c_str(), -1, NULL, 0);
    if (n <= 0) return std::wstring();
    std::wstring out((size_t)n - 1, L'\0');
    MultiByteToWideChar(CP_ACP, 0, s.c_str(), -1, &out[0], n);
    return out;
}

static std::string get_env_string(const char* name) {
    DWORD need = GetEnvironmentVariableA(name, NULL, 0);
    if (need == 0) return std::string();
    std::string out(need, '\0');
    DWORD got = GetEnvironmentVariableA(name, &out[0], need);
    if (got == 0 || got >= need) return std::string();
    out.resize(got);
    return out;
}

static std::string join_path(const std::string& a, const std::string& b) {
    if (a.empty()) return b;
    char last = a[a.size() - 1];
    if (last == '\\' || last == '/') return a + b;
    return a + "\\" + b;
}

static bool ensure_dir_recursive(const std::string& dir) {
    if (dir.empty()) return false;
    for (size_t i = 0; i <= dir.size(); i++) {
        if (i != dir.size() && dir[i] != '\\' && dir[i] != '/') continue;
        std::string part = dir.substr(0, i);
        if (part.empty()) continue;
        if (part.size() == 2 && part[1] == ':') continue;
        if (!CreateDirectoryA(part.c_str(), NULL)) {
            DWORD e = GetLastError();
            if (e != ERROR_ALREADY_EXISTS) return false;
        }
    }
    return true;
}

static bool file_exists_nonempty(const std::string& path) {
    WIN32_FILE_ATTRIBUTE_DATA fad = {};
    if (!GetFileAttributesExA(path.c_str(), GetFileExInfoStandard, &fad))
        return false;
    if (fad.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) return false;
    return fad.nFileSizeHigh != 0 || fad.nFileSizeLow != 0;
}

static std::string win_error(DWORD err) {
    char* msg = NULL;
    DWORD n = FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER |
                             FORMAT_MESSAGE_FROM_SYSTEM |
                             FORMAT_MESSAGE_IGNORE_INSERTS,
                             NULL, err, 0, (LPSTR)&msg, 0, NULL);
    std::string out;
    if (n && msg) {
        out.assign(msg, n);
        while (!out.empty() && (out.back() == '\r' || out.back() == '\n' ||
                                out.back() == ' ')) {
            out.pop_back();
        }
    }
    if (msg) LocalFree(msg);
    if (out.empty()) {
        char buf[32];
        sprintf_s(buf, sizeof(buf), "error %lu", err);
        out = buf;
    }
    return out;
}

static std::string format_guid_age(const GUID& g, DWORD age) {
    std::ostringstream os;
    os << std::uppercase << std::hex << std::setfill('0')
       << std::setw(8) << g.Data1
       << std::setw(4) << g.Data2
       << std::setw(4) << g.Data3;
    for (int i = 0; i < 8; i++) {
        os << std::setw(2) << (unsigned int)g.Data4[i];
    }
    os << std::uppercase << std::hex << age;
    return os.str();
}

static bool read_pdb_info(const std::vector<unsigned char>& data,
                          const TextInfo& pe,
                          PdbInfo* out)
{
    if (!out) return false;
    *out = {};
    if (pe.debug_rva == 0 || pe.debug_size < sizeof(IMAGE_DEBUG_DIRECTORY))
        return false;

    DWORD debug_off = 0;
    if (!rva_to_file_off(pe, pe.debug_rva, pe.debug_size, &debug_off))
        return false;
    if ((size_t)debug_off + pe.debug_size > data.size())
        return false;

    ULONG count = pe.debug_size / sizeof(IMAGE_DEBUG_DIRECTORY);
    for (ULONG i = 0; i < count; i++) {
        const IMAGE_DEBUG_DIRECTORY* dbg =
            (const IMAGE_DEBUG_DIRECTORY*)&data[(size_t)debug_off +
                                                i * sizeof(IMAGE_DEBUG_DIRECTORY)];
        if (dbg->Type != IMAGE_DEBUG_TYPE_CODEVIEW || dbg->SizeOfData < 24)
            continue;

        DWORD cv_off = dbg->PointerToRawData;
        if (cv_off == 0 &&
            !rva_to_file_off(pe, dbg->AddressOfRawData, dbg->SizeOfData, &cv_off)) {
            continue;
        }
        if ((size_t)cv_off + dbg->SizeOfData > data.size())
            continue;
        const unsigned char* cv = &data[cv_off];
        if (memcmp(cv, "RSDS", 4) != 0)
            continue;

        out->present = true;
        memcpy(&out->guid, cv + 4, sizeof(GUID));
        out->age = *(const DWORD*)(cv + 20);

        size_t name_start = (size_t)cv_off + 24;
        size_t name_end = name_start;
        size_t name_limit = (size_t)cv_off + dbg->SizeOfData;
        while (name_end < name_limit && data[name_end] != 0) name_end++;
        out->original_path.assign((const char*)&data[name_start],
                                  name_end - name_start);
        out->pdb_name = basename_from_path(out->original_path);
        out->guid_age = format_guid_age(out->guid, out->age);
        return !out->pdb_name.empty() && !out->guid_age.empty();
    }
    return false;
}

static bool download_pdb_to_cache(const PdbInfo& pdb,
                                  std::string* out_pdb_dir,
                                  std::string* out_pdb_path)
{
    if (!pdb.present || pdb.pdb_name.empty() || pdb.guid_age.empty())
        return false;

    std::string program_data = get_env_string("ProgramData");
    if (program_data.empty()) program_data = "C:\\ProgramData";
    std::string root = join_path(program_data, "F20Driver\\symbols");
    std::string pdb_dir = join_path(join_path(root, pdb.pdb_name), pdb.guid_age);
    std::string pdb_path = join_path(pdb_dir, pdb.pdb_name);
    if (out_pdb_dir) *out_pdb_dir = pdb_dir;
    if (out_pdb_path) *out_pdb_path = pdb_path;

    if (file_exists_nonempty(pdb_path)) {
        std::cout << "  PDB cache hit: " << pdb_path << "\n";
        return true;
    }

    if (!ensure_dir_recursive(pdb_dir)) {
        std::cerr << "  [pdb] cannot create cache dir: " << pdb_dir
                  << " (" << win_error(GetLastError()) << ")\n";
        return false;
    }

    std::string url = "https://msdl.microsoft.com/download/symbols/" +
                      pdb.pdb_name + "/" + pdb.guid_age + "/" + pdb.pdb_name;
    std::cout << "  PDB download: " << url << "\n";

    HRESULT hr = URLDownloadToFileA(NULL, url.c_str(), pdb_path.c_str(), 0, NULL);
    if (FAILED(hr) || !file_exists_nonempty(pdb_path)) {
        DeleteFileA(pdb_path.c_str());
        std::cerr << "  [pdb] download failed: HRESULT=0x"
                  << std::hex << std::uppercase << (unsigned long)hr
                  << std::dec << "\n";
        return false;
    }

    std::cout << "  PDB cached: " << pdb_path << "\n";
    return true;
}

static bool resolve_symbol_with_dbghelp(const char* image_path,
                                        const TextInfo& pe,
                                        const std::string& symbol_path,
                                        DWORD* out_rva)
{
    if (!out_rva) return false;
    *out_rva = 0;

    HANDLE proc = GetCurrentProcess();
    SymSetOptions(SYMOPT_DEFERRED_LOADS |
                  SYMOPT_UNDNAME |
                  SYMOPT_EXACT_SYMBOLS |
                  SYMOPT_FAIL_CRITICAL_ERRORS);

    std::wstring wide_symbol_path = widen_acp(symbol_path);
    if (!SymInitializeW(proc, wide_symbol_path.c_str(), FALSE)) {
        std::cerr << "  [pdb] SymInitializeW failed: "
                  << win_error(GetLastError()) << "\n";
        return false;
    }

    bool ok = false;
    do {
        std::wstring wide_image = widen_acp(image_path);
        DWORD64 mod_base = SymLoadModuleExW(proc, NULL, wide_image.c_str(),
                                            L"kbdclass", 0, pe.image_size,
                                            NULL, 0);
        if (mod_base == 0) {
            std::cerr << "  [pdb] SymLoadModuleExW failed: "
                      << win_error(GetLastError()) << "\n";
            break;
        }

        const wchar_t* names[] = {
            L"kbdclass!KeyboardClassServiceCallback",
            L"KeyboardClassServiceCallback",
        };
        for (const wchar_t* name : names) {
            SYMBOL_INFO_PACKAGEW sip = {};
            sip.si.SizeOfStruct = sizeof(SYMBOL_INFOW);
            sip.si.MaxNameLen = MAX_SYM_NAME;
            if (!SymFromNameW(proc, name, &sip.si))
                continue;

            DWORD64 base = sip.si.ModBase ? sip.si.ModBase : mod_base;
            if (sip.si.Address < base ||
                sip.si.Address >= base + pe.image_size) {
                std::cerr << "  [pdb] symbol address outside module: "
                          << "addr=0x" << std::hex << sip.si.Address
                          << " base=0x" << base << std::dec << "\n";
                continue;
            }

            DWORD rva = (DWORD)(sip.si.Address - base);
            if (rva < pe.text_rva || rva >= pe.text_rva + pe.text_size) {
                std::cerr << "  [pdb] symbol RVA 0x" << std::hex << rva
                          << " is outside .text" << std::dec << "\n";
                continue;
            }

            *out_rva = rva;
            std::wcout << L"  PDB symbol: " << name
                       << L" RVA=0x" << std::hex << std::uppercase << rva
                       << std::dec << L"\n";
            ok = true;
            break;
        }

        if (!ok) {
            std::cerr << "  [pdb] SymFromName failed for "
                         "KeyboardClassServiceCallback: "
                      << win_error(GetLastError()) << "\n";
        }
    } while (false);

    SymCleanup(proc);
    return ok;
}

static bool find_callback_by_pdb(const std::vector<unsigned char>& data,
                                 const TextInfo& pe,
                                 const char* image_path,
                                 DWORD* out_rva)
{
    if (!out_rva) return false;
    *out_rva = 0;

    PdbInfo pdb;
    if (!read_pdb_info(data, pe, &pdb)) {
        std::cerr << "  [pdb] no RSDS CodeView record in image\n";
        return false;
    }

    std::cout << "PDB info:\n";
    std::cout << "  name=" << pdb.pdb_name << "\n";
    std::cout << "  guid+age=" << pdb.guid_age << "\n";

    std::string pdb_dir;
    std::string pdb_path;
    bool have_cached_pdb = download_pdb_to_cache(pdb, &pdb_dir, &pdb_path);

    std::string program_data = get_env_string("ProgramData");
    if (program_data.empty()) program_data = "C:\\ProgramData";
    std::string symbol_root = join_path(program_data, "F20Driver\\symbols");
    ensure_dir_recursive(symbol_root);

    std::string symbol_path;
    if (have_cached_pdb) {
        symbol_path += pdb_dir;
        symbol_path += ";";
    }
    symbol_path += "srv*";
    symbol_path += symbol_root;
    symbol_path += "*https://msdl.microsoft.com/download/symbols";

    std::string env_symbol_path = get_env_string("_NT_SYMBOL_PATH");
    if (!env_symbol_path.empty()) {
        symbol_path += ";";
        symbol_path += env_symbol_path;
    }

    std::cout << "  symbol path=" << symbol_path << "\n";
    return resolve_symbol_with_dbghelp(image_path, pe, symbol_path, out_rva);
}

// ============================================================================
// Pattern matching
// ============================================================================
static bool pattern_match(const unsigned char* data, const Sig& sig) {
    for (size_t k = 0; k < sig.mask.size(); k++) {
        if (sig.mask[k] == 'x' && data[k] != sig.bytes[k]) return false;
    }
    return true;
}

static std::vector<size_t> scan_sig(const std::vector<unsigned char>& data,
                                     const Sig& sig,
                                     size_t start, size_t end)
{
    std::vector<size_t> hits;
    if (sig.mask.size() == 0 || start + sig.mask.size() > end) return hits;
    size_t last = end - sig.mask.size();
    for (size_t i = start; i <= last; i++) {
        if (pattern_match(&data[i], sig)) hits.push_back(i);
    }
    return hits;
}

// ============================================================================
// looks_like_function - candidate function should have epilogue + ret +
// at least 2 calls within its first ~8 KB. Filters out random byte sequences
// that happen to match a prologue pattern but aren't real functions.
// ============================================================================
static bool looks_like_function(const std::vector<unsigned char>& data,
                                 size_t off, size_t text_end)
{
    size_t max_scan = 0x2000;
    if (off + max_scan > text_end) max_scan = text_end - off;
    if (max_scan < 4) return false;

    bool has_epilogue = false;
    bool has_ret = false;
    int  call_count = 0;

    const unsigned char* p = &data[off];
    for (size_t i = 0; i + 3 < max_scan; i++) {
        unsigned char b0 = p[i];
        if (!has_epilogue && b0 == 0x48 && p[i + 1] == 0x83 && p[i + 2] == 0xC4)
            has_epilogue = true;
        if (!has_ret && b0 == 0xC3) has_ret = true;
        if (b0 == 0xE8) call_count++;
    }
    return has_epilogue && has_ret && call_count >= 2;
}

// ============================================================================
// SHA256 of file bytes -> lowercase hex
// ============================================================================
static std::string sha256_hex(const std::vector<unsigned char>& data) {
    std::string out;
    BCRYPT_ALG_HANDLE alg = NULL;
    BCRYPT_HASH_HANDLE hash = NULL;
    NTSTATUS s = BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM,
                                              NULL, 0);
    if (s != 0) return out;

    s = BCryptCreateHash(alg, &hash, NULL, 0, NULL, 0, 0);
    if (s != 0) { BCryptCloseAlgorithmProvider(alg, 0); return out; }

    BCryptHashData(hash, (PUCHAR)data.data(), (ULONG)data.size(), 0);

    unsigned char digest[32] = {};
    BCryptFinishHash(hash, digest, 32, 0);
    BCryptDestroyHash(hash);
    BCryptCloseAlgorithmProvider(alg, 0);

    char buf[3];
    for (int i = 0; i < 32; i++) {
        sprintf_s(buf, sizeof(buf), "%02x", digest[i]);
        out += buf;
    }
    return out;
}

// ============================================================================
// Registry write
// ============================================================================
static bool set_reg_sz_utf8(HKEY hk, const wchar_t* name,
                            const std::string& value)
{
    int need = MultiByteToWideChar(CP_UTF8, 0, value.c_str(), -1, NULL, 0);
    if (need <= 0) return false;
    std::vector<wchar_t> wide((size_t)need);
    if (MultiByteToWideChar(CP_UTF8, 0, value.c_str(), -1,
                            wide.data(), need) != need) {
        return false;
    }
    return RegSetValueExW(hk, name, 0, REG_SZ, (const BYTE*)wide.data(),
                          (DWORD)(wide.size() * sizeof(wchar_t))) == ERROR_SUCCESS;
}

static bool write_registry(DWORD rva, DWORD timestamp, DWORD image_size,
                            const std::string& sha256_hex_s,
                            const std::string& sig_name)
{
    HKEY hk = NULL;
    DWORD disp = 0;
    LSTATUS rs = RegCreateKeyExW(HKEY_LOCAL_MACHINE, L"SOFTWARE\\F20Driver",
                                  0, NULL, REG_OPTION_NON_VOLATILE, KEY_WRITE,
                                  NULL, &hk, &disp);
    if (rs != ERROR_SUCCESS) return false;

    RegSetValueExW(hk, L"CallbackRva", 0, REG_DWORD,
                   (BYTE*)&rva, sizeof(rva));
    RegSetValueExW(hk, L"KbdTimestamp", 0, REG_DWORD,
                   (BYTE*)&timestamp, sizeof(timestamp));
    RegSetValueExW(hk, L"KbdImageSize", 0, REG_DWORD,
                   (BYTE*)&image_size, sizeof(image_size));
    bool ok = set_reg_sz_utf8(hk, L"KbdSha256", sha256_hex_s) &&
              set_reg_sz_utf8(hk, L"Signature", sig_name);
    RegCloseKey(hk);
    return ok;
}

// ============================================================================
// Diagnostic dump - list top candidate function starts so we can identify
// new signature variants from user logs.
// ============================================================================
static void dump_candidates(const std::vector<unsigned char>& data,
                             const TextInfo& pe)
{
    const std::vector<unsigned char> common =
        { 0x48,0x89,0x5C,0x24,0 };
    const std::string mask = "xxxx?";
    size_t start = pe.text_file_off;
    size_t end = start + pe.text_size;

    std::cout << "\n=== DIAGNOSTIC: candidate function starts in .text ===\n";
    int count = 0;
    if (end <= common.size() || start + common.size() > end) return;
    size_t last = end - common.size();
    for (size_t i = start; i <= last; i++) {
        bool ok = true;
        for (size_t k = 0; k < common.size(); k++) {
            if (mask[k] == 'x' && data[i + k] != common[k]) { ok = false; break; }
        }
        if (!ok) continue;
        if (!looks_like_function(data, i, end)) continue;
        DWORD rva = (DWORD)(i - pe.text_file_off) + pe.text_rva;
        printf("  RVA=0x%06X  bytes: ", rva);
        for (int k = 0; k < 48 && (i + k) < data.size(); k++) {
            printf("%02x ", data[i + k]);
        }
        printf("\n");
        if (++count >= 20) {
            printf("  ... (limited to 20)\n");
            break;
        }
    }
    std::cout << "=== send these to dev if your build needs a new sig ===\n";
}

// ============================================================================
// main
// ============================================================================
int main(int argc, char** argv) {
    // Default: scan the live system kbdclass. Argv[1] override is for diag /
    // testing against a kbdclass.sys collected from another machine.
    const char* kbd_path = "C:\\Windows\\System32\\drivers\\kbdclass.sys";
    bool dry_run = false;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--dry") == 0) {
            dry_run = true;
        } else {
            kbd_path = argv[i];
        }
    }

    std::ifstream f(kbd_path, std::ios::binary | std::ios::ate);
    if (!f) {
        std::cerr << "[!] cannot open " << kbd_path << "\n";
        return 1;
    }
    std::streamsize sz = f.tellg();
    if (sz <= 0) { std::cerr << "[!] empty file\n"; return 1; }
    f.seekg(0, std::ios::beg);
    std::vector<unsigned char> data((size_t)sz);
    if (!f.read((char*)data.data(), sz)) {
        std::cerr << "[!] read failed\n";
        return 1;
    }
    f.close();

    TextInfo pe;
    if (!parse_pe(data, &pe)) {
        std::cerr << "[!] PE parse failed\n";
        return 1;
    }

    std::string sha = sha256_hex(data);

    printf("kbdclass.sys: size=%zu  timestamp=0x%08X\n",
           data.size(), pe.timestamp);
    printf("  .text RVA=0x%X size=0x%X\n", pe.text_rva, pe.text_size);
    printf("  sha256=%s...\n", sha.substr(0, 32).c_str());

    DWORD pdb_rva = 0;
    if (find_callback_by_pdb(data, pe, kbd_path, &pdb_rva)) {
        printf("[+] Found via PDB: RVA=0x%X\n", pdb_rva);

        if (dry_run) {
            std::cout << "[dry] skipping registry write\n";
            return 0;
        }
        if (!write_registry(pdb_rva, pe.timestamp, pe.image_size, sha,
                            "pdb_symbol")) {
            std::cerr << "[!] Registry write failed (need admin)\n";
            return 3;
        }
        printf("[+] Wrote HKLM\\SOFTWARE\\F20Driver\\CallbackRva = 0x%X\n",
               pdb_rva);
        printf("[+] Wrote KbdTimestamp = 0x%08X\n", pe.timestamp);
        printf("[+] Wrote KbdImageSize = 0x%X\n", pe.image_size);
        printf("[+] Wrote Signature = pdb_symbol\n");
        return 0;
    }

    printf("[?] PDB lookup failed/unavailable - falling back to signatures.\n");
    printf("Scanning signatures:\n");

    size_t start = pe.text_file_off;
    size_t end   = start + pe.text_size;
    if (end > data.size()) end = data.size();

    auto sigs = BuildSigs();
    for (const auto& sig : sigs) {
        auto hits = scan_sig(data, sig, start, end);
        std::vector<size_t> verified;
        for (auto h : hits) {
            if (looks_like_function(data, h, end)) verified.push_back(h);
        }
        printf("  %-24s hits=%zu verified=%zu\n",
               sig.name, hits.size(), verified.size());
        if (verified.size() == 1) {
            size_t h = verified[0];
            DWORD rva = (DWORD)(h - pe.text_file_off) + pe.text_rva;
            printf("[+] Found via %s: file=0x%zX RVA=0x%X\n",
                   sig.name, h, rva);

            if (dry_run) {
                std::cout << "[dry] skipping registry write\n";
                return 0;
            }
            if (!write_registry(rva, pe.timestamp, pe.image_size, sha, sig.name)) {
                std::cerr << "[!] Registry write failed (need admin)\n";
                return 3;
            }
            printf("[+] Wrote HKLM\\SOFTWARE\\F20Driver\\CallbackRva = 0x%X\n", rva);
            printf("[+] Wrote KbdTimestamp = 0x%08X\n", pe.timestamp);
            printf("[+] Wrote KbdImageSize = 0x%X\n", pe.image_size);
            return 0;
        }
    }

    std::cerr << "[!] No strict signature matched.\n";
    std::cerr << "[!] Driver will run in monitor-only mode (no inject, no BSOD).\n";
    dump_candidates(data, pe);
    return 2;
}

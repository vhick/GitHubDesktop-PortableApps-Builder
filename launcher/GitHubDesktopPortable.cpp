// GitHub Desktop PortableApps launcher. MIT. Windows x64, C++17.
// Process-scoped path setup; no registry/shortcut deletion or global environment changes.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <filesystem>
#include <string>
#include <vector>
#include <stdexcept>
#include <cstdio>

namespace fs = std::filesystem;

static void fail(const wchar_t* msg) {
  MessageBoxW(nullptr, msg, L"GitHub Desktop Portable - launch error", MB_OK | MB_ICONERROR);
}
static std::wstring module_path() {
  std::vector<wchar_t> buf(32768);
  DWORD n = GetModuleFileNameW(nullptr, buf.data(), static_cast<DWORD>(buf.size()));
  if (!n || n >= buf.size()) throw std::runtime_error("cannot locate launcher executable");
  return std::wstring(buf.data(), n);
}
static std::wstring quote(const std::wstring& s) {
  std::wstring out = L"\"";
  size_t slash = 0;
  for (wchar_t c : s) {
    if (c == L'\\') { ++slash; continue; }
    if (c == L'"') { out.append(slash * 2 + 1, L'\\'); out.push_back(L'"'); slash = 0; continue; }
    out.append(slash, L'\\'); slash = 0;
    out.push_back(c);
  }
  out.append(slash * 2, L'\\'); out.push_back(L'"');
  return out;
}
static void env(const wchar_t* name, const std::wstring& value) {
  if (!SetEnvironmentVariableW(name, value.c_str())) throw std::runtime_error("cannot set child environment");
}
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
  try {
    const fs::path root = fs::path(module_path()).parent_path();
    const fs::path appDir = root / L"App" / L"GitHubDesktop";
    const fs::path appExe = appDir / L"GitHubDesktop.exe";
    const fs::path data = root / L"Data";
    const fs::path profile = data / L"Profile";
    const fs::path home = data / L"GitHome";
    if (!fs::is_regular_file(appExe)) { fail(L"App\\GitHubDesktop\\GitHubDesktop.exe was not found. Package is incomplete."); return 10; }
    fs::create_directories(profile / L"Chromium");
    fs::create_directories(profile / L"logs");
    fs::create_directories(home);
    fs::create_directories(data / L"TraceGuard");
    // HOME/GIT_CONFIG_GLOBAL apply to this child process tree only, never system-wide.
    env(L"GHD_PORTABLE_ROOT", data.wstring());
    env(L"HOME", home.wstring());
    env(L"GIT_CONFIG_GLOBAL", (home / L".gitconfig").wstring());
    env(L"XDG_CONFIG_HOME", (home / L".config").wstring());
    env(L"XDG_CACHE_HOME", (home / L".cache").wstring());

    int argc = 0;
    LPWSTR* argv = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!argv) throw std::runtime_error("argument parsing failed");
    std::wstring cmd = quote(appExe.wstring());
    for (int i = 1; i < argc; ++i) { cmd.push_back(L' '); cmd += quote(argv[i]); }
    LocalFree(argv);
    std::vector<wchar_t> mutableCmd(cmd.begin(), cmd.end());
    mutableCmd.push_back(L'\0');
    STARTUPINFOW si{}; si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    // Start suspended to add Chromium children to a job before they spawn.
    if (!CreateProcessW(appExe.c_str(), mutableCmd.data(), nullptr, nullptr, FALSE,
                        CREATE_SUSPENDED, nullptr, appDir.c_str(), &si, &pi)) {
      fail(L"Cannot start GitHubDesktop.exe. Check App contents and file permissions."); return 11;
    }
    HANDLE job = CreateJobObjectW(nullptr, nullptr);
    bool assigned = job && AssignProcessToJobObject(job, pi.hProcess);
    // Never terminate someone else's process; the job is unnamed and contains only our child tree.
    if (ResumeThread(pi.hThread) == static_cast<DWORD>(-1)) {
      TerminateProcess(pi.hProcess, 12); // Our process has not started executing yet.
      if (job) CloseHandle(job);
      CloseHandle(pi.hThread); CloseHandle(pi.hProcess); return 12;
    }
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD exitCode = 1;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    CloseHandle(pi.hProcess);
    // Wait for normal Chromium/renderer child shutdown without killing descendants.
    if (assigned) { (void)WaitForSingleObject(job, 30000); }
    if (job) CloseHandle(job);
    return static_cast<int>(exitCode);
  } catch (const std::exception&) {
    fail(L"Portable startup failed while preparing Data. Check write permissions and disk space.");
    return 13;
  }
}

// Unofficial GitHub Desktop PortableApps launcher. MIT. Windows x64 C++17.
// Opt-in, reversible browser auth callback: only HKCU\Software\Classes\x-github-desktop-auth.
// b1r5: callback invocations are one-shot; normal launch waits on actual job accounting.
// Never modify installed GitHub Desktop's other protocols, shortcuts, or HKLM.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <shellapi.h>
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>
#include <stdexcept>
#include "AuthProtocolGuard.h"
#include "ProcessLifecycle.h"

namespace fs = std::filesystem;
static const wchar_t* kConsentFile = L"AuthRedirectConsent.txt";
static void notice(const wchar_t* title, const wchar_t* text, UINT flags = MB_OK | MB_ICONWARNING) {
  MessageBoxW(nullptr, text, title, flags);
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
    out.append(slash, L'\\'); slash = 0; out.push_back(c);
  }
  out.append(slash * 2, L'\\'); out.push_back(L'"');
  return out;
}
static void env(const wchar_t* name, const std::wstring& value) {
  if (!SetEnvironmentVariableW(name, value.c_str())) throw std::runtime_error("cannot set child environment");
}
static void logStatus(const fs::path& data, const std::wstring& line) {
  // Never write OAuth callback URLs, codes, account names or tokens to disk.
  std::wofstream out(data / L"TraceGuard" / L"AuthProtocolStatus.txt", std::ios::app);
  if (out) out << line << L"\n";
}
static int askConsent(const fs::path& data, bool forcePrompt) {
  const auto file = data / kConsentFile;
  if (!forcePrompt && fs::exists(file)) {
    std::ifstream in(file, std::ios::binary);
    std::string val; std::getline(in, val);
    if (val == "enabled") return 1;
    if (val == "disabled") return 0;
    throw std::runtime_error("unknown auth consent file contents");
  }
  int response = MessageBoxW(nullptr,
    L"GitHub Desktop Portable needs a Windows browser callback for GitHub sign-in.\n\n"
    L"Enable a TEMPORARY handler for x-github-desktop-auth?\n\n"
    L"YES: Back up any existing per-user handler, redirect sign-in to this portable copy "
    L"while it runs, and restore the previous handler on normal exit.\n\n"
    L"NO: Leave the Windows handler unchanged (browser sign-in may not finish).\n\n"
    L"The setting is remembered inside this portable Data folder. "
    L"An installed GitHub Desktop may not receive sign-in callbacks during the portable session.\n\n"
    L"Cancel: do not start the application.",
    L"GitHub Desktop Portable - browser sign-in permission",
    MB_YESNOCANCEL | MB_ICONQUESTION | MB_DEFBUTTON2);
  if (response == IDCANCEL || response == 0) return -1;
  const bool granted = response == IDYES;
  std::ofstream out(file, std::ios::binary | std::ios::trunc);
  if (!out) throw std::runtime_error("cannot save browser sign-in consent");
  out << (granted ? "enabled\n" : "disabled\n");
  out.flush();
  if (!out) throw std::runtime_error("cannot flush browser sign-in consent");
  return granted ? 1 : 0;
}
static bool isCallback(const std::vector<std::wstring>& args) {
  if (args.empty() || args.front() != L"--protocol-launcher") return false;
  // Windows invokes the registered callback with one URL argument only. Never
  // interpret URL content as independent CLI flags or shell commands.
  return args.size() == 2 &&
      args[1].rfind(L"x-github-desktop-auth://", 0) == 0 &&
      args[1].size() < 8192 && args[1].find_first_of(L"\r\n\0", 0, 2) == std::wstring::npos;
}
struct MutexLock {
  HANDLE h = nullptr;
  bool owns = false;
  ~MutexLock() {
    if (owns) ReleaseMutex(h);
    if (h) CloseHandle(h);
  }
  bool lock() {
    // Session-scoped, covers all portable copies to prevent clobbering each other's callback.
    h = CreateMutexW(nullptr, FALSE, L"Local\\vhick.GitHubDesktopPortable.auth.callback.v1");
    if (!h) return false;
    DWORD rc = WaitForSingleObject(h, 0);
    owns = rc == WAIT_OBJECT_0 || rc == WAIT_ABANDONED;
    return owns;
  }
};
int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
  try {
    const fs::path launcher = module_path();
    const fs::path root = launcher.parent_path();
    const fs::path appDir = root / L"App" / L"GitHubDesktop";
    const fs::path appExe = appDir / L"GitHubDesktop.exe";
    const fs::path data = root / L"Data";
    const fs::path profile = data / L"Profile";
    const fs::path home = data / L"GitHome";
    if (!fs::is_regular_file(appExe)) {
      notice(L"GitHub Desktop Portable", L"Missing App\\GitHubDesktop\\GitHubDesktop.exe; package incomplete.");
      return 10;
    }
    fs::create_directories(profile / L"Chromium");
    fs::create_directories(profile / L"logs");
    fs::create_directories(home);
    fs::create_directories(data / L"TraceGuard");
    env(L"GHD_PORTABLE_ROOT", data.wstring());
    env(L"HOME", home.wstring());
    env(L"GIT_CONFIG_GLOBAL", (home / L".gitconfig").wstring());
    env(L"XDG_CONFIG_HOME", (home / L".config").wstring());
    env(L"XDG_CACHE_HOME", (home / L".cache").wstring());

    int argc = 0;
    LPWSTR* raw = CommandLineToArgvW(GetCommandLineW(), &argc);
    if (!raw) throw std::runtime_error("argument parsing failed");
    std::vector<std::wstring> args;
    for (int i = 1; i < argc; ++i) args.emplace_back(raw[i]);
    LocalFree(raw);
    bool callback = isCallback(args);
    if (!callback && !args.empty() && args[0] == L"--protocol-launcher") {
      notice(L"GitHub Desktop Portable", L"Rejected malformed browser callback arguments.");
      return 15;
    }
    if (!callback && !args.empty() && args[0] == L"--auth-redirect-settings") {
      (void)askConsent(data, true);
      return 0;
    }

    // Browser callback subprocesses must NOT acquire the primary session mutex,
    // touch the registry, show consent dialogs or change recovery state.
    MutexLock lock;
    std::unique_ptr<AuthProtocolGuard> auth;
    if (!callback) {
      if (lock.lock()) {
        const auto journal = data / L"TraceGuard" / L"AuthProtocolRecovery.bin";
        const auto ownerCmd = quote(launcher.wstring()) + L" --protocol-launcher \"%1\"";
        auth = std::make_unique<AuthProtocolGuard>(L"x-github-desktop-auth", journal, ownerCmd);
        std::wstring recovery;
        if (!auth->recover(recovery)) {
          logStatus(data, L"RECOVERY CONFLICT: " + recovery);
          notice(L"GitHub Desktop Portable - callback recovery", recovery.c_str());
          // Do NOT override an unverified current handler while a journal is unresolved.
        } else {
          int enabled = askConsent(data, false);
          if (enabled < 0) return 0;
          if (enabled == 1) {
            std::wstring outcome;
            if (!auth->enable(outcome)) {
              logStatus(data, L"SIGN-IN UNAVAILABLE: " + outcome);
              notice(L"GitHub Desktop Portable - sign-in callback", outcome.c_str());
            } else {
              logStatus(data, L"AUTH HANDLER ACTIVE: temporary per-user browser callback registered.");
            }
          } else {
            logStatus(data, L"AUTH HANDLER DISABLED: no Windows protocol override requested.");
          }
        }
      } else {
        // A second ordinary launcher cannot safely own/manage the same callback,
        // nor can it reliably track the already-running app's process tree.
        logStatus(data, L"Auth callback mutex held by another portable instance; duplicate launch blocked.");
        notice(L"GitHub Desktop Portable",
               L"Another GitHub Desktop Portable launcher is already running.\n"
               L"Use its existing window, or close all portable GitHub Desktop processes "
               L"before launching a different copy. No protocol changes were made.");
        return 17;
      }
    }

    std::wstring cmd = quote(appExe.wstring());
    for (const auto& arg : args) cmd += L" " + quote(arg);
    std::vector<wchar_t> mutableCmd(cmd.begin(), cmd.end());
    mutableCmd.push_back(L'\0');
    STARTUPINFOW si{}; si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    // The browser callback is not a new interactive session. Launch the exact
    // packaged EXE with a safe, quoted URL argument, then DETACH immediately.
    // Electron's single-instance handler forwards it to the existing window.
    // Never hold a job/mutex or wait indefinitely for a callback-only process.
    if (callback) {
      if (!CreateProcessW(appExe.c_str(), mutableCmd.data(), nullptr, nullptr, FALSE,
                          0, nullptr, appDir.c_str(), &si, &pi)) {
        logStatus(data, L"CALLBACK SPAWN FAILED: packaged application was not started.");
        return 11;
      }
      CloseHandle(pi.hThread);
      CloseHandle(pi.hProcess);
      logStatus(data, L"CALLBACK INVOKED: OS launched portable handler; application acceptance not yet confirmed.");
      return 0;
    }

    if (!CreateProcessW(appExe.c_str(), mutableCmd.data(), nullptr, nullptr, FALSE,
                        CREATE_SUSPENDED, nullptr, appDir.c_str(), &si, &pi)) {
      notice(L"GitHub Desktop Portable", L"Failed to start the packaged GitHubDesktop.exe.");
      return 11;
    }
    HANDLE job = CreateJobObjectW(nullptr, nullptr);
    bool assigned = job && AssignProcessToJobObject(job, pi.hProcess);
    if (auth && auth->isActive() && !assigned) {
      // Cannot prove full descendant shutdown without our job. Fail closed
      // BEFORE the packaged application runs, then restore the auth handler.
      TerminateProcess(pi.hProcess, 16); // Own still-suspended process only.
      if (job) CloseHandle(job);
      CloseHandle(pi.hThread); CloseHandle(pi.hProcess);
      notice(L"GitHub Desktop Portable", L"Cannot track full GitHub Desktop process tree; sign-in session was not started.");
      return 16;
    }
    if (ResumeThread(pi.hThread) == static_cast<DWORD>(-1)) {
      TerminateProcess(pi.hProcess, 12); // Own still-suspended child only.
      if (job) CloseHandle(job);
      CloseHandle(pi.hThread); CloseHandle(pi.hProcess); return 12;
    }
    CloseHandle(pi.hThread);
    DWORD primaryWait = WaitForSingleObject(pi.hProcess, INFINITE);
    if (primaryWait != WAIT_OBJECT_0) {
      CloseHandle(pi.hProcess);
      if (job) CloseHandle(job);
      logStatus(data, L"PROCESS TRACKING FAILED: initial app process wait failed; recovery journal preserved.");
      if (auth) auth->abandonForRecovery();
      return 18;
    }
    DWORD exitCode = 1;
    GetExitCodeProcess(pi.hProcess, &exitCode);
    CloseHandle(pi.hProcess);

    // Windows job objects become signaled only in specific end-of-job-limit
    // scenarios. Waiting directly on a job handle can hang forever even with
    // ZERO child processes. Use QueryInformationJobObject ActiveProcesses.
    bool drained = true;
    if (assigned) drained = WaitForJobProcessesToExit(job);
    if (job) CloseHandle(job);
    if (!drained) {
      // Cannot safely establish complete shutdown. Leave the journal and
      // handler untouched rather than restoring while descendants may live.
      logStatus(data, L"PROCESS TRACKING FAILED: application child shutdown not confirmed; journal preserved.");
      notice(L"GitHub Desktop Portable - process tracking",
             L"Could not confirm full child-process shutdown. The authentication "
             L"recovery journal was retained. Close all portable GitHub Desktop "
             L"processes before relaunching; do not delete the journal.");
      // Guard destructor may restore: disarm below via explicit retain method.
      if (auth) auth->abandonForRecovery();
      return 18;
    }
    if (auth && auth->isActive()) {
      std::wstring outcome;
      if (!auth->restore(outcome)) {
        logStatus(data, L"HOST HANDLER PRESERVED: " + outcome);
        notice(L"GitHub Desktop Portable - handler restoration", outcome.c_str());
      } else {
        logStatus(data, L"CLEAN EXIT: previous browser sign-in handler safely restored.");
      }
    }
    return static_cast<int>(exitCode);
  } catch (const std::exception&) {
    notice(L"GitHub Desktop Portable", L"Startup or sign-in callback protection failed. Check Data folder permissions.");
    return 13;
  }
}

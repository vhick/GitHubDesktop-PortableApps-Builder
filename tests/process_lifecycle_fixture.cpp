// Windows hosted-runner fixture for real job process counting.
// Spawns ONLY its own test executable; does not touch GitHub Desktop,
// registry settings, profiles, services or unrelated processes.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <string>
#include <cwchar>
#include <iostream>
#include <stdexcept>
#include "ProcessLifecycle.h"

static void require(bool yes, const char* msg) {
  if (!yes) throw std::runtime_error(msg);
}
static std::wstring self() {
  wchar_t buffer[32768]{};
  const DWORD count = GetModuleFileNameW(nullptr, buffer, 32768);
  require(count && count < 32768, "test exe path not found");
  return std::wstring(buffer, count);
}
static PROCESS_INFORMATION spawn(const std::wstring& mode, bool suspended) {
  std::wstring full = self();
  std::wstring cmd = L"\"" + full + L"\" " + mode;
  std::wstring::value_type zero = L'\0';
  cmd.push_back(zero);
  STARTUPINFOW startup{}; startup.cb = sizeof(startup);
  PROCESS_INFORMATION process{};
  require(CreateProcessW(full.c_str(), cmd.data(), nullptr, nullptr, FALSE,
                         suspended ? CREATE_SUSPENDED : 0, nullptr, nullptr,
                         &startup, &process) != 0, "fixture CreateProcess failed");
  return process;
}
int wmain(int argc, wchar_t** argv) {
  try {
    if (argc == 2 && wcscmp(argv[1], L"--fixture-grandchild") == 0) {
      Sleep(1800);
      return 0;
    }
    if (argc == 2 && wcscmp(argv[1], L"--fixture-child") == 0) {
      PROCESS_INFORMATION p = spawn(L"--fixture-grandchild", false);
      CloseHandle(p.hThread);
      CloseHandle(p.hProcess);
      return 0;
    }
    require(argc == 1, "fixture has unexpected argument");
    HANDLE job = CreateJobObjectW(nullptr, nullptr);
    require(job != nullptr, "fixture job creation failed");
    PROCESS_INFORMATION p = spawn(L"--fixture-child", true);
    require(AssignProcessToJobObject(job, p.hProcess) != 0,
            "fixture cannot assign suspended child to job");
    require(ResumeThread(p.hThread) != static_cast<DWORD>(-1),
            "fixture cannot resume child");
    CloseHandle(p.hThread);
    require(WaitForSingleObject(p.hProcess, 10000) == WAIT_OBJECT_0,
            "fixture child did not exit");
    CloseHandle(p.hProcess);

    // A descendant remains active after its initial parent exits. The new
    // wait function must observe that descendant instead of restoring early.
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION counts{};
    require(QueryInformationJobObject(job, JobObjectBasicAccountingInformation,
                                      &counts, sizeof(counts), nullptr) != 0,
            "fixture job query failed");
    require(counts.ActiveProcesses >= 1,
            "fixture expected a running grandchild after initial child exited");
    require(WaitForJobProcessesToExit(job, 50, 10000),
            "fixture failed to detect entire process tree exiting");
    CloseHandle(job);
    std::cout << "PASS: original child exited, descendant tracked, job drained\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr << "FAIL: " << e.what() << "\n";
    return 1;
  }
}

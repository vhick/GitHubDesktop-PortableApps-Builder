#pragma once
// Wait for real Windows job accounting to reach zero after the app exits.
// A job handle is NOT a general-purpose event that signals when processes quit.
// This does not kill, suspend or modify any process.
#include <windows.h>

inline bool WaitForJobProcessesToExit(HANDLE job, DWORD intervalMs = 250,
                                     ULONGLONG maxWaitMs = 0) {
  if (!job || job == INVALID_HANDLE_VALUE) return false;
  const ULONGLONG start = GetTickCount64();
  for (;;) {
    JOBOBJECT_BASIC_ACCOUNTING_INFORMATION counts{};
    if (!QueryInformationJobObject(job, JobObjectBasicAccountingInformation,
                                  &counts, sizeof(counts), nullptr)) {
      return false;
    }
    if (counts.ActiveProcesses == 0) return true;
    if (maxWaitMs != 0 && GetTickCount64() - start >= maxWaitMs) return false;
    Sleep(intervalMs);
  }
}

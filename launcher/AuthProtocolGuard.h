#pragma once
// Windows per-user, opt-in, transaction-journaled browser sign-in callback handler.
// No elevation, HKLM edits, or arbitrary registry-tree removal.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <filesystem>
#include <string>

class AuthProtocolGuard {
public:
  AuthProtocolGuard(std::wstring scheme, std::filesystem::path journal,
                    std::wstring command);
  AuthProtocolGuard(const AuthProtocolGuard&) = delete;
  AuthProtocolGuard& operator=(const AuthProtocolGuard&) = delete;
  ~AuthProtocolGuard() noexcept;
  // Recovers a prior interrupted session. Returns false on conflict and preserves journal.
  bool recover(std::wstring& reason);
  // Requires explicit informed user consent and exclusive mutex held by caller.
  bool enable(std::wstring& reason);
  // Restores existing state only when our exact command is still registered.
  bool restore(std::wstring& reason);
  bool isActive() const noexcept { return active_; }
private:
  std::wstring scheme_;
  std::filesystem::path journal_;
  std::wstring command_;
  bool active_ = false;
};

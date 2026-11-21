#include "AuthProtocolGuard.h"
#include <shlobj.h>
#include <array>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <stdexcept>
#include <vector>

namespace {
constexpr wchar_t kPrefix[] = L"Software\\Classes\\";
constexpr wchar_t kUrlValue[] = L"URL Protocol";
constexpr wchar_t kCommandSubkey[] = L"\\shell\\open\\command";
constexpr uint32_t kMagic = 0x34484741; // 'AGH4' v4 journal, not an executable or token
constexpr size_t kMaxJournal = 1024 * 1024;
struct Value {
  bool present = false;
  DWORD type = REG_NONE;
  std::vector<BYTE> bytes;
};
struct Snapshot {
  std::array<bool, 4> existed{}; // root, shell, open, command
  Value url, prior;
  std::wstring ownedCommand;
};
void append(std::vector<BYTE>& v, uint32_t n) {
  for (int i = 0; i < 4; ++i) v.push_back(static_cast<BYTE>((n >> (i * 8)) & 255));
}
void pushBytes(std::vector<BYTE>& v, const BYTE* bytes, size_t count) {
  if (count > kMaxJournal) throw std::runtime_error("oversized journal entry");
  append(v, static_cast<uint32_t>(count));
  if (count != 0) v.insert(v.end(), bytes, bytes + count);
}
void pushValue(std::vector<BYTE>& v, const Value& x) {
  append(v, x.present ? 1u : 0u);
  append(v, x.type);
  pushBytes(v, x.bytes.data(), x.bytes.size());
}
uint32_t take32(const std::vector<BYTE>& v, size_t& at) {
  if (at + 4 > v.size()) throw std::runtime_error("truncated auth journal");
  uint32_t n = 0;
  for (int i = 0; i < 4; ++i) n |= static_cast<uint32_t>(v[at++]) << (i * 8);
  return n;
}
std::vector<BYTE> takeBytes(const std::vector<BYTE>& v, size_t& at) {
  uint32_t n = take32(v, at);
  if (n > kMaxJournal || n > v.size() - at) throw std::runtime_error("invalid auth journal length");
  auto begin = v.begin() + static_cast<std::ptrdiff_t>(at);
  std::vector<BYTE> ret(begin, begin + n); at += n;
  return ret;
}
Value takeValue(const std::vector<BYTE>& v, size_t& at) {
  Value x;
  const auto p = take32(v, at);
  if (p > 1) throw std::runtime_error("invalid auth journal bool");
  x.present = p == 1;
  x.type = take32(v, at);
  x.bytes = takeBytes(v, at);
  return x;
}
std::vector<BYTE> serialize(const Snapshot& s) {
  std::vector<BYTE> out;
  append(out, kMagic);
  for (bool b : s.existed) append(out, b ? 1u : 0u);
  pushValue(out, s.url);
  pushValue(out, s.prior);
  const BYTE* p = reinterpret_cast<const BYTE*>(s.ownedCommand.data());
  pushBytes(out, p, s.ownedCommand.size() * sizeof(wchar_t));
  if (out.size() > kMaxJournal) throw std::runtime_error("oversized auth journal");
  return out;
}
Snapshot deserialize(const std::vector<BYTE>& v) {
  size_t at = 0;
  if (take32(v, at) != kMagic) throw std::runtime_error("unknown auth journal format");
  Snapshot s;
  for (auto& b : s.existed) {
    const auto n = take32(v, at);
    if (n > 1) throw std::runtime_error("invalid auth journal flags");
    b = n == 1;
  }
  s.url = takeValue(v, at);
  s.prior = takeValue(v, at);
  auto raw = takeBytes(v, at);
  if (raw.size() % sizeof(wchar_t) != 0 || raw.empty() || at != v.size())
    throw std::runtime_error("invalid auth journal command");
  s.ownedCommand.resize(raw.size() / sizeof(wchar_t));
  std::memcpy(s.ownedCommand.data(), raw.data(), raw.size());
  if (s.ownedCommand.find(L"GitHubDesktopPortable.exe\" --protocol-launcher \"%1\"") == std::wstring::npos)
    throw std::runtime_error("auth journal does not identify our compiled launcher");
  return s;
}
struct Key {
  HKEY handle = nullptr;
  ~Key() { if (handle) RegCloseKey(handle); }
  Key(const Key&) = delete;
  Key& operator=(const Key&) = delete;
  Key() = default;
};
std::wstring rootFor(const std::wstring& scheme) { return std::wstring(kPrefix) + scheme; }
std::array<std::wstring, 4> pathsFor(const std::wstring& scheme) {
  const auto root = rootFor(scheme);
  return {root, root + L"\\shell", root + L"\\shell\\open", root + kCommandSubkey};
}
bool exists(const std::wstring& path) {
  Key key;
  auto rc = RegOpenKeyExW(HKEY_CURRENT_USER, path.c_str(), 0, KEY_READ, &key.handle);
  if (rc == ERROR_FILE_NOT_FOUND) return false;
  if (rc != ERROR_SUCCESS) throw std::runtime_error("cannot inspect registry key");
  return true;
}
void openKey(const std::wstring& path, REGSAM rights, Key& key, bool create) {
  LONG rc;
  if (create) rc = RegCreateKeyExW(HKEY_CURRENT_USER, path.c_str(), 0, nullptr,
                    REG_OPTION_NON_VOLATILE, rights, nullptr, &key.handle, nullptr);
  else rc = RegOpenKeyExW(HKEY_CURRENT_USER, path.c_str(), 0, rights, &key.handle);
  if (rc != ERROR_SUCCESS) throw std::runtime_error("cannot open per-user auth registry key");
}
Value readValue(HKEY key, const wchar_t* name) {
  Value x;
  DWORD size = 0;
  LONG rc = RegQueryValueExW(key, name, nullptr, &x.type, nullptr, &size);
  if (rc == ERROR_FILE_NOT_FOUND) return x;
  if (rc != ERROR_SUCCESS || size > kMaxJournal / 2) throw std::runtime_error("cannot inspect registry value");
  x.bytes.resize(size);
  rc = RegQueryValueExW(key, name, nullptr, &x.type, x.bytes.data(), &size);
  if (rc != ERROR_SUCCESS) throw std::runtime_error("cannot read registry value");
  x.bytes.resize(size); x.present = true;
  return x;
}
Value stringValue(const std::wstring& v) {
  Value x; x.present = true; x.type = REG_SZ;
  x.bytes.resize((v.size() + 1) * sizeof(wchar_t));
  std::memcpy(x.bytes.data(), v.c_str(), x.bytes.size());
  return x;
}
bool same(const Value& x, const Value& y) {
  return x.present == y.present && (!x.present || (x.type == y.type && x.bytes == y.bytes));
}
void writeValue(HKEY key, const wchar_t* name, const Value& val) {
  LONG rc = val.present
    ? RegSetValueExW(key, name, 0, val.type, val.bytes.data(), static_cast<DWORD>(val.bytes.size()))
    : RegDeleteValueW(key, name);
  if (!val.present && rc == ERROR_FILE_NOT_FOUND) return;
  if (rc != ERROR_SUCCESS) throw std::runtime_error("cannot update auth registry value");
}
bool emptyKey(const std::wstring& path) {
  Key key; openKey(path, KEY_READ, key, false);
  DWORD subkeys = 0, values = 0;
  if (RegQueryInfoKeyW(key.handle, nullptr, nullptr, nullptr, &subkeys, nullptr,
          nullptr, &values, nullptr, nullptr, nullptr, nullptr) != ERROR_SUCCESS)
    throw std::runtime_error("cannot inspect empty auth key");
  return subkeys == 0 && values == 0;
}
void saveJournal(const std::filesystem::path& file, const Snapshot& s) {
  if (std::filesystem::exists(file)) throw std::runtime_error("unresolved previous auth journal");
  auto bytes = serialize(s);
  auto tmp = file;
  tmp += L"." + std::to_wstring(GetCurrentProcessId()) + L".tmp";
  HANDLE h = CreateFileW(tmp.c_str(), GENERIC_WRITE, 0, nullptr, CREATE_NEW,
                         FILE_ATTRIBUTE_NORMAL | FILE_FLAG_WRITE_THROUGH, nullptr);
  if (h == INVALID_HANDLE_VALUE) throw std::runtime_error("cannot create auth recovery journal");
  DWORD wrote = 0;
  BOOL ok = WriteFile(h, bytes.data(), static_cast<DWORD>(bytes.size()), &wrote, nullptr);
  BOOL flushed = ok && wrote == bytes.size() && FlushFileBuffers(h);
  CloseHandle(h);
  if (!flushed) throw std::runtime_error("cannot durably write auth recovery journal");
  if (!MoveFileExW(tmp.c_str(), file.c_str(), MOVEFILE_WRITE_THROUGH))
    throw std::runtime_error("cannot commit auth recovery journal");
}
Snapshot loadJournal(const std::filesystem::path& file) {
  auto n = std::filesystem::file_size(file);
  if (!n || n > kMaxJournal) throw std::runtime_error("invalid auth journal size");
  std::ifstream f(file, std::ios::binary);
  if (!f) throw std::runtime_error("cannot read auth recovery journal");
  std::vector<BYTE> v(static_cast<size_t>(n));
  f.read(reinterpret_cast<char*>(v.data()), static_cast<std::streamsize>(n));
  if (!f) throw std::runtime_error("truncated auth recovery journal");
  return deserialize(v);
}
void checkUserChoice(const std::wstring& scheme) {
  auto path = L"Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\" + scheme + L"\\UserChoice";
  if (exists(path)) throw std::runtime_error("Windows UserChoice overrides the scheme; use Default Apps to change it; no registry override attempted");
}
}

AuthProtocolGuard::AuthProtocolGuard(std::wstring scheme, std::filesystem::path journal,
                                     std::wstring command)
  : scheme_(std::move(scheme)), journal_(std::move(journal)), command_(std::move(command)) {
  if (scheme_ != L"x-github-desktop-auth" &&
      scheme_ != L"x-github-desktop-dev-auth" &&
      scheme_.rfind(L"x-vhick-auth-guard-fixture-", 0) != 0)
    throw std::runtime_error("auth scheme not allowlisted");
  if (command_.find(L"GitHubDesktopPortable.exe\" --protocol-launcher \"%1\"") == std::wstring::npos)
    throw std::runtime_error("invalid portable launcher registry command");
}
AuthProtocolGuard::~AuthProtocolGuard() noexcept {
  if (active_) {
    try { std::wstring reason; (void)restore(reason); } catch (...) { /* journal remains */ }
  }
}
bool AuthProtocolGuard::recover(std::wstring& reason) { return restore(reason); }
bool AuthProtocolGuard::enable(std::wstring& reason) {
  try {
    if (std::filesystem::exists(journal_)) {
      if (!recover(reason)) return false;
    }
    checkUserChoice(scheme_);
    Snapshot s;
    s.ownedCommand = command_;
    const auto paths = pathsFor(scheme_);
    for (size_t i = 0; i < paths.size(); ++i) s.existed[i] = exists(paths[i]);
    if (s.existed[0]) {
      Key root; openKey(paths[0], KEY_QUERY_VALUE, root, false);
      s.url = readValue(root.handle, kUrlValue);
    }
    if (s.existed[3]) {
      Key commandKey; openKey(paths[3], KEY_QUERY_VALUE, commandKey, false);
      s.prior = readValue(commandKey.handle, nullptr);
    }
    // Persist full original bytes BEFORE changing anything in HKCU.
    saveJournal(journal_, s);
    {
      Key root; openKey(paths[0], KEY_READ | KEY_WRITE, root, true);
      writeValue(root.handle, kUrlValue, stringValue(L""));
      Key commandKey; openKey(paths[3], KEY_READ | KEY_WRITE, commandKey, true);
      writeValue(commandKey.handle, nullptr, stringValue(command_));
    }
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, nullptr, nullptr);
    active_ = true;
    reason = L"Temporary authentication callback registered for this session.";
    return true;
  } catch (const std::exception&) {
    reason = L"Could not safely register temporary auth callback. See Data\\TraceGuard recovery journal. Sign-in redirect is unavailable.";
    // A partially applied change has a durable journal; repair using the same strict ownership check.
    if (std::filesystem::exists(journal_)) {
      std::wstring repair; (void)restore(repair);
    }
    return false;
  }
}
bool AuthProtocolGuard::restore(std::wstring& reason) {
  if (!std::filesystem::exists(journal_)) { active_ = false; return true; }
  try {
    Snapshot s = loadJournal(journal_);
    const auto paths = pathsFor(scheme_);
    if (!exists(paths[3])) {
      // The original command is already gone; do not blindly recreate anything.
      if (s.prior.present) { reason = L"Auth registry command removed by another app; backup preserved for manual review."; return false; }
    } else {
      Key commandKey; openKey(paths[3], KEY_QUERY_VALUE | KEY_SET_VALUE, commandKey, false);
      const Value actual = readValue(commandKey.handle, nullptr);
      if (same(actual, stringValue(s.ownedCommand))) {
        writeValue(commandKey.handle, nullptr, s.prior);
      } else if (!same(actual, s.prior)) {
        reason = L"Auth handler changed during session. Preserved newer host setting and recovery journal; no destructive cleanup.";
        return false;
      }
    }
    if (exists(paths[0])) {
      Key root; openKey(paths[0], KEY_QUERY_VALUE | KEY_SET_VALUE, root, false);
      Value actual = readValue(root.handle, kUrlValue);
      if (same(actual, stringValue(L""))) writeValue(root.handle, kUrlValue, s.url);
      else if (!same(actual, s.url)) {
        reason = L"URL Protocol registration changed externally; original state retained in journal.";
        return false;
      }
    }
    // Remove only the keys created by us AND proven empty, deepest first.
    for (int i = 3; i >= 0; --i) {
      if (!s.existed[static_cast<size_t>(i)] && exists(paths[static_cast<size_t>(i)])) {
        if (!emptyKey(paths[static_cast<size_t>(i)]) ||
            RegDeleteKeyW(HKEY_CURRENT_USER, paths[static_cast<size_t>(i)].c_str()) != ERROR_SUCCESS) {
          reason = L"Auth registration has unexpected additions; retained it and the journal for review.";
          return false;
        }
      }
    }
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, nullptr, nullptr);
    std::filesystem::remove(journal_);
    active_ = false;
    reason = L"Previous per-user authentication handler restored safely.";
    return true;
  } catch (const std::exception&) {
    reason = L"Could not complete auth registry restoration. Recovery journal retained; installed app settings not force-overwritten.";
    return false;
  }
}

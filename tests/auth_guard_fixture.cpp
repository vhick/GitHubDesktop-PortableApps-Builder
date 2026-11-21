// Headless Windows registry fixture. Test scheme is unique and NOT used by GitHub.
// Does not install, launch or authenticate GitHub Desktop.
#define UNICODE
#define _UNICODE
#include <windows.h>
#include <filesystem>
#include <string>
#include <iostream>
#include <stdexcept>
#include "AuthProtocolGuard.h"
namespace fs=std::filesystem;
static std::wstring regRoot(const std::wstring& scheme) { return L"Software\\Classes\\" + scheme; }
static void must(bool yes, const char* message) { if (!yes) throw std::runtime_error(message); }
static std::wstring getCommand(const std::wstring& root) {
  HKEY h=nullptr;
  if (RegOpenKeyExW(HKEY_CURRENT_USER,(root+L"\\shell\\open\\command").c_str(),0, KEY_READ, &h)!=ERROR_SUCCESS) return L"";
  wchar_t result[4096]{};
  DWORD size=sizeof(result),type=0;
  LONG rc=RegQueryValueExW(h,nullptr,nullptr,&type,(BYTE*)result,&size);
  RegCloseKey(h);
  return rc==ERROR_SUCCESS && type==REG_SZ ? std::wstring(result) : L"";
}
static bool exists(const std::wstring& root) {
  HKEY h=nullptr;
  LONG rc=RegOpenKeyExW(HKEY_CURRENT_USER,root.c_str(),0, KEY_READ,&h);
  if(rc==ERROR_SUCCESS) { RegCloseKey(h); return true; }
  return false;
}
static void setCommand(const std::wstring& root,const std::wstring& value) {
  HKEY h=nullptr;
  must(RegCreateKeyExW(HKEY_CURRENT_USER,(root+L"\\shell\\open\\command").c_str(),0,nullptr,0,KEY_WRITE,nullptr,&h,nullptr)==ERROR_SUCCESS,"create fixture");
  const auto rc=RegSetValueExW(h,nullptr,0,REG_SZ,(const BYTE*)value.c_str(),static_cast<DWORD>((value.size()+1)*sizeof(wchar_t)));
  RegCloseKey(h);must(rc==ERROR_SUCCESS,"write fixture");
}
int wmain() {
  const auto scheme=L"x-vhick-auth-guard-fixture-"+std::to_wstring(GetCurrentProcessId());
  const auto root=regRoot(scheme);
  const auto temp=fs::temp_directory_path() / (L"ghdp-auth-fixture-"+std::to_wstring(GetCurrentProcessId()));
  const auto journal=temp/L"journal.bin";
  const auto owner=L"\"C:\\Portable Apps\\GitHubDesktopPortable.exe\" --protocol-launcher \"%1\"";
  try {
    must(!exists(root),"fixture root already existed");
    fs::create_directories(temp);
    {
      AuthProtocolGuard guard(scheme,journal,owner);
      std::wstring reason;
      must(guard.enable(reason),"new protocol registration failed");
      must(getCommand(root)==owner,"new protocol not owned");
      must(guard.restore(reason),"new protocol restoration failed");
      must(!exists(root),"new protocol not fully removed");
      must(!fs::exists(journal),"journal not removed");
    }
    // Existing installed-app handler must be preserved byte-for-byte.
    const std::wstring original=L"\"C:\\Installed App\\GitHubDesktop.exe\" --protocol-launcher \"%1\"";
    setCommand(root,original);
    {
      AuthProtocolGuard guard(scheme,journal,owner);
      std::wstring reason;
      must(guard.enable(reason),"existing handler temporary override failed");
      must(getCommand(root)==owner,"new callback not visible");
      must(guard.restore(reason),"existing handler restore failed");
      must(getCommand(root)==original,"pre-existing handler was not restored");
      must(!fs::exists(journal),"old-handler journal retained unexpectedly");
    }
    {
      AuthProtocolGuard guard(scheme,journal,owner);
      std::wstring reason;
      must(guard.enable(reason),"conflict scenario registration failed");
      const std::wstring concurrent=L"\"C:\\Another App\\Other.exe\" \"%1\"";
      setCommand(root,concurrent);
      must(!guard.restore(reason),"changed handler was overwritten");
      must(getCommand(root)==concurrent,"external handler was not protected");
      must(fs::exists(journal),"conflict journal missing");
      // Simulate external app voluntarily restoring previous command, then recover.
      setCommand(root,original);
      must(guard.recover(reason),"journal recovery after conflict failed");
      must(getCommand(root)==original,"recovery changed preexisting command");
      must(!fs::exists(journal),"resolved journal remained");
    }
    // Fixture root is unique to this process; no actual installed-app entry is removed.
    must(RegDeleteTreeW(HKEY_CURRENT_USER,root.c_str())==ERROR_SUCCESS,"fixture cleanup failed");
    fs::remove_all(temp);
    std::cout<<"PASS: Windows HKCU fixture new/existing/conflicting protocol, recovery and restore\n";
    return 0;
  } catch (const std::exception& e) {
    std::cerr<<"FAIL: "<<e.what()<<" (fixture preserved for review)\n";
    return 1;
  }
}

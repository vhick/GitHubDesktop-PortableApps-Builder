# Build-stage verification matrix — status at kit authoring

| Stage | Status | Actual evidence available |
| --- | --- | --- |
| Mode selection and upstream 3.6.10 source architecture | SOURCE-INSPECTED | GitHub source and official release documentation |
| Source paths for Electron userData/logs and protocol registration | SOURCE-INSPECTED | `main.ts`, `get-log-path.ts`, `notifications.ts` |
| Shared Package Builder v1.0.0 interface and behavior | SOURCE-INSPECTED | Exact tag `action.yml`, `build.ps1`, `common.ps1`, NSIS source |
| Shared Publisher v1.1.1 interface and release collision protection | SOURCE-INSPECTED | Exact `action.yml`, `publish.py` and release page |
| Offline Python source patch, workflow string and ZIP-negative tests | STATIC-VALIDATED if local unit suite succeeds | `python -m unittest discover -s tests -v` output |
| GitHub-hosted Windows source compilation and native dependency installation | NOT YET VERIFIED | Requires actual GitHub Actions run |
| Actual Win64 C++ root launcher compilation | NOT YET VERIFIED | Requires Windows MSVC runner |
| Actual GitHub Desktop app launched from root launcher | NOT YET VERIFIED | Requires interactive Windows GUI test |
| Electron profile, Chromium and Git global data containment | NOT YET VERIFIED | Requires runtime file-system monitoring |
| Host credential-store isolation / authentication persistence | NOT YET VERIFIED; known risk | keytar/GCM behavior may be host-bound |
| TraceGuard foreign host-data recovery | NOT IMPLEMENTED / NOT CLAIMED | Early profile redirection used; no host-scavenging logic |
| ShellGuard protocol cleanup | NOT REQUIRED FOR SUPPRESSED SOURCE PATH; broader runtime unverified | Automatic protocol registration prevented in source; no generalized cleanup |
| Notification and browser sign-in success | NOT YET VERIFIED; potential failures | Manual GUI/OS integration testing required |
| Independently validated ready-to-extract PortableApps ZIP | NOT YET VERIFIED | Build script contains tests; no large Windows app bytes created here |
| Shared custom-NSIS installer generation | NOT YET VERIFIED | GitHub Actions must run |
| Installer file PE/embedded integrity | NOT YET VERIFIED | independent checker included, but no compiled installer available |
| Interactive installer upgrade, rollback, relocation | NOT YET VERIFIED | Manual Windows checklist |
| Publisher dry run and final release publication | NOT YET VERIFIED | Workflow invokes pinned publisher; no GitHub Release created |

The kit ZIP itself is a *source builder kit*, not a compiled PortableApps application. Static tests do not prove Windows runtime safety, and an Actions build success will still not prove GUI/OS integration.

## Potential failure causes worth investigating first

- Version drift: current fail-closed adapter accepts only exact 3.6.10; newer stable tags are intentionally not compiled until source review.
- Upstream Node/Electron native modules, Git submodule downloads, bundled Git and package-manager postinstall may be sensitive to CI toolchain changes.
- OAuth browser callback may be unavailable because Windows protocol registration is suppressed to protect the installed GitHub Desktop.
- Windows credential vault and Git Credential Manager may leave host-bound state despite portable profile paths.
- Native notifications depend on Windows shortcut/CLSID infrastructure and are not fully resolved by `app.setAppUserModelId` alone.
- Squirrel update paths are disabled; upgrades are handled by replacement of package-managed files only.

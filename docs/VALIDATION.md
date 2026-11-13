# Build-stage verification matrix — status at kit authoring

| Stage | Status | Actual evidence available |
| --- | --- | --- |
| Mode selection and upstream 3.6.10 source architecture | SOURCE-INSPECTED | GitHub source and official release documentation |
| Source paths for Electron userData/logs and protocol registration | SOURCE-INSPECTED | `main.ts`, `get-log-path.ts`, `notifications.ts` |
| Shared Package Builder v1.0.0 interface and behavior | SOURCE-INSPECTED | Exact tag `action.yml`, `build.ps1`, `common.ps1`, NSIS source |
| Shared Publisher v1.1.1 interface and release collision protection | SOURCE-INSPECTED | Exact `action.yml`, `publish.py` and release page |
| Offline Python source patch, workflow string and ZIP-negative tests | STATIC-VALIDATED if local unit suite succeeds | `python -m unittest discover -s tests -v` output |
| GitHub-hosted Windows source compilation and native dependency installation | WINDOWS-COMPILED (b1r2 user-run) | Logs `logs_117102594875.zip`: successful Yarn install and Electron packager output |
| Actual Win64 C++ root launcher compilation | FAILED/BLOCKED (b1r2); USER-CONFIRMED (b1r3 base launcher); NOT YET VERIFIED (b1r4 new launcher) | b1r2 logs show CMD quoting error; b1r3 uses Developer PowerShell but has not been built yet |
| Actual GitHub Desktop app launched from root launcher | NOT YET VERIFIED | Requires interactive Windows GUI test |
| Electron profile, Chromium and Git global data containment | NOT YET VERIFIED | Requires runtime file-system monitoring |
| Host credential-store isolation / authentication persistence | NOT YET VERIFIED; known risk | keytar/GCM behavior may be host-bound |
| TraceGuard foreign host-data recovery | NOT IMPLEMENTED / NOT CLAIMED | Early profile redirection used; no host-scavenging logic |
| ShellGuard protocol cleanup | STATIC-VALIDATED (b1r4); WINDOWS-RUNTIME NOT YET VERIFIED | Opt-in, per-user auth scheme journal/conditional restoration; broad automatic source registrations still disabled |
| Notification and browser sign-in success | NOT YET VERIFIED; potential failures | Manual GUI/OS integration testing required |
| Independently validated ready-to-extract PortableApps ZIP | NOT YET VERIFIED | Build script contains tests; no large Windows app bytes created here |
| Shared custom-NSIS installer generation | NOT YET VERIFIED | GitHub Actions must run |
| Installer file PE/embedded integrity | NOT YET VERIFIED | independent checker included, but no compiled installer available |
| Interactive installer upgrade, rollback, relocation | NOT YET VERIFIED | Manual Windows checklist |
| Publisher dry run and final release publication | NOT YET VERIFIED | Workflow invokes pinned publisher; no GitHub Release created |

## Observed failed b1r1 build and b1r2 remedy

- **FAILED/BLOCKED (b1r1 user-run, 2026-11-12):** `yarn install` postinstall TypeScript TS7016 cannot find `glob` declarations, plus TS7006 in callback parameters. No GitHub Desktop EXE/ZIP/installer was produced.
- **SOURCE-INSPECTED:** Upstream 3.6.10 root `package.json` declares `@types/glob` in `devDependencies`, used by `script/post-install.ts`.
- **SOURCE-INSPECTED:** Yarn Classic ignores `devDependencies` when `NODE_ENV=production` unless overridden.
- **STATIC-VALIDATED (b1r2 only):** Dependency install now uses development env plus `--production=false` before switching to production build; regression tests enforce this order.
- **WINDOWS-COMPILED (b1r2 user-run):** Upstream GitHub Desktop source build generated `work/source/dist/GitHubDesktop-win32-x64` with exit code 0. This does not demonstrate launch or portability.
- **FAILED/BLOCKED (b1r2 user-run):** Separate C++ launcher compilation failed before `cl.exe` due to nested CMD quoting and Visual Studio paths with spaces.
- **STATIC-VALIDATED (b1r3):** Launcher compilation now calls supported Visual Studio Developer PowerShell and MSVC directly without temporary batch/cmd quoting; regression tests assert this design.
- **USER-CONFIRMED (b1r3 base launcher); NOT YET VERIFIED (b1r4 new launcher):** Real MSVC launcher output, PortableApps ZIP and installer, interactive runtime.

The kit ZIP itself is a *source builder kit*, not a compiled PortableApps application. Static tests do not prove Windows runtime safety, and an Actions build success will still not prove GUI/OS integration.

## Potential failure causes worth investigating first

- Version drift: current fail-closed adapter accepts only exact 3.6.10; newer stable tags are intentionally not compiled until source review.
- Upstream Node/Electron native modules, Git submodule downloads, bundled Git and package-manager postinstall may be sensitive to CI toolchain changes.
- b1r3 OAuth browser callback **FAILED IN USER TEST**: missing `x-github-desktop-auth` registration. b1r4 adds opt-in session-scoped registration and crash-safe conditional restoration, but has not yet been Windows-tested.
- Windows credential vault and Git Credential Manager may leave host-bound state despite portable profile paths.
- Native notifications depend on Windows shortcut/CLSID infrastructure and are not fully resolved by `app.setAppUserModelId` alone.
- Squirrel update paths are disabled; upgrades are handled by replacement of package-managed files only.

- **STATIC-VALIDATED (b1r4):** 16 offline Python regression tests, package scripts and opt-in registry guard assertions.
- **NOT YET VERIFIED (b1r4):** Actual new Win64 launcher build, isolated Windows HKCU fixture, real browser authentication, multiple-instance and crash recovery, portable ZIP/installer and publisher.
- **USER-CONFIRMED (b1r3):** Existing GitHub Desktop GUI launched successfully, but browser authentication failed as shown in screenshots.

## b1r4 user-reported defects, b1r5 correction

- **USER-OBSERVED (b1r4):** GUI closes but `GitHubDesktopPortable.exe` remains running; OAuth browser screen does not return a signed-in app.
- **FILE-INSPECTED:** user-provided consent contains `enabled`; TraceGuard status says a second portable launcher could not own the authentication mutex; the AGH4 journal is parseable and reports no pre-existing HKCU auth key. Current registry state is unknown.
- **SOURCE-INSPECTED:** b1r4's normal and callback paths wait indefinitely on the job handle, but Windows job objects do not signal on ordinary active-process-zero. b1r5 replaces this with supported job-accounting API and makes callback-only launch one-shot. Duplicate ordinary launches fail closed.
- **STATIC-VALIDATED (b1r5):** `python -m unittest discover -s tests -v` verifies source invariants and new Windows fixture wiring. This does not execute Win32 code on Linux.
- **NOT YET VERIFIED (b1r5):** real Windows compilation, isolated child/grandchild job fixture, full callback delivery to Electron, browser OAuth, credential persistence, installer upgrades and publisher.

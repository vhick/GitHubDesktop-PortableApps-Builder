# GitHub Desktop PortableApps Builder Kit b1r3 — 2026-11-12

## Observed Windows build failure

Input: `logs_117102594875.zip` (b1r2 GitHub Actions user-run).

- **WINDOWS-COMPILED:** `Build actual modified GitHub Desktop application from source` finished successfully. The log states `Packaging app for platform win32 x64 using electron v44.9.1`, `Built to .../dist/GitHubDesktop-win32-x64` and `Done in 128.21s`.
- **FAILED/BLOCKED:** Step 11 `Compile real C++17 Win64 root launcher` failed:
  - `'"' is not recognized as an internal or external command`
  - `'C:\Program' is not recognized as an internal or external command`
  - `'" >nul' is not recognized as an internal or external command`
  - `scripts/compile_launcher.ps1:21` → `MSVC launcher compilation failed: 1`.
- **NOT FATAL:** Webpack reported `Error parsing bundle asset ...174.js: Cannot use 'import.meta' outside a module`, but it still compiled with warnings and the application packaging step completed. No change is made to suppress this warning.

## Actual cause

b1r2 generated a temporary `.cmd` and then asked PowerShell to run `cmd.exe /D /C` with nested double quotes. The nested parser broke arguments containing spaces before `cl.exe` could start. This is entirely a kit orchestration bug, not an upstream compilation or missing-dependency error.

## Changes

1. **`scripts/compile_launcher.ps1`:** Find the installed x64 Visual C++ workload using Microsoft's `vswhere`, call Visual Studio's documented `Launch-VsDevShell.ps1` directly, verify `VSCMD_VER` and `cl.exe`, then invoke `cl.exe` from PowerShell with correctly separated native arguments. No `cmd.exe`, temporary batch, lossy ASCII path conversion, or shell quoting layer remains.
2. **Output verification:** Check compiler exit code, resulting EXE presence and x64 PE signature/machine before allowing the build to progress.
3. **`.github/workflows/build-portableapps.yml`:** Default `package_revision` updated to `r3`.
4. **`tests/test_kit.py`:** Regression tests prohibit nested CMD launcher compilation and check direct MSVC, architecture and output validation.
5. **`README.md`, `docs/VALIDATION.md`:** Record the actually completed upstream Windows build and remaining unverified stages.

## Evidence and next steps

- Source-built Electron application: **WINDOWS-COMPILED in user's b1r2 log**.
- b1r3 scripts: **STATIC-VALIDATED after local test execution**.
- b1r3 Win64 launcher: **NOT YET VERIFIED**.
- PortableApps ZIP, installer, publication, authentication and notifications: **NOT YET VERIFIED**.

Overwrite the independent builder repo with b1r3, commit and push, and rerun `Build GitHub Desktop PortableApps (source-built x64)` with `upstream_version=latest`, `package_revision=r3` and `publish=true`.

Microsoft developer shell documentation: https://learn.microsoft.com/en-us/visualstudio/ide/reference/command-prompt-powershell?view=visualstudio

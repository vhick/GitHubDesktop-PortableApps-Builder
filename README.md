# GitHub Desktop PortableApps Builder Kit — b1r1 (experimental)

**Selected mode:** PORTABLEAPPS only. **Target architecture:** Windows x64.

This independent repository builds **GitHub Desktop from the exact stable upstream tag** (currently source-audited `release-3.6.10`), adds an early in-process Electron profile redirection, compiles a genuine Win64 root launcher, stages a PortableApps-compatible package, independently validates a ZIP, invokes the pinned shared custom-NSIS installer action, then publishes using the pinned Universal Release Publisher.

This kit is **not** an official GitHub Desktop portable distribution. No packaged Windows executable, Windows GUI test, or published release was produced during authoring of this kit. It has **not yet been proven fully portable**. It is intentionally conservative about credentials, authentication protocol handling, and notifications; see `docs/PORTABILITY-AUDIT.md` and `docs/VALIDATION.md` before relying on it.

## Quick start with GitHub Desktop (no local compiler required)

1. On github.com, create an **empty, separate** repository, e.g. `GitHubDesktop-PortableApps-Builder`. Do not fork `desktop/desktop`. Choose public or private. Do not generate a README from GitHub's creation screen.
2. In GitHub Desktop, select **File → Clone Repository → URL**, then paste your empty repository URL; choose a local folder.
3. Extract this kit ZIP **into that repository's root**. Ensure `.github/workflows/build-portableapps.yml` exists; on Windows, hidden dot folders may not be visible unless hidden files are shown.
4. In GitHub Desktop, verify all added files, enter a commit message, choose **Commit to main**, and **Push origin**. No `git init` and no local compiler are required.
5. In the browser, open the new repository → **Actions** → **Build GitHub Desktop PortableApps (source-built x64)** → **Run workflow**.
6. Leave `upstream_version=latest` and `package_revision=r1`. Keep `publish=true` to create a downloadable release after both ZIP and installer checks. The workflow is manual by default and may consume substantial Windows Actions minutes.
7. Inspect the Actions job logs. It downloads source/submodules and compiles the real Electron Windows app; successful compilation alone does **not** mean portability is verified.
8. Once the workflow **succeeds**, open the repository's **Releases** page. Download the `GitHubDesktopPortable_..._x64_r1.zip` and its `.paf.exe` installer. The publisher creates `SHA256SUMS.txt` containing the actual SHA-256 for both assets.
9. Extract the ZIP to a regular folder or USB drive, or run the independent PortableApps-style installer. In the PortableApps Platform, refresh the app menu. Start `GitHubDesktopPortable.exe` **in the package root**.
10. Your retained profile and Git global config are under `GitHubDesktopPortable/Data/`. To upgrade, close GitHub Desktop, **back up Data**, replace `App/`, `Other/` and the root launcher while preserving `Data/` unchanged; or select the **same existing portable folder** in the installer. Never merge installed `%APPDATA%` profiles automatically.
11. Rollback: fully exit the app, back up `Data`, restore old `App`, `Other`, and launcher together. A newer profile/database schema may not work with an older app; never discard the newer Data backup.

## What it does

- Source: a GitHub release tag matching numeric stable `X.Y.Z` only, followed by a `git fetch` of the **exact ref** and recording its full commit SHA and `yarn.lock` SHA-256.
- Source adapter: `scripts/patch_source.py` rejects any release except the currently audited `3.6.10`, and rejects missing/duplicated anchors. This is deliberate; no silent compiling of unreviewed future releases.
- Profile: `patches/portable-bootstrap.ts`, imported before normal main-process imports, sets Electron `userData`, `sessionData`, logs and portable AUMID inside `Data/Profile` **before app startup**.
- Git: the compiled launcher passes process-local `HOME`, `GIT_CONFIG_GLOBAL`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` under `Data/GitHome` to GitHub Desktop and its descendants, without changing Windows system variables.
- Shell: the patch prevents automatic URL protocol registration in the portable version; it does **not** modify installed app shortcuts, registry keys, PATH, or the default URL handler.
- Updates: the Squirrel updater is disabled in portable mode, because it assumes a normal installed app and could overwrite that installation.
- Notifications: a separate portable CLSID is chosen to avoid reusing the installed app's Squirrel toast CLSID. Native toast activation still requires separate Windows integration, and click-to-open is not verified.
- Launcher: MSVC C++17 Win64 PE launches the packaged `GitHubDesktop.exe` with argument forwarding, waits for the application, and attempts to wait for descendants. No remote control, process injection, broad cleanup, or automatic elevation.
- Stage: original upstream icon is copied from verified source; 16/32 pixel PNGs are derived from it. Installer identity is independent of official GitHub Desktop and official PortableApps distribution.
- ZIP: verified with Python `zipfile.testzip()`, PE header/architecture, required resources, PortableApps metadata, and safe entry names.
- Installer: generated only by the pinned `vhick/Portable-Package-Builder@v1.0.0` **custom-nsis** composite action, pinned in workflow to verified immutable commit SHA.
- Publisher: only `vhick/portable-release-publisher@v1.1.1`, pinned to immutable SHA, with dry-run before real publication; default pruning OFF.

## Major known constraints — READ BEFORE USE

1. **GitHub account sign-in may fail.** The upstream browser OAuth callback uses Windows protocol handlers; this kit does not silently replace the installed app's handlers. Browser callback/credentials and enterprise sign-in remain **NOT YET VERIFIED**. Do not use this package as your sole Git client until those tests pass.
2. **Credential data may remain on the host.** `keytar` / Windows Credential Manager, Git Credential Manager, Windows DPAPI, SSH-agent, Git/SSH credentials, external tools, Git hooks and downloaded repository paths are not proven entirely contained under `Data`. Sign-in on a different computer may require reauthentication. No unsafe plaintext-token migration is included.
3. **Notifications are not proven fully working.** Windows toast activation/click callbacks typically require OS registration. This package avoids borrowing the installed application's identity, but cannot claim full notification activation portability without an opt-in Windows integration and manual test.
4. **Do not assume no Windows traces.** Windows shell caches, Recent Items, Jump Lists, file dialogs, Prefetch, notifications, OS credential storage, and external apps may create user-managed or OS-managed state. No broad deletion of those areas is attempted.
5. **Source compilation is heavy.** Upstream uses Node/Electron, native modules and vendored Yarn. The kit does not download or ship a precompiled Windows GitHub Desktop binary.
6. **Unverified newer release:** `latest` means the newest stable release **at or below the currently audited adapter version**. 3.6.11+ requires an explicit source audit and adapter update before shipping.
7. **Signing and branding:** This unofficial rebuilt executable is **unsigned by GitHub, Inc.** The launcher and installer are community binaries. Antivirus warnings are possible. The source icon is used with original attribution; do not claim GitHub endorsement.

## Packaging-only retry without recompilation

If a source-built ZIP was already published but its installer failed, open **Actions → Repackage validated GitHub Desktop ZIP (installer only)**. Enter the exact existing builder-repository release tag (`...-ziponly` if the installer failed), the exact ZIP filename, and `installer_revision=r1`. The workflow downloads `SHA256SUMS.txt` and that ZIP from **this same builder repository**, checks the exact SHA-256, extracts the validated contents, invokes the shared custom-NSIS installer action, and publishes an independent `-installer-r1` release. It never recompiles GitHub Desktop or downloads an unverified external package.

## Workflows, filenames and dependencies

- `.github/workflows/build-portableapps.yml`: one hosted Windows 2022 source-build job with a manual dispatcher; `.github/workflows/repackage-only.yml` is the packaging-only retry path. No paid runner, PAT, local compiler, or committed generated binaries.
- `scripts/resolve_release.py`: GitHub REST API stable resolver, correct numeric version sorting and explicit 404 handling.
- `scripts/get_source.ps1`: pinned upstream Git source checkout and lockfile provenance record.
- `scripts/patch_source.py`, `patches/portable-bootstrap.ts`: fail-closed source modification and audit manifest.
- `scripts/build_source.ps1`: upstream vendored Yarn `install --frozen-lockfile`, then `build:prod` with community signing disabled.
- `scripts/compile_launcher.ps1`, `launcher/GitHubDesktopPortable.cpp`: actual C++17 compiler blueprint for root PE.
- `scripts/stage.py`: source-built application, icon, data layout, PortableApps metadata, ZIP verification and SHA256 build manifest.
- `scripts/validate_installer.ps1`: independently check installer PE/archive/hash after the shared builder.
- `tests/test_kit.py`: controlled fail-closed source/ZIP tests. These are **static test fixtures, not interactive GUI tests**.

## If the workflow fails

- **Source version rejected:** explicit version 3.6.10 remains supported; future versions need review, not an automatic search-and-replace.
- **Yarn install / native dependency fails:** inspect the failing module and Node toolchain in Actions logs. Preserve full error text, do not skip errors or disable integrity verification.
- **Compilation fails:** check script build/webpack errors and `work/source/.node-version`. Never substitute a mock binary.
- **Installer failure:** ZIP verification may still have succeeded. With `publish=true`, the ZIP is published in a separately labeled `-ziponly` release and the job still fails; `.paf.exe` must not be advertised as successful.
- **GUI/profile issues:** run the acceptance checklist in `docs/WINDOWS-ACCEPTANCE.md` before using this on valuable repositories.

## External primary sources

- Upstream: https://github.com/desktop/desktop and https://github.com/desktop/desktop/releases
- Source paths and Windows data: https://github.com/desktop/desktop/blob/development/docs/installation.md
- PortableApps format: https://portableapps.com/development/portableapps.com_format
- Shared package builder v1.0.0: https://github.com/vhick/Portable-Package-Builder/releases/tag/v1.0.0
- Shared release publisher v1.1.1: https://github.com/vhick/portable-release-publisher/releases/tag/v1.1.1

### License

Builder source is MIT-licensed. GitHub Desktop's upstream source declares MIT, while bundled dependencies/assets can have separate notices. Actual upstream source license is copied into the generated package; inspect dependency licenses and trademark/branding policy before redistribution. This is independent community packaging.

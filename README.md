# GitHub Desktop PortableApps Builder Kit — b1r5 (experimental)

**Selected mode:** PORTABLEAPPS only. **Target architecture:** Windows x64.

This independent repository builds **GitHub Desktop from the exact stable upstream tag** (currently source-audited `release-3.6.10`), adds an early in-process Electron profile redirection, compiles a genuine Win64 root launcher, stages a PortableApps-compatible package, independently validates a ZIP, invokes the pinned shared custom-NSIS installer action, then publishes using the pinned Universal Release Publisher.

This kit is **not** an official GitHub Desktop portable distribution. No packaged Windows executable, Windows GUI test, or published release was produced during authoring of this kit. It has **not yet been proven fully portable**. It is intentionally conservative about credentials, authentication protocol handling, and notifications; see `docs/PORTABILITY-AUDIT.md` and `docs/VALIDATION.md` before relying on it.

## b1r5 correction — browser callback and launcher shutdown (2026-11-13)

**Actual user evidence:** b1r4 launches GitHub Desktop's GUI, but the browser authorization never returns successfully. Task Manager shows `GitHubDesktopPortable.exe` still alive after the GUI closes. The provided `Data/AuthRedirectConsent.txt` contains `enabled`; the TraceGuard status says a second launcher found the authentication mutex already owned. The supplied recovery journal was successfully parsed, showing no prior per-user auth protocol key existed. This does **not** prove what Windows currently has registered.

**Identified code bug:** b1r4 uses `WaitForSingleObject(job, INFINITE)` after the app's process exits. A Windows Job Object is **not** ordinarily signaled merely because its active process count reaches zero. That design can leave a launcher process stuck indefinitely and the temporary callback handler unrecovered. Callback-only launches have the same job wait and can also remain stuck. See Microsoft's Job Objects documentation.

**b1r5 fix:** The **main** launcher now waits for `GitHubDesktop.exe`, then queries Job Object **ActiveProcesses** until the tracked tree empties. Callback-only launches start the same packaged application with their quoted `--protocol-launcher` URL, close handles, and exit promptly without taking the registry mutex. Concurrent **ordinary** launches that cannot acquire the session mutex now stop rather than silently starting an untracked instance. No forced termination is used. If process tracking fails, the guard preserves its recovery journal rather than restoring an uncertain state. An isolated C++ Windows job fixture runs in CI, and token-free status messages identify which stage the callback reached.

**Important upgrade from a stranded b1r4 launcher:** Close the GUI, confirm any remaining `GitHubDesktopPortable.exe` belongs to **this portable folder**, and end only that stranded launcher in Task Manager. **Back up the entire Data directory and do not delete `Data/TraceGuard/AuthProtocolRecovery.bin`.** Replace `App/`, `Other/` and the root launcher from the new r5 package, keeping Data untouched. On first new launch the journal is evaluated, and the prior handler restored only where ownership can be established; then the new session can register its own temporary callback using existing consent. If registry ownership differs, the launcher must leave the conflict and journal for manual review. The sign-in result still needs Windows GUI testing.

**Diagnostic after sign-in attempt:** Open `Data/TraceGuard/AuthProtocolStatus.txt`. `AUTH HANDLER ACTIVE` confirms our registration step succeeded, `CALLBACK INVOKED` means Windows launched our handler (not proof GitHub Desktop accepted it), `CALLBACK SPAWN FAILED` means its child process could not start, and `CLEAN EXIT` means prior handler restoration completed. Do not share OAuth links, codes, tokens, or unredacted app logs. Read `docs/RELEASE-NOTES-b1r5.md` for detailed evidence and acceptance steps.

**Validation:** local tests and kit structure only at authoring time; the new b1r5 Windows PE, job fixture, login flow and installer upgrade are NOT YET VERIFIED. The shared pinned actions and version-limited upstream adapter remain unchanged.

## b1r4 browser sign-in callback fix (2026-11-13)

**Problem reproduced by user:** The b1r3 program launches and opens the browser, but after GitHub authorization the browser never returns to the portable application. The b1r3 source patch explicitly stopped registering all Windows schemes. GitHub Desktop 3.6.10 uses `x-github-desktop-auth://` for OAuth callbacks; without an active Windows handler, authentication cannot finish.

**Fix:** The real root C++ launcher now prompts on first normal launch for permission to manage **one** user-level URL scheme for the session: `HKCU\Software\Classes\x-github-desktop-auth`. The YES choice is recorded as `Data/AuthRedirectConsent.txt` and used on subsequent starts; NO is also remembered. A separate **Other/Source/Configure-Browser-SignIn.cmd** can be used later to change that preference through the compiled launcher, without modifying or executing any arbitrary registry script.

With consent, the launcher preserves the original handler command and `URL Protocol` value (including exact value types/bytes and whether the corresponding keys existed) in a durable `Data/TraceGuard/AuthProtocolRecovery.bin` **before changing the registry**. It points callbacks at the real root `GitHubDesktopPortable.exe --protocol-launcher "%1"`, which forwards them to the packaged application with the portable environment. The source-built application still suppresses broad automatic registration of `x-github-client`, `github-windows` and unrelated schemes.

After complete application/child-process shutdown, the launcher restores the saved handler **only if its own exact command is still the registered command**. It avoids overwriting any registry value another program has changed, removes only newly created empty keys, and retains a recovery journal for a conflicted/interrupted operation. The next launch retries idempotent recovery; a registry conflict blocks a new override. A process mutex prevents two portable copies from registering the callback at the same time. The callback subprocess never modifies the registry or asks again.

**Limitations:** The installed GitHub Desktop will not receive that scheme's sign-in callbacks while the portable session owns it. Running installed/portable concurrently is not advised. Windows UserChoice overrides, mismatched elevation, browser prompts or external handlers may still prevent sign-in; the fix does not guarantee success without real GUI testing. GitHub credential storage and notifications remain separately unverified. No permanent association, elevation, HKLM edit, shell shortcut cleanup or broad registry sweep is used.

**Validation:** 16 local Python static/regression tests pass. b1r4's C++ compile and isolated Windows registry fixture are configured in CI but have NOT run in this environment. Do not call this a runtime-confirmed sign-in fix until the user completes the Windows flow.

## b1r3 correction (2026-11-12)

The user's b1r2 GitHub Actions logs showed a **successful complete GitHub Desktop 3.6.10 Electron source build** and a failure in the **separate C++ launcher compilation** step. `compile_launcher.ps1` created a transient batch file, then launched it with nested PowerShell/CMD quoting. Windows CMD split the Visual Studio path containing spaces and failed before invoking `cl.exe`.

b1r3 replaces the brittle batch file with Microsoft's documented Visual Studio `Launch-VsDevShell.ps1` in the current PowerShell process, then invokes `cl.exe` directly using argument-array boundaries and checks the resulting x64 PE. The change is confined to the launcher compiler step and regression tests; no upstream source adapters, data handling or shared actions are changed. No completed b1r3 Windows build or GUI runtime test is claimed.

## Quick start with GitHub Desktop (no local compiler required)

1. On github.com, create an **empty, separate** repository, e.g. `GitHubDesktop-PortableApps-Builder`. Do not fork `desktop/desktop`. Choose public or private. Do not generate a README from GitHub's creation screen.
2. In GitHub Desktop, select **File → Clone Repository → URL**, then paste your empty repository URL; choose a local folder.
3. Extract this kit ZIP **into that repository's root**. Ensure `.github/workflows/build-portableapps.yml` exists; on Windows, hidden dot folders may not be visible unless hidden files are shown.
4. In GitHub Desktop, verify all added files, enter a commit message, choose **Commit to main**, and **Push origin**. No `git init` and no local compiler are required.
5. In the browser, open the new repository → **Actions** → **Build GitHub Desktop PortableApps (source-built x64)** → **Run workflow**.
6. Leave `upstream_version=latest` and `package_revision=r5`. Keep `publish=true` to create a downloadable release after both ZIP and installer checks. The workflow is manual by default and may consume substantial Windows Actions minutes.
7. Inspect the Actions job logs. It downloads source/submodules and compiles the real Electron Windows app; successful compilation alone does **not** mean portability is verified.
8. Once the workflow **succeeds**, open the repository's **Releases** page. Download the `GitHubDesktopPortable_..._x64_r5.zip` and its `.paf.exe` installer. The publisher creates `SHA256SUMS.txt` containing the actual SHA-256 for both assets.
9. Extract the ZIP to a regular folder or USB drive, or run the independent PortableApps-style installer. In the PortableApps Platform, refresh the app menu. Start `GitHubDesktopPortable.exe` **in the package root**.
10. Your retained profile and Git global config are under `GitHubDesktopPortable/Data/`. To upgrade, close GitHub Desktop, **back up Data**, replace `App/`, `Other/` and the root launcher while preserving `Data/` unchanged; or select the **same existing portable folder** in the installer. Never merge installed `%APPDATA%` profiles automatically.
11. Rollback: fully exit the app, back up `Data`, restore old `App`, `Other`, and launcher together. A newer profile/database schema may not work with an older app; never discard the newer Data backup.

## b1r2 — correction for submitted b1r1 GitHub Actions logs

The b1r1 run failed at `source-build-and-package / 10_Build actual modified GitHub Desktop application from source` while executing upstream `script/post-install.ts`. Errors TS7016 and TS7006 for `glob` arose because b1r1 set `NODE_ENV=production` **before** Yarn Classic installed dependencies, unintentionally excluding upstream `devDependencies` (`@types/glob`). This kit sets `NODE_ENV=development` while installing, passes explicit `--production=false` to root Yarn, verifies the real `@types/glob` declarations, and switches to production mode only for `build:prod`. No changes to upstream lockfiles, `skipLibCheck`, `transpileOnly`, or fabricated `.d.ts` stubs. The test suite checks this ordering.

**Evidence:** The diagnosis was confirmed from the b1r1 logs and upstream/Yarn source. The subsequent user-run b1r2 workflow **successfully completed GitHub Desktop source compilation**, then failed in the separate C++ launcher compiler (corrected in b1r3). GUI operation, ZIP, installer and portability remain unverified.

## What it does

- Source: a GitHub release tag matching numeric stable `X.Y.Z` only, followed by a `git fetch` of the **exact ref** and recording its full commit SHA and `yarn.lock` SHA-256.
- Source adapter: `scripts/patch_source.py` rejects any release except the currently audited `3.6.10`, and rejects missing/duplicated anchors. This is deliberate; no silent compiling of unreviewed future releases.
- Profile: `patches/portable-bootstrap.ts`, imported before normal main-process imports, sets Electron `userData`, `sessionData`, logs and portable AUMID inside `Data/Profile` **before app startup**.
- Git: the compiled launcher passes process-local `HOME`, `GIT_CONFIG_GLOBAL`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME` under `Data/GitHome` to GitHub Desktop and its descendants, without changing Windows system variables.
- Shell: the source patch suppresses broad automatic URL registration. The **compiled launcher**, only with user consent, temporarily overrides the single `x-github-desktop-auth` user handler, preserving/restoring the previous handler conditionally and journaling crash recovery. It never alters HKLM, installed shortcuts, `x-github-client` or `github-windows`.
- Updates: the Squirrel updater is disabled in portable mode, because it assumes a normal installed app and could overwrite that installation.
- Notifications: a separate portable CLSID is chosen to avoid reusing the installed app's Squirrel toast CLSID. Native toast activation still requires separate Windows integration, and click-to-open is not verified.
- Launcher: MSVC C++17 Win64 PE launches the packaged `GitHubDesktop.exe` with argument forwarding, waits for the application, and attempts to wait for descendants. No remote control, process injection, broad cleanup, or automatic elevation.
- Stage: original upstream icon is copied from verified source; 16/32 pixel PNGs are derived from it. Installer identity is independent of official GitHub Desktop and official PortableApps distribution.
- ZIP: verified with Python `zipfile.testzip()`, PE header/architecture, required resources, PortableApps metadata, and safe entry names.
- Installer: generated only by the pinned `vhick/Portable-Package-Builder@v1.0.0` **custom-nsis** composite action, pinned in workflow to verified immutable commit SHA.
- Publisher: only `vhick/portable-release-publisher@v1.1.1`, pinned to immutable SHA, with dry-run before real publication; default pruning OFF.

## Major known constraints — READ BEFORE USE

1. **GitHub browser sign-in is now enabled only with informed permission, but success is NOT YET VERIFIED.** First startup asks whether to enable a temporary per-user `x-github-desktop-auth` callback. Select YES for browser authentication. On clean exit the previous handler is restored; if it changed externally, the launcher protects the newer setting and leaves its recovery journal. This conflicts temporarily with installed GitHub Desktop sign-in, and Windows browser/UserChoice settings may still block callbacks. Do not use this package as your sole Git client until end-to-end tests pass.
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
- `scripts/build_source.ps1`: upstream vendored Yarn `install --frozen-lockfile --production=false` with `NODE_ENV=development` (including upstream nested app install), verify `@types/glob`, then `NODE_ENV=production` for `build:prod` with community signing disabled.
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

## Browser sign-in acceptance (b1r5)

1. Close any normally installed GitHub Desktop; do **not** run either copy as Administrator.
2. Preserve your existing `GitHubDesktopPortable/Data` directory, and install b1r4 as an app/launcher upgrade (ZIP extraction or installer to same folder).
3. Run **GitHubDesktopPortable.exe** from the root. On the permission dialog select **YES** for the temporary authentication handler. The choice is saved in `Data/AuthRedirectConsent.txt`.
4. Select **Sign in to GitHub.com**, complete browser authorization, and accept the browser prompt to open the application. Confirm the account becomes visible inside the **portable** GitHub Desktop.
5. Close the portable app **completely**. The launcher waits for all its job descendants to exit and conditionally restores the previous `HKCU\Software\Classes\x-github-desktop-auth` command. If the previous command was absent, it removes only its own empty keys.
6. To review or turn off consent later, run `Other\Source\Configure-Browser-SignIn.cmd`. This only invokes the compiled root launcher in settings mode. Select **NO** to stop overriding the protocol on subsequent sessions.
7. A recovery or conflict message means the launcher has deliberately left an ambiguous registry state unchanged. Do not delete `Data\TraceGuard\AuthProtocolRecovery.bin` or manually force registry replacements. Inspect `Data\TraceGuard\AuthProtocolStatus.txt` and compare handler ownership before resolving the conflict.

For read-only diagnostics in Windows Command Prompt, use `reg query "HKCU\Software\Classes\x-github-desktop-auth\shell\open\command" /ve` before launch, during the session, and after exit. A missing key before and after is fine. During the opted-in session it should point to the **portable root launcher**, not an installed `GitHubDesktop.exe`. Never paste OAuth callback URLs or authorization codes into bug reports.

**If the browser still won't return to the app:** check Windows browser permission, Default Apps protocol associations, any existing installed instance, and whether browser/portable run at different privilege levels. The GitHub team tracks similar Windows problems in upstream issue #22325. Select NO for temporary registration and use the installed desktop client if your system prohibits this URI callback; do not bypass the Windows UserChoice mechanism.

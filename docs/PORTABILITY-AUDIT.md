# Application-specific Windows portability audit

Audit target: GitHub Desktop source release `release-3.6.10` (3.6.10). Source code locations were examined through upstream GitHub release-tag URLs during preparation of b1r1. Runtime traces were **not** captured on an actual Windows desktop. `source-identity.json` in future build outputs will identify the **full upstream commit** after exact tag checkout; do not assume a short release-list hash is the verified full commit.

## Selected architecture

**PORTABLEAPPS, x64 only.** GitHub Desktop is a regular on-demand GUI application. A compiled root launcher and PortableApps-style installer are useful for removable-folder workflows. This is not a NATIVE product, and this kit does not claim to ship directly runnable native-portable `GitHubDesktop.exe`.

## Source/build provenance

- Source code: `https://github.com/desktop/desktop`, release-tag `release-3.6.10`, MIT source-license declaration.
- Framework: Electron, TypeScript/JavaScript, Webpack, Node.js, Git for Windows/dugite; native dependencies include `keytar` and `registry-js` per `app/package.json`.
- Build: `yarn install --frozen-lockfile` then `yarn build:prod`, run under upstream `.node-version` (`24.22.1` for 3.6.10); Windows Visual C++ compiler is needed for launcher and upstream native modules.
- Packager: `script/build.ts` runs `@electron/packager` with `asar: false` and `GitHubDesktop-win32-x64` output. `script/package.ts` normally creates Squirrel.Windows setup and `.nupkg`; this kit does **not** use that installer.
- Software version source: `app/package.json` is `3.6.10`. Lockfile `yarn.lock` exists at that tag and is hashed in each build.
- Most recent numeric stable at audit: 3.6.10. GitHub releases also list beta builds, deliberately excluded.
- Upstream normal Windows installation storage is documented as `%LOCALAPPDATA%\GitHubDesktop` (installed versions) and `%APPDATA%\GitHub Desktop` (profile and logs).

## Mode-specific findings

Evidence labels indicate what is observed *in source* vs inferred. No row below is a claim of Windows-runtime verification.

| Finding | Evidence (path and type) | Host path | Responsible | NATIVE remedy | PORTABLEAPPS remedy | Data safety / functionality / test / limitation |
| --- | --- | --- | --- | --- | --- | --- |
| Electron userData / log path | **SOURCE-INSPECTED**: `app/src/main-process/main.ts` imports logging, sets app logs; `app/src/lib/logging/get-log-path.ts` gets Electron `userData` | `%APPDATA%\GitHub Desktop` normally | Upstream + Electron | Not applicable | First imported `portable-bootstrap.ts` sets `userData`, `sessionData`, logs to `Data/Profile` | No broad APPDATA redirects; static patch test only; profile first-run/move **not yet verified** |
| Installed binary versions + Squirrel | **SOURCE-INSPECTED** `app/src/main-process/squirrel-updater.ts` and `script/package.ts`; documented install path | `%LOCALAPPDATA%\GitHubDesktop` | Installer/updater | Not applicable | Source-built unpacked Electron app; app-window auto-updater disabled for portable launches | Protects installed program; check update UI **not yet verified** |
| URL protocols | **SOURCE-INSPECTED**: `app/src/main-process/main.ts` calls `setAsDefaultProtocolClient` for `x-github-client`, `x-github-desktop-auth`, `github-windows` | HKCU Windows URL protocol class and shell choice (exact keys not runtime verified) | Upstream Electron + Windows shell | Not applicable | Prevents automatic protocol registration in portable mode | Installed handler preserved, **but browser OAuth sign-in may not work**. Explicit opt-in, rollback-safe handler implementation not provided. Manual test required |
| Notifications + toast CLSID | **SOURCE-INSPECTED**: `app/src/main-process/notifications.ts` + `find-toast-activator-clsid.ts` inspect installed Squirrel shortcuts; fallback known CLSID | Windows Start Menu and notification identity | App + native notifications + Windows shell | Not applicable | Separate portable CLSID, not installed Squirrel fallback | No borrowed installed CLSID; notification click activation not proven, may require per-user COM/shortcut registration |
| Git global config | **SOURCE-INSPECTED**: `app/src/lib/git/config.ts` calls `git config --global`; `app/src/lib/git/core.ts` invokes dugite | HOME/.gitconfig or configured Git global file | Git dependency | Not applicable | Child-scoped `HOME`/`GIT_CONFIG_GLOBAL` in `Data/GitHome` | Existing host global config unchanged by these commands; Git extension/hook behavior still requires verification |
| Git credentials | **SOURCE-INSPECTED dependency** `keytar` in `app/package.json`; **INFERRED** Windows Credential Manager usage from keytar | Windows credential vault (exact entries NOT captured) | Dependency / Windows | Not applicable | No token harvesting or unprotected plaintext copying; document non-mobility | **Hard portability limitation.** Sign-in across accounts/computers unverified; data possibly remains on host |
| Git Credential Manager / SSH | **SOURCE-INSPECTED dependency** Git for Windows/dugite; **INFERRED** helper/SSH behavior | User credential store, `%USERPROFILE%\.ssh`, Git helper state | Git/SSH external dependencies | Not applicable | Scope child `HOME`; do not change user-wide SSH/credential settings | SSH agent, repository hooks, external shells may still access host. No automatic deletion |
| Other app sessions/preferences | **INFERRED** Electron/Chromium profile cache, IndexedDB, window state | userData and sessionData | Electron + application | Not applicable | Before-init `app.setPath` paths under Data | First/second-run database and completely empty subdir preservation requires Windows manual test |
| OS caches and recent activity | **INFERRED**, Windows-managed; no application-specific trace evidence | Jump Lists, Prefetch, Start Menu cache, Explorer | Windows shell | Not applicable | Leave Windows-managed state alone; no broad ShellGuard deletion | Cannot promise zero Windows traces. Never interfere with installed apps |
| Worktrees and repos | **SOURCE-INSPECTED** Git commands, source paths and UI | Locations selected by user, Downloads/Documents/Desktop | User-selected content | Not applicable | No relocation or capture of repositories; profile stays in Data | Chosen repository files are intentionally outside portable package; do not silently migrate |
| Scripts / external editors / terminals | **INFERRED** from app support and Git integration | Any user-selected path | External apps | Not applicable | No global environment/registry modification; launcher environment inherited only by children | System tools, hooks and editors may write normally, not app-owned traces to scavenge |

## TraceGuard / ShellGuard decision

**No destructive post-exit TraceGuard/ShellGuard is shipped.** This is a deliberate, evidence-based safety decision rather than an assertion that no traces exist. Documented upstream application settings/log paths are redirected **before startup**. Automatic protocol registration and Squirrel updater are blocked at source. No safe, precisely attributable additional files/registry keys have been demonstrated through a Windows runtime trace. Broad post-exit harvesting of shared system directories or Credential Manager would risk data loss and installed-app interference.

`Data/TraceGuard/` exists and is preserved, including when completely empty, for future *evidence-driven* additions. It is **not** a functioning registry/shortcut harvesting engine. Do not claim empty-directory recovery of foreign host state has been tested or implemented.

## Compatibility and limitations

- Project build uses exact 3.6.10 source. All future 3.6.11+ source layouts require another audit before patching; CI fails closed rather than applying assumptions.
- Application startup under source-built unsigned Electron, authentication flows, Windows toast activator behavior, Git global config containment, and Windows Credential Manager entry ownership are **NOT YET VERIFIED**.
- Changing GitHub Desktop's `userData` could interact with upstream settings migration and Squirrel assumptions. No installed profile is migrated by default.
- Browser OAuth may be unavailable because protected installed URL protocols are not overridden. Use a normal installed GitHub Desktop for any blocked login flow until a verified, reversible opt-in callback implementation exists.
- Windows x64 only. No ARM64 or 32-bit claims.

## Action audits (verified source and tag)

| Component | Baseline tag | Immutable commit | Verified interface |
| --- | --- | --- | --- |
| Shared Package Builder | `v1.0.0` | `0112c35580e83b37eb8757ebcb949274e1631a04` | `source-dir`, `output-dir`, `engine=custom-nsis`, `running-exe`, `timeout-seconds`, `package-revision` and `installer-file`, `installer-sha256`, `app-id`, `app-version` outputs |
| Universal Release Publisher | `v1.1.1` | `cb64f86ac2d8c67506db5832de07f9ff58cbeaeb` | `files`, `tag`, `release-title`, `tag-prefix`, `keep-releases`, `prune`, `dry-run`; generates `SHA256SUMS.txt`, protects publisher-owned releases |

Actual read source files:
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/action.yml
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/scripts/build.ps1
- https://raw.githubusercontent.com/vhick/Portable-Package-Builder/v1.0.0/nsis/community-installer.nsi
- https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/action.yml
- https://raw.githubusercontent.com/vhick/portable-release-publisher/v1.1.1/scripts/publish.py
- https://raw.githubusercontent.com/desktop/desktop/release-3.6.10/app/src/main-process/main.ts
- https://raw.githubusercontent.com/desktop/desktop/release-3.6.10/app/src/main-process/notifications.ts
- https://raw.githubusercontent.com/desktop/desktop/release-3.6.10/app/src/main-process/app-window.ts
- https://raw.githubusercontent.com/desktop/desktop/release-3.6.10/app/src/main-process/squirrel-updater.ts
- https://raw.githubusercontent.com/desktop/desktop/release-3.6.10/app/src/lib/git/config.ts
- https://raw.githubusercontent.com/desktop/desktop/release-3.6.10/script/build.ts

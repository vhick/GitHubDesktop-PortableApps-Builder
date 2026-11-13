# GitHub Desktop PortableApps Builder Kit b1r6 — OAuth scheme mismatch correction

Date: 2026-11-13. Upstream: desktop/desktop release-3.6.10. Mode: PORTABLEAPPS only.

## Confirmed source mismatch (not speculation)

`app/app-info.ts` calculates `__DEV_SECRETS__` as `isDevBuild || !process.env.DESKTOP_OAUTH_CLIENT_SECRET`. b1r5 builds with `RELEASE_CHANNEL=production` and `NODE_ENV=production` but does not inject an OAuth client secret, so `__DEV_SECRETS__` is **true** and the upstream public development OAuth client is compiled in. `app/src/main-process/main.ts` selects `x-github-desktop-dev-auth` when `__DEV_SECRETS__` is true. Previous b1r4/b1r5 launchers only registered `x-github-desktop-auth`, which is the **wrong protocol** for the shipped source build. The upstream OAuth callback needs the application to receive its matching scheme; registration of the other scheme cannot complete the handoff.

Verified upstream refs:
- https://github.com/desktop/desktop/blob/release-3.6.10/app/app-info.ts
- https://github.com/desktop/desktop/blob/release-3.6.10/app/src/main-process/main.ts
- https://github.com/desktop/desktop/blob/release-3.6.10/app/src/lib/api.ts
- https://github.com/desktop/desktop/blob/release-3.6.10/script/dist-info.ts

## Implementation

1. `launcher/GitHubDesktopPortable.cpp` now accepts and temporarily registers `x-github-desktop-dev-auth://` only. Browser callback launches are still one-shot and isolated from primary mutex ownership.
2. Before registering the new scheme, launcher conditionally recovers the old b1r4/b1r5 production-scheme `Data/TraceGuard/AuthProtocolRecovery.bin` journal. It fails closed on a conflict, preserving any newer host handler. NEVER delete this journal to avoid a conflict.
3. The new scheme uses its own `Data/TraceGuard/AuthDevProtocolRecovery.bin` journal, preserving separate identities and preventing cross-scheme restoration.
4. `launcher/AuthProtocolGuard.cpp` explicitly allowlists the development scheme (and retains the old production scheme solely for legacy recovery). It makes no HKLM edits and only handles approved scheme-specific per-user values.
5. `scripts/build_source.ps1` refuses unexpected OAuth client credentials, ensuring the source build and launcher still agree; it never echoes credentials.
6. `scripts/stage.py` checks the actual built `resources/app/main.js` includes `x-github-desktop-dev-auth`. This is a build-time fail-closed check, not a real Windows sign-in test.
7. Existing b1r5 Job Object lifecycle/termination fixes and dev dependency/MSVC compiler fixes are kept.
8. Optional `Other/Source/Diagnose-Browser-SignIn.cmd` performs read-only inspection of per-user/effective protocol routing and produces `Data/TraceGuard/AuthDiagnostics.txt` with only boolean outcomes and launcher status labels (no URL, code, token or full path). Windows PowerShell execution policy may prevent the optional script from running; no machine settings are modified to work around policy.

## Secure upgrade

Close the existing portable GUI and any verified orphaned root launcher. Back up the entire `Data` folder, including both original journal and consent. Replace App, launcher, and Other from the r6 output without deleting Data or private profiles. On startup the old journal is inspected. A conflict is surfaced; never manually force its removal or modify another application's handler. The default consent file remains valid if it says `enabled`.

## Validation and unresolved risks

- SOURCE-INSPECTED: Upstream scheme selection vs launcher source mismatch.
- STATIC-VALIDATED: Local kit regression tests, archive structure and YAML; final results documented in docs/VALIDATION.md.
- NOT YET VERIFIED: Windows C++ compilation of b1r6, real registry behavior, callback delivery, OAuth/token exchange, credential portability, GUI lifecycle, NSIS installer upgrade, GitHub release publication.
- Windows Default Apps UserChoice, browser external-app handoff and admin privilege mismatches could still block URI invocation even with matching scheme; inspect token-free `Data/TraceGuard/AuthProtocolStatus.txt` if so.

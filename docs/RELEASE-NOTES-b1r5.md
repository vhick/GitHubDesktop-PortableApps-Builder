# GitHub Desktop PortableApps Builder Kit b1r5 — launcher lifecycle and callback retry

Date: 2026-11-13. Source app: audited desktop/desktop release-3.6.10.
Mode: PORTABLEAPPS, Windows x64. Shared actions pinned exactly as b1r4.

## Evidence from user b1r4 runtime

- USER-OBSERVED: GitHub Desktop GUI starts and the browser reaches GitHub authorization, but the portable app does not complete sign-in.
- USER-OBSERVED: Task Manager shows GitHubDesktopPortable.exe remaining after the GUI closes (about 1.1 MB in screenshot).
- FILE-INSPECTED: Data/AuthRedirectConsent.txt says `enabled`.
- FILE-INSPECTED: Data/TraceGuard/AuthProtocolStatus.txt says `Auth callback mutex held by another portable instance; not overwritten.`
- FILE-INSPECTED: AuthProtocolRecovery.bin (AGH4 journal) is valid, records that the four allowlisted per-user auth registry keys did not exist before registration, and records a compiled-launcher owned command. The current Windows registry could NOT be inspected and may have changed since journal creation.

## Diagnosed defects in b1r4 launcher

1. b1r4 calls `WaitForSingleObject(job, INFINITE)`. Microsoft's Job Objects documentation does not define normal job-process completion as the job object's signaled condition. The signaled state is for end-of-job time-limit expiration. This can leave the launcher running after all child processes have quit, holding the session mutex and preventing restoration.
2. Callback-only invocations also create a job and use that same invalid wait. A browser callback can therefore leave additional launcher processes stuck.
3. A second ordinary root launcher currently logs a mutex conflict yet STILL starts the packaged application. This makes handler ownership and lifecycle untrackable.
4. b1r4 lacks a token-safe indication that the Windows callback actually entered the portable launcher.

## Changes

- `launcher/ProcessLifecycle.h`: real `QueryInformationJobObject(..., JobObjectBasicAccountingInformation, ...)` with `ActiveProcesses` accounting. The main launcher waits for the initial app process and then polls until tracked descendants are zero. No forced termination.
- `launcher/GitHubDesktopPortable.cpp`: browser callbacks call the real packaged executable with the same profile environment, close their process handles, and return immediately; no auth registry mutation, mutex acquisition, or job wait in callback path. A duplicate ordinary launch is blocked with a clear message.
- `launcher/AuthProtocolGuard.h`: fail-closed option to preserve the journal if descendant tracking itself fails (avoids destructor triggering unsafe early restore).
- No-auth-URL diagnostics in Data/TraceGuard/AuthProtocolStatus.txt: `AUTH HANDLER ACTIVE`, `CALLBACK INVOKED`, `CALLBACK SPAWN FAILED`, `CLEAN EXIT`, `PROCESS TRACKING FAILED`.
- `tests/process_lifecycle_fixture.cpp`: Windows headless test creates only its own child and grandchild, verifies that the grandchild remains counted after the parent exits, and waits for a real job process count of zero.
- `scripts/compile_launcher.ps1`: compiles and executes new Windows fixture; does not run GitHub Desktop GUI or touch the real auth handler.
- `tests/test_kit.py`: regression checks for the correct job accounting and the nonblocking callback launch.
- `build-portableapps.yml`: default package revision r5.

## Data safety and b1r4 recovery

**Do not delete Data or TraceGuard.** The b1r4 journal is evidence that a temporary per-user auth handler may still exist. Before upgrading, close GitHub Desktop's portable GUI and safely terminate the stranded `GitHubDesktopPortable.exe` launcher **only after verifying the image/path belongs to this portable package**. Do not end unrelated installed application processes. Back up the complete portable Data directory, including `AuthProtocolRecovery.bin` and `AuthProtocolStatus.txt`.

Install the new App and launcher while retaining the existing Data unchanged. On first b1r5 launch, under exclusive mutex, the guard attempts conditional recovery of b1r4's journal before a new temporary override. If another program has changed the callback handler, it preserves that value and the journal; it will report a conflict, not force an overwrite. Never delete the journal to suppress this safety check. If the new app resides at a new path, the journal still contains the old owned command and is recovered on ownership proof rather than path equality to the new build.

The browser sign-in still needs an interactive Windows test. If a successful sign-in does not occur, check the token-free TraceGuard status:
- `AUTH HANDLER ACTIVE`, but no `CALLBACK INVOKED`: browser/Windows protocol dispatch, Windows Default Apps UserChoice, URL permission or privilege mismatch are likely; no need to send the private OAuth URL.
- `CALLBACK INVOKED`, but no account sign-in: Windows invoked the portable handler; inspect GitHub Desktop's sanitized app logs for upstream argument handling or credential/API errors.
- `CLEAN EXIT`: handler restoration was completed after tracked children exited.

## Verification

- FILE-INSPECTED and SOURCE-INSPECTED: input journal/status and exact b1r4 launcher code.
- STATIC-VALIDATED: Python unit/regression tests and ZIP integrity after kit generation.
- NOT YET VERIFIED: revised C++ launcher compilation, Windows job fixture execution, actual browser sign-in, credential storage, installer upgrade and release publication. The GitHub-hosted Windows job will establish some, not all, of this evidence.

No upstream source adapter modification, automatic URL registration, globally redirected TEMP, forced application kills, HKLM change, or unbounded host-data scavenging was introduced.

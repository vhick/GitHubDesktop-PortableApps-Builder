# GitHub Desktop PortableApps Builder Kit b1r7 — Dynamic Stable Version Support

Date: 2026-11-21. Selected mode: PORTABLEAPPS, Windows x64. Underlying app: https://github.com/desktop/desktop.

## User-reported failure and exact fix

`logs_121437119019.zip` shows `release-3.6.11` was resolved and fetched correctly. Source adapter failed with `No audited patch adapter for 3.6.11; supported upstream version: 3.6.10`. No application compilation, launcher compilation, ZIP, installer or release followed.

The old implementation had **two** ceilings: `resolve_release.py` selected newest stable not later than 3.6.10 for `latest`, and `patch_source.py` refused to patch newer source even when `3.6.11` was requested explicitly.

b1r7 removes both ceilings. Version resolution still rejects prereleases, drafts and nonstandard versions. Source patching now uses version-neutral, precise source anchors and checks critical GitHub Desktop identity, MIT license, minimum inspected version 3.6.10, early Electron initialization point, upstream dev OAuth and callback scheme, and single-instance handler. It preflights *every* anchor before changing any source file. Incompatible upstream source fails with a descriptive error and no partial edits. Each patch's source version and before/after SHA-256 is recorded. Original verified upstream tag, commit and yarn lock hashes remain in source identity output.

## Source evidence

Official `release-3.6.11` source was inspected in upstream files `app/src/main-process/main.ts`, `app/src/main-process/app-window.ts`, `app/src/main-process/notifications.ts`, `script/build.ts`, `app/app-info.ts`, and `app/package.json`. Those exact patch patterns remained available in 3.6.11. Official release notes state Git was updated to 2.56.1.

The b1r6 compiled Win64 launcher, GitHub sign-in callback `x-github-desktop-dev-auth://`, opt-in HKCU registration with conditional restoration, Data/TraceGuard recovery journals, safe app shutdown, portable paths and compiled OAuth guard are preserved unchanged. Both pinned shared actions and packaging-only workflow are retained unchanged.

## How to build in GitHub Actions

1. Back up the existing builder repository, then extract this ZIP into its root, including `.github`.
2. In GitHub Desktop commit with summary `Support dynamic stable GitHub Desktop versions - b1r7` and push.
3. Open **Actions → Build GitHub Desktop PortableApps (source-built x64) → Run workflow**.
4. Select `upstream_version=latest` (or `3.6.11`), `package_revision=r7`, `publish=true`.
5. Inspect each independent stage in the run. If the 3.6.11 build and both package checks succeed, go to builder-repository **Releases** for the `GitHubDesktopPortable_3.6.11_x64_r7.zip`, separately built installer and checksums. These names are expected, not artifacts already produced.
6. Close the portable app, back up the entire `GitHubDesktopPortable/Data` directory, install/replace package-managed components without overwriting Data, and test sign-in, full shutdown, registry restoration, existing-installed app coexistence, and account profile persistence.

## Release status

The updated builder kit and offline source fixtures are STATIC-VALIDATED. The prior b1r6 is USER-CONFIRMED working, including browser OAuth. b1r7 source compilation, Windows runtime, installer and release publication are NOT YET VERIFIED until GitHub Actions and an interactive Windows user test succeed.

## GitHub Desktop commit

Summary: `Support dynamic stable GitHub Desktop versions - b1r7`

Description:
```
- Remove the hard-coded 3.6.10 cap from latest stable release resolution.
- Replace strict version-only refusal with application-specific source, OAuth, and patch-anchor preflight checks.
- Abort without partial source edits on incompatible upstream changes.
- Preserve b1r6 launcher, OAuth, TraceGuard and the pinned shared packaging/release actions.
- Add 3.6.11 compatibility and drift regression fixtures; refresh documentation and default package revision to r7.
```

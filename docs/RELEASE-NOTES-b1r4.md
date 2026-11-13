# GitHub Desktop PortableApps Builder Kit b1r4 — 2026-11-13

## User-observed failure

b1r3 compiled, packaged and launched GitHub Desktop, but browser OAuth authorization did not return to the application (screenshots). This was anticipated in the b1r3 source audit: broad protocol registrations were suppressed to protect installed-app associations. Upstream 3.6.10 handles callbacks using `x-github-desktop-auth://` and `--protocol-launcher` via second-instance handoff.

## Changes

- New C++ `launcher/AuthProtocolGuard.cpp` and `.h`: opt-in HKCU-only auth protocol with exact original value types/bytes, journal written before edits, locked single-owner session, conditional restoration, conflict preservation, cautious empty-key removal and crash recovery.
- Revised root compiled C++ launcher: first-launch consent prompt, persisted consent under Data, secure browser callback forwarding without any registry mutation in callback subprocess; complete job child-tree wait before restore; fail closed when job assignment is unavailable during auth.
- Existing app-source patch remains conservative and suppresses normal automatic `x-github-client`, `x-github-desktop-auth`, `github-windows` registration by the Electron application itself.
- `scripts/compile_launcher.ps1`: individually compile and link both C++ translation units with Advapi32, followed by isolated Windows HKCU registry fixture (non-GitHub test scheme).
- `tests/auth_guard_fixture.cpp`: headless test of new handler creation, restoring an existing handler, conflict preservation, and recovery. Runs only on hosted Windows when compiler step runs.
- `scripts/stage.py`: installer/ZIP includes optional sign-in settings helper and updated portability limitations; preserves Data and journals.
- Full-workflow default revision updated to r4. Pinned shared package builder v1.0.0 and release publisher v1.1.1 remain unchanged.

## Verification

- 16 offline local Python regression tests: STATIC-VALIDATED.
- b1r3 GUI opens: USER-CONFIRMED; b1r3 browser sign-in: FAILED/USER-OBSERVED.
- b1r4 actual compiled C++ launcher, Windows HKCU fixture, OAuth callback, installed app coexistence, package/installer, publisher: NOT YET VERIFIED.

## Use

Push this kit to the **same independent builder repository**. Run full source workflow with upstream_version=latest, package_revision=r4, publish=true. The previous compiled b1r3 launcher **cannot** be repaired through installer-only repackage; rebuild the launcher. Back up and retain `Data` when upgrading. First portable startup: choose YES to permit temporary browser callback. Do not run portable and installed GitHub Desktop simultaneously for sign-in. The setting can later be changed with `Other/Source/Configure-Browser-SignIn.cmd`. Never share a copied OAuth callback URL or its code.

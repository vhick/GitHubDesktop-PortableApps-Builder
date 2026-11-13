# Manual Windows 10/11 acceptance tests — NOT executed during kit creation

Use a disposable Windows test account/VM before testing with real repositories. Capture screenshots, Process Monitor (ProcMon) and before/after registry/file inventories. Never run destructive registry cleanup on a normal workstation. All tests below are pending; mark each PASS/FAIL with dated evidence after actual execution.

## Functional first run

- [ ] Build workflow compiles real source-built `App/GitHubDesktop/GitHubDesktop.exe` and real root launcher.
- [ ] Execute from regular folder, folder containing spaces, and Unicode folder name.
- [ ] Launch from a different current working directory; CLI `--cli-open` arguments survive.
- [ ] Observe first run, app window, main repository list, clone, open, commit, branch switch, push and pull.
- [ ] Edit preferences, close app completely, restart and confirm persistence.
- [ ] Inspect `Data/Profile` logs, databases, settings, Chromium session storage and `Data/GitHome` git config.
- [ ] Inspect Windows installed `%APPDATA%\GitHub Desktop` and `%LOCALAPPDATA%\GitHubDesktop` before/during/after. Any unexpected changes must be attributed.
- [ ] Before first launch, snapshot `HKCU\Software\Classes\x-github-desktop-dev-auth` without saving any OAuth URLs/tokens in screenshots or logs.
- [ ] Launch b1r6, choose **YES** in the explicit temporary handler permission prompt, and check registry command points to this portable root `GitHubDesktopPortable.exe --protocol-launcher "%1"`.
- [ ] Sign in via browser; confirm Windows prompts to open GitHub Desktop Portable, auth returns to the running app and account becomes signed in. If it does not, **FAIL sign-in** rather than manually exporting credentials.
- [ ] Exit the portable app and all descendants; verify the original handler exactly matches the prelaunch values (or new key removed when absent).
- [ ] Choose NO via `Other/Source/Configure-Browser-SignIn.cmd`; verify no auth registry modification, even after repeated starts.
- [ ] Kill the primary launcher during temporary registration in disposable VM; relaunch and verify journal-based restoration and no installed-app data loss.
- [ ] While portable is running, allow an independent test app to modify the auth handler; verify portable preserves the newer value on shutdown and retains conflict journal for manual review.
- [ ] Test ZIP folder/USB relocation with a stale recovery journal; verify old handler is restored only if its owned command is still present.
- [ ] Verify non-elevated browser and portable app, or document failure if privilege mismatch. Windows UserChoice may block protocol handling.
- [ ] Check Git credential entries, reauthentication on second machine, Git Credential Manager, SSH key path and credential-protection policy. Do not export saved secrets.

## Windows shell coexistence

- [ ] Install standard GitHub Desktop in a disposable account; establish existing URL protocol handlers and shortcuts.
- [ ] Run portable version with opt-in: `x-github-client` and `github-windows` remain unchanged, while `x-github-desktop-dev-auth` is temporarily owned and safely restored after exit.
- [ ] Verify installed desktop profile remains unchanged when the portable version runs.
- [ ] Confirm updater never replaces the installed application or writes under Squirrel version path.
- [ ] Test toast shown, click-to-open and focus. Mark notifications as failed if click activation is missing; no false PASS.
- [ ] Observe Windows Jump Lists, Start Menu/Desktop shortcuts, notification registry entries and installed AUMID; distinguish OS-managed state.

## Process and safety

- [ ] From a b1r4 build with an orphaned root launcher, end only that verified portable launcher, **retain** the b1r4/b1r5 TraceGuard production-scheme journal, and launch b1r6; confirm conditional recovery and fresh auth registration without overwriting changed host associations.
- [ ] While the application is running, launch the same root EXE a second time; confirm the second ordinary process exits after a duplicate warning rather than starting an untracked app.
- [ ] After real OAuth, check `AUTH HANDLER ACTIVE` then `CALLBACK INVOKED` in the token-free status file; do not copy the browser callback URL into any report.
- [ ] Close the GUI and observe `CLEAN EXIT` and restoration of prior `x-github-desktop-dev-auth` handler; `GitHubDesktopPortable.exe` should no longer appear in Task Manager unless application descendants legitimately remain.

- [ ] Launcher exit, app close, duplicate instance, child Git processes, external editor, background fetch, crash and forced kill. Verify only our launcher remains during the GUI session and exits shortly after the last app child process closes; no indefinite job wait.
- [ ] Kill launcher/app mid-operation; reopen. No broad TraceGuard recovery is present or claimed.
- [ ] Place completely empty directories and nested empty trees under `Data`; check they survive ZIP extraction and installer upgrade.
- [ ] Put a sentinel file in a pre-existing installed `AppData` profile; never modify/delete it with portable startup.
- [ ] Move portable package to another volume/drive letter, launch and verify settings and Git config survive. Reauthorize credentials if needed.
- [ ] Check read-only USB folder: startup should fail safely without writing host profile or deleting files.

## Installer/reinstallation

- [ ] Confirm `.paf.exe` authentic PE, expected source/binary payload, matching SHA256SUMS.txt and independent NSIS identity.
- [ ] Inspect setup UI; choose a new destination and verify correct folder.
- [ ] Run reinstall/upgrade into same portable folder with existing Data and empty nested directories. Verify preserved Data bytes and tree.
- [ ] Test running-app guard. Installer must refuse update when the app is active.
- [ ] Test failed update and rollback. Do not delete `.__UPB_Backup` or `.__UPB_Stage` without verifying ownership and recovery.
- [ ] Validate obsolete binary removal and safeguard user edits placed inside managed App directories (archive them before upgrades).
- [ ] Roll back to older app and check schema incompatibility; restore Data backup if required.

## Reporting

Do not write `USER-CONFIRMED` until the actual user reports successful application testing. Distinguish `WINDOWS-COMPILED`, `STATIC-VALIDATED`, `AUTOMATED-RUNTIME-TESTED`, `MANUAL-WINDOWS-TESTED` and `NOT YET VERIFIED` for each subsystem.

## b1r6-specific migration checks

- [ ] Preserve legacy `AuthProtocolRecovery.bin` until the launcher has safely recovered it; do not delete it manually.
- [ ] With no OAuth client-secret override, verify built `resources/app/main.js` contains `x-github-desktop-dev-auth`; staging refuses mismatches.
- [ ] With explicit consent, the *development* protocol command points to the current root launcher. The old production protocol is restored to prior state.
- [ ] After browser authorization, `CALLBACK INVOKED` is recorded in `Data/TraceGuard/AuthProtocolStatus.txt` (never log the callback URL or code).
- [ ] After full process-tree shutdown, the new development protocol is conditionally restored and `AuthDevProtocolRecovery.bin` is gone only if its restoration completed safely.
- [ ] Test installed GitHub Desktop sign-in after the portable session to confirm its production handler was preserved.

- [ ] While the app is open, optionally run `Other/Source/Diagnose-Browser-SignIn.cmd` and verify per-user/effective routing points at this root launcher; do not disable script execution policy if blocked.

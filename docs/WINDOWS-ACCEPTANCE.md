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
- [ ] Check whether GitHub login via browser works. If callback fails, **FAIL sign-in**; do not alter registered URL handlers without consent.
- [ ] Check Git credential entries, reauthentication on second machine, Git Credential Manager, SSH key path and credential-protection policy. Do not export saved secrets.

## Windows shell coexistence

- [ ] Install standard GitHub Desktop in a disposable account; establish existing URL protocol handlers and shortcuts.
- [ ] Run portable version; verify registered `x-github-client`, `x-github-desktop-auth` and `github-windows` handlers are unchanged.
- [ ] Verify installed desktop profile remains unchanged when the portable version runs.
- [ ] Confirm updater never replaces the installed application or writes under Squirrel version path.
- [ ] Test toast shown, click-to-open and focus. Mark notifications as failed if click activation is missing; no false PASS.
- [ ] Observe Windows Jump Lists, Start Menu/Desktop shortcuts, notification registry entries and installed AUMID; distinguish OS-managed state.

## Process and safety

- [ ] Launcher exit, app close, duplicate instance, child Git processes, external editor, background fetch, crash and forced kill. Ensure no launcher hung indefinitely.
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

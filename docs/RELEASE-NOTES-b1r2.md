# GitHub Desktop PortableApps Builder Kit b1r2 — 2026-11-12

## Reproducible failure

User GitHub Actions logs `logs_117095726286.zip` reached `source-build-and-package / 10_Build actual modified GitHub Desktop application from source` and failed while Yarn Classic ran `script/post-install.ts`:

- TS7016: declaration file for `glob` missing.
- TS7006: callback arguments `error` and `files` implicitly `any`.
- `Upstream Yarn install failed: 1`.

Upstream 3.6.10 declares `@types/glob` in root `devDependencies`. The b1r1 script set `NODE_ENV=production` before `yarn install`, so Yarn Classic omitted the types. That setting also affects the upstream postinstall's nested Yarn install.

## Corrective changes

1. `scripts/build_source.ps1`: Set `NODE_ENV=development` for dependency installation and nested postinstall; explicit `--production=false` on root vendored Yarn Classic; verify the official `node_modules/@types/glob/index.d.ts` is present; change `NODE_ENV=production` **only after install** and run `build:prod`.
2. `.github/workflows/build-portableapps.yml`: New default `package_revision=r2` to distinguish corrected outputs.
3. `tests/test_kit.py`: Add two regression tests for dependency mode and correct build order.
4. README and validation documentation updated to explain diagnosis and re-run.

No changes to upstream version, lockfile, pinned shared action commits, launcher design, profile data, or installer mechanism.

## Evidence boundary

- **FAILED/BLOCKED:** Prior b1r1 full Windows build (user supplied log).
- **SOURCE-INSPECTED:** GitHub Desktop package.json and Yarn Classic documentation.
- **STATIC-VALIDATED:** Local tests and ZIP integrity in b1r2 (see build-kit report).
- **NOT YET VERIFIED:** b1r2 Windows build, PE launcher, PortableApps application ZIP, installer, interactive runtime/credential/sign-in/notifications.

Primary references:
- https://github.com/desktop/desktop/blob/release-3.6.10/package.json
- https://github.com/desktop/desktop/blob/release-3.6.10/script/post-install.ts
- https://classic.yarnpkg.com/en/docs/cli/install#toc-yarn-install-production-true-false

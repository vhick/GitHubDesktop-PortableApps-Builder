"""Offline non-GUI fixtures. NOT evidence of real Windows runtime portability."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name+'.py'))
    item = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(item)
    return item

class SafeAdapters(unittest.TestCase):
    def test_numeric_semver_and_prerelease_excluded(self):
        r = module('resolve_release')
        self.assertTrue(r.RX.fullmatch('release-3.6.10'))
        self.assertFalse(r.RX.fullmatch('release-3.6.11-beta1'))
        self.assertGreater((3,6,10),(3,6,9))

    def test_source_patcher_refuses_drift(self):
        r = module('patch_source')
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'sample.ts'
            f.write_text('const original = 5\n', encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError,'drift'):
                r.replace_exact(f, 'missing', 'updated')
            self.assertEqual(f.read_text(encoding='utf-8'),'const original = 5\n')

    def test_source_patcher_refuses_duplicate_anchors(self):
        r = module('patch_source')
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'dup.ts'
            f.write_text('target target', encoding='utf-8')
            with self.assertRaises(RuntimeError): r.replace_exact(f,'target','changed')

    def test_zip_validator_rejects_invalid_layout(self):
        s = module('stage')
        with tempfile.TemporaryDirectory() as td:
            z=Path(td)/'bad.zip'
            with zipfile.ZipFile(z,'w') as h: h.writestr('wrong/file.txt', 'fake')
            with self.assertRaisesRegex(RuntimeError,'ZIP missing'):
                s.verify_zip(z)

    def test_workflow_uses_only_pinned_actions_and_no_unsupported_mode(self):
        text=(ROOT/'.github/workflows/build-portableapps.yml').read_text(encoding='utf-8')
        self.assertIn('0112c35580e83b37eb8757ebcb949274e1631a04', text)
        self.assertIn('cb64f86ac2d8c67506db5832de07f9ff58cbeaeb', text)
        self.assertIn('custom-nsis', text)
        self.assertNotIn('engine: official', text)
        self.assertIn('steps.installer.outcome', text)

    def test_b1r2_yarn_installs_dev_types_before_production_build(self):
        # Regression for submitted b1r1 Windows CI logs (TS7016 + TS7006).
        # Yarn Classic skips devDependencies with NODE_ENV=production.
        script=(ROOT/'scripts/build_source.ps1').read_text(encoding='utf-8')
        dev_env = script.index("$env:NODE_ENV = 'development'")
        install = script.index('install --frozen-lockfile --non-interactive --production=false')
        verify = script.index("node_modules/@types/glob/index.d.ts")
        production_env = script.index("$env:NODE_ENV = 'production'")
        build = script.index('build:prod', production_env)
        self.assertTrue(dev_env < install < verify < production_env < build)
        self.assertIn("Missing root @types/glob despite full Yarn install", script)
        self.assertNotIn('transpileOnly', script)
        self.assertNotIn('skipLibCheck', script)

    def test_latest_fresh_build_revision(self):
        workflow=(ROOT/'.github/workflows/build-portableapps.yml').read_text(encoding='utf-8')
        self.assertIn('default: r7', workflow)
        self.assertIn('scripts/build_source.ps1', workflow)

    def test_b1r3_launcher_compiler_avoids_nested_windows_cmd_quoting(self):
        # Failure reproduced by user's b1r2 log: CMD split the Visual Studio path.
        script=(ROOT/'scripts/compile_launcher.ps1').read_text(encoding='utf-8')
        self.assertIn('Launch-VsDevShell.ps1',script)
        self.assertIn('-Arch amd64 -HostArch amd64 -SkipAutomaticLocation',script)
        self.assertIn("Get-Command 'cl.exe'",script)
        self.assertIn('& $cl.Source',script)
        self.assertIn('"/Fo:$obj"',script)
        self.assertIn('"/Fe:$out"',script)
        self.assertNotIn('cmd.exe /D /C',script)
        self.assertNotIn('compile-launcher.cmd',script)
        self.assertNotIn('Set-Content -LiteralPath $batch',script)
        self.assertNotIn('vcvars64.bat',script)

    def test_b1r3_launcher_compiler_checks_exit_arch_and_revision(self):
        script=(ROOT/'scripts/compile_launcher.ps1').read_text(encoding='utf-8')
        self.assertIn('$exitCode = $LASTEXITCODE',script)
        self.assertIn('if ($exitCode -ne 0)',script)
        self.assertIn('ReadUInt32() -ne 0x00004550',script)
        self.assertIn('ReadUInt16() -ne 0x8664',script)
        self.assertIn('user32.lib shell32.lib advapi32.lib',script)
        workflow=(ROOT/'.github/workflows/build-portableapps.yml').read_text(encoding='utf-8')
        self.assertIn('default: r7',workflow)
        self.assertIn('scripts/compile_launcher.ps1',workflow)

    def test_launcher_has_no_broad_delete(self):
        text=(ROOT/'launcher/GitHubDesktopPortable.cpp').read_text(encoding='utf-8')
        self.assertIn('GetModuleFileNameW', text)
        self.assertIn('CreateProcessW', text)
        self.assertIn('GIT_CONFIG_GLOBAL', text)
        self.assertNotIn('RegDeleteTree', text)
        self.assertNotIn('RemoveDirectoryW', text)
        self.assertNotIn('JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE',text)


    @staticmethod
    def make_upstream_fixture(base, version='3.6.11', *, drift=False):
        """Representative exact 3.6.11 API/source anchors inspected upstream.
        A fixture checks our patcher's behavior; it is NOT a full upstream build.
        """
        source = Path(base) / 'src'
        def write(relative, value):
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding='utf-8')
        write('app/package.json', json.dumps({
            'name':'desktop', 'productName':'GitHub Desktop',
            'version':version, 'license':'MIT'}))
        write('app/app-info.ts',
              "__OAUTH_CLIENT_ID__: s(process.env.DESKTOP_OAUTH_CLIENT_ID || devClientId),\n"
              "__OAUTH_SECRET__: s(\n        process.env.DESKTOP_OAUTH_CLIENT_SECRET || devClientSecret\n      ),\n"
              "__DEV_SECRETS__: isDevBuild || !process.env.DESKTOP_OAUTH_CLIENT_SECRET,\n")
        write('app/src/main-process/main.ts',
              "import '../lib/logging/main/install'\n"
              "const protocolLauncherArg = '--protocol-launcher'\n"
              "if (__DEV_SECRETS__) {\n  possibleProtocols.add('x-github-desktop-dev-auth')\n"
              "} else {\n  possibleProtocols.add('x-github-desktop-auth')\n" 
              "app.requestSingleInstanceLock()\n"
              "args['protocol-launcher'] === true\n"
              "  possibleProtocols.forEach(protocol => setAsDefaultProtocolClient(protocol))\n")
        write('app/src/main-process/app-window.ts',
              '    this.setupAutoUpdater()\n  public async checkForUpdates(url: string) {\n'
              '  public quitAndInstallUpdate() {\n    autoUpdater.quitAndInstall()\n')
        write('app/src/main-process/notifications.ts',
              '  windowsToastActivatorClsid = findToastActivatorClsid()\n'
              if not drift else '  windowsToastActivatorClsid = changedByUpstream()\n')
        write('script/build.ts', 'const isPublishableBuild = isPublishable()\n')
        return source

    def test_source_adapter_supports_stable_3610_and_3611(self):
        patcher = module('patch_source')
        for version in ('3.6.10', '3.6.11'):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as td:
                source = self.make_upstream_fixture(td, version)
                result = patcher.apply(source, ROOT/'patches')
                self.assertEqual(len(result), 8)
                patched=(source/'app/src/main-process/main.ts').read_text(encoding='utf-8')
                self.assertTrue(patched.startswith("import './portable-bootstrap'"))
                self.assertIn('if (!process.env.GHD_PORTABLE_ROOT)', patched)
                self.assertTrue((source/'app/src/main-process/portable-bootstrap.ts').exists())
                self.assertTrue(all(e['upstream_version'] == version for e in result))

    def test_version_resolver_numeric_order_without_3610_ceiling(self):
        resolver = module('resolve_release')
        original = resolver.get_json
        records = [
            {'tag_name':'release-3.6.9', 'prerelease':False, 'draft':False},
            {'tag_name':'release-3.6.10', 'prerelease':False, 'draft':False},
            {'tag_name':'release-3.6.11-beta1', 'prerelease':True, 'draft':False},
            {'tag_name':'release-3.6.11', 'prerelease':False, 'draft':False},
            {'tag_name':'release-3.6.12-rc1', 'prerelease':True, 'draft':False},
        ]
        resolver.get_json = lambda url: records
        try:
            result = resolver.resolve('latest')
            self.assertEqual(result['tag'], 'release-3.6.11')
        finally:
            resolver.get_json = original

    def test_source_drift_preflight_does_not_partially_patch_files(self):
        patcher = module('patch_source')
        with tempfile.TemporaryDirectory() as td:
            source = self.make_upstream_fixture(td, '3.6.11', drift=True)
            main = source/'app/src/main-process/main.ts'
            before = main.read_bytes()
            with self.assertRaisesRegex(RuntimeError, 'drift'):
                patcher.apply(source, ROOT/'patches')
            self.assertEqual(main.read_bytes(), before)
            self.assertFalse((source/'app/src/main-process/portable-bootstrap.ts').exists())

    def test_future_structurally_compatible_stable_can_patch_but_oauth_drift_stops(self):
        patcher = module('patch_source')
        with tempfile.TemporaryDirectory() as td:
            source = self.make_upstream_fixture(td, '3.7.0')
            result = patcher.apply(source, ROOT/'patches')
            self.assertEqual(len(result), 8)
        with tempfile.TemporaryDirectory() as td:
            source = self.make_upstream_fixture(td, '3.7.0')
            app_info=source/'app/app-info.ts'
            app_info.write_text(app_info.read_text(encoding='utf-8').replace(
                '__DEV_SECRETS__:', '__DEV_SECRETS_NEW__:'),encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'OAuth contract changed'):
                patcher.apply(source,ROOT/'patches')

    def test_3611_dynamic_resolver_patcher_and_untouched_61_launcher(self):
        workflow=(ROOT/'.github/workflows/build-portableapps.yml').read_text(encoding='utf-8')
        self.assertNotIn('--adapter-max',workflow)
        self.assertIn('default: r7',workflow)
        resolver=(ROOT/'scripts/resolve_release.py').read_text(encoding='utf-8')
        self.assertNotIn('adapter_max',resolver)
        patch=(ROOT/'scripts/patch_source.py').read_text(encoding='utf-8')
        self.assertIn('check_source_contract',patch)
        self.assertIn('before mutating ANY source',patch)
        launcher=(ROOT/'launcher/GitHubDesktopPortable.cpp').read_text(encoding='utf-8')
        self.assertIn('x-github-desktop-dev-auth://',launcher)

    def test_package_appid_unique(self):
        s=module('stage')
        self.assertEqual(s.APP_ID, 'GitHubDesktopPortableVhick')


    def test_b1r4_opt_in_reversible_callback_is_bounded(self):
        launcher = (ROOT/'launcher/GitHubDesktopPortable.cpp').read_text(encoding='utf-8')
        guard = (ROOT/'launcher/AuthProtocolGuard.cpp').read_text(encoding='utf-8')
        self.assertIn('x-github-desktop-auth', launcher)
        self.assertIn('MB_YESNOCANCEL', launcher)
        self.assertIn('AuthRedirectConsent.txt', launcher)
        self.assertIn('AuthProtocolRecovery.bin', launcher)
        self.assertIn('--protocol-launcher', launcher)
        self.assertIn('isCallback(args)', launcher)
        self.assertNotIn('WaitForSingleObject(job, INFINITE)', launcher)
        self.assertIn('WaitForJobProcessesToExit(job)', launcher)
        self.assertIn('RegSetValueExW', guard)
        self.assertIn('RegDeleteValueW', guard)
        self.assertIn('s.ownedCommand', guard)
        self.assertIn('MOVEFILE_WRITE_THROUGH', guard)
        self.assertIn('RegQueryInfoKeyW', guard)
        self.assertNotIn('HKEY_LOCAL_MACHINE', guard)
        self.assertNotIn('RegDeleteTree', guard)
        self.assertNotIn('TerminateProcess(pi.hProcess)', guard)

    def test_b1r4_win_fixture_and_compiler(self):
        compiler = (ROOT/'scripts/compile_launcher.ps1').read_text(encoding='utf-8')
        test_src = (ROOT/'tests/auth_guard_fixture.cpp').read_text(encoding='utf-8')
        self.assertIn('launcher/AuthProtocolGuard.cpp', compiler)
        self.assertIn('tests/auth_guard_fixture.cpp', compiler)
        self.assertIn('AUTOMATED-RUNTIME-TESTED', compiler)
        self.assertIn('x-vhick-auth-guard-fixture-', test_src)
        self.assertNotIn('x-github-desktop-auth', test_src)
        self.assertIn('regRoot(scheme)', test_src)
        self.assertIn('guard.restore(reason)', test_src)
        self.assertIn('guard.recover(reason)', test_src)

    def test_b1r5_job_wait_and_callback_detach(self):
        source = (ROOT/'launcher/GitHubDesktopPortable.cpp').read_text(encoding='utf-8')
        lifecycle = (ROOT/'launcher/ProcessLifecycle.h').read_text(encoding='utf-8')
        self.assertNotIn('WaitForSingleObject(job, INFINITE)', source)
        self.assertIn('QueryInformationJobObject(job, JobObjectBasicAccountingInformation', lifecycle)
        self.assertIn('counts.ActiveProcesses == 0', lifecycle)
        self.assertIn('GetTickCount64()', lifecycle)
        self.assertIn('if (callback) {', source)
        self.assertIn('CALLBACK INVOKED:', source)
        self.assertIn('AUTH HANDLER ACTIVE:', source)
        self.assertIn('if (!callback) {', source)
        self.assertIn('auth->abandonForRecovery()', source)
        callback_start = source.index('if (callback) {\n      if (!CreateProcessW')
        callback_end = source.index('\n\n    if (!CreateProcessW', callback_start)
        callback_code = source[callback_start:callback_end]
        self.assertIn('CloseHandle(pi.hProcess);', callback_code)
        self.assertIn('return 0;', callback_code)
        self.assertNotIn('WaitForSingleObject', callback_code)
        self.assertNotIn('AssignProcessToJobObject', callback_code)
        self.assertNotIn('lock.lock()', callback_code)

    def test_b1r5_windows_fixture_and_compiler(self):
        fixture = (ROOT/'tests/process_lifecycle_fixture.cpp').read_text(encoding='utf-8')
        compiler = (ROOT/'scripts/compile_launcher.ps1').read_text(encoding='utf-8')
        self.assertIn('--fixture-grandchild', fixture)
        self.assertIn('AssignProcessToJobObject(job, p.hProcess)', fixture)
        self.assertIn('counts.ActiveProcesses >= 1', fixture)
        self.assertIn('WaitForJobProcessesToExit(job, 50, 10000)', fixture)
        self.assertIn('tests/process_lifecycle_fixture.cpp', compiler)
        self.assertIn('& $lifecycleFixture', compiler)
        self.assertIn('AUTOMATED-RUNTIME-TESTED (Windows, isolated job fixture)', compiler)

    def test_b1r6_oauth_scheme_matches_upstream_public_dev_client(self):
        # Upstream release-3.6.10 app/app-info.ts:
        # __DEV_SECRETS__=isDevBuild || !process.env.DESKTOP_OAUTH_CLIENT_SECRET
        # => community source build expects x-github-desktop-dev-auth.
        launcher=(ROOT/'launcher/GitHubDesktopPortable.cpp').read_text(encoding='utf-8')
        guard=(ROOT/'launcher/AuthProtocolGuard.cpp').read_text(encoding='utf-8')
        build=(ROOT/'scripts/build_source.ps1').read_text(encoding='utf-8')
        stage=(ROOT/'scripts/stage.py').read_text(encoding='utf-8')
        self.assertIn('x-github-desktop-dev-auth://', launcher)
        self.assertIn('AuthDevProtocolRecovery.bin', launcher)
        self.assertIn('L"x-github-desktop-dev-auth"', launcher)
        self.assertIn('L"x-github-desktop-dev-auth"', guard)
        self.assertIn('DESKTOP_OAUTH_CLIENT_SECRET', build)
        self.assertIn("This builder requires upstream public development OAuth credentials", build)
        self.assertIn("if 'x-github-desktop-dev-auth' not in compiled_text:", stage)
        self.assertIn('Source build OAuth protocol mismatch', stage)
        # Built callback branch must reject production URL arguments.
        callback_branch=launcher[launcher.index('static bool isCallback'):launcher.index('struct MutexLock')]
        self.assertIn('x-github-desktop-dev-auth://', callback_branch)
        self.assertNotIn('L"x-github-desktop-auth://"', callback_branch)

    def test_b1r6_legacy_and_current_auth_journals_are_separate(self):
        src=(ROOT/'launcher/GitHubDesktopPortable.cpp').read_text(encoding='utf-8')
        old=src.index('AuthProtocolGuard legacy(L"x-github-desktop-auth"')
        recovery=src.index('if (!legacy.recover(legacyRecovery))', old)
        newer=src.index('L"x-github-desktop-dev-auth", journal', recovery)
        self.assertLess(old, recovery)
        self.assertLess(recovery, newer)
        self.assertIn('AuthProtocolRecovery.bin',src)
        self.assertIn('AuthDevProtocolRecovery.bin',src)
        self.assertIn('return 19;',src)
        self.assertIn('AUTH HANDLER ACTIVE: x-github-desktop-dev-auth',src)

    def test_b1r6_read_only_auth_diagnostic(self):
        ps=(ROOT/'scripts/diagnose_auth.ps1').read_text(encoding='utf-8')
        self.assertIn('x-github-desktop-dev-auth', ps)
        self.assertIn('Registry::HKEY_CLASSES_ROOT',ps)
        self.assertIn('Current-user command matches this root launcher',ps)
        self.assertIn('Effective HKCR command matches this root launcher',ps)
        self.assertIn('Windows UserChoice exists for scheme',ps)
        self.assertNotIn('Set-ItemProperty',ps)
        self.assertNotIn('New-ItemProperty',ps)
        self.assertNotIn('Remove-ItemProperty',ps)
        self.assertNotIn('RegSetValueExW',ps)
        stage=(ROOT/'scripts/stage.py').read_text(encoding='utf-8')
        self.assertIn('Diagnose-Browser-SignIn.cmd',stage)
        self.assertIn('Diagnose-Browser-SignIn.ps1',stage)

    def test_b1r6_docs_and_workflow_revision(self):
        workflow=(ROOT/'.github/workflows/build-portableapps.yml').read_text(encoding='utf-8')
        self.assertIn('default: r7',workflow)
        self.assertIn('build_source.ps1',workflow)
        release=(ROOT/'docs/RELEASE-NOTES-b1r6.md').read_text(encoding='utf-8')
        self.assertIn('__DEV_SECRETS__',release)
        self.assertIn('x-github-desktop-dev-auth',release)
        readme=(ROOT/'README.md').read_text(encoding='utf-8')
        self.assertIn('b1r6 correction',readme)

    def test_b1r4_profile_and_protocol_source_patch_remain_isolated(self):
        patch = (ROOT/'scripts/patch_source.py').read_text(encoding='utf-8')
        self.assertIn('if (!process.env.GHD_PORTABLE_ROOT)', patch)
        self.assertIn('possibleProtocols.forEach(protocol => setAsDefaultProtocolClient(protocol))', patch)
        self.assertIn('setupAutoUpdater()', patch)
        stage = (ROOT/'scripts/stage.py').read_text(encoding='utf-8')
        self.assertIn('Configure-Browser-SignIn.cmd', stage)
        self.assertIn('AuthProtocolRecovery.bin', stage)

if __name__ == '__main__': unittest.main()

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

    def test_b1r2_fresh_build_revision(self):
        workflow=(ROOT/'.github/workflows/build-portableapps.yml').read_text(encoding='utf-8')
        self.assertIn('default: r2', workflow)
        self.assertIn('scripts/build_source.ps1', workflow)

    def test_launcher_has_no_broad_delete(self):
        text=(ROOT/'launcher/GitHubDesktopPortable.cpp').read_text(encoding='utf-8')
        self.assertIn('GetModuleFileNameW', text)
        self.assertIn('CreateProcessW', text)
        self.assertIn('GIT_CONFIG_GLOBAL', text)
        self.assertNotIn('RegDeleteTree', text)
        self.assertNotIn('RemoveDirectoryW', text)
        self.assertNotIn('JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE',text)


    def test_source_adapter_applies_expected_3610_anchors(self):
        patcher = module('patch_source')
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / 'src'
            def write(relative, value):
                path = source / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value, encoding='utf-8')
            write('app/package.json', '{"version":"3.6.10"}')
            write('app/src/main-process/main.ts',
                  "import '../lib/logging/main/install'\n  possibleProtocols.forEach(protocol => setAsDefaultProtocolClient(protocol))\n")
            write('app/src/main-process/app-window.ts',
                  '    this.setupAutoUpdater()\n  public async checkForUpdates(url: string) {\n'
                  '  public quitAndInstallUpdate() {\n    autoUpdater.quitAndInstall()\n')
            write('app/src/main-process/notifications.ts',
                  '  windowsToastActivatorClsid = findToastActivatorClsid()\n')
            write('script/build.ts', 'const isPublishableBuild = isPublishable()\n')
            result=patcher.apply(source, ROOT/'patches')
            self.assertEqual(len(result), 8)
            patched=(source/'app/src/main-process/main.ts').read_text(encoding='utf-8')
            self.assertTrue(patched.startswith("import './portable-bootstrap'"))
            self.assertIn('if (!process.env.GHD_PORTABLE_ROOT)', patched)
            self.assertTrue((source/'app/src/main-process/portable-bootstrap.ts').exists())

    def test_version_resolver_numeric_order_and_adapter_ceiling(self):
        resolver = module('resolve_release')
        initial = resolver.get_json
        records = [
            {'tag_name':'release-3.6.9', 'prerelease':False, 'draft':False},
            {'tag_name':'release-3.6.10-beta1', 'prerelease':True, 'draft':False},
            {'tag_name':'release-3.6.10', 'prerelease':False, 'draft':False},
            {'tag_name':'release-3.7.0', 'prerelease':False, 'draft':False},
        ]
        resolver.get_json = lambda url: records
        try:
            result = resolver.resolve('latest','3.6.10')
            self.assertEqual(result['tag'], 'release-3.6.10')
        finally:
            resolver.get_json = initial
    def test_package_appid_unique(self):
        s=module('stage')
        self.assertEqual(s.APP_ID, 'GitHubDesktopPortableVhick')

if __name__ == '__main__': unittest.main()

import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import io
from unittest.mock import patch

import release_modules as release
from build_registry import module_notices

class ModuleReleaseTests(unittest.TestCase):
    def test_archives_are_reproducible_flat_and_reject_escaping_paths(self):
        files = [('module.json', b'{}'), ('LICENSE', b'license')]
        data = release.archive(files)
        self.assertEqual(data, release.archive(list(reversed(files))))
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            self.assertEqual(package.read('LICENSE'), b'license')
        for name in ['../escape', '/escape', 'C:/escape', 'nested\\escape']:
            with self.assertRaises(ValueError):
                release.archive([(name, b'no')])

    def test_catalog_has_complete_legal_material_and_matching_hashes(self):
        index = release.verify_registry(release.ROOT / 'registry')
        self.assertEqual(len(index['modules']), 17)
        self.assertTrue(all(m['min_ide'] == '1.1.0' and m['archive']['url'].startswith('https://github.com/sherhn/Light-Modules/releases/download/') for m in index['modules']))

    def test_html_attribution_is_bundled(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module_notices({'id': 'html'}, root)
            self.assertIn('HTML5 Logo by W3C', (root / 'THIRD_PARTY_NOTICES.md').read_text())
            self.assertTrue((root / 'HTML5-CC-BY-3.0.txt').is_file())

    def test_modified_payload_is_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'registry'
            shutil.copytree(release.ROOT / 'registry', target)
            (target / 'modules/python/LICENSE').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                release.verify_registry(target)


    def test_python_functions_keep_import_state_sibling_imports_async_and_main_guard(self):
        import shlex, subprocess, sys
        module = json.loads((release.ROOT / 'registry/modules/python/module.json').read_text(encoding='utf-8'))
        code = shlex.split(module['code_actions'][0]['command'])[2]
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'code space пример'
            folder.mkdir()
            (folder / 'sibling.py').write_text('VALUE = 42\n')
            source = folder / 'source.py'
            source.write_text('from dataclasses import dataclass\nfrom sibling import VALUE\n@dataclass\nclass Value:\n    number: int = VALUE\ndef ping():\n    print("SYNC-FUNCTION", Value().number)\nasync def async_ping():\n    print("ASYNC-FUNCTION")\nif __name__ == "__main__":\n    print("MUST-NOT-RUN")\n')
            for function, expected in [('ping', 'SYNC-FUNCTION 42'), ('async_ping', 'ASYNC-FUNCTION')]:
                result = subprocess.run([sys.executable, '-c', code, str(source), function], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(expected, result.stdout)
                self.assertNotIn('MUST-NOT-RUN', result.stdout)
                self.assertFalse((folder / '__pycache__').exists())

    def test_javascript_exported_functions_work_in_esm_and_commonjs(self):
        import shlex, shutil, subprocess
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is not installed')
        module = json.loads((release.ROOT / 'registry/modules/javascript/module.json').read_text(encoding='utf-8'))
        code = shlex.split(module['code_actions'][0]['command'])[3]
        with tempfile.TemporaryDirectory() as temporary:
            for extension, content in [('mjs', "export async function ping() { console.log('ESM-FUNCTION'); }"), ('cjs', "exports.ping = () => console.log('CJS-FUNCTION');")]:
                source = Path(temporary) / ('code ~ # % пример.' + extension)
                source.write_text(content)
                result = subprocess.run([node, '--input-type=module', '-e', code, str(source), 'ping'], capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('FUNCTION', result.stdout)

if __name__ == '__main__':
    unittest.main()

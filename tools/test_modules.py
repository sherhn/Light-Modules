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

if __name__ == '__main__':
    unittest.main()

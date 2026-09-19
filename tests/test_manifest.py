import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'manifest', Path(__file__).resolve().parents[1] / 'scripts/check-manifest.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ManifestTest(unittest.TestCase):
    def valid(self):
        return dict(schemaVersion=1, releaseId='test-1', datasheets='datasheets-test-1.xtf',
                    catalog=None, duckdb='catalog-test-1.duckdb')

    def test_empty_catalog_still_requires_duckdb(self):
        module.validate(self.valid())
        manifest = self.valid()
        del manifest['duckdb']
        with self.assertRaises(ValueError):
            module.validate(manifest)

    def test_rejects_external_and_mixed_release_references(self):
        for path in ('https://other.example/catalog.duckdb', '../catalog.duckdb', 'catalog-old.duckdb'):
            manifest = self.valid()
            manifest['duckdb'] = path
            with self.assertRaises(ValueError):
                module.validate(manifest)

    def test_rejects_non_object_and_boolean_schema(self):
        for value in ([], None, dict(self.valid(), schemaVersion=True)):
            with self.assertRaises(ValueError):
                module.validate(value)


if __name__ == '__main__':
    unittest.main()

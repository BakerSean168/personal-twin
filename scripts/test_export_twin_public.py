from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).with_name("export_twin_public.py")
spec = importlib.util.spec_from_file_location("export_twin_public", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TwinPublicProjectionTests(unittest.TestCase):
    def test_current_public_catalog_is_explicit_and_empty(self):
        projection = module.build_projection()
        self.assertEqual(projection["payload"]["spaces"], [])
        self.assertEqual(projection["payload"]["bodyProfiles"], [])
        self.assertEqual(projection["payload"]["furnitureLayouts"], [])
        self.assertEqual(projection["payload"]["assets"], [])

    def test_public_path_cannot_escape_public_boundary(self):
        with self.assertRaisesRegex(module.ProjectionError, "escapes exports/public"):
            module.safe_public_path("../../data/private/body.json")

    def test_exporter_never_discovers_unlisted_files(self):
        with tempfile.TemporaryDirectory() as raw:
            public_root = Path(raw)
            (public_root / "unlisted.json").write_text('{"secret": true}', encoding="utf-8")
            with mock.patch.object(module, "PUBLIC_ROOT", public_root), mock.patch.object(
                module, "CATALOG_PATH", public_root / "catalog.json"
            ):
                (public_root / "catalog.json").write_text(
                    '{"schemaVersion":1,"spaces":[],"bodyProfiles":[],"furnitureLayouts":[],"assets":[]}',
                    encoding="utf-8",
                )
                self.assertEqual(module.listed_assets(module.load_json(public_root / "catalog.json")), [])


if __name__ == "__main__":
    unittest.main()

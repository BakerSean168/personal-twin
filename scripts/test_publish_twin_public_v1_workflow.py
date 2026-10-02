from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-twin-public-v1.yml"
VALIDATE = ROOT / ".github" / "workflows" / "validate.yml"


class TwinPublicV1WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.validate = VALIDATE.read_text(encoding="utf-8")

    def test_publication_is_explicit_only(self) -> None:
        self.assertIn("workflow_dispatch:", self.workflow)
        self.assertNotIn("push:", self.workflow)
        self.assertNotIn("pull_request:", self.workflow)

    def test_validation_avoids_duplicate_feature_branch_runs(self) -> None:
        self.assertIn("push:\n    branches: [main]", self.validate)
        self.assertIn("pull_request:\n    branches: [main]", self.validate)

    def test_main_validation_still_proves_public_boundary(self) -> None:
        for expected in (
            "scripts/test_export_twin_public.py",
            "scripts/test_publish_twin_public_v1_workflow.py",
            "scripts/export_twin_public.py",
            "scripts/verify_twin_public.py",
        ):
            self.assertIn(expected, self.validate)

    def test_manual_publication_keeps_contract_verification(self) -> None:
        self.assertIn("python3 scripts/validate_json.py", self.workflow)
        self.assertIn("python3 scripts/export_twin_public.py", self.workflow)
        self.assertIn("python3 scripts/verify_twin_public.py", self.workflow)
        self.assertIn("generated/twin-public-v1.json", self.workflow)
        self.assertIn("generated/twin-public-v1.manifest.json", self.workflow)


if __name__ == "__main__":
    unittest.main()

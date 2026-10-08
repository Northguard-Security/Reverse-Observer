"""Offline artifact-integrity tests. No packets are transmitted or captured."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tools.evidence_manifest import build_manifest, verify_manifest


class EvidenceManifestTests(unittest.TestCase):
    def test_create_and_verify_local_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "control.bin").write_bytes(b"controlled synthetic capture")
            manifest = build_manifest("controlled-lab-001", ["control.bin"], base)
            self.assertEqual(manifest["analyst_status"], "unverified")
            self.assertEqual(manifest["status_basis"], "analyst_supplied_not_automatically_validated")
            self.assertEqual(manifest["artifacts"][0]["sha256"], hashlib.sha256(b"controlled synthetic capture").hexdigest())
            self.assertEqual(verify_manifest(manifest, base), 1)
            self.assertEqual(json.loads(json.dumps(manifest))["experiment_id"], "controlled-lab-001")

    def test_tampered_artifact_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            path = base / "test.bin"
            path.write_bytes(b"before")
            record = build_manifest("test-tamper", ["test.bin"], base)
            path.write_bytes(b"after")
            with self.assertRaisesRegex(ValueError, "Evidence mismatch"):
                verify_manifest(record, base)

    def test_missing_or_outside_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for name in ("missing.bin", "../other.bin", "/tmp/example.bin"):
                with self.subTest(name=name):
                    with self.assertRaises(ValueError):
                        build_manifest("test-paths", [name], base)

    def test_duplicate_paths_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "x.bin").write_bytes(b"x")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                build_manifest("test-duplicate", ["x.bin", "x.bin"], base)

    def test_wrong_manifest_version_is_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "Unknown"):
                verify_manifest({"format": "unknown", "artifacts": []}, Path(temporary))


if __name__ == "__main__":
    unittest.main()

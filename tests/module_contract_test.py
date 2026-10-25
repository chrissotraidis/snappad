import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import module_contract as contract


class ModuleContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="SnapPad contract spaces ")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.patch_root = mock.patch.object(contract, "ROOT", self.root)
        self.patch_root.start(); self.addCleanup(self.patch_root.stop)
        for command in (("init", "-q"), ("config", "user.email", "test@example.invalid"),
                        ("config", "user.name", "Synthetic test")):
            self.git(*command)
        (self.source / "header.h").write_bytes(b"original header\n")
        self.git("add", "."); self.git("commit", "-qm", "synthetic source")
        self.commit = self.git("rev-parse", "HEAD").decode().strip()
        (self.root / "dependencies.lock.json").write_text(json.dumps({"sources": {
            "paperMarioReCut": {"commit": self.commit}}}))

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], stderr=subprocess.PIPE)

    def test_known_patch_verification_preserves_source_and_original_index(self):
        patch = self.root / "port/patches/n64recomp/reviewed.patch"
        patch.parent.mkdir(parents=True)
        patch.write_bytes(b"--- a/header.h\n+++ b/header.h\n@@ -1 +1 @@\n-original header\n+reviewed header\n")
        self.git("apply", str(patch))
        before = (self.source / ".git/index").read_bytes()
        reviewed = (self.source / "header.h").read_bytes()
        self.assertTrue(contract.same_source_bytes(reviewed, b"reviewed header\n"))
        contract.verify_source(self.source)
        self.assertEqual(before, (self.source / ".git/index").read_bytes())
        self.assertEqual((self.source / "header.h").read_bytes(), reviewed)
        (self.source / "header.h").write_bytes(b"unrelated local edit\n")
        with self.assertRaisesRegex(ValueError, "unreviewed source changes"):
            contract.verify_source(self.source)
        self.assertEqual(before, (self.source / ".git/index").read_bytes())
        self.assertEqual((self.source / "header.h").read_bytes(), b"unrelated local edit\n")

    def test_missing_reviewed_patch_and_wrong_revision_are_rejected(self):
        patch = self.root / "port/patches/n64recomp/reviewed.patch"
        patch.parent.mkdir(parents=True)
        patch.write_bytes(b"--- a/header.h\n+++ b/header.h\n@@ -1 +1 @@\n-original header\n+reviewed header\n")
        with self.assertRaisesRegex(ValueError, "unreviewed source changes"):
            contract.verify_source(self.source)
        self.git("commit", "--allow-empty", "-qm", "different source pin")
        with self.assertRaisesRegex(ValueError, "different revision"):
            contract.verify_source(self.source)
        self.assertEqual((self.source / "header.h").read_bytes(), b"original header\n")

    def test_reviewed_patch_addition_is_verified_without_staging_it(self):
        patch = self.root / "port/patches/n64recomp/reviewed.patch"
        patch.parent.mkdir(parents=True)
        patch.write_bytes(b"--- /dev/null\n+++ b/added.h\n@@ -0,0 +1 @@\n+reviewed addition\n")
        self.git("apply", str(patch))
        before = (self.source / ".git/index").read_bytes()
        contract.verify_source(self.source)
        self.assertEqual(before, (self.source / ".git/index").read_bytes())
        self.assertEqual(self.git("ls-files", "--others", "--exclude-standard").strip(), b"added.h")
        (self.source / "added.h").write_bytes(b"unexpected added header contents\n")
        with self.assertRaisesRegex(ValueError, "unreviewed source changes"):
            contract.verify_source(self.source)
        self.assertEqual(before, (self.source / ".git/index").read_bytes())

    def test_checkout_line_endings_are_allowed_only_for_text(self):
        self.assertTrue(contract.same_source_bytes(b"header\r\n", b"header\n"))
        self.assertFalse(contract.same_source_bytes(b"binary\0\r\n", b"binary\0\n"))
        (self.source / "header.h").write_bytes(b"original header\r\n")
        contract.verify_source(self.source)

    def test_windows_patch_checkout_uses_same_reviewed_bytes(self):
        patch = self.root / "port/patches/n64recomp/reviewed.patch"
        patch.parent.mkdir(parents=True)
        patch.write_bytes(b"--- a/header.h\r\n+++ b/header.h\r\n@@ -1 +1 @@\r\n-original header\r\n+reviewed header\r\n")
        (self.source / "header.h").write_bytes(b"reviewed header\r\n")
        before = (self.source / ".git/index").read_bytes()
        contract.verify_source(self.source)
        self.assertEqual(before, (self.source / ".git/index").read_bytes())
        self.assertIn(b"\r\n", patch.read_bytes())

    def test_untracked_header_is_refused_without_changing_source_or_index(self):
        unexpected = self.source / "unexpected.h"
        unexpected.write_bytes(b"unreviewed header\n")
        before = (self.source / ".git/index").read_bytes()
        with self.assertRaisesRegex(ValueError, "unreviewed source files.*unexpected.h"):
            contract.verify_source(self.source)
        self.assertEqual(unexpected.read_bytes(), b"unreviewed header\n")
        self.assertEqual(before, (self.source / ".git/index").read_bytes())
        unexpected.unlink()
        (self.source / ".git/info/exclude").write_text("build/\n")
        (self.source / "build").mkdir()
        (self.source / "build/object.o").write_bytes(b"ignored synthetic output")
        contract.verify_source(self.source)

    def test_full_input_record_detects_overlay_headers_and_added_files(self):
        generated = self.root / "private generated"
        (generated / "aot").mkdir(parents=True)
        (generated / "evidence").mkdir()
        overlay = generated / "aot/recomp_overlays.inl"
        overlay.write_text("// synthetic overlay table\n")
        (generated / "aot/fixture.c").write_text("int synthetic(void) { return 1; }\n")
        (generated / "evidence/G2-generation.json").write_text("{}\n")
        record = self.root / "inputs.json"
        with mock.patch.object(contract, "verify_source"), mock.patch.object(contract, "verify_generated"), \
                mock.patch.object(contract, "identity", return_value="test-contract"):
            record.write_text(json.dumps(contract.input_record(generated, self.source)))
            contract.verify_inputs(generated, self.source, record)
            before = record.read_bytes()
            overlay.write_text("// changed overlay table\n")
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                contract.verify_inputs(generated, self.source, record)
            self.assertEqual(record.read_bytes(), before)
            overlay.write_text("// synthetic overlay table\n")
            (generated / "aot/extra.c").write_text("int unexpected;\n")
            with self.assertRaisesRegex(ValueError, "inputs changed"):
                contract.verify_inputs(generated, self.source, record)

    def test_host_manifest_changes_identity_with_normalized_line_endings(self):
        script = self.root / "scripts/module_contract.py"
        script.parent.mkdir(); script.write_bytes(b"# synthetic verifier\n")
        (self.root / "CMakeLists.txt").write_bytes(b"# synthetic project\n")
        manifest = self.root / "cmake/host-tools/windows-utf8.manifest"
        manifest.parent.mkdir(parents=True)
        manifest.write_bytes(b"<activeCodePage>UTF-8</activeCodePage>\n")
        with mock.patch.object(contract, "__file__", str(script)):
            original = contract.identity()
            manifest.write_bytes(b"<activeCodePage>UTF-8</activeCodePage>\r\n")
            self.assertEqual(original, contract.identity())
            manifest.write_bytes(b"<activeCodePage>Legacy</activeCodePage>\n")
            self.assertNotEqual(original, contract.identity())


if __name__ == "__main__":
    unittest.main()

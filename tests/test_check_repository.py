"""Exercise the CLI against small, disposable repositories with invented data."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "tools" / "check_repository.py"


class RepositoryCheckTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "repo"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("commit", "-qm", "Initial fixture", "--allow-empty")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def track(self, path, content):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.git("add", "--", path)

    def check(self, expected, cwd=None):
        run = subprocess.run([sys.executable, "-I", str(CHECKER)], cwd=cwd or self.root, capture_output=True, text=True)
        self.assertEqual(run.returncode, expected, run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        return json.loads(run.stdout), run.stderr

    def test_configuration_errors_do_not_quote_input(self):
        marker = "invented-diagnostic-marker"
        self.track("sample.ini", marker + "\n")
        self.track("sample.json", '{\n  "' + marker + '" 42\n}')
        self.track("sample.yml", "valid: true\n---\nvalue: [" + marker + "\n")
        self.track("sample.py", "if " + marker + ":\n")
        _, log = self.check(1)
        self.assertNotIn(marker, log)
        self.assertIn("sample.ini: configuration error at line 1", log)
        self.assertIn("sample.json: configuration error at line 2", log)
        self.assertIn("sample.yml: configuration error at line", log)
        self.assertIn("sample.py: Python syntax error at line 1", log)

    def test_skill_uses_yaml_types_and_allows_trailing_delimiter_space(self):
        entry = "skills/sample/SKILL.md"
        self.track(entry, "---\nname: sample\ndescription: >\n  first line\n  second line\n---  \nBody\n")
        counts, _ = self.check(0)
        self.assertEqual(counts["skill_entries"], 1)
        for value in ("false", "['list']", "'  '", "[unclosed"):
            with self.subTest(value=value):
                self.track(entry, f"---\nname: sample\ndescription: {value}\n---\n")
                _, log = self.check(1)
                self.assertIn(entry + ": configuration error", log)

    def test_normalized_sibling_collisions_in_index_and_deleted_tree(self):
        self.track("Docs/a", "one")
        self.track("docs/b", "two")
        self.track("Ｆoo", "three")
        self.track("foo/child", "four")
        _, log = self.check(1)
        self.assertIn("index entry", log)
        self.assertGreaterEqual(log.count("case/Unicode path collision"), 2)
        self.git("commit", "-qm", "Record conflicting spellings")
        self.git("rm", "-qr", "Docs", "docs", "Ｆoo", "foo")
        self.git("commit", "-qm", "Remove fixture")
        _, log = self.check(1)
        self.assertIn("tree ", log)
        self.assertEqual(log.count("case/Unicode path collision"), 2)

    def test_history_scans_deleted_files_and_all_restored_rules(self):
        samples = {
            "signed URL": "?sig=" + "invented-value",
            "bearer credential": "Bearer " + "invented-example-value",
            "session cookie": "Cookie: " + "session=" + "invented-example",
            "contact address": "sample" + "@" + "fixture.test",
            "personal identifier": "139" + "0" * 8,
        }
        self.track("old.txt", "\n".join(samples.values()))
        self.git("commit", "-qm", "Record invented fixtures")
        self.git("rm", "-q", "old.txt")
        self.git("commit", "-qm", "Remove fixtures")
        counts, log = self.check(1)
        self.assertEqual(counts["tracked"], 0)
        for category, value in samples.items():
            self.assertIn(category, log)
            self.assertNotIn(value, log)

    def test_only_identity_headers_are_exempt_from_contact_rule(self):
        mailbox = "fixture" + "@" + "metadata.test"
        self.git("config", "user.email", mailbox)
        self.git("commit", "--allow-empty", "-qm", "Plain message")
        self.check(0)
        self.git("switch", "-qc", "other")
        self.git("commit", "--allow-empty", "-qm", "Message includes " + mailbox)
        self.git("tag", "-a", "fixture-tag", "-m", "Tag includes " + mailbox)
        self.git("switch", "-q", "main")
        counts, log = self.check(1)
        self.assertEqual(counts["tag"], 1)
        self.assertIn("commit ", log)
        self.assertIn("tag ", log)
        self.assertEqual(log.count("contact address"), 2)
        self.assertNotIn(mailbox, log)

    def test_coauthored_by_trailer_is_exempt_from_contact_rule(self):
        coauthor = "12345+dev" + "@" + "users.noreply.github.com"
        self.git(
            "commit", "--allow-empty", "-qm",
            "Squash PR (#2)\n\nCo-authored-by: Dev <" + coauthor + ">",
        )
        self.check(0)
        leaked = "private" + "@" + "fixture.test"
        self.git(
            "commit", "--allow-empty", "-qm",
            "Squash PR (#3)\n\nCo-authored-by: Dev <" + coauthor + "> " + leaked,
        )
        _, log = self.check(1)
        self.assertIn("contact address", log)
        self.assertNotIn(leaked, log)

    def test_signed_query_parameters(self):
        keys = ("x-amz-signature", "X-Amz-Credential", "X-Goog-Signature", "SIG", "access_token", "auth_token")
        for key in keys:
            with self.subTest(key=key):
                self.track("query.txt", f"?page=1&{key}=" + "x" * 8)
                _, log = self.check(1)
                self.assertIn("query.txt: signed URL", log)
        self.track("query.txt", "?page=1&format=plaintext")
        self.check(0)

    def test_private_path_is_redacted(self):
        path = "sample" + "@" + "fixture.test"
        self.track(path, "sample")
        _, log = self.check(1)
        self.assertIn("index entry 1: contact address", log)
        self.assertNotIn(path, log)

    def test_shallow_checkout_is_reported(self):
        clone = self.root.parent / "clone"
        self.git("clone", "-q", "--depth=1", self.root.as_uri(), str(clone))
        _, log = self.check(1, cwd=clone)
        self.assertIn("shallow checkout", log)

    def test_workspace_requires_matching_manifest_pair(self):
        self.track("workspace/package.json", '{"dependencies":{"fixture":"1"}}')
        _, log = self.check(1)
        self.assertIn("must both be present", log)
        self.track("workspace/package-lock.json", '{"packages":{"":{"dependencies":{}}}}')
        _, log = self.check(1)
        self.assertIn("out of sync", log)
        self.track("workspace/package-lock.json", '{"packages":{"":{"dependencies":{"fixture":"1"}}}}')
        self.check(0)

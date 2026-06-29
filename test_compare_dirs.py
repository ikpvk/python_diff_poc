import json
import tempfile
import unittest
from pathlib import Path

from compare_dirs import (
    _strip_noise,
    _noise_deep_eq,
    _norm_path,
    json_tree_diff,
    compare_dirs,
    walk_all,
)


class TestStripNoise(unittest.TestCase):

    def test_exact_match(self):
        self.assertEqual(_strip_noise("xyz", "xyz"), "")

    def test_no_match(self):
        self.assertEqual(_strip_noise("hello", "xyz"), "hello")

    def test_prefix(self):
        self.assertEqual(_strip_noise("xyz-foo", "xyz"), "foo")

    def test_suffix(self):
        self.assertEqual(_strip_noise("foo-xyz", "xyz"), "foo")

    def test_infix_middle(self):
        self.assertEqual(_strip_noise("foo-xyz-bar", "xyz"), "foo-bar")

    def test_infix_at_end(self):
        self.assertEqual(_strip_noise("foo-xyz-", "xyz"), "foo")

    def test_infix_at_start(self):
        self.assertEqual(_strip_noise("-xyz-foo", "xyz"), "foo")

    def test_prefix_and_suffix(self):
        self.assertEqual(_strip_noise("xyz-foo-xyz", "xyz"), "foo")

    def test_double_infix(self):
        self.assertEqual(_strip_noise("a-xyz-b-xyz", "xyz"), "a-b")

    def test_empty_noise(self):
        self.assertEqual(_strip_noise("hello", ""), "hello")

    def test_none_noise(self):
        self.assertEqual(_strip_noise("hello", None), "hello")

    def test_non_string_input(self):
        self.assertEqual(_strip_noise(42, "xyz"), 42)

    def test_trailing_infix_bug_case(self):
        self.assertEqual(_strip_noise("name-dev-", "dev"), "name")

    def test_noise_inside_word_no_dash(self):
        self.assertEqual(_strip_noise("developer", "dev"), "developer")

    def test_word_equals_noise(self):
        self.assertEqual(_strip_noise("dev", "dev"), "")


class TestNoiseDeepEq(unittest.TestCase):

    def test_strings_equal_after_noise(self):
        self.assertTrue(_noise_deep_eq("hello-xyz", "hello", "xyz"))

    def test_strings_different_after_noise(self):
        self.assertFalse(_noise_deep_eq("hello-xyz", "world", "xyz"))

    def test_dicts_keys_with_noise(self):
        self.assertTrue(_noise_deep_eq({"xyz-a": 1}, {"a": 1}, "xyz"))

    def test_dicts_key_noise_value_diff(self):
        self.assertFalse(_noise_deep_eq({"xyz-a": 1}, {"a": 2}, "xyz"))

    def test_dicts_extra_noise_key(self):
        self.assertFalse(_noise_deep_eq({"a": 1, "xyz-b": 2}, {"a": 1}, "xyz"))

    def test_lists_with_noise_items(self):
        self.assertTrue(_noise_deep_eq(["a-xyz", "b"], ["a", "b"], "xyz"))

    def test_nested_dicts(self):
        self.assertTrue(
            _noise_deep_eq({"a": {"xyz-b": 1}}, {"a": {"b": 1}}, "xyz")
        )

    def test_nested_lists(self):
        self.assertTrue(
            _noise_deep_eq(
                {"items": ["a-xyz", "b-xyz"]}, {"items": ["a", "b"]}, "xyz"
            )
        )

    def test_type_mismatch(self):
        self.assertFalse(_noise_deep_eq(1, "1", "xyz"))

    def test_different_types(self):
        self.assertFalse(_noise_deep_eq([], {}, "xyz"))

    def test_no_noise_arg(self):
        self.assertTrue(_noise_deep_eq("hello", "hello", None))
        self.assertFalse(_noise_deep_eq("hello", "world", None))

    def test_trailing_infix(self):
        self.assertTrue(
            _noise_deep_eq({"name-dev-": "alice-dev"}, {"name": "alice"}, "dev")
        )


class TestNormPath(unittest.TestCase):

    def test_normalize_path(self):
        self.assertEqual(
            _norm_path(Path("xyz-sub/info.json"), "xyz"),
            Path("sub/info.json"),
        )

    def test_normalize_path_no_noise(self):
        p = Path("sub/info.json")
        self.assertEqual(_norm_path(p, "xyz"), p)


class TestJsonTreeDiff(unittest.TestCase):

    def test_no_diff(self):
        a = {"name": "alice", "age": 30}
        b = {"name": "alice", "age": 30}
        self.assertEqual(json_tree_diff(a, b), [])

    def test_type_mismatch(self):
        lines = json_tree_diff({"a": 1}, {"a": "1"})
        self.assertEqual(len(lines), 1)
        self.assertIn("→", lines[0])

    def test_added_key(self):
        lines = json_tree_diff({"a": 1}, {"a": 1, "b": 2})
        self.assertTrue(any("+ b" in line for line in lines))

    def test_removed_key(self):
        lines = json_tree_diff({"a": 1, "b": 2}, {"a": 1})
        self.assertTrue(any("- b" in line for line in lines))

    def test_changed_value(self):
        lines = json_tree_diff({"a": 1}, {"a": 2})
        self.assertTrue(any("1" in line and "2" in line for line in lines))

    def test_noise_matches_keys(self):
        lines = json_tree_diff(
            {"name-dev-": "alice", "age": 30},
            {"name": "alice", "age": 30},
            "dev",
        )
        self.assertEqual(lines, [])

    def test_noise_matches_values(self):
        lines = json_tree_diff(
            {"greeting": "hello-dev"},
            {"greeting": "hello"},
            "dev",
        )
        self.assertEqual(lines, [])

    def test_noise_matches_list_items(self):
        lines = json_tree_diff(
            {"tags": ["a-dev", "b"]},
            {"tags": ["a", "b"]},
            "dev",
        )
        self.assertEqual(lines, [])

    def test_noise_infix_at_end(self):
        lines = json_tree_diff(
            {"key-dev-": 1, "other": "val-dev"},
            {"key": 1, "other": "val"},
            "dev",
        )
        self.assertEqual(lines, [])

    def test_real_diff_persists_with_noise(self):
        lines = json_tree_diff(
            {"real": 100, "xyz-same": "x"},
            {"real": 200, "same": "x"},
            "xyz",
        )
        self.assertTrue(any("real" in line for line in lines))

    def test_no_noise_arg(self):
        lines = json_tree_diff({"a": 1}, {"a": 2})
        self.assertEqual(len(lines), 1)

    def test_nested_dict_with_noise(self):
        lines = json_tree_diff(
            {"config": {"timeout-dev": 30, "enabled": True}},
            {"config": {"timeout": 30, "enabled": True}},
            "dev",
        )
        self.assertEqual(lines, [])

    def test_nested_dict_real_diff(self):
        lines = json_tree_diff(
            {"config": {"timeout-dev": 30, "enabled": False}},
            {"config": {"timeout": 30, "enabled": True}},
            "dev",
        )
        self.assertTrue(any("enabled" in line for line in lines))


class TestCompareDirsIntegration(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dir_a = self.tmp / "a"
        self.dir_b = self.tmp / "b"
        self.dir_a.mkdir()
        self.dir_b.mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def _write(self, base, path, data):
        f = base / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data))

    def test_identical_dirs(self):
        self._write(self.dir_a, "f.json", {"a": 1})
        self._write(self.dir_b, "f.json", {"a": 1})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b))
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("fully matched", output)

    def test_file_only_in_a(self):
        self._write(self.dir_a, "only.json", {"a": 1})
        self._write(self.dir_b, "f.json", {"a": 1})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b))
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("mismatches found", output)
        self.assertIn("Only in", output)

    def test_noise_eliminates_dir_diff(self):
        self._write(self.dir_a, "xyz-f.json", {"a": 1})
        self._write(self.dir_b, "f.json", {"a": 1})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b), "xyz")
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("fully matched", output)

    def test_noise_eliminates_subdir_diff(self):
        (self.dir_a / "xyz-sub").mkdir()
        self._write(self.dir_a, "xyz-sub/f.json", {"a": 1})
        (self.dir_b / "sub").mkdir()
        self._write(self.dir_b, "sub/f.json", {"a": 1})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b), "xyz")
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("fully matched", output)

    def test_trailing_infix_integration(self):
        self._write(self.dir_a, "f.json", {"name-dev-": "alice-dev"})
        self._write(self.dir_b, "f.json", {"name": "alice"})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b), "dev")
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("fully matched", output)

    def test_real_diff_persists_integration(self):
        self._write(self.dir_a, "f.json", {"real": 100, "xyz-extra": "x"})
        self._write(self.dir_b, "f.json", {"real": 200, "extra": "x"})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b), "xyz")
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("mismatches found", output)
        self.assertIn("real", output)

    def test_no_noise_arg_integration(self):
        self._write(self.dir_a, "f.json", {"a": 1})
        self._write(self.dir_b, "f.json", {"a": 2})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b))
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("mismatches found", output)
        self.assertIn("a", output)

    def test_list_diff_with_noise(self):
        self._write(self.dir_a, "f.json", {"items": ["a-xyz", "b"]})
        self._write(self.dir_b, "f.json", {"items": ["a", "b"]})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b), "xyz")
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("fully matched", output)

    def test_git_ignored(self):
        (self.dir_a / ".git").mkdir()
        self._write(self.dir_a, ".git/config", {"ignore": "me"})
        self._write(self.dir_a, "f.json", {"a": 1})
        self._write(self.dir_b, "f.json", {"a": 1})
        with tempfile.TemporaryFile("w+") as buf:
            import sys
            old = sys.stdout
            sys.stdout = buf
            try:
                compare_dirs(str(self.dir_a), str(self.dir_b))
                buf.seek(0)
                output = buf.read()
            finally:
                sys.stdout = old
        self.assertIn("fully matched", output)


class TestWalkAll(unittest.TestCase):

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def test_yields_files_and_dirs(self):
        (self.tmp / "sub").mkdir()
        (self.tmp / "sub" / "f.json").write_text("{}")
        (self.tmp / "f.json").write_text("{}")
        results = list(walk_all(self.tmp))
        results_str = {str(p) for p in results}
        self.assertIn("f.json", results_str)
        self.assertIn("sub/f.json", results_str)

    def test_skips_git(self):
        (self.tmp / ".git").mkdir()
        (self.tmp / ".git" / "config").write_text("")
        (self.tmp / "f.json").write_text("{}")
        results = list(walk_all(self.tmp))
        results_str = {str(p) for p in results}
        self.assertNotIn(".git", results_str)
        self.assertNotIn(".git/config", results_str)
        self.assertIn("f.json", results_str)


if __name__ == "__main__":
    unittest.main()

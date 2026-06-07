"""Tool implementations."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from wire0 import tools


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_cwd = Path.cwd()
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        tools.set_root(self.root)
        (self.root / "hello.txt").write_text("hello world\nline two\n", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "other.py").write_text("def foo():\n    return 1\n", encoding="utf-8")

    def tearDown(self) -> None:
        os.chdir(self._orig_cwd)
        tools.set_root(self._orig_cwd)
        self.tmp.cleanup()

    def test_grep_finds_match(self) -> None:
        out = tools.grep("foo", paths=["."])
        self.assertIn("other.py", out)
        self.assertIn("def foo", out)

    def test_list_dir(self) -> None:
        out = tools.list_dir(paths=["."])
        self.assertIn("hello.txt", out)
        self.assertIn("sub", out)

    def test_read_file(self) -> None:
        out = tools.read_file(paths=["hello.txt"])
        self.assertIn("hello world", out)
        self.assertIn("1|", out)

    def test_patch_file(self) -> None:
        out = tools.patch_file(path="hello.txt", old="hello world", new="hi world")
        self.assertIn("Patched", out)
        self.assertEqual((self.root / "hello.txt").read_text(encoding="utf-8"), "hi world\nline two\n")

    def test_write_and_delete(self) -> None:
        w = tools.write_file(path="new.txt", content="new file")
        self.assertIn("Wrote", w)
        self.assertTrue((self.root / "new.txt").exists())
        d = tools.delete_path(paths=["new.txt"])
        self.assertIn("Deleted", d)
        self.assertFalse((self.root / "new.txt").exists())


if __name__ == "__main__":
    unittest.main()
